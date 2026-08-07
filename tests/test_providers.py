"""Provider registry tests."""
from __future__ import annotations

from backend.providers import list_providers, get_provider, PROVIDERS


def test_list_providers():
    providers = list_providers()
    assert len(providers) >= 3
    ids = {p.id for p in providers}
    assert "openrouter" in ids


def test_get_provider():
    p = get_provider("openrouter")
    assert p is not None
    assert p.base_url
    assert get_provider("nonexistent-xyz") is None


def test_providers_dict():
    assert "openrouter" in PROVIDERS
    assert PROVIDERS["openrouter"].key_env_var
