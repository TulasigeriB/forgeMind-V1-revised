from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app


def make_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), engine


def register(client, organization, email):
    response = client.post("/auth/register", json={
        "organization_name": organization,
        "email": email,
        "password": "correct-horse-battery",
        "default_currency": "INR",
    })
    assert response.status_code == 201, response.text
    return response.json()


def teardown(client, engine):
    client.close()
    app.dependency_overrides.clear()
    engine.dispose()


def test_register_login_and_me():
    client, engine = make_client()
    try:
        registered = register(client, "Acme Manufacturing", "owner@acme.example")
        assert registered["user"]["role"] == "owner"
        token = registered["access_token"]
        me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["email"] == "owner@acme.example"

        login = client.post("/auth/login", json={
            "email": "OWNER@ACME.EXAMPLE",
            "password": "correct-horse-battery",
        })
        assert login.status_code == 200
        assert login.json()["user"]["id"] == registered["user"]["id"]
    finally:
        teardown(client, engine)


def test_customers_require_auth_and_are_crud():
    client, engine = make_client()
    try:
        registered = register(client, "Acme Manufacturing", "owner@acme.example")
        headers = {"Authorization": f"Bearer {registered['access_token']}"}
        assert client.get("/customers").status_code == 401

        created = client.post("/customers", headers=headers, json={
            "name": "  Precision Components  ",
            "email": "SALES@EXAMPLE.COM",
            "contact_name": "Sam",
        })
        assert created.status_code == 201, created.text
        customer = created.json()
        assert customer["name"] == "Precision Components"
        assert customer["email"] == "sales@example.com"

        listed = client.get("/customers", headers=headers)
        assert listed.status_code == 200
        assert len(listed.json()) == 1

        updated = client.patch(f"/customers/{customer['id']}", headers=headers, json={
            "name": "Precision Components",
            "email": "sales@example.com",
            "contact_name": "Alex",
            "phone": None,
            "address": None,
            "notes": "Updated contact",
        })
        assert updated.status_code == 200
        assert updated.json()["contact_name"] == "Alex"

        deleted = client.delete(f"/customers/{customer['id']}", headers=headers)
        assert deleted.status_code == 204
        assert client.get(f"/customers/{customer['id']}", headers=headers).status_code == 404
    finally:
        teardown(client, engine)


def test_customer_records_are_isolated_by_organization():
    client, engine = make_client()
    try:
        first = register(client, "First Works", "owner@first.example")
        second = register(client, "Second Works", "owner@second.example")
        first_headers = {"Authorization": f"Bearer {first['access_token']}"}
        second_headers = {"Authorization": f"Bearer {second['access_token']}"}
        created = client.post("/customers", headers=first_headers, json={"name": "Private Customer"})
        assert created.status_code == 201
        customer_id = created.json()["id"]

        assert client.get(f"/customers/{customer_id}", headers=second_headers).status_code == 404
        assert client.get("/customers", headers=second_headers).json() == []
    finally:
        teardown(client, engine)


def test_registration_rejects_duplicate_email():
    client, engine = make_client()
    try:
        register(client, "First Works", "owner@example.com")
        response = client.post("/auth/register", json={
            "organization_name": "Second Works",
            "email": "owner@example.com",
            "password": "correct-horse-battery",
        })
        assert response.status_code == 409
    finally:
        teardown(client, engine)


def test_rfqs_are_crud_and_scoped_to_organization():
    client, engine = make_client()
    try:
        first = register(client, "First Works", "owner@first.example")
        second = register(client, "Second Works", "owner@second.example")
        h1 = {"Authorization": f"Bearer {first['access_token']}"}
        h2 = {"Authorization": f"Bearer {second['access_token']}"}
        customer = client.post("/customers", headers=h1, json={"name": "Precision Customer"}).json()
        payload = {"customer_id": customer["id"], "reference": "RFQ-2026-001", "title": "Housing machining", "description": "CNC machined aluminium housing", "quantity": 250, "due_date": "2026-11-15", "status": "Received", "notes": "Drawing revision A"}
        created = client.post("/rfqs", headers=h1, json=payload)
        assert created.status_code == 201, created.text
        record = created.json()
        assert record["customer_name"] == "Precision Customer"
        assert record["status"] == "Received"
        assert client.get("/rfqs", headers=h1).json()[0]["reference"] == "RFQ-2026-001"
        assert client.get(f"/rfqs/{record['id']}", headers=h2).status_code == 404
        assert client.get("/rfqs", headers=h2).json() == []
        payload["status"] = "Quoting"
        updated = client.patch(f"/rfqs/{record['id']}", headers=h1, json=payload)
        assert updated.status_code == 200 and updated.json()["status"] == "Quoting"
        assert client.delete(f"/rfqs/{record['id']}", headers=h1).status_code == 204
    finally:
        teardown(client, engine)
