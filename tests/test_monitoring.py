"""Unit tests for system metrics, database, and alert threshold engine."""

from app.models.database import fetch_metrics_history, init_db
from app.monitoring.alert_engine import (
    acknowledge_alert,
    count_active_alerts,
    evaluate_thresholds,
    fetch_alerts,
    trigger_test_alert,
)
from app.monitoring.system_metrics import collect_system_metrics


def test_collect_system_metrics_returns_real_structure():
    metrics = collect_system_metrics(app_start_time=100.0)
    assert "cpu" in metrics
    assert "memory" in metrics
    assert "disk" in metrics
    assert "network" in metrics
    assert 0.0 <= metrics["cpu"]["percent"] <= 100.0
    assert metrics["memory"]["total_gb"] > 0
    assert metrics["disk"]["total_gb"] > 0


def test_alert_threshold_creation_and_acknowledgement(tmp_path):
    db_file = str(tmp_path / "test_alerts.db")
    init_db(db_file)

    fake_high_metrics = {
        "host": {"hostname": "test-node"},
        "cpu": {"percent": 92.5},
        "memory": {"percent": 45.0},
        "disk": {"percent": 50.0},
    }
    thresholds = {"cpu": 80.0, "ram": 85.0, "disk": 90.0}

    created = evaluate_thresholds(db_file, fake_high_metrics, thresholds)
    assert len(created) == 1
    assert created[0]["metric"] == "cpu"
    assert count_active_alerts(db_file) == 1

    alerts = fetch_alerts(db_file)
    assert len(alerts) == 1
    assert alerts[0]["acknowledged"] == 0

    assert acknowledge_alert(db_file, alerts[0]["id"]) is True
    updated = fetch_alerts(db_file)
    assert updated[0]["acknowledged"] == 1


def test_trigger_test_alert_does_not_overwrite_real_metrics(tmp_path):
    db_file = str(tmp_path / "test_sim.db")
    init_db(db_file)
    thresholds = {"cpu": 80.0, "ram": 85.0, "disk": 90.0}

    alert = trigger_test_alert(db_file, "ram", 91.5, thresholds)
    assert alert["metric"] == "memory"
    assert alert["source"] == "TEST DATA"
    assert "[TEST DATA]" in alert["message"]
    assert alert["severity"] == "warning"
    assert fetch_metrics_history(db_file) == []
