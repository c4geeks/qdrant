# Install Qdrant on Rocky Linux 10 / AlmaLinux 10

Companion to: https://computingforgeeks.com/install-qdrant-rocky-linux/

Tested on Rocky Linux 10.1 (Red Quartz) with SELinux enforcing. Same steps apply to AlmaLinux 10 because they share the RHEL 10 package ecosystem.

## Two install paths

```bash
# Docker CE (with automatic kernel mismatch handling)
./install-docker.sh

# Rootless Podman (RHEL native, SELinux confined)
./install-podman.sh
```

Both scripts detect the latest Qdrant release tag and use the official upstream image.

## Files

- [`install-docker.sh`](./install-docker.sh) — installs Docker CE, handles the `kernel-modules-extra-matched` mismatch you hit on a fresh cloud image, runs Qdrant with the SELinux `:z` mount label.
- [`install-podman.sh`](./install-podman.sh) — installs Podman, runs Qdrant rootless with the `:z,U` bind mount flags rootless requires.
- [`qdrant.container`](./qdrant.container) — Quadlet unit for a systemd-managed rootless deployment. Drop at `~/.config/containers/systemd/qdrant.container`.

## Real gotchas this catches

1. **Docker daemon will not start on a fresh Rocky 10 cloud image**. The `kernel-modules-extra-matched` package pulled in by `docker-ce` is for a newer kernel than the one currently running. The script installs the matching kernel and prompts for a reboot.

2. **Rootless Podman bind mount fails without `:U`**. Without it Qdrant inside the container cannot write to the mount because of the user-namespace UID mapping. Symptom: `Permission denied (os error 13)`.

3. **`firewall-cmd --reload` wipes Docker's nftables rules**. After every reload, restart Docker so it re-injects them. Both scripts print the reminder.

## Production posture

This is the bare install. For real workloads add:

- API key + TLS reverse proxy (see `../tls-nginx/` once the security article ships)
- Snapshots to S3 (see `../backup/`)
- Prometheus monitoring (see `../monitoring/`)
