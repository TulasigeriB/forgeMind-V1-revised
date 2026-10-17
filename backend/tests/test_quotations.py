from test_auth_customers import make_client, register


def test_quotation_costing_and_organization_scope():
    client, engine = make_client()
    try:
        auth = register(client, "Quote Org", "quote@example.com")
        headers = {"Authorization": f"Bearer {auth['access_token']}"}
        customer = client.post("/customers", headers=headers, json={"name": "Acme Manufacturing"})
        assert customer.status_code == 201, customer.text
        rfq = client.post("/rfqs", headers=headers, json={
            "customer_id": customer.json()["id"], "reference": "RFQ-100", "title": "Machined bracket", "quantity": 10,
        })
        assert rfq.status_code == 201, rfq.text
        payload = {
            "rfq_id": rfq.json()["id"], "reference": "QUO-100", "revision": 1,
            "currency": "INR", "status": "Draft", "line_items": [{
                "description": "Aluminium bracket", "quantity": 10, "unit": "pcs",
                "material_unit_cost": 20, "labor_unit_cost": 5, "overhead_unit_cost": 2,
                "unit_selling_price": 40,
            }],
        }
        created = client.post("/quotations", headers=headers, json=payload)
        assert created.status_code == 201, created.text
        result = created.json()
        assert result["customer_name"] == "Acme Manufacturing"
        assert result["material_cost"] == "200.00"
        assert result["labor_cost"] == "50.00"
        assert result["overhead_cost"] == "20.00"
        assert result["total_cost"] == "270.00"
        assert result["selling_price"] == "400.00"
        assert result["gross_margin_percent"] == "32.500"
        assert client.get("/quotations", headers=headers).json()[0]["reference"] == "QUO-100"
        other = register(client, "Other Org", "otherquote@example.com")
        other_headers = {"Authorization": f"Bearer {other['access_token']}"}
        assert client.get("/quotations", headers=other_headers).json() == []
        assert client.get(f"/quotations/{result['id']}", headers=other_headers).status_code == 404
    finally:
        client.close()
        engine.dispose()
