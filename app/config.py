import os
from dotenv import load_dotenv

load_dotenv()

admin_mode_switch = False

# Base configuration class
class Config:
    MONGO_URI = os.getenv("MONGO_URI")
    SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(24))

# Development configuration class
class DevelopmentConfig(Config):
    DB_NAME = os.getenv("DB_NAME_DEV")
    DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL_DEV")

# Production configuration class
class ProductionConfig(Config):
    DB_NAME = os.getenv("DB_NAME")
    DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Switch between configs using environment variable
if os.getenv("FLASK_ENV") == "development":
    current_config = DevelopmentConfig
else:
    current_config = ProductionConfig
