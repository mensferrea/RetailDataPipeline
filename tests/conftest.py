import pytest
from src.database import Base, engine, init_db_schemas
from src.services.seeder_service import SeederService


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    init_db_schemas()
    Base.metadata.create_all(bind=engine)
    seeder = SeederService()
    seeder.seed_all()
    yield
