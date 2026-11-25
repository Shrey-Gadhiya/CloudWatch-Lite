# Environment Setup & Prerequisites — CloudWatch Lite

This document records the development environment requirements, detected tool versions, and installation instructions for **CloudWatch Lite**.

---

## 1. System Requirements

| Resource | Minimum | Recommended | Detected on This Machine |
| :--- | :--- | :--- | :--- |
| **Operating System** | Windows 10/11 (64-bit) | Windows 11 with WSL 2 | Windows 11 |
| **CPU** | 2 cores | 4+ cores | 12 logical processors |
| **RAM** | 8 GB | 16 GB | ~15.7 GB (16 GB) |
| **Free Disk Space** | 15 GB | 30+ GB | 22.54 GB free on `C:` |

> [!NOTE]
> Docker images for Python, Prometheus, Grafana, Node Exporter, and cAdvisor typically consume 2–4 GB of disk space. Periodically running `docker system prune` helps keep disk usage low on `C:`.

---

## 2. Required Software & Verification Status

| Tool | Purpose | Status | Detected Version |
| :--- | :--- | :--- | :--- |
| **Python** | Backend API, monitoring agent, tests | Installed | `Python 3.14.7` (Docker target: `3.12-slim`) |
| **Git** | Version control & CI/CD triggers | Installed | `2.54.0.windows.1` |
| **Docker Desktop** | Local container runtime | Installed (Daemon Stopped) | `Docker 29.8.0` |
| **Docker Compose** | Multi-container orchestration | Installed | `v5.5.1` |
| **WSL 2** | Linux kernel backend for Docker | Enabled | Default Version `2` (`docker-desktop`) |
| **AWS CLI** | AWS ECR, IAM, Secrets Manager, CloudWatch | Installed | `aws-cli/2.40.2` |
| **Terraform** | Infrastructure as Code (AWS provisioning) | **Missing** | Not installed |

---

## 3. Missing / Action-Required Items

### A. Start Docker Desktop (Required before Phase 5)
Docker Desktop is installed, but the Docker Engine daemon is currently not running.

**How to start it:**
1. Open the Windows Start Menu and search for **Docker Desktop**.
2. Launch **Docker Desktop** and wait until the whale icon in the system tray stops animating and shows **Engine running**.
3. Verify in PowerShell:
   ```powershell
   docker info
   ```

### B. Install Terraform (Required before Phase 8)
Terraform is used in Phase 8 to provision AWS infrastructure (VPC, EC2/ECS, ECR, IAM, CloudWatch).

**Official Download Link:**
- [https://developer.hashicorp.com/terraform/install](https://developer.hashicorp.com/terraform/install)

**Installation Steps (Windows):**
1. **Option 1 — Using Winget (Recommended):**
   ```powershell
   winget install HashiCorp.Terraform
   ```
2. **Option 2 — Manual Zip Install:**
   - Download the **Windows AMD64** `.zip` from the official link above.
   - Extract `terraform.exe` to a folder such as `C:\Tools\terraform\`.
   - Add `C:\Tools\terraform\` to your Windows **System PATH** environment variable.
   - Restart PowerShell / your IDE terminal.

**Verify Installation:**
```powershell
terraform --version
```

---

## 4. Reference Installation Links (All Prerequisites)

If setting up on a fresh Windows 11 machine, install the following tools in order:

1. **WSL 2**:
   ```powershell
   wsl --install
   ```
   Documentation: [https://learn.microsoft.com/en-us/windows/wsl/install](https://learn.microsoft.com/en-us/windows/wsl/install)

2. **Git for Windows**:
   - Download: [https://git-scm.com/download/win](https://git-scm.com/download/win)

3. **Python (3.12+)**:
   - Download: [https://www.python.org/downloads/windows/](https://www.python.org/downloads/windows/)
   - Ensure **"Add python.exe to PATH"** is checked during installation.

4. **Docker Desktop for Windows**:
   - Download: [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)
   - Ensure **Use the WSL 2 based engine** is enabled in Docker Desktop Settings.

5. **AWS CLI v2**:
   - Download: [https://awscli.amazonaws.com/AWSCLIV2.msi](https://awscli.amazonaws.com/AWSCLIV2.msi)
   - Guide: [https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

6. **Terraform**:
   - Download: [https://developer.hashicorp.com/terraform/install](https://developer.hashicorp.com/terraform/install)

---

## 5. Verification Checklist

Run the following PowerShell commands to verify the complete environment:

```powershell
python --version
pip --version
git --version
docker --version
docker compose version
docker info
aws --version
terraform --version
wsl --status
```
