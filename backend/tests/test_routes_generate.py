from pathlib import Path

from flask import Flask

from backend.api.routes import setup_routes


class _ImmediateThread:
    def __init__(self, target, args=()):
        self._target = target
        self._args = args
        self.daemon = False

    def start(self):
        # Run synchronously to keep tests deterministic.
        self._target(*self._args)


def test_post_generate_returns_podcast_id(tmp_path, monkeypatch):
    app = Flask(__name__)

    class _Service:
        def __init__(self):
            self.called = False
            self.args = None

        def create_podcast_dir(self) -> Path:
            d = tmp_path / "podcast_abc"
            d.mkdir(parents=True, exist_ok=True)
            return d

        def generate_podcast(self, podcast_dir: Path, num_articles: int, categories=None):
            self.called = True
            self.args = (podcast_dir, num_articles, categories)

    service = _Service()

    # Patch the threading.Thread used inside routes.py
    import backend.api.routes as routes_mod
    monkeypatch.setattr(routes_mod.threading, "Thread", _ImmediateThread)

    setup_routes(app, service)
    client = app.test_client()

    resp = client.post("/generate", json={"num_articles": 1})
    assert resp.status_code == 200
    assert resp.get_json()["podcast_id"] == "podcast_abc"
    assert service.called
    assert service.args[1] == 1
    assert service.args[2] is None

