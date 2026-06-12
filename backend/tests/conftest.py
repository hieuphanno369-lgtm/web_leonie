"""Per-test SQLite fixture — patches get_connection default to use a fresh temp DB."""
import pytest
import database


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    database.create_tables(db_path)
    orig_defaults = database.get_connection.__defaults__
    database.get_connection.__defaults__ = (db_path,)
    yield db_path
    database.get_connection.__defaults__ = orig_defaults
