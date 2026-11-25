"""Web UI routes serving the CloudWatch Lite dashboard."""

from flask import Blueprint, Response, render_template
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

web_bp = Blueprint("web", __name__)


@web_bp.route("/")
def index():
    """Render the main CloudWatch Lite monitoring dashboard."""
    return render_template("index.html")


@web_bp.route("/metrics")
def prometheus_metrics():
    """Expose Prometheus-formatted metrics for scraping."""
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
