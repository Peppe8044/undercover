import runpy

from fastapi.testclient import TestClient

from backend import db
from backend.main import app


def test_seed_counts():
    assert db.seed() == {
        "claims": 25,
        "policies": 50,
        "customers": 49,
        "handlers": 3,
    }


def test_seed_holds_only_the_queue():
    with db.connect() as connection:
        ids = [row["claim_id"] for row in connection.execute("SELECT * FROM claims")]
    assert ids == [f"CLM-{number}" for number in range(1001, 1026)]


def test_seed_command(capsys):
    runpy.run_module("backend.seed", run_name="__main__")
    assert "25 claims, 50 policies, 49 customers and 3 handlers" in (
        capsys.readouterr().out
    )


def test_startup_seeds_a_missing_database(tmp_path, monkeypatch):
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "fresh.db"))
    with TestClient(app) as client:
        assert len(client.get("/api/claims").json()) == 25


def test_startup_keeps_an_existing_database():
    with db.connect() as connection:
        connection.execute("UPDATE claims SET status = 'decided'")
    with TestClient(app) as client:
        assert {claim["status"] for claim in client.get("/api/claims").json()} == {
            "decided"
        }
