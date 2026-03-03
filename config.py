# config.py
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """
    GlobalIT-CRM configuration.
    - Uses SQLite DB inside /instance/crm.db
    - SECRET_KEY can be overridden via environment variable
    """

    # Security
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-to-a-strong-secret-key")

    # Database (SQLite in instance folder)
    INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
    DB_PATH = os.path.join(INSTANCE_DIR, "crm.db")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session cookie safety (good defaults)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"