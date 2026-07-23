"""
Application configuration.

Supports:

- Development
- Production
- Testing
"""

import os


BASE_DIR = os.path.abspath(
    os.path.dirname(__file__)
)


class Config:
    """
    Base configuration.
    """

    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "development-secret-key"
    )

    PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL")

    QUIZ_DEFAULT_TIME_LIMIT_SECONDS = int(
        os.environ.get("QUIZ_DEFAULT_TIME_LIMIT_SECONDS", "23")
    )

    QUIZ_DEFAULT_POINTS_BASE = int(
        os.environ.get("QUIZ_DEFAULT_POINTS_BASE", "10")
    )

    QUIZ_FEEDBACK_SECONDS = int(
        os.environ.get("QUIZ_FEEDBACK_SECONDS", "10")
    )


    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" +
        os.path.join(
            BASE_DIR,
            "instance",
            "vote.db"
        )
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
