import os

class Config:
    """Base configuration for the app."""
    SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key")
    MONGO_URI = os.getenv("MONGO_URI")
    DB_NAME = os.getenv("DB_NAME")
    DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
    ADMIN_EMAILS = os.getenv("ADMIN_EMAILS", "").split(',')
    DEPUTY_EMAILS = os.getenv("DEPUTY_EMAILS", "").split(',')

class AdminConfig(Config):
    """Configuration for Admin mode."""
    DB_NAME = os.getenv("DB_NAME_DEV")
    DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL_DEV")
    EMAIL = os.getenv("EMAIL")  # Override user email in admin mode
    ADMIN_EMAILS = os.getenv("ADMIN_EMAILS_DEV", "").split(',')
    DEPUTY_EMAILS = os.getenv("DEPUTY_EMAILS_DEV", "").split(',')
