import os
from datetime import timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as aioredis

# ===== MongoDB config =====
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "clinic_db")

mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client[MONGO_DB_NAME]
patients_collection = db["patients"]
counters_collection = db["counters"]
users_collection = db["users"]

# ===== Redis config =====
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_CHANNEL = os.getenv("REDIS_CHANNEL", "patient_events")
redis_client = aioredis.from_url(
    f"redis://{REDIS_HOST}:{REDIS_PORT}",
    decode_responses=True
)

# ===== JWT config =====
SECRET_KEY = os.getenv("JWT_SECRET", "change_this_secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
ACCESS_TOKEN_EXPIRE_DELTA = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
