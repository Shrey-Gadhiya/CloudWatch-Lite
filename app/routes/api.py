"""REST API endpoints for CloudWatch Lite."""

import time
from flask import Blueprint, current_app, jsonify, request
from app.models.database import fetch_logs, fetch_metrics_history
from app.monitoring.alert_engine import (
    acknowledge_alert,
    count_active_alerts,
    evaluate_thresholds,
    fetch_alerts,
    trigger_test_alert,
)
from app.monitoring.docker_metrics import collect_docker_containers
from app.monitoring.prometheus_exporter import update_prometheus_metrics
from app.monitoring.system_metrics import collect_system_metrics

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/health", methods=["GET"])
def health():
    """Health-check endpoint for Docker, load balancers, and monitoring."""
    start = time.perf_counter()
    app_start = current_app.config.get("APP_START_TIME")
    uptime_seconds = max(0, int(time.time() - app_start)) if app_start else 0
    response_time_ms = round((time.perf_counter() - start) * 1000, 2)

    return jsonify(
        {
            "status": "healthy",
            "service": "cloudwatch-lite",
            "uptime_seconds": uptime_seconds,
            "response_time_ms": response_time_ms,
        }
    ), 200


@api_bp.route("/metrics", methods=["GET"])
def metrics():
    """Return real-time system metrics collected via psutil."""
    start = time.perf_counter()
    app_start = current_app.config.get("APP_START_TIME")
    db_path = current_app.config["DATABASE_PATH"]

    data = collect_system_metrics(app_start_time=app_start)
    thresholds = {
        "cpu": current_app.config["CPU_ALERT_THRESHOLD"],
        "ram": current_app.config["RAM_ALERT_THRESHOLD"],
        "disk": current_app.config["DISK_ALERT_THRESHOLD"],
    }
    evaluate_thresholds(db_path, data, thresholds)
    active_alerts = count_active_alerts(db_path)
    update_prometheus_metrics(data, active_alerts)

    data["response_time_ms"] = round((time.perf_counter() - start) * 1000, 2)
    data["active_alerts"] = active_alerts
    data["thresholds"] = thresholds
    return jsonify(data), 200


@api_bp.route("/metrics/history", methods=["GET"])
def metrics_history():
    """Return historical metrics snapshots from SQLite."""
    limit_raw = request.args.get("limit", "60")
    try:
        limit = max(1, min(500, int(limit_raw)))
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400

    history = fetch_metrics_history(current_app.config["DATABASE_PATH"], limit=limit)
    return jsonify({"count": len(history), "history": history}), 200


@api_bp.route("/servers", methods=["GET"])
def servers():
    """Return monitored server inventory with real host status."""
    app_start = current_app.config.get("APP_START_TIME")
    data = collect_system_metrics(app_start_time=app_start)
    host = data["host"]
    server = {
        "id": host["hostname"],
        "hostname": host["hostname"],
        "os": f"{host['os']} {host['os_release']}",
        "architecture": host["architecture"],
        "environment": host["environment"],
        "status": "online",
        "cpu_percent": data["cpu"]["percent"],
        "ram_percent": data["memory"]["percent"],
        "disk_percent": data["disk"]["percent"],
        "uptime_seconds": host["system_uptime_seconds"],
    }
    return jsonify(
        {
            "summary": {"total": 1, "online": 1, "offline": 0},
            "servers": [server],
        }
    ), 200


@api_bp.route("/containers", methods=["GET"])
def containers():
    """Return Docker container statuses via Docker SDK."""
    result = collect_docker_containers()
    return jsonify(result), 200


@api_bp.route("/alerts", methods=["GET"])
def alerts():
    """Return stored alerts with optional severity and status filters."""
    severity = request.args.get("severity")
    status = request.args.get("status")
    items = fetch_alerts(
        current_app.config["DATABASE_PATH"],
        severity=severity,
        status=status,
    )
    return jsonify({"count": len(items), "alerts": items}), 200


@api_bp.route("/alerts/acknowledge", methods=["POST"])
def ack_alert():
    """Acknowledge an alert by ID."""
    payload = request.get_json(silent=True) or {}
    alert_id = payload.get("id")
    if not isinstance(alert_id, int) or alert_id <= 0:
        return jsonify({"error": "Valid positive integer 'id' is required"}), 400

    updated = acknowledge_alert(current_app.config["DATABASE_PATH"], alert_id)
    if not updated:
        return jsonify({"error": f"Alert #{alert_id} not found"}), 404

    return jsonify({"status": "acknowledged", "id": alert_id}), 200


@api_bp.route("/logs", methods=["GET"])
def logs():
    """Return recent structured application logs."""
    level = request.args.get("level")
    limit_raw = request.args.get("limit", "100")
    try:
        limit = max(1, min(500, int(limit_raw)))
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400

    items = fetch_logs(current_app.config["DATABASE_PATH"], level=level, limit=limit)
    return jsonify({"count": len(items), "logs": items}), 200


@api_bp.route("/test/trigger-alert", methods=["POST"])
def test_trigger_alert():
    """Dev/test-only endpoint to simulate CPU, RAM, or disk threshold alerts."""
    env = str(current_app.config.get("FLASK_ENV", "development")).lower()
    is_testing = bool(current_app.config.get("TESTING", False))
    if env not in ("development", "test", "testing") and not is_testing:
        return jsonify(
            {"error": "Alert Testing Mode is disabled outside local development/test"}
        ), 403

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON body is required"}), 400

    metric = payload.get("metric")
    value = payload.get("value")
    thresholds = {
        "cpu": current_app.config["CPU_ALERT_THRESHOLD"],
        "ram": current_app.config["RAM_ALERT_THRESHOLD"],
        "disk": current_app.config["DISK_ALERT_THRESHOLD"],
    }

    try:
        alert = trigger_test_alert(
            current_app.config["DATABASE_PATH"],
            metric=metric,
            value=value,
            thresholds=thresholds,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"status": "triggered", "test_data": True, "alert": alert}), 201
