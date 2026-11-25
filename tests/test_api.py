"""API endpoint tests for CloudWatch Lite."""

import pytest
from app import create_app


@pytest.fixture()
def client(tmp_path):
    db_path = str(tmp_path / "test_api.db")
    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    with app.test_client() as test_client:
        yield test_client


def test_dashboard_route(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"CloudWatch Lite" in res.data


def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert data["service"] == "cloudwatch-lite"


def test_metrics_endpoint(client):
    res = client.get("/api/metrics")
    assert res.status_code == 200
    data = res.get_json()
    assert "cpu" in data
    assert "memory" in data
    assert "disk" in data
    assert "network" in data


def test_servers_and_history_endpoints(client):
    res_srv = client.get("/api/servers")
    assert res_srv.status_code == 200
    assert res_srv.get_json()["summary"]["total"] == 1

    res_hist = client.get("/api/metrics/history?limit=10")
    assert res_hist.status_code == 200
    assert "history" in res_hist.get_json()


def test_containers_alerts_and_logs_endpoints(client):
    res_c = client.get("/api/containers")
    assert res_c.status_code == 200
    assert "available" in res_c.get_json()

    res_a = client.get("/api/alerts")
    assert res_a.status_code == 200
    assert "alerts" in res_a.get_json()

    res_ack = client.post("/api/alerts/acknowledge", json={"id": 9999})
    assert res_ack.status_code == 404

    res_ack_bad = client.post("/api/alerts/acknowledge", json={"id": "bad"})
    assert res_ack_bad.status_code == 400

    res_logs = client.get("/api/logs")
    assert res_logs.status_code == 200
    assert res_logs.get_json()["count"] >= 1


def test_prometheus_metrics_endpoint(client):
    client.get("/api/metrics")
    res = client.get("/metrics")
    assert res.status_code == 200
    assert b"cloudwatch_lite_cpu_usage_percent" in res.data


def test_trigger_test_alert_and_acknowledge(client):
    for metric, val, expected_sev in [
        ("cpu", 88, "warning"),
        ("memory", 91, "warning"),
        ("disk", 96, "critical"),
    ]:
        res = client.post("/api/test/trigger-alert", json={"metric": metric, "value": val})
        assert res.status_code == 201
        body = res.get_json()
        assert body["test_data"] is True
        assert body["alert"]["source"] == "TEST DATA"
        assert "[TEST DATA]" in body["alert"]["message"]
        assert body["alert"]["severity"] == expected_sev

        ack = client.post("/api/alerts/acknowledge", json={"id": body["alert"]["id"]})
        assert ack.status_code == 200


def test_trigger_test_alert_invalid_inputs(client):
    assert client.post("/api/test/trigger-alert", json={"metric": "gpu", "value": 95}).status_code == 400
    assert client.post("/api/test/trigger-alert", json={"metric": "cpu", "value": 50}).status_code == 400
    assert client.post("/api/test/trigger-alert", json={"metric": "cpu", "value": 150}).status_code == 400
    assert client.post("/api/test/trigger-alert", json={"metric": "cpu", "value": "high"}).status_code == 400
    assert client.post("/api/test/trigger-alert", data="not-json").status_code == 400


def test_trigger_test_alert_blocked_in_production(tmp_path):
    db_path = str(tmp_path / "prod_api.db")
    app = create_app({"TESTING": False, "FLASK_ENV": "production", "DATABASE_PATH": db_path})
    with app.test_client() as prod_client:
        res = prod_client.post("/api/test/trigger-alert", json={"metric": "cpu", "value": 90})
        assert res.status_code == 403
