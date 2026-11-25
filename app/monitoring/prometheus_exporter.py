"""Prometheus metrics exposition for CloudWatch Lite."""

from prometheus_client import Counter, Gauge, Histogram

CPU_USAGE_GAUGE = Gauge(
    "cloudwatch_lite_cpu_usage_percent",
    "Current CPU utilization percentage",
)
RAM_USAGE_GAUGE = Gauge(
    "cloudwatch_lite_memory_usage_percent",
    "Current RAM utilization percentage",
)
RAM_USED_GB_GAUGE = Gauge(
    "cloudwatch_lite_memory_used_gb",
    "Current RAM used in GB",
)
DISK_USAGE_GAUGE = Gauge(
    "cloudwatch_lite_disk_usage_percent",
    "Current disk utilization percentage",
)
NET_SENT_BYTES_GAUGE = Gauge(
    "cloudwatch_lite_network_bytes_sent_total",
    "Total network bytes sent",
)
NET_RECV_BYTES_GAUGE = Gauge(
    "cloudwatch_lite_network_bytes_recv_total",
    "Total network bytes received",
)
APP_UPTIME_GAUGE = Gauge(
    "cloudwatch_lite_app_uptime_seconds",
    "CloudWatch Lite application uptime in seconds",
)
ACTIVE_ALERTS_GAUGE = Gauge(
    "cloudwatch_lite_active_alerts_total",
    "Number of active alerts",
)
HTTP_REQUESTS_COUNTER = Counter(
    "cloudwatch_lite_http_requests_total",
    "Total HTTP requests served by CloudWatch Lite",
    ["method", "endpoint", "status"],
)
HTTP_LATENCY_HISTOGRAM = Histogram(
    "cloudwatch_lite_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["endpoint"],
)


def update_prometheus_metrics(metrics: dict, active_alerts: int) -> None:
    """Sync latest psutil and alert metrics into Prometheus gauges."""
    CPU_USAGE_GAUGE.set(metrics["cpu"]["percent"])
    RAM_USAGE_GAUGE.set(metrics["memory"]["percent"])
    RAM_USED_GB_GAUGE.set(metrics["memory"]["used_gb"])
    DISK_USAGE_GAUGE.set(metrics["disk"]["percent"])
    NET_SENT_BYTES_GAUGE.set(metrics["network"]["bytes_sent"])
    NET_RECV_BYTES_GAUGE.set(metrics["network"]["bytes_recv"])
    APP_UPTIME_GAUGE.set(metrics["host"]["app_uptime_seconds"])
    ACTIVE_ALERTS_GAUGE.set(active_alerts)
