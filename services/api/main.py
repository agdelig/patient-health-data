import json
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pymongo import ReturnDocument

from config import (
    patients_collection, counters_collection, users_collection,
    redis_client, ACCESS_TOKEN_EXPIRE_DELTA, REDIS_CHANNEL
)
from auth import (
    authenticate_user, create_access_token, get_password_hash, get_current_user
)
from models.objects import PatientRecord, UserCreate, UserResponse

app = FastAPI(title="Patient Health Data API", version="1.0")

# ===== Helpers =====
async def get_next_sequence(name: str) -> int:
    result = await counters_collection.find_one_and_update(
        {"_id": name},
        {"$inc": {"sequence_value": 1}},
        return_document=ReturnDocument.AFTER,
        upsert=True
    )
    return result["sequence_value"]

# ===== Security endpoints =====
@app.post(
    "/register",
    response_model=UserResponse,
    tags=["security"],
    responses={
        400: {"description": "Username already exists"},
        500: {"description": "Internal Server Error"}
    }
)
async def register_user(user: UserCreate):
    if await users_collection.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed_pw = get_password_hash(user.password)
    await users_collection.insert_one({"username": user.username, "hashed_password": hashed_pw})
    return UserResponse(username=user.username, message="User created successfully")

@app.post(
    "/token",
    tags=["security"],
    responses={
        401: {"description": "Incorrect username or password"},
        500: {"description": "Internal Server Error"}
    }
)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    token = create_access_token({"sub": user["username"]}, expires_delta=ACCESS_TOKEN_EXPIRE_DELTA)
    return {"access_token": token, "token_type": "bearer"}

# ===== Patient endpoints =====
@app.post(
    "/evaluate",
    tags=["patients"],
    responses={
        201: {"description": "Recommendation created successfully"},
        500: {"description": "Internal Server Error"}
    }
)
async def evaluate_patient(patient: PatientRecord, current_user: dict = Depends(get_current_user)):
    patient_id = await get_next_sequence("patient_id")
    patient_doc = patient.as_dict(patient_id)
    insert_result = await patients_collection.insert_one(patient_doc)
    saved_doc = await patients_collection.find_one({"_id": insert_result.inserted_id}, {"_id": 0})

    event = {
        "patient_id": patient_id,
        "recommendation_id": f"rec-{patient_id}",
        "recommendation": patient_doc["recommendation"],
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    await redis_client.publish(REDIS_CHANNEL, json.dumps(event))

    return saved_doc

@app.get(
    "/recommendation/{patient_id}",
    tags=["patients"],
    responses={
        200: {"description": "Recommendation retrieved successfully"},
        404: {"description": "Patient not found"},
        500: {"description": "Internal Server Error"}
    }
)
async def get_recommendation(patient_id: int, current_user: dict = Depends(get_current_user)):
    cached = await redis_client.get(f"recommendation:{patient_id}")
    if cached:
        return json.loads(cached)

    doc = await patients_collection.find_one({"patient_id": patient_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Patient not found")
    result = {
        "patient_id": doc["patient_id"],
        "recommendation": doc["recommendation"]
    }
    await redis_client.setex(f"recommendation:{patient_id}", 3600, json.dumps(result))
    return result

@app.get(
    "/patients",
    tags=["patients"],
    responses={
        200: {"description": "List of patients retrieved successfully"},
        500: {"description": "Internal Server Error"}
    }
)
async def list_patients(current_user: dict = Depends(get_current_user)):
    patients = []
    async for doc in patients_collection.find({}, {"_id": 0}):
        patients.append(doc)
    return patients
