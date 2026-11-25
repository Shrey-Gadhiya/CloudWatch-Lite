"""Application configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Central configuration for CloudWatch Lite."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-local-secret-change-in-prod")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    PORT = int(os.getenv("PORT", "5000"))

    DATABASE_PATH = os.getenv("DATABASE_PATH", "data/cloudwatch_lite.db")
    METRICS_POLL_INTERVAL_SECONDS = int(
        os.getenv("METRICS_POLL_INTERVAL_SECONDS", "5")
    )

    CPU_ALERT_THRESHOLD = float(os.getenv("CPU_ALERT_THRESHOLD", "80"))
    RAM_ALERT_THRESHOLD = float(os.getenv("RAM_ALERT_THRESHOLD", "85"))
    DISK_ALERT_THRESHOLD = float(os.getenv("DISK_ALERT_THRESHOLD", "90"))

    APP_START_TIME = None  # Populated at app startup
