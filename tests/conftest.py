import io
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from PIL import Image, ImageDraw
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import create_app


@pytest.fixture
def clean_jpeg_bytes() -> bytes:
    img = Image.new("RGB", (400, 300), color=(200, 220, 240))
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 350, 250], outline=(100, 100, 100), width=2)
    draw.text((120, 140), "Clean Document", fill=(50, 50, 50))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=95)
    return buffer.getvalue()


@pytest.fixture
def tampered_jpeg_bytes(clean_jpeg_bytes) -> bytes:
    """JPEG with a spliced uncompressed patch to produce a strong ELA signal."""
    base = Image.open(io.BytesIO(clean_jpeg_bytes)).convert("RGB")
    overlay = Image.new("RGB", (350, 250))
    pixels = overlay.load()
    for x in range(350):
        for y in range(250):
            pixels[x, y] = ((x * 7 + y * 13) % 256, (x * 3 + y * 11) % 256, (x * 5 + y * 17) % 256)
    base.paste(overlay, (25, 25))
    buffer = io.BytesIO()
    base.save(buffer, format="JPEG", quality=95)
    return buffer.getvalue()


from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.types import TypeDecorator


class GUID(TypeDecorator):
    """SQLite-compatible UUID type for tests."""

    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return uuid.UUID(value)
        return value


def _sqlite_compat_metadata():
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, UUID):
                column.type = GUID()
            elif isinstance(column.type, JSONB):
                column.type = JSON()


@pytest_asyncio.fixture
async def db_session():
    _sqlite_compat_metadata()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict:
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    resp = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": "testpass123", "full_name": "Test User"},
    )
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
