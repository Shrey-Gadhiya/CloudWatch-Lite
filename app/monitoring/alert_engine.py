"""Alert evaluation, persistence, and acknowledgement engine."""

from app.models.database import get_connection, insert_log, utc_now_iso


def evaluate_thresholds(
    db_path: str,
    metrics: dict,
    thresholds: dict,
    docker_info: dict | None = None,
) -> list[dict]:
    """Evaluate CPU, RAM, disk, and container health thresholds and update alerts."""
    checks = [
        (
            "cpu",
            metrics["cpu"]["percent"],
            thresholds["cpu"],
            "critical" if metrics["cpu"]["percent"] >= 95 else "warning",
            f"CPU usage at {metrics['cpu']['percent']}% (threshold {thresholds['cpu']}%)",
        ),
        (
            "memory",
            metrics["memory"]["percent"],
            thresholds["ram"],
            "critical" if metrics["memory"]["percent"] >= 95 else "warning",
            f"Memory usage at {metrics['memory']['percent']}% (threshold {thresholds['ram']}%)",
        ),
        (
            "disk",
            metrics["disk"]["percent"],
            thresholds["disk"],
            "critical" if metrics["disk"]["percent"] >= 95 else "warning",
            f"Disk usage at {metrics['disk']['percent']}% (threshold {thresholds['disk']}%)",
        ),
    ]

    created_alerts = []
    now = utc_now_iso()
    hostname = metrics["host"]["hostname"]

    with get_connection(db_path) as conn:
        for metric_name, value, limit, severity, msg in checks:
            existing = conn.execute(
                """
                SELECT id FROM alerts
                WHERE metric = ? AND status = 'active'
                ORDER BY id DESC LIMIT 1
                """,
                (metric_name,),
            ).fetchone()

            if value > limit:
                if not existing:
                    conn.execute(
                        """
                        INSERT INTO alerts (
                            timestamp, severity, source, metric, value,
                            threshold, message, status, acknowledged
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'active', 0)
                        """,
                        (now, severity, hostname, metric_name, value, limit, msg),
                    )
                    created_alerts.append({"metric": metric_name, "severity": severity, "message": msg})
            elif existing:
                conn.execute(
                    "UPDATE alerts SET status = 'resolved' WHERE id = ?",
                    (existing["id"],),
                )

        if docker_info and docker_info.get("available"):
            unhealthy_count = docker_info["summary"].get("unhealthy", 0)
            existing_docker = conn.execute(
                """
                SELECT id FROM alerts
                WHERE metric = 'container_health' AND status = 'active'
                ORDER BY id DESC LIMIT 1
                """
            ).fetchone()
            if unhealthy_count > 0 and not existing_docker:
                msg = f"{unhealthy_count} Docker container(s) reporting unhealthy status"
                conn.execute(
                    """
                    INSERT INTO alerts (
                        timestamp, severity, source, metric, value,
                        threshold, message, status, acknowledged
                    ) VALUES (?, 'critical', 'docker', 'container_health', ?, 0, ?, 'active', 0)
                    """,
                    (now, unhealthy_count, msg),
                )
                created_alerts.append({"metric": "container_health", "severity": "critical", "message": msg})
            elif unhealthy_count == 0 and existing_docker:
                conn.execute(
                    "UPDATE alerts SET status = 'resolved' WHERE id = ?",
                    (existing_docker["id"],),
                )

        conn.commit()

    for alert in created_alerts:
        insert_log(db_path, alert["severity"], "alert-engine", alert["message"])

    return created_alerts


def fetch_alerts(
    db_path: str,
    severity: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Fetch alerts from SQLite with optional severity and status filters."""
    query = (
        "SELECT id, timestamp, severity, source, metric, value, threshold, "
        "message, status, acknowledged, acknowledged_at FROM alerts WHERE 1=1"
    )
    params: list = []

    if severity and severity.lower() != "all":
        query += " AND lower(severity) = ?"
        params.append(severity.lower())

    if status and status.lower() != "all":
        query += " AND lower(status) = ?"
        params.append(status.lower())

    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with get_connection(db_path) as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [dict(r) for r in rows]


def acknowledge_alert(db_path: str, alert_id: int) -> bool:
    """Mark an alert as acknowledged. Returns True if a row was updated."""
    now = utc_now_iso()
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """
            UPDATE alerts
            SET acknowledged = 1, acknowledged_at = ?
            WHERE id = ?
            """,
            (now, alert_id),
        )
        conn.commit()
        updated = cur.rowcount > 0
    if updated:
        insert_log(db_path, "info", "alert-engine", f"Alert #{alert_id} acknowledged")
    return updated


def count_active_alerts(db_path: str) -> int:
    """Return the count of active unacknowledged alerts."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM alerts WHERE status = 'active'"
        ).fetchone()
    return int(row["cnt"]) if row else 0


DEFAULT_TEST_VALUES = {
    "cpu": 88.0,
    "memory": 91.0,
    "disk": 94.0,
}


def trigger_test_alert(
    db_path: str,
    metric: str,
    value: float | None,
    thresholds: dict,
) -> dict:
    """Simulate a threshold breach alert clearly labelled as TEST DATA."""
    normalized = (metric or "").strip().lower()
    if normalized == "ram":
        normalized = "memory"

    if normalized not in ("cpu", "memory", "disk"):
        raise ValueError("metric must be one of: cpu, memory, ram, disk")

    threshold_key = "ram" if normalized == "memory" else normalized
    limit = float(thresholds[threshold_key])

    if value is None:
        sim_value = DEFAULT_TEST_VALUES[normalized]
    else:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("value must be a number between 0 and 100")
        sim_value = round(float(value), 1)

    if sim_value < 0 or sim_value > 100:
        raise ValueError("value must be between 0 and 100")

    if sim_value <= limit:
        raise ValueError(
            f"Simulated {normalized} value ({sim_value}%) must exceed threshold ({limit}%)"
        )

    severity = "critical" if sim_value >= 95 else "warning"
    now = utc_now_iso()
    source = "TEST DATA"
    message = (
        f"[TEST DATA] Simulated {normalized.upper()} threshold breach: "
        f"{sim_value}% (threshold {limit}%)"
    )

    with get_connection(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO alerts (
                timestamp, severity, source, metric, value,
                threshold, message, status, acknowledged
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'active', 0)
            """,
            (now, severity, source, normalized, sim_value, limit, message),
        )
        conn.commit()
        alert_id = cur.lastrowid

    insert_log(db_path, severity, "alert-test-mode", message)

    return {
        "id": alert_id,
        "timestamp": now,
        "severity": severity,
        "source": source,
        "metric": normalized,
        "value": sim_value,
        "threshold": limit,
        "message": message,
        "status": "active",
        "acknowledged": 0,
        "test_data": True,
    }
