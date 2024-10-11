import requests
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "Hello, welcome to the translation API. Navigate to /translate-eng-to-span to get started!"}


def test_translate():
    response = client.post(
        "/translate-eng-to-span",
        json={"text": "hello"}
    )
    assert response.status_code == 200
