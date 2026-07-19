import os

BASE_DIR = os.path.abspath(
    os.path.dirname(__file__)
)

INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)

class Config:
    """
    Base configuration.
    """

    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "development-secret-key"
    )

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(INSTANCE_DIR, 'vote.db')}"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    """
    Development settings.
    """

    DEBUG = True

    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    """
    Production settings.
    """

    DEBUG = False

class TestingConfig(Config):
    """
    Testing settings.
    """

    TESTING = True

    SQLALCHEMY_DATABASE_URI = (
        "sqlite:///:memory:"
    )

config = {

    "development": DevelopmentConfig,

    "production": ProductionConfig,

    "testing": TestingConfig,

    "default": DevelopmentConfig

}