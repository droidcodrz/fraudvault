import os
import uuid
from pathlib import Path

import aioboto3
from botocore.config import Config

from app.config import get_settings

settings = get_settings()


def _local_path(storage_key: str) -> Path:
    base = Path(settings.local_storage_dir)
    path = base / storage_key
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


async def upload_file(storage_key: str, file_obj, content_type: str | None = None) -> str:
    if settings.use_local_storage:
        path = _local_path(storage_key)
        if hasattr(file_obj, "read"):
            content = file_obj.read()
            if hasattr(content, "__await__"):
                content = await content
        else:
            content = file_obj
        path.write_bytes(content if isinstance(content, bytes) else bytes(content))
        return storage_key

    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=Config(signature_version="s3v4"),
    ) as client:
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type
        await client.upload_fileobj(file_obj, settings.r2_bucket_name, storage_key, ExtraArgs=extra_args)
    return storage_key


async def upload_bytes(storage_key: str, data: bytes, content_type: str | None = None) -> str:
    if settings.use_local_storage:
        path = _local_path(storage_key)
        path.write_bytes(data)
        return storage_key

    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=Config(signature_version="s3v4"),
    ) as client:
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type
        await client.put_object(Bucket=settings.r2_bucket_name, Key=storage_key, Body=data, **extra_args)
    return storage_key


async def download_file(storage_key: str) -> bytes:
    if settings.use_local_storage:
        path = _local_path(storage_key)
        return path.read_bytes()

    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=Config(signature_version="s3v4"),
    ) as client:
        response = await client.get_object(Bucket=settings.r2_bucket_name, Key=storage_key)
        async with response["Body"] as stream:
            return await stream.read()


async def get_presigned_url(storage_key: str, expires_in: int = 3600) -> str:
    if settings.use_local_storage:
        return f"file://{os.path.abspath(_local_path(storage_key))}"

    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=Config(signature_version="s3v4"),
    ) as client:
        url = await client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.r2_bucket_name, "Key": storage_key},
            ExpiresIn=expires_in,
        )
        return url


def build_upload_key(user_id: uuid.UUID, job_id: uuid.UUID, filename: str) -> str:
    return f"uploads/{user_id}/{job_id}/{filename}"


def build_heatmap_key(job_id: uuid.UUID) -> str:
    return f"heatmaps/{job_id}.png"
