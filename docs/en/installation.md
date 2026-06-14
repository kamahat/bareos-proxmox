# Installation — bareos-fd-proxmox-plugin

> ⚙️ [Configuration →](configuration.md)

## Prerequisites

- Proxmox VE 7+ (tested on PVE 8/9)
- Bareos File Daemon **25.x** installed on the Proxmox node
- `bareos-filedaemon-python3-plugin` package installed
- Python 3.10+
- Root access on the Proxmox node

> **Important:** The plugin **must** be installed on the **Proxmox node itself** (not on a
> dedicated Bareos server). `vzdump` must run locally on the node where the VMs live.

## Step 1 — Install Bareos File Daemon on the Proxmox node

If not already installed:

```bash
# Add Bareos repository (adjust for your Bareos version)
wget -q https://download.bareos.org/bareos/release/25/Debian_13/Release.key \
     -O /etc/apt/keyrings/bareos.gpg
echo "deb [signed-by=/etc/apt/keyrings/bareos.gpg] \
  https://download.bareos.org/bareos/release/25/Debian_13 /" \
  > /etc/apt/sources.list.d/bareos.list

apt-get update
apt-get install bareos-filedaemon bareos-filedaemon-python3-plugin
```

## Step 2 — Install bareos-fd-proxmox-plugin

**Option A — Download from GitHub Releases (recommended)**

```bash
LATEST=$(curl -sSf https://api.github.com/repos/kamahat/bareos-proxmox/releases/latest \
         | grep '"tag_name"' | cut -d'"' -f4)
wget "https://github.com/kamahat/bareos-proxmox/releases/download/${LATEST}/bareos-fd-proxmox-plugin_${LATEST#v}_all.deb"
apt install ./bareos-fd-proxmox-plugin_*.deb
```

**Option B — apt repository (recommended for recurring updates)**

```bash
# Add GPG signing key
curl -fsSL https://kamahat.github.io/bareos-proxmox/apt-signing-key.asc \
  | gpg --dearmor > /etc/apt/keyrings/bareos-proxmox.gpg

# Add repository
echo "deb [signed-by=/etc/apt/keyrings/bareos-proxmox.gpg] \
  https://kamahat.github.io/bareos-proxmox stable main" \
  > /etc/apt/sources.list.d/bareos-proxmox.list

# Install
apt-get update
apt-get install bareos-fd-proxmox-plugin
```

**Option C — Build from source**

```bash
git clone https://github.com/kamahat/bareos-proxmox.git
cd bareos-proxmox
apt-get install build-essential debhelper devscripts
dpkg-buildpackage -us -uc -b
apt install ../bareos-fd-proxmox-plugin_*.deb
```

## Step 3 — Verify installation

The package installs:

| File | Purpose |
|------|---------|
| `/usr/lib/bareos/plugins/bareos_fd_proxmox.py` | Bareos Python plugin |
| `/usr/bin/vzdump-bareos` | GID-fix wrapper (critical — see [SECURITY.md](../../SECURITY.md)) |
| `/etc/systemd/system/bareos-filedaemon.service.d/proxmox.conf` | Adds `SupplementaryGroups=root` |

```bash
# Verify files are present
ls -la /usr/lib/bareos/plugins/bareos_fd_proxmox.py
ls -la /usr/bin/vzdump-bareos
cat /etc/systemd/system/bareos-filedaemon.service.d/proxmox.conf

# Verify bareos-fd restarted and loads the plugin
systemctl status bareos-filedaemon
journalctl -u bareos-filedaemon --since "5 minutes ago"
```

## Step 4 — Allow bareos-fd to connect to the Director

On the Proxmox node, add a TLS-PSK entry in bareos-fd for your Director (see
[Configuration →](configuration.md)).

## Uninstall

```bash
apt remove bareos-fd-proxmox-plugin
systemctl restart bareos-filedaemon
```
