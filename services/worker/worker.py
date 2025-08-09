import redis
import os
import time

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_CHANNEL = os.getenv("REDIS_CHANNEL", "patient_events")

def main():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    # Subscribe to the channel
    pubsub = r.pubsub()
    pubsub.subscribe(REDIS_CHANNEL)

    print(f"Worker subscribed to channel '{REDIS_CHANNEL}' on {REDIS_HOST}:{REDIS_PORT}", flush=True)

    # Keep processing messages forever
    for message in pubsub.listen():
        if message["type"] == "message":
            print(f"[WORKER] Received: {message['data']}", flush=True)
        elif message["type"] == "subscribe":
            print(f"[WORKER] Subscribed successfully to '{REDIS_CHANNEL}'", flush=True)

if __name__ == "__main__":
    while True:
        try:
            main()
        except redis.exceptions.ConnectionError as e:
            print(f"[WORKER] Redis connection error: {e}. Retrying in 5 seconds...", flush=True)
            time.sleep(5)
