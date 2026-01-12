import os
import sys
from pathlib import Path

import pytest

# Ensure project root is on sys.path (mirrors backend/app.py behavior)
_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from backend.core.state_manager import PodcastState


def pytest_collection_modifyitems(config, items):
    """
    Default behavior: skip integration tests unless explicitly selected.

    Run integration tests with:
      pytest -m integration
    """
    markexpr = getattr(config.option, "markexpr", "") or ""
    run_integration = "integration" in markexpr
    if run_integration:
        return

    skip_integration = pytest.mark.skip(reason="Skipped by default. Run with: pytest -m integration")
    for item in items:
        if item.get_closest_marker("integration"):
            item.add_marker(skip_integration)


@pytest.fixture
def tmp_podcast_dir(tmp_path: Path) -> Path:
    d = tmp_path / "podcast_test"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def state() -> PodcastState:
    # No socketio in tests.
    return PodcastState(socketio=None)


@pytest.fixture
def openai_api_key() -> str:
    # Unit tests use a dummy key and stub network calls.
    return os.getenv("OPENAI_API_KEY", "test_openai_key")


@pytest.fixture
def perplexity_api_key() -> str:
    return os.getenv("PERPLEXITY_API_KEY", "test_perplexity_key")

