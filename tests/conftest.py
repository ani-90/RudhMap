"""Keep the extraction cache of every test inside pytest's temp dirs, never
in the user's real cache folder."""
import pytest


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path_factory, monkeypatch):
    monkeypatch.setenv("RUDHMAP_CACHE_DIR", str(tmp_path_factory.mktemp("rudhmap_cache")))
