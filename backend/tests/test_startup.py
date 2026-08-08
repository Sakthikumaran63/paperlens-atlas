import pytest
from app.main import app


def test_fastapi_app_instantiation():
    assert app.title == "paperlens-backend"
    assert app.openapi_url == "/api/v1/openapi.json"
