import pytest


@pytest.mark.asyncio
async def test_create_and_use_api_key(client, auth_headers, clean_jpeg_bytes):
    key_resp = await client.post(
        "/v1/keys",
        headers=auth_headers,
        json={"name": "Test Key", "environment": "test"},
    )
    assert key_resp.status_code == 201
    raw_key = key_resp.json()["key"]
    assert raw_key.startswith("fv_test_")

    detect_resp = await client.post(
        "/v1/detect",
        headers={"X-API-Key": raw_key},
        files={"file": ("clean.jpg", clean_jpeg_bytes, "image/jpeg")},
        data={"async_mode": "false"},
    )
    assert detect_resp.status_code == 200
    assert detect_resp.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_list_keys(client, auth_headers):
    await client.post(
        "/v1/keys",
        headers=auth_headers,
        json={"name": "List Test Key"},
    )
    list_resp = await client.get("/v1/keys", headers=auth_headers)
    assert list_resp.status_code == 200
    keys = list_resp.json()
    assert len(keys) >= 1
    assert "prefix" in keys[0]
    assert "key" not in keys[0]
