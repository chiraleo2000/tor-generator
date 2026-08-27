"""Object storage client: local MinIO vs Amazon S3/IAM."""

from unittest.mock import MagicMock, patch

from app.config import Settings
from app.export.minio_storage import build_minio_client, ensure_minio_bucket


def test_build_minio_client_local_http():
    settings = Settings(
        minio_endpoint="minio:9000",
        minio_access_key="minioadmin",
        minio_secret_key="secret",
        minio_secure=False,
        minio_use_iam=False,
    )
    with patch("app.export.minio_storage.Minio") as mocked:
        build_minio_client(settings)
    kwargs = mocked.call_args.kwargs
    assert mocked.call_args.args[0] == "minio:9000"
    assert kwargs["secure"] is False
    assert kwargs["access_key"] == "minioadmin"


def test_build_minio_client_s3_iam():
    settings = Settings(
        minio_endpoint="s3.ap-southeast-1.amazonaws.com",
        minio_secure=True,
        minio_region="ap-southeast-1",
        minio_use_iam=True,
    )
    fake_creds = object()
    with (
        patch("minio.credentials.IamAwsProvider", return_value=fake_creds),
        patch("app.export.minio_storage.Minio") as mocked,
    ):
        build_minio_client(settings)
    kwargs = mocked.call_args.kwargs
    assert kwargs["secure"] is True
    assert kwargs["region"] == "ap-southeast-1"
    assert kwargs["credentials"] is fake_creds
    assert "access_key" not in kwargs


def test_ensure_minio_bucket_skips_create_on_s3():
    settings = Settings(minio_bucket="tor-prod-exports", minio_secure=True)
    client = MagicMock()
    client.bucket_exists.return_value = False
    ensure_minio_bucket(client, settings)
    client.make_bucket.assert_not_called()


def test_ensure_minio_bucket_creates_local_minio():
    settings = Settings(minio_bucket="tor-documents", minio_secure=False, minio_use_iam=False)
    client = MagicMock()
    client.bucket_exists.return_value = False
    ensure_minio_bucket(client, settings)
    client.make_bucket.assert_called_once_with("tor-documents")
