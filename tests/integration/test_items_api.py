from __future__ import annotations

from fastapi.testclient import TestClient


def create_item(client: TestClient, **overrides: object) -> dict:
    payload = {"name": "Widget", "price_cents": 1500, "quantity": 3}
    payload.update(overrides)
    response = client.post("/api/items", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_item_returns_201_with_generated_id(client: TestClient) -> None:
    body = create_item(client)

    assert body["id"]
    assert body["name"] == "Widget"
    assert body["price_cents"] == 1500


def test_get_item_returns_created_item(client: TestClient) -> None:
    created = create_item(client)

    response = client.get(f"/api/items/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_unknown_item_returns_404(client: TestClient) -> None:
    response = client.get("/api/items/does-not-exist")

    assert response.status_code == 404


def test_list_items_returns_created_items(client: TestClient) -> None:
    create_item(client, name="A")
    create_item(client, name="B")

    response = client.get("/api/items")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


def test_list_items_respects_limit(client: TestClient) -> None:
    for i in range(5):
        create_item(client, name=f"item-{i}")

    response = client.get("/api/items", params={"limit": 2, "offset": 0})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2


def test_delete_item_returns_204_and_removes_it(client: TestClient) -> None:
    created = create_item(client)

    delete_response = client.delete(f"/api/items/{created['id']}")
    get_response = client.get(f"/api/items/{created['id']}")

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


def test_delete_unknown_item_returns_404(client: TestClient) -> None:
    response = client.delete("/api/items/does-not-exist")

    assert response.status_code == 404


# --- Negative / error-path tests -------------------------------------------------


def test_create_item_rejects_blank_name(client: TestClient) -> None:
    response = client.post("/api/items", json={"name": "  ", "price_cents": 100, "quantity": 1})

    assert response.status_code == 422


def test_create_item_rejects_negative_price(client: TestClient) -> None:
    response = client.post("/api/items", json={"name": "Widget", "price_cents": -1, "quantity": 1})

    assert response.status_code == 422


def test_create_item_rejects_negative_quantity(client: TestClient) -> None:
    response = client.post(
        "/api/items", json={"name": "Widget", "price_cents": 100, "quantity": -1}
    )

    assert response.status_code == 422


def test_create_item_rejects_unknown_fields(client: TestClient) -> None:
    response = client.post(
        "/api/items",
        json={"name": "Widget", "price_cents": 100, "quantity": 1, "is_admin": True},
    )

    assert response.status_code == 422


def test_list_items_rejects_limit_above_max(client: TestClient) -> None:
    response = client.get("/api/items", params={"limit": 500})

    assert response.status_code == 422


def test_list_items_rejects_negative_offset(client: TestClient) -> None:
    response = client.get("/api/items", params={"offset": -1})

    assert response.status_code == 422
