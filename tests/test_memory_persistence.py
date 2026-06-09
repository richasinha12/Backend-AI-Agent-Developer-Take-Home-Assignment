import os
import sys
from pathlib import Path


def test_memory_persists_across_calls(tmp_path):
    # Use a temp sqlite db file for the test
    db_path = tmp_path / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    # Ensure repo root is on sys.path so `import app.*` works without packaging.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

    from fastapi.testclient import TestClient

    from app.main import create_app  # import after env var
    from app.db.init_db import init_db

    init_db()
    client = TestClient(create_app())

    user_id = "u1"
    r1 = client.post(f"/chat/{user_id}", json={"message": "What's your enterprise pricing?"})
    assert r1.status_code == 200
    j1 = r1.json()
    assert "eval" in j1 and "tools_called" in j1
    assert "search_catalog" in j1["tools_called"]
    assert "get_user_memory" in j1["tools_called"]

    r2 = client.post(f"/chat/{user_id}", json={"message": "Does that include SSO?"})
    assert r2.status_code == 200
    j2 = r2.json()
    assert "sso" in j2["response"].lower()

    hist = client.get(f"/chat/{user_id}/history").json()
    assert len(hist) >= 4  # user+assistant twice
