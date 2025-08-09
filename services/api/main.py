import os
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from models.objects import PatientRecord
from pymongo import ReturnDocument
import redis.asyncio as aioredis


app = FastAPI()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "clinic_db")

client = AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB_NAME]
patients_collection = db["patients"]
counters_collection = db["counters"]

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_CHANNEL = os.getenv("REDIS_CHANNEL", "patient_events")
redis_client = aioredis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}", decode_responses=True)

CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", 360))

async def get_next_sequence(name: str) -> int:
    result = await counters_collection.find_one_and_update(
        {"_id": name},
        {"$inc": {"sequence_value": 1}},
        return_document=ReturnDocument.AFTER,
        upsert=True
    )
    return result["sequence_value"]


@app.post("/evaluate",
          response_model=PatientRecord,
          summary="Evaluate patient and return clinical recommendation")
async def evaluate_patient(patient: PatientRecord):
    patient_id = await get_next_sequence("patient_id")
    patient_doc = patient.as_dict(patient_id)
    await patients_collection.insert_one(patient_doc)

    # Generate a recommendation event
    event = {
        "patient_id": patient_id,
        "recommendation_id": f"rec-{patient_id}",  # could be a UUID
        "recommendation": patient_doc["recommendation"],
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    await redis_client.publish(REDIS_CHANNEL, json.dumps(event))

    return patient_doc


@app.get("/recommendation/{patient_id}", summary="Get stored recommendation by patient ID")
async def get_recommendation(patient_id: int):
    cache_key = f"recommendation:{patient_id}"

    # Try to get from Redis cache
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # If not cached, fetch from DB
    doc = await patients_collection.find_one({"patient_id": patient_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Patient not found")

    response = {
        "patient_id": doc["patient_id"],
        "recommendation": doc["recommendation"]
    }

    # Cache the response in Redis
    await redis_client.set(cache_key, json.dumps(response), ex=CACHE_TTL_SECONDS)

    return response
