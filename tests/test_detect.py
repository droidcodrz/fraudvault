import pytest


@pytest.mark.asyncio
async def test_detect_clean_image(client, auth_headers, clean_jpeg_bytes):
    response = await client.post(
        "/v1/detect",
        headers=auth_headers,
        files={"file": ("clean.jpg", clean_jpeg_bytes, "image/jpeg")},
        data={"async_mode": "false"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["verdict"] in ("authentic", "inconclusive")


@pytest.mark.asyncio
async def test_detect_tampered_image(client, auth_headers, tampered_jpeg_bytes):
    response = await client.post(
        "/v1/detect",
        headers=auth_headers,
        files={"file": ("tampered.jpg", tampered_jpeg_bytes, "image/jpeg")},
        data={"async_mode": "false"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["verdict"] == "tampered"
    assert data["risk_score"] > 0


@pytest.mark.asyncio
async def test_detect_invalid_file_type(client, auth_headers):
    response = await client.post(
        "/v1/detect",
        headers=auth_headers,
        files={"file": ("test.txt", b"hello", "text/plain")},
        data={"async_mode": "false"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_FILE_TYPE"
