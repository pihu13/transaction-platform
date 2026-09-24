import os
import tempfile
import pytest
from fastapi.testclient import TestClient

##Test configuration
def pytest_configure(config):
    pass


@pytest.fixture()
def app_client(monkeypatch):
    db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_file.close()
    url = f"sqlite:///{db_file.name}"
    monkeypatch.setenv("DATABASE_URL", url)
    # modules are imported after env setup in test files where needed
    from app import db
    from app import main
    db.engine.dispose()
    db.engine = db.create_engine(url, connect_args={"check_same_thread": False}, future=True)
    db.SessionLocal.configure(bind=db.engine)
    db.Base.metadata.drop_all(bind=db.engine)
    db.Base.metadata.create_all(bind=db.engine)
    with TestClient(main.app) as client:
        yield client
    db.engine.dispose()
    os.unlink(db_file.name)
