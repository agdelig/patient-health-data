import os
from fastapi import FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from models.objects import PatientRecord
from pymongo import ReturnDocument


app = FastAPI()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "clinic_db")

client = AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB_NAME]
patients_collection = db["patients"]
counters_collection = db["counters"]

async def get_next_sequence(name: str) -> int:
    result = await counters_collection.find_one_and_update(
        {"_id": name},
        {"$inc": {"sequence_value": 1}},
        return_document=ReturnDocument.AFTER,
        upsert=True
    )
    return result["sequence_value"]


@app.post("/evaluate", summary="Evaluate patient and return clinical recommendation")
async def evaluate_patient(patient: PatientRecord):
    # Store patient in Mongo
    patient_id = await get_next_sequence("patient_id")
    result = await patients_collection.insert_one(patient.as_dict(patient_id))

    stored = patient.as_dict(patient_id)
    stored["_id"] = str(result.inserted_id)
    return stored


@app.get("/recommendation/{patient_id}", summary="Get stored recommendation by patient ID")
async def get_recommendation(patient_id: int):
    doc = await patients_collection.find_one({"patient_id": patient_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {
        "patient_id": doc["patient_id"],
        "recommendation": doc["recommendation"]
    }
