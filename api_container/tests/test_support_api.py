import pytest
from fastapi.testclient import TestClient
import os
import sys

# Run with the following command:
# pytest SupportService/api_container/tests/test_support_api.py

# Set the TESTING environment variable
os.environ['TESTING'] = '1'

# Set a default DATABASE_URL for testing
os.environ['DATABASE_URL'] = 'sqlite:///test.db'

# Add the necessary paths to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lib')))
from SupportService.api_container.support_api import app, reports_manager, help_tks_manager

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_database():
    reports_manager.create_table()
    session = reports_manager.Session()
    session.query(reports_manager.reports).delete()
    session.commit()
    session.close()

def test_report_account():
    response = client.put("/accounts/test_user", json={
        "title": "Test Title",
        "description": "Test Description",
        "complainant": "test_user"
    })
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "report_id" in response.json()

def test_report_account_missing_fields():
    response = client.put("/accounts/test_user", json={
        "title": "Test Title",
        "description": "Test Description"
    })
    assert response.status_code == 400
    assert "Missing fields" in response.json()["detail"]

def test_report_service():
    response = client.put("/services/test_service", json={
        "title": "Test Title",
        "description": "Test Description",
        "complainant": "test_user"
    })
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "report_id" in response.json()

def test_report_service_missing_fields():
    response = client.put("/services/test_service", json={
        "title": "Test Title",
        "description": "Test Description"
    })
    assert response.status_code == 400
    assert "Missing fields" in response.json()["detail"]

def test_get_account_reports():
    client.put("/accounts/test_user", json={
        "title": "Test Title",
        "description": "Test Description",
        "complainant": "test_user"
    })
    response = client.get("/accounts/test_user")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Test Title"

def test_get_account_reports_not_found():
    response = client.get("/accounts/non_existent_user")
    assert response.status_code == 404
    assert response.json()["detail"] == "Reports not found"

def test_get_service_reports():
    client.put("/services/test_service", json={
        "title": "Test Title",
        "description": "Test Description",
        "complainant": "test_user"
    })
    response = client.get("/services/test_service")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Test Title"

def test_get_service_reports_not_found():
    response = client.get("/services/non_existent_service")
    assert response.status_code == 404
    assert response.json()["detail"] == "Reports not found"