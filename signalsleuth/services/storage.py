"""
Persistent storage for chapter HTML game packages.

Default: local disk under uploads/chapters (fine for a VM with a real volume).
Production on ephemeral hosts (Vercel, Render free, etc.): set S3-compatible env
vars so uploads survive redeploys. If STORAGE_BACKEND is not set but S3_BUCKET
is, the S3 backend is chosen automatically.

Files shipped with the code live in ``games/`` and are always readable as a
fallback (read-only), so built-in games work even on a read-only filesystem.

  STORAGE_BACKEND=local|s3
  S3_BUCKET=
  S3_REGION=auto
  S3_ENDPOINT_URL=   # required for R2, MinIO, Backblaze B2 S3 API, etc.
  S3_ACCESS_KEY=
  S3_SECRET_KEY=
  S3_PREFIX=signalsleuth/games/
"""
from __future__ import annotations

import os

from .. import config

LOCAL_UPLOAD_DIR = config.UPLOAD_DIR   # writable cache / local backend (/tmp on Vercel)
BUNDLED_DIR = config.GAMES_DIR         # read-only files shipped with the code
try:
    LOCAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass


def backend_name() -> str:
    explicit = (os.environ.get("STORAGE_BACKEND") or "").strip().lower()
    if explicit:
        return explicit
    return "s3" if (os.environ.get("S3_BUCKET") or "").strip() else "local"


def _s3_client():
    import boto3
    from botocore.client import Config

    kwargs = {
        "service_name": "s3",
        "aws_access_key_id": os.environ.get("S3_ACCESS_KEY") or os.environ.get("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": os.environ.get("S3_SECRET_KEY") or os.environ.get("AWS_SECRET_ACCESS_KEY"),
        "region_name": os.environ.get("S3_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "auto",
    }
    endpoint = os.environ.get("S3_ENDPOINT_URL") or ""
    if endpoint:
        kwargs["endpoint_url"] = endpoint
        kwargs["config"] = Config(signature_version="s3v4")
    return boto3.client(**kwargs)


def _s3_bucket() -> str:
    return (os.environ.get("S3_BUCKET") or "").strip()


def _s3_key(filename: str) -> str:
    prefix = os.environ.get("S3_PREFIX") or "signalsleuth/games/"
    if not prefix.endswith("/"):
        prefix += "/"
    return prefix + filename.lstrip("/")


def save_game_file(filename: str, stream_or_bytes) -> str:
    """Save uploaded game HTML. Returns stored filename (not full path)."""
    if hasattr(stream_or_bytes, "read"):
        data = stream_or_bytes.read()
    else:
        data = stream_or_bytes
    if isinstance(data, str):
        data = data.encode("utf-8")

    if backend_name() == "s3":
        bucket = _s3_bucket()
        if not bucket:
            raise RuntimeError("STORAGE_BACKEND=s3 but S3_BUCKET is not set")
        client = _s3_client()
        client.put_object(
            Bucket=bucket,
            Key=_s3_key(filename),
            Body=data,
            ContentType="text/html; charset=utf-8",
        )
        # Keep a local cache copy for injection/read performance
        try:
            (LOCAL_UPLOAD_DIR / filename).write_bytes(data)
        except OSError:
            pass
        return filename

    dest = LOCAL_UPLOAD_DIR / filename
    dest.write_bytes(data)
    return filename


def delete_game_file(filename: str) -> None:
    if not filename:
        return
    local = LOCAL_UPLOAD_DIR / filename
    if local.is_file():
        try:
            local.unlink()
        except OSError:
            pass
    if backend_name() == "s3" and _s3_bucket():
        try:
            _s3_client().delete_object(Bucket=_s3_bucket(), Key=_s3_key(filename))
        except Exception:
            pass


def load_game_bytes(filename: str) -> bytes | None:
    """Load game HTML bytes from local cache or object storage."""
    if not filename:
        return None
    local = LOCAL_UPLOAD_DIR / filename
    if local.is_file():
        return local.read_bytes()
    bundled = BUNDLED_DIR / filename
    if bundled.is_file():
        return bundled.read_bytes()
    if backend_name() == "s3" and _s3_bucket():
        try:
            obj = _s3_client().get_object(Bucket=_s3_bucket(), Key=_s3_key(filename))
            data = obj["Body"].read()
            try:  # refresh local cache (may be read-only)
                local.write_bytes(data)
            except OSError:
                pass
            return data
        except Exception:
            return None
    return None


def game_file_exists(filename: str) -> bool:
    if not filename:
        return False
    if (LOCAL_UPLOAD_DIR / filename).is_file() or (BUNDLED_DIR / filename).is_file():
        return True
    if backend_name() == "s3" and _s3_bucket():
        try:
            _s3_client().head_object(Bucket=_s3_bucket(), Key=_s3_key(filename))
            return True
        except Exception:
            return False
    return False


def storage_status() -> dict:
    persistent = backend_name() == "s3" or os.environ.get("PERSISTENT_DISK") == "1"
    status = {
        "backend": backend_name(),
        "local_dir": str(LOCAL_UPLOAD_DIR),
        "s3_bucket": _s3_bucket() or None,
        "s3_prefix": os.environ.get("S3_PREFIX") or "signalsleuth/games/",
        "persistent": persistent,
    }
    if config.IS_VERCEL and not persistent:
        status["warning"] = (
            "Uploaded games are stored on temporary disk and will disappear. "
            "Set STORAGE_BACKEND=s3 and the S3_* variables."
        )
    return status
