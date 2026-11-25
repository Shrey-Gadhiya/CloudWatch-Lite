/* CloudWatch Lite — Frontend Dashboard Controller */

const state = {
  activeView: "overview",
  charts: {},
  latestMetrics: null,
  latestContainers: null,
};

const VIEW_META = {
  overview: ["Overview", "Real-time system & container telemetry"],
  infrastructure: ["Infrastructure", "Local stack & monitoring services"],
  servers: ["Server Monitoring", "Host availability and resource utilization"],
  containers: ["Docker Containers", "Live container status via Docker SDK"],
  cpu: ["CPU Monitoring", "Per-core CPU utilization and frequency"],
  memory: ["Memory Monitoring", "RAM and swap allocation"],
  disk: ["Disk Monitoring", "Storage capacity and I/O counters"],
  network: ["Network Monitoring", "Network throughput and packet counters"],
  alerts: ["Alerts", "Threshold-based alerts and acknowledgements"],
  logs: ["Logs", "Structured application and alert events"],
  settings: ["Settings", "Active thresholds and API endpoints"],
};

function formatUptime(seconds) {
  if (seconds == null) return "--";
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m ${s}s`;
  return `${m}m ${s}s`;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = String(text ?? "");
  return div.innerHTML;
}

function initCharts() {
  const baseLineOpts = (maxVal = 100) => ({
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: "#94a3b8", maxTicksLimit: 8 }, grid: { color: "rgba(148,163,184,0.08)" } },
      y: { min: 0, max: maxVal, ticks: { color: "#94a3b8" }, grid: { color: "rgba(148,163,184,0.08)" } },
    },
  });

  state.charts.cpu = new Chart(document.getElementById("cpuChart"), {
    type: "line",
    data: {
      labels: [],
      datasets: [{ label: "CPU %", data: [], borderColor: "#3b82f6", backgroundColor: "rgba(59,130,246,0.15)", fill: true, tension: 0.3, pointRadius: 1 }],
    },
    options: baseLineOpts(100),
  });

  state.charts.ram = new Chart(document.getElementById("ramChart"), {
    type: "line",
    data: {
      labels: [],
      datasets: [{ label: "RAM %", data: [], borderColor: "#38bdf8", backgroundColor: "rgba(56,189,248,0.15)", fill: true, tension: 0.3, pointRadius: 1 }],
    },
    options: baseLineOpts(100),
  });

  state.charts.disk = new Chart(document.getElementById("diskChart"), {
    type: "doughnut",
    data: {
      labels: ["Used (GB)", "Free (GB)"],
      datasets: [{ data: [0, 1], backgroundColor: ["#f59e0b", "#1e293b"], borderWidth: 0 }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: { legend: { position: "bottom", labels: { color: "#cbd5e1" } } },
    },
  });

  state.charts.net = new Chart(document.getElementById("netChart"), {
    type: "bar",
    data: {
      labels: ["Sent (MB)", "Received (MB)"],
      datasets: [{ label: "MB", data: [0, 0], backgroundColor: ["#3b82f6", "#22c55e"], borderRadius: 6 }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#94a3b8" }, grid: { display: false } },
        y: { beginAtZero: true, ticks: { color: "#94a3b8" }, grid: { color: "rgba(148,163,184,0.08)" } },
      },
    },
  });

  state.charts.latency = new Chart(document.getElementById("latencyChart"), {
    type: "line",
    data: {
      labels: [],
      datasets: [{ label: "ms", data: [], borderColor: "#a855f7", backgroundColor: "rgba(168,85,247,0.15)", fill: true, tension: 0.3, pointRadius: 1 }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#94a3b8", maxTicksLimit: 6 }, grid: { color: "rgba(148,163,184,0.08)" } },
        y: { beginAtZero: true, ticks: { color: "#94a3b8" }, grid: { color: "rgba(148,163,184,0.08)" } },
      },
    },
  });
}

async function fetchJson(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(`${url} returned ${res.status}`);
  return res.json();
}

function renderOverview(metrics, history, servers, containers, alerts) {
  document.getElementById("envBadgeText").textContent =
    `${metrics.host.hostname} (${metrics.host.environment})`;

  document.getElementById("kpiTotalServers").textContent = servers.summary.total;
  document.getElementById("kpiOnlineOffline").textContent =
    `${servers.summary.online} online / ${servers.summary.offline} offline`;

  document.getElementById("kpiCpu").textContent = `${metrics.cpu.percent}%`;
  document.getElementById("kpiCpuCores").textContent =
    `${metrics.cpu.logical_cores} logical / ${metrics.cpu.physical_cores} physical`;

  document.getElementById("kpiRam").textContent = `${metrics.memory.percent}%`;
  document.getElementById("kpiRamDetail").textContent =
    `${metrics.memory.used_gb} / ${metrics.memory.total_gb} GB`;

  document.getElementById("kpiDisk").textContent = `${metrics.disk.percent}%`;
  document.getElementById("kpiDiskDetail").textContent =
    `${metrics.disk.used_gb} / ${metrics.disk.total_gb} GB`;

  const totalNetMb = (metrics.network.sent_mb + metrics.network.recv_mb).toFixed(1);
  document.getElementById("kpiNet").textContent = `${totalNetMb} MB`;
  document.getElementById("kpiNetDetail").textContent =
    `TX ${metrics.network.sent_mb} MB / RX ${metrics.network.recv_mb} MB`;

  if (containers.available) {
    document.getElementById("kpiContainers").textContent = containers.summary.running;
    document.getElementById("kpiContainersDetail").textContent =
      `${containers.summary.total} total (${containers.summary.stopped} stopped)`;
  } else {
    document.getElementById("kpiContainers").textContent = "Unavailable";
    document.getElementById("kpiContainersDetail").textContent = "Docker socket not accessible";
  }

  document.getElementById("kpiUptime").textContent = formatUptime(metrics.host.app_uptime_seconds);
  document.getElementById("kpiLatency").textContent = `API latency: ${metrics.response_time_ms} ms`;

  document.getElementById("kpiAlerts").textContent = metrics.active_alerts;
  const badge = document.getElementById("sidebarAlertBadge");
  if (metrics.active_alerts > 0) {
    badge.textContent = metrics.active_alerts;
    badge.classList.remove("d-none");
  } else {
    badge.classList.add("d-none");
  }

  // Update charts from real history
  const points = history.history.length
    ? history.history
    : [{
        timestamp: metrics.timestamp,
        cpu_percent: metrics.cpu.percent,
        ram_percent: metrics.memory.percent,
        response_time_ms: metrics.response_time_ms,
      }];

  const labels = points.map((p) => new Date(p.timestamp).toLocaleTimeString());
  state.charts.cpu.data.labels = labels;
  state.charts.cpu.data.datasets[0].data = points.map((p) => p.cpu_percent);
  state.charts.cpu.update();

  state.charts.ram.data.labels = labels;
  state.charts.ram.data.datasets[0].data = points.map((p) => p.ram_percent);
  state.charts.ram.update();

  state.charts.disk.data.datasets[0].data = [metrics.disk.used_gb, metrics.disk.free_gb];
  state.charts.disk.update();

  state.charts.net.data.datasets[0].data = [metrics.network.sent_mb, metrics.network.recv_mb];
  state.charts.net.update();

  state.charts.latency.data.labels = labels;
  state.charts.latency.data.datasets[0].data = points.map((p) => p.response_time_ms);
  state.charts.latency.update();

  // Host health mini table
  document.getElementById("overviewServerTable").innerHTML = buildServersTable(servers.servers);

  // Recent alerts
  const alertsEl = document.getElementById("overviewAlertsList");
  if (!alerts.alerts.length) {
    alertsEl.innerHTML = `<div class="text-muted small">No alerts recorded. All monitored thresholds are healthy.</div>`;
  } else {
    alertsEl.innerHTML = alerts.alerts.slice(0, 5).map((a) => `
      <div class="alert-item severity-${escapeHtml(a.severity)}">
        <div class="d-flex justify-content-between">
          <strong>${escapeHtml(a.severity.toUpperCase())} · ${escapeHtml(a.metric)}</strong>
          <span class="badge ${a.status === "active" ? "bg-danger" : "bg-success"}">${escapeHtml(a.status)}</span>
        </div>
        <div class="text-muted small mt-1">${escapeHtml(a.message)}</div>
      </div>
    `).join("");
  }
}

function buildServersTable(servers) {
  return `
    <table class="table table-hover align-middle">
      <thead>
        <tr>
          <th>Hostname</th><th>OS</th><th>Status</th><th>CPU</th><th>RAM</th><th>Disk</th><th>Uptime</th>
        </tr>
      </thead>
      <tbody>
        ${servers.map((s) => `
          <tr>
            <td class="fw-semibold">${escapeHtml(s.hostname)}</td>
            <td>${escapeHtml(s.os)} (${escapeHtml(s.architecture)})</td>
            <td><span class="badge bg-success">${escapeHtml(s.status)}</span></td>
            <td>${s.cpu_percent}%</td>
            <td>${s.ram_percent}%</td>
            <td>${s.disk_percent}%</td>
            <td class="font-mono">${formatUptime(s.uptime_seconds)}</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function renderContainers(containers) {
  const badge = document.getElementById("dockerAvailabilityBadge");
  const target = document.getElementById("containersTableContainer");

  if (!containers.available) {
    badge.className = "badge bg-warning text-dark";
    badge.textContent = "Unavailable";
    target.innerHTML = `
      <div class="alert alert-warning mb-0">
        <strong>Docker Engine unavailable:</strong> ${escapeHtml(containers.error || "Socket not mounted or daemon stopped.")}
      </div>`;
    return;
  }

  badge.className = "badge bg-success";
  badge.textContent = `${containers.summary.running} Running / ${containers.summary.total} Total`;

  if (!containers.containers.length) {
    target.innerHTML = `<p class="text-muted mb-0">No Docker containers found.</p>`;
    return;
  }

  target.innerHTML = `
    <table class="table table-hover align-middle">
      <thead>
        <tr><th>ID</th><th>Name</th><th>Image</th><th>Status</th><th>Health</th></tr>
      </thead>
      <tbody>
        ${containers.containers.map((c) => `
          <tr>
            <td class="font-mono">${escapeHtml(c.id)}</td>
            <td class="fw-semibold">${escapeHtml(c.name)}</td>
            <td class="font-mono small">${escapeHtml(c.image)}</td>
            <td><span class="badge ${c.status === "running" ? "bg-success" : "bg-secondary"}">${escapeHtml(c.status)}</span></td>
            <td><span class="badge ${c.health === "healthy" ? "bg-success" : c.health === "unhealthy" ? "bg-danger" : "bg-dark"}">${escapeHtml(c.health)}</span></td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function renderDetailedViews(metrics, servers, containers) {
  document.getElementById("serversTableContainer").innerHTML = buildServersTable(servers.servers);

  document.getElementById("infraDetails").innerHTML = `
    <div class="col-md-4"><div class="kpi-card"><div class="kpi-header">Host</div><div class="kpi-value fs-5">${escapeHtml(metrics.host.hostname)}</div><div class="kpi-meta">${escapeHtml(metrics.host.os)} ${escapeHtml(metrics.host.os_release)}</div></div></div>
    <div class="col-md-4"><div class="kpi-card"><div class="kpi-header">Runtime</div><div class="kpi-value fs-5">Python ${escapeHtml(metrics.host.python_version)}</div><div class="kpi-meta">Mode: ${escapeHtml(metrics.host.environment)}</div></div></div>
    <div class="col-md-4"><div class="kpi-card"><div class="kpi-header">Docker Engine</div><div class="kpi-value fs-5">${containers.available ? "Connected" : "Unavailable"}</div><div class="kpi-meta">${containers.available ? `${containers.summary.total} containers detected` : "Not accessible"}</div></div></div>
  `;

  document.getElementById("cpuDetailsContainer").innerHTML = `
    <p class="mb-3">Overall CPU: <strong>${metrics.cpu.percent}%</strong> · Frequency: <strong>${metrics.cpu.frequency_mhz ?? "Unavailable"} MHz</strong></p>
    <div class="row g-2">
      ${metrics.cpu.per_core.map((val, idx) => `
        <div class="col-6 col-md-3">
          <div class="p-2 rounded bg-dark border border-secondary-subtle">
            <div class="d-flex justify-content-between small mb-1"><span>Core ${idx}</span><span>${val}%</span></div>
            <div class="progress" style="height:6px;"><div class="progress-bar bg-primary" style="width:${val}%"></div></div>
          </div>
        </div>
      `).join("")}
    </div>
  `;

  document.getElementById("memoryDetailsContainer").innerHTML = `
    <div class="row g-3">
      <div class="col-md-4"><div class="kpi-card"><div class="kpi-header">Used RAM</div><div class="kpi-value">${metrics.memory.used_gb} GB</div><div class="kpi-meta">${metrics.memory.percent}% of ${metrics.memory.total_gb} GB</div></div></div>
      <div class="col-md-4"><div class="kpi-card"><div class="kpi-header">Available RAM</div><div class="kpi-value">${metrics.memory.available_gb} GB</div></div></div>
      <div class="col-md-4"><div class="kpi-card"><div class="kpi-header">Swap Usage</div><div class="kpi-value">${metrics.memory.swap_percent}%</div><div class="kpi-meta">Total ${metrics.memory.swap_total_gb} GB</div></div></div>
    </div>
  `;

  document.getElementById("diskDetailsContainer").innerHTML = `
    <div class="row g-3">
      <div class="col-md-4"><div class="kpi-card"><div class="kpi-header">Mount (${escapeHtml(metrics.disk.mount)})</div><div class="kpi-value">${metrics.disk.percent}%</div><div class="kpi-meta">${metrics.disk.used_gb} / ${metrics.disk.total_gb} GB</div></div></div>
      <div class="col-md-4"><div class="kpi-card"><div class="kpi-header">Disk Read</div><div class="kpi-value">${metrics.disk.read_mb} MB</div></div></div>
      <div class="col-md-4"><div class="kpi-card"><div class="kpi-header">Disk Write</div><div class="kpi-value">${metrics.disk.write_mb} MB</div></div></div>
    </div>
  `;

  document.getElementById("networkDetailsContainer").innerHTML = `
    <div class="row g-3">
      <div class="col-md-3"><div class="kpi-card"><div class="kpi-header">Data Sent</div><div class="kpi-value">${metrics.network.sent_mb} MB</div><div class="kpi-meta">${metrics.network.packets_sent} packets</div></div></div>
      <div class="col-md-3"><div class="kpi-card"><div class="kpi-header">Data Received</div><div class="kpi-value">${metrics.network.recv_mb} MB</div><div class="kpi-meta">${metrics.network.packets_recv} packets</div></div></div>
      <div class="col-md-3"><div class="kpi-card"><div class="kpi-header">Errors In</div><div class="kpi-value">${metrics.network.errin}</div></div></div>
      <div class="col-md-3"><div class="kpi-card"><div class="kpi-header">Errors Out</div><div class="kpi-value">${metrics.network.errout}</div></div></div>
    </div>
  `;

  document.getElementById("settingsContainer").innerHTML = `
    <div class="row g-3">
      <div class="col-md-6">
        <h6>Alert Thresholds</h6>
        <ul class="list-group list-group-flush">
          <li class="list-group-item bg-transparent text-light border-secondary-subtle d-flex justify-content-between"><span>CPU Warning Threshold</span><strong>${metrics.thresholds.cpu}%</strong></li>
          <li class="list-group-item bg-transparent text-light border-secondary-subtle d-flex justify-content-between"><span>RAM Warning Threshold</span><strong>${metrics.thresholds.ram}%</strong></li>
          <li class="list-group-item bg-transparent text-light border-secondary-subtle d-flex justify-content-between"><span>Disk Warning Threshold</span><strong>${metrics.thresholds.disk}%</strong></li>
        </ul>
      </div>
      <div class="col-md-6">
        <h6>Available Endpoints</h6>
        <ul class="list-group list-group-flush font-mono small">
          <li class="list-group-item bg-transparent text-light border-secondary-subtle">GET /api/health</li>
          <li class="list-group-item bg-transparent text-light border-secondary-subtle">GET /api/metrics</li>
          <li class="list-group-item bg-transparent text-light border-secondary-subtle">GET /api/metrics/history</li>
          <li class="list-group-item bg-transparent text-light border-secondary-subtle">GET /api/servers</li>
          <li class="list-group-item bg-transparent text-light border-secondary-subtle">GET /api/containers</li>
          <li class="list-group-item bg-transparent text-light border-secondary-subtle">GET /api/alerts · POST /api/alerts/acknowledge</li>
          <li class="list-group-item bg-transparent text-light border-secondary-subtle">GET /api/logs · GET /metrics (Prometheus)</li>
        </ul>
      </div>
    </div>
  `;
}

async function loadAlertsTable() {
  const severity = document.getElementById("alertSeverityFilter").value;
  const status = document.getElementById("alertStatusFilter").value;
  const data = await fetchJson(`/api/alerts?severity=${severity}&status=${status}`);
  const target = document.getElementById("alertsTableContainer");

  if (!data.alerts.length) {
    target.innerHTML = `<p class="text-muted mb-0">No alerts match the selected filter.</p>`;
    return;
  }

  target.innerHTML = `
    <table class="table table-hover align-middle">
      <thead><tr><th>ID</th><th>Time</th><th>Severity</th><th>Source</th><th>Metric</th><th>Message</th><th>Status</th><th>Action</th></tr></thead>
      <tbody>
        ${data.alerts.map((a) => `
          <tr>
            <td>#${a.id}</td>
            <td class="font-mono small">${new Date(a.timestamp).toLocaleString()}</td>
            <td><span class="badge ${a.severity === "critical" ? "bg-danger" : "bg-warning text-dark"}">${escapeHtml(a.severity)}</span></td>
            <td>${a.source === "TEST DATA" ? `<span class="badge bg-info text-dark">TEST DATA</span>` : escapeHtml(a.source)}</td>
            <td>${escapeHtml(a.metric)}</td>
            <td>${escapeHtml(a.message)}</td>
            <td><span class="badge ${a.status === "active" ? "bg-danger" : "bg-success"}">${escapeHtml(a.status)}</span></td>
            <td>
              ${a.acknowledged
                ? `<span class="text-success small"><i class="bi bi-check-circle-fill"></i> Acked</span>`
                : `<button class="btn btn-sm btn-outline-primary" onclick="ackAlert(${a.id})">Acknowledge</button>`}
            </td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

window.triggerTestAlert = async function (metric, value) {
  const feedback = document.getElementById("testAlertFeedback");
  try {
    const res = await fetch("/api/test/trigger-alert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ metric, value }),
    });
    const data = await res.json();
    if (!res.ok) {
      feedback.className = "small mt-2 text-danger";
      feedback.textContent = data.error || "Failed to trigger test alert.";
    } else {
      feedback.className = "small mt-2 text-success";
      feedback.textContent = `Triggered #${data.alert.id}: ${data.alert.message}`;
      await refreshAll();
    }
  } catch (err) {
    feedback.className = "small mt-2 text-danger";
    feedback.textContent = `Error: ${err.message}`;
  }
};

window.ackAlert = async function (id) {
  await fetchJson("/api/alerts/acknowledge", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id }),
  });
  await refreshAll();
};

async function loadLogs() {
  const level = document.getElementById("logLevelFilter").value;
  const data = await fetchJson(`/api/logs?level=${level}`);
  const el = document.getElementById("logsContainer");
  if (!data.logs.length) {
    el.innerHTML = `<div class="text-muted">No logs recorded.</div>`;
    return;
  }
  el.innerHTML = data.logs.map((l) => `
    <div class="log-line">
      <span class="text-muted">${escapeHtml(l.timestamp)}</span>
      <span class="badge ${l.level === "CRITICAL" ? "bg-danger" : l.level === "WARNING" ? "bg-warning text-dark" : "bg-info text-dark"}">${escapeHtml(l.level)}</span>
      <span class="text-primary">[${escapeHtml(l.source)}]</span>
      <span>${escapeHtml(l.message)}</span>
    </div>
  `).join("");
}

async function refreshAll() {
  try {
    const [health, metrics, history, servers, containers, alerts] = await Promise.all([
      fetchJson("/api/health"),
      fetchJson("/api/metrics"),
      fetchJson("/api/metrics/history?limit=40"),
      fetchJson("/api/servers"),
      fetchJson("/api/containers"),
      fetchJson("/api/alerts"),
    ]);

    document.getElementById("healthDot").className = "status-dot dot-online";
    document.getElementById("healthLabel").textContent = `API ${health.status}`;
    document.getElementById("lastUpdated").textContent = new Date().toLocaleTimeString();

    renderOverview(metrics, history, servers, containers, alerts);
    renderContainers(containers);
    renderDetailedViews(metrics, servers, containers);
    await loadAlertsTable();
    await loadLogs();
  } catch (err) {
    document.getElementById("healthDot").className = "status-dot dot-offline";
    document.getElementById("healthLabel").textContent = "API Unavailable";
    console.error("Dashboard refresh failed:", err);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initCharts();

  document.querySelectorAll(".sidebar-nav .nav-link").forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const view = link.dataset.view;
      document.querySelectorAll(".sidebar-nav .nav-link").forEach((n) => n.classList.remove("active"));
      link.classList.add("active");
      document.querySelectorAll(".view-section").forEach((s) => s.classList.remove("active"));
      document.getElementById(`view-${view}`).classList.add("active");
      const [title, sub] = VIEW_META[view];
      document.getElementById("pageTitle").textContent = title;
      document.getElementById("pageSubtitle").textContent = sub;
      document.getElementById("sidebar").classList.remove("mobile-open");
    });
  });

  document.getElementById("sidebarToggle").addEventListener("click", () => {
    document.getElementById("sidebar").classList.toggle("collapsed");
  });

  document.getElementById("mobileMenuBtn").addEventListener("click", () => {
    document.getElementById("sidebar").classList.toggle("mobile-open");
  });

  document.getElementById("refreshBtn").addEventListener("click", refreshAll);
  document.getElementById("alertSeverityFilter").addEventListener("change", loadAlertsTable);
  document.getElementById("alertStatusFilter").addEventListener("change", loadAlertsTable);
  document.getElementById("logLevelFilter").addEventListener("change", loadLogs);

  refreshAll();
  setInterval(refreshAll, 5000);
});
