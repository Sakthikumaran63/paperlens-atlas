from app.core.config import Settings


def test_default_config_validation():
    custom_settings = Settings(
        PROJECT_NAME="test-paperlens",
        ENV="test",
        LOG_LEVEL="DEBUG",
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/testdb",
        CORS_ORIGINS=["http://localhost:3000"]
    )
    assert custom_settings.PROJECT_NAME == "test-paperlens"
    assert custom_settings.ENV == "test"
    assert custom_settings.LOG_LEVEL == "DEBUG"
    assert custom_settings.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/testdb"
    assert custom_settings.CORS_ORIGINS == ["http://localhost:3000"]
