"""S3 KB prefix download for cloud seed."""

import os
from pathlib import Path
from unittest.mock import MagicMock

from app.storage.s3_kb_sync import download_prefix, main


def test_download_prefix_skips_folder_keys_and_strips_prefix(tmp_path: Path):
    client = MagicMock()
    page = {
        "Contents": [
            {"Key": "sources/"},
            {"Key": "sources/คู่มือแนวปฏิบัติ_การจัดซื้อจัดจ้างภาครัฐ.pdf"},
            {"Key": "sources/การจัดซื้อจัดจ้าง/ข้อมูลดิบ/พรบ.pdf"},
        ]
    }
    client.get_paginator.return_value.paginate.return_value = [page]

    count = download_prefix("tor-prod-kb-source", "sources/", tmp_path, client=client)

    assert count == 2
    assert client.download_file.call_count == 2
    first_dest = Path(client.download_file.call_args_list[0].args[2])
    assert first_dest.parent == tmp_path


def test_main_sync_only_sets_env(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("KB_SOURCE_BUCKET", "tor-prod-kb-source")
    monkeypatch.setenv("KB_LOCAL_DIR", str(tmp_path))

    def fake_download(bucket, prefix, dest, client=None):
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "ok.pdf").write_bytes(b"%PDF")
        return 1

    monkeypatch.setattr("app.storage.s3_kb_sync.download_prefix", fake_download)
    assert main(["--sync-only"]) == 0
    assert Path(tmp_path / "ok.pdf").is_file()
    assert os.environ["KB_SOURCES_ROOT"] == str(tmp_path)
