import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from main import app, get_current_user

@pytest.fixture
def anyio_backend():
    return 'asyncio'

mock_user = {"username": "testuser"}

mock_patient_doc = {
    "patient_id": 1,
    "age": 70,
    "chronic_pain": True,
    "recommendation": "Physical Therapy"
}

@pytest.mark.anyio
@patch("main.users_collection.find_one", new_callable=AsyncMock)
@patch("main.users_collection.insert_one", new_callable=AsyncMock)
@patch("main.get_password_hash")
async def test_register_user_success(mock_hash, mock_insert, mock_find):
    mock_find.return_value = None
    mock_hash.return_value = "hashedpw"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/register", json={"username": "newuser", "password": "pass"})
    assert response.status_code == 200
    assert response.json()["username"] == "newuser"

@pytest.mark.anyio
@patch("main.users_collection.find_one", new_callable=AsyncMock)
async def test_register_user_already_exists(mock_find_one):
    mock_find_one.return_value = {"username": "existinguser"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/register", json={"username": "existinguser", "password": "pass"})
    assert response.status_code == 400
    assert "already exists" in response.text

@pytest.mark.anyio
@patch("main.authenticate_user", new_callable=AsyncMock)
@patch("main.create_access_token")
async def test_login_success(mock_create_token, mock_authenticate):
    mock_authenticate.return_value = mock_user
    mock_create_token.return_value = "token123"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/token", data={"username": "testuser", "password": "pass"})
    assert response.status_code == 200
    assert response.json()["access_token"] == "token123"

@pytest.mark.anyio
@patch("main.authenticate_user", new_callable=AsyncMock)
async def test_login_invalid_credentials(mock_authenticate):
    mock_authenticate.return_value = None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/token", data={"username": "wronguser", "password": "wrongpass"})
    assert response.status_code == 401
    assert "Incorrect username or password" in response.text

@pytest.mark.asyncio
@patch("main.get_next_sequence", new_callable=AsyncMock)
@patch("main.patients_collection.insert_one", new_callable=AsyncMock)
@patch("main.patients_collection.find_one", new_callable=AsyncMock)  # <-- Add this patch
@patch("main.redis_client.publish", new_callable=AsyncMock)
async def test_evaluate_patient_success(mock_redis_pub, mock_find_one, mock_insert, mock_sequence):
    # Arrange: mock returned values
    async def fake_get_current_user():
        return mock_user
    app.dependency_overrides[get_current_user] = fake_get_current_user

    mock_sequence.return_value = 1
    mock_redis_pub.return_value = 1
    mock_insert.return_value.inserted_id = 123  # Mock inserted_id for find_one filter
    mock_find_one.return_value = mock_patient_doc  # Mock the document find_one returns

    patient_data = {
        "age": 70,
        "height": 1.75,
        "weight": 85.0,
        "resent_surgery": False,
        "chronic_pain": True
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Authorization": "Bearer dummy_token"}
        response = await ac.post("/evaluate", json=patient_data, headers=headers)

    # Assertions
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["patient_id"] == 1
    assert "recommendation" in json_data

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_evaluate_patient_unauthorized():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        patient_data = {
            "age": 70,
            "height": 1.75,
            "weight": 85.0,
            "resent_surgery": False,
            "chronic_pain": True
        }
        response = await ac.post("/evaluate", json=patient_data)
    assert response.status_code == 401

@pytest.mark.anyio
@patch("main.redis_client.get", new_callable=AsyncMock)
@patch("main.patients_collection.find_one", new_callable=AsyncMock)
@patch("main.redis_client.setex", new_callable=AsyncMock)
async def test_get_recommendation_cache_miss(mock_redis_setex, mock_find_one, mock_redis_get):
    async def fake_get_current_user():
        return mock_user
    app.dependency_overrides[get_current_user] = fake_get_current_user

    mock_redis_get.return_value = None
    mock_find_one.return_value = mock_patient_doc

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Authorization": "Bearer dummy_token"}
        response = await ac.get("/recommendation/1", headers=headers)

    assert response.status_code == 200
    assert response.json()["recommendation"] == "Physical Therapy"
    mock_redis_setex.assert_called_once()

    app.dependency_overrides.clear()

@pytest.mark.anyio
@patch("main.redis_client.get", new_callable=AsyncMock)
async def test_get_recommendation_cache_hit(mock_redis_get):
    async def fake_get_current_user():
        return mock_user
    app.dependency_overrides[get_current_user] = fake_get_current_user

    mock_redis_get.return_value = '{"patient_id": 1, "recommendation": "Physical Therapy"}'

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Authorization": "Bearer dummy_token"}
        response = await ac.get("/recommendation/1", headers=headers)

    assert response.status_code == 200
    assert response.json()["recommendation"] == "Physical Therapy"

    app.dependency_overrides.clear()

@pytest.mark.anyio
@patch("main.redis_client.get", new_callable=AsyncMock)
@patch("main.patients_collection.find_one", new_callable=AsyncMock)
async def test_get_recommendation_not_found(mock_find_one, mock_redis_get):
    async def fake_get_current_user():
        return mock_user
    app.dependency_overrides[get_current_user] = fake_get_current_user

    mock_redis_get.return_value = None
    mock_find_one.return_value = None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Authorization": "Bearer dummy_token"}
        response = await ac.get("/recommendation/999", headers=headers)

    assert response.status_code == 404

    app.dependency_overrides.clear()

@pytest.mark.anyio
async def test_get_recommendation_unauthorized():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/recommendation/1")
    assert response.status_code == 401

class AsyncIterator:
    def __init__(self, items):
        self._items = items
    def __aiter__(self):
        self._iter = iter(self._items)
        return self
    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration

@pytest.mark.anyio
@patch("main.patients_collection.find")
async def test_list_patients_success(mock_find):
    async def fake_get_current_user():
        return {"username": "testuser"}

    app.dependency_overrides[get_current_user] = fake_get_current_user

    mock_find.return_value = AsyncIterator([
        {"patient_id": 1, "recommendation": "Physical Therapy"},
        {"patient_id": 2, "recommendation": "Weight Management Program"},
    ])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Authorization": "Bearer dummy_token"}
        response = await ac.get("/patients", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["patient_id"] == 1
    assert data[1]["recommendation"] == "Weight Management Program"

    app.dependency_overrides.clear()

@pytest.mark.anyio
async def test_list_patients_unauthorized():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/patients")
    assert response.status_code == 401

