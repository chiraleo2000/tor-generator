"""Defaults in constants.py must follow `.env.example` keys."""

from app.providers.constants import _env_int, _env_str


def test_lm_studio_model_key_matches_env_example(monkeypatch):
    monkeypatch.delenv("LM_STUDIO_MODEL", raising=False)
    assert _env_str("LM_STUDIO_MODEL", "google/gemma-4-e4b") == "google/gemma-4-e4b"
    monkeypatch.setenv("LM_STUDIO_MODEL", "google/gemma-4-e4b")
    assert _env_str("LM_STUDIO_MODEL", "other") == "google/gemma-4-e4b"


def test_embedding_model_key_matches_env_example(monkeypatch):
    monkeypatch.delenv("LM_STUDIO_EMBEDDING_MODEL", raising=False)
    assert (
        _env_str("LM_STUDIO_EMBEDDING_MODEL", "text-embedding-embeddinggemma-300m")
        == "text-embedding-embeddinggemma-300m"
    )


def test_embedding_dimensions_key(monkeypatch):
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "768")
    assert _env_int("EMBEDDING_DIMENSIONS", 768) == 768
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "1024")
    assert _env_int("EMBEDDING_DIMENSIONS", 768) == 1024
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "")
    assert _env_int("EMBEDDING_DIMENSIONS", 768) == 768
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "nope")
    assert _env_int("EMBEDDING_DIMENSIONS", 768) == 768


def test_env_str_strips_trailing_space(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite ")
    assert _env_str("GEMINI_MODEL", "x") == "gemini-3.5-flash-lite"
