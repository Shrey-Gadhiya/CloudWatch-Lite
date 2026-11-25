"""Flask application factory for CloudWatch Lite."""

import logging
import threading
import time
from flask import Flask, g, request

from app.config import Config
from app.models.database import init_db, insert_log, insert_metric_snapshot
from app.monitoring.alert_engine import count_active_alerts, evaluate_thresholds
from app.monitoring.docker_metrics import collect_docker_containers
from app.monitoring.prometheus_exporter import (
    HTTP_LATENCY_HISTOGRAM,
    HTTP_REQUESTS_COUNTER,
    update_prometheus_metrics,
)
from app.monitoring.system_metrics import collect_system_metrics
from app.routes.api import api_bp
from app.routes.web import web_bp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("cloudwatch-lite")


def _background_collector(app: Flask) -> None:
    """Periodically sample system metrics, store history, and evaluate alerts."""
    interval = app.config["METRICS_POLL_INTERVAL_SECONDS"]
    db_path = app.config["DATABASE_PATH"]
    thresholds = {
        "cpu": app.config["CPU_ALERT_THRESHOLD"],
        "ram": app.config["RAM_ALERT_THRESHOLD"],
        "disk": app.config["DISK_ALERT_THRESHOLD"],
    }

    while True:
        try:
            start = time.perf_counter()
            metrics = collect_system_metrics(
                app_start_time=app.config.get("APP_START_TIME")
            )
            docker_info = collect_docker_containers()
            evaluate_thresholds(db_path, metrics, thresholds, docker_info)
            active_alerts = count_active_alerts(db_path)
            update_prometheus_metrics(metrics, active_alerts)

            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            insert_metric_snapshot(
                db_path,
                {
                    "timestamp": metrics["timestamp"],
                    "cpu_percent": metrics["cpu"]["percent"],
                    "ram_percent": metrics["memory"]["percent"],
                    "disk_percent": metrics["disk"]["percent"],
                    "net_bytes_sent": metrics["network"]["bytes_sent"],
                    "net_bytes_recv": metrics["network"]["bytes_recv"],
                    "response_time_ms": elapsed_ms,
                },
            )
        except Exception as exc:
            logger.error("Background collector error: %s", exc)
        time.sleep(interval)


def create_app(test_config: dict | None = None) -> Flask:
    """Create and configure the Flask application instance."""
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["APP_START_TIME"] = time.time()

    if test_config:
        app.config.update(test_config)

    init_db(app.config["DATABASE_PATH"])
    insert_log(app.config["DATABASE_PATH"], "info", "startup", "CloudWatch Lite initialized")

    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp)

    @app.before_request
    def _before_req():
        g.req_start = time.perf_counter()

    @app.after_request
    def _after_req(response):
        endpoint = request.endpoint or "unknown"
        elapsed = time.perf_counter() - getattr(g, "req_start", time.perf_counter())
        HTTP_REQUESTS_COUNTER.labels(
            method=request.method,
            endpoint=endpoint,
            status=str(response.status_code),
        ).inc()
        HTTP_LATENCY_HISTOGRAM.labels(endpoint=endpoint).observe(elapsed)
        return response

    if not app.config.get("TESTING", False):
        thread = threading.Thread(
            target=_background_collector,
            args=(app,),
            daemon=True,
            name="metrics-collector",
        )
        thread.start()

    return app
