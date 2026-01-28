from httpx import AsyncClient


async def test_list_districts(client: AsyncClient) -> None:
    response = await client.get("/v1/districts")
    assert response.status_code == 200

    body = response.json()
    assert body == [
        {"code": "11", "name": "Lisboa"},
        {"code": "13", "name": "Porto"},
    ]


async def test_list_municipalities_in_district(client: AsyncClient) -> None:
    response = await client.get("/v1/districts/11/municipalities")
    assert response.status_code == 200

    body = response.json()
    # Ordered by name: Lisboa, Sintra
    assert [m["code"] for m in body] == ["1106", "1111"]
    assert all(m["district"] == {"code": "11", "name": "Lisboa"} for m in body)


async def test_list_municipalities_unknown_district_returns_404(
    client: AsyncClient,
) -> None:
    response = await client.get("/v1/districts/99/municipalities")
    assert response.status_code == 404
    assert response.json()["detail"] == "District 99 not found"


async def test_list_municipalities_invalid_code_format_returns_422(
    client: AsyncClient,
) -> None:
    response = await client.get("/v1/districts/abc/municipalities")
    assert response.status_code == 422
