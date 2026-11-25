"""Real-time host/container system metrics collector using psutil."""

import os
import platform
import socket
import time
from datetime import datetime, timezone
import psutil


def _bytes_to_gb(num_bytes: int) -> float:
    return round(num_bytes / (1024 ** 3), 2)


def _bytes_to_mb(num_bytes: int) -> float:
    return round(num_bytes / (1024 ** 2), 2)


def collect_system_metrics(app_start_time: float | None = None) -> dict:
    """Collect real CPU, RAM, disk, network, and uptime metrics via psutil."""
    now = time.time()
    boot_time = psutil.boot_time()
    system_uptime_sec = max(0, int(now - boot_time))
    app_uptime_sec = (
        max(0, int(now - app_start_time)) if app_start_time is not None else 0
    )

    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)
    cpu_count_logical = psutil.cpu_count(logical=True) or 0
    cpu_count_physical = psutil.cpu_count(logical=False) or 0
    cpu_freq = psutil.cpu_freq()

    load_avg = None
    if hasattr(os, "getloadavg"):
        try:
            load_avg = [round(x, 2) for x in os.getloadavg()]
        except OSError:
            load_avg = None

    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()

    disk_path = "C:\\" if platform.system() == "Windows" else "/"
    disk = psutil.disk_usage(disk_path)
    disk_io = psutil.disk_io_counters()

    net_io = psutil.net_io_counters()

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "host": {
            "hostname": socket.gethostname(),
            "os": platform.system(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "environment": (
                "container"
                if os.path.exists("/.dockerenv")
                else "local-host"
            ),
            "system_uptime_seconds": system_uptime_sec,
            "app_uptime_seconds": app_uptime_sec,
        },
        "cpu": {
            "percent": round(cpu_percent, 1),
            "per_core": [round(c, 1) for c in cpu_per_core],
            "logical_cores": cpu_count_logical,
            "physical_cores": cpu_count_physical,
            "frequency_mhz": round(cpu_freq.current, 1) if cpu_freq else None,
            "load_avg": load_avg,
        },
        "memory": {
            "percent": round(vm.percent, 1),
            "total_gb": _bytes_to_gb(vm.total),
            "used_gb": _bytes_to_gb(vm.used),
            "available_gb": _bytes_to_gb(vm.available),
            "swap_percent": round(swap.percent, 1),
            "swap_total_gb": _bytes_to_gb(swap.total),
        },
        "disk": {
            "mount": disk_path,
            "percent": round(disk.percent, 1),
            "total_gb": _bytes_to_gb(disk.total),
            "used_gb": _bytes_to_gb(disk.used),
            "free_gb": _bytes_to_gb(disk.free),
            "read_mb": _bytes_to_mb(disk_io.read_bytes) if disk_io else 0.0,
            "write_mb": _bytes_to_mb(disk_io.write_bytes) if disk_io else 0.0,
        },
        "network": {
            "bytes_sent": net_io.bytes_sent if net_io else 0,
            "bytes_recv": net_io.bytes_recv if net_io else 0,
            "sent_mb": _bytes_to_mb(net_io.bytes_sent) if net_io else 0.0,
            "recv_mb": _bytes_to_mb(net_io.bytes_recv) if net_io else 0.0,
            "packets_sent": net_io.packets_sent if net_io else 0,
            "packets_recv": net_io.packets_recv if net_io else 0,
            "errin": net_io.errin if net_io else 0,
            "errout": net_io.errout if net_io else 0,
        },
    }
