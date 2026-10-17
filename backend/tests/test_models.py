from app.db.base import Base


def test_metadata_contains_expected_tables_and_constraints():
    assert set(Base.metadata.tables) == {
        "organizations", "users", "audit_events", "customers", "rfqs"
    }
    users = Base.metadata.tables["users"]
    assert any(constraint.name == "uq_users_org_email" for constraint in users.constraints)
    assert "organization_id" in users.c
    assert users.c.organization_id.foreign_keys

    customers = Base.metadata.tables["customers"]
    assert "organization_id" in customers.c
    assert customers.c.organization_id.foreign_keys
    assert any(constraint.name == "uq_customers_org_name" for constraint in customers.constraints)

    rfqs = Base.metadata.tables["rfqs"]
    assert rfqs.c.organization_id.foreign_keys
    assert rfqs.c.customer_id.foreign_keys
    assert any(constraint.name == "uq_rfqs_org_reference" for constraint in rfqs.constraints)
