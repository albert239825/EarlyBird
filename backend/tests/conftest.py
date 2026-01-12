import os
import shutil
import sys
from pathlib import Path
from datetime import datetime

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

@pytest.fixture
def elevenlabs_api_key() -> str:
    return os.getenv("ELEVENLABS_API_KEY", "test_elevenlabs_key")


@pytest.fixture
def tmp_backend_root(tmp_path: Path) -> Path:
    """
    Temp backend_root for storage + route tests.
    PodcastStorage(backend_root) writes under backend_root/finished_podcasts/.
    """
    return tmp_path / "backend_root"


@pytest.fixture
def test_output_dir() -> Path | None:
    """
    Optional persistent test output directory for inspecting integration test artifacts.
    
    Set KEEP_TEST_OUTPUT=1 environment variable to enable.
    Outputs will be saved to backend/tests/test_output/<test_name>_<timestamp>/
    
    Returns None if KEEP_TEST_OUTPUT is not set (files won't be persisted).
    """
    if not os.getenv("KEEP_TEST_OUTPUT"):
        return None
    
    output_base = Path(__file__).parent / "test_output"
    output_base.mkdir(exist_ok=True)
    return output_base


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook to capture test result for persist_test_output fixture.
    """
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


@pytest.fixture(autouse=True)
def persist_test_output(request, tmp_podcast_dir: Path, test_output_dir: Path | None):
    """
    Automatically copy test directory to persistent location after integration tests.
    
    Only runs if:
    - KEEP_TEST_OUTPUT=1 is set
    - Test is marked with @pytest.mark.integration
    - Test passes (so you can inspect successful runs)
    """
    # Only persist for integration tests
    if not request.node.get_closest_marker("integration"):
        yield
        return
    
    # Only persist if KEEP_TEST_OUTPUT is set
    if test_output_dir is None:
        yield
        return
    
    yield  # Run the test
    
    # After test completes, copy files if test passed
    # Check the report from the hook
    if hasattr(request.node, 'rep_call') and request.node.rep_call.passed:
        test_name = request.node.name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = test_output_dir / f"{test_name}_{timestamp}"
        
        try:
            shutil.copytree(tmp_podcast_dir, output_path)
            print(f"\n{'='*60}")
            print(f"Test output persisted to: {output_path}")
            print(f"{'='*60}\n")
        except Exception as e:
            print(f"\n⚠ Warning: Could not persist test output: {e}\n")

