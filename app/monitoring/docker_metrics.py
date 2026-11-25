"""Docker container monitoring via Docker SDK for Python."""

import docker
from docker.errors import DockerException


def collect_docker_containers() -> dict:
    """Return real Docker container statuses or an explicit unavailable state."""
    try:
        client = docker.from_env(timeout=3)
        containers = client.containers.list(all=True)
    except (DockerException, Exception) as exc:
        return {
            "available": False,
            "error": str(exc),
            "summary": {"total": 0, "running": 0, "stopped": 0, "unhealthy": 0},
            "containers": [],
        }

    items = []
    running = 0
    stopped = 0
    unhealthy = 0

    for container in containers:
        attrs = container.attrs or {}
        state = attrs.get("State", {})
        health = state.get("Health", {}).get("Status", "none")
        status = container.status  # e.g. 'running', 'exited'

        if status == "running":
            running += 1
        else:
            stopped += 1

        if health == "unhealthy":
            unhealthy += 1

        image_tags = container.image.tags if container.image else []
        image_name = image_tags[0] if image_tags else attrs.get("Config", {}).get("Image", "unknown")

        items.append(
            {
                "id": container.short_id,
                "name": container.name,
                "image": image_name,
                "status": status,
                "health": health,
                "created": attrs.get("Created", ""),
            }
        )

    return {
        "available": True,
        "error": None,
        "summary": {
            "total": len(items),
            "running": running,
            "stopped": stopped,
            "unhealthy": unhealthy,
        },
        "containers": items,
    }
