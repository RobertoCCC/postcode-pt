from httpx import AsyncClient


async def test_lookup_returns_full_hierarchy(client: AsyncClient) -> None:
    response = await client.get("/v1/postal-codes/1100-038")
    assert response.status_code == 200

    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1

    entry = body[0]
    assert entry["code"] == "1100-038"
    assert entry["designation"] == "LISBOA"
    assert entry["street"] == {"type": "Rua", "name": "do Arsenal"}
    assert entry["locality"] == {"code": "10123", "name": "LISBOA"}
    assert entry["municipality"] == {"code": "1106", "name": "Lisboa"}
    assert entry["district"] == {"code": "11", "name": "Lisboa"}


async def test_lookup_returns_multiple_entries_for_same_code(client: AsyncClient) -> None:
    response = await client.get("/v1/postal-codes/1100-039")
    assert response.status_code == 200

    body = response.json()
    assert len(body) == 2
    streets = {(e["street"]["type"], e["street"]["name"]) for e in body}
    assert streets == {("Rua", "da Alfândega"), ("Praça", "do Comércio")}


async def test_lookup_with_null_street_fields(client: AsyncClient) -> None:
    response = await client.get("/v1/postal-codes/2710-001")
    assert response.status_code == 200
    body = response.json()
    assert body[0]["street"] == {"type": None, "name": None}


async def test_lookup_unknown_code_returns_404(client: AsyncClient) -> None:
    response = await client.get("/v1/postal-codes/9999-999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Postal code 9999-999 not found"


async def test_invalid_cp4_format_returns_422(client: AsyncClient) -> None:
    response = await client.get("/v1/postal-codes/abc-038")
    assert response.status_code == 422


async def test_invalid_cp3_format_returns_422(client: AsyncClient) -> None:
    response = await client.get("/v1/postal-codes/1100-12")
    assert response.status_code == 422
