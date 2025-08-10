# Patient Health Data Microservices

Simple microservices app with FastAPI API service, background worker, MongoDB, and Redis.

## Quick Start

1. Clone repo and run:
```
docker compose -f docker_compose.yml up --build
```


2. Open API docs at `http://localhost:8090/docs`

## Running API tests 

Tests can be run using docker compose. 

```
docker compose -f docker_compose.yml run --rm test pytest tests/test_api.py --verbose
```

## API Endpoints

- POST /register — Register user  
- POST /token — Get JWT token  
- POST /evaluate — Submit patient data, get recommendation  
- GET /recommendation/{patient_id} — Get recommendation by ID  
- GET /patients — List all patients

(All patient endpoints require Bearer JWT token.)

## License

MIT
