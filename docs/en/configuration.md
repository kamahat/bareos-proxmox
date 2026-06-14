# Configuration — bareos-fd-proxmox-plugin

> 📦 [Installation ←](installation.md)

## Overview

Configuration is split across two machines:

| Where | What |
|-------|------|
| **Proxmox node** (bareos-fd) | Client definition, plugin directory |
| **Bareos Director** | FileSet, Job, Client resource |

---

## Proxmox node — bareos-fd configuration

### `/etc/bareos/bareos-fd.d/client/myself.conf`

```
Client {
  Name = pve1-fd
  Plugin Directory = "/usr/lib/bareos/plugins"
  Plugin Names = "python3"
}
```

> Replace `pve1-fd` with your node's hostname + `-fd`.

### `/etc/hosts` on the Proxmox node

Add your Bareos Director's hostname:

```
192.168.20.81  bareos
```

### Restart

```bash
systemctl restart bareos-filedaemon
# Verify no errors
journalctl -u bareos-filedaemon -n 20
```

---

## Bareos Director configuration

### Client resource

`/etc/bareos/bareos-dir.d/client/pve1-fd.conf`:

```
Client {
  Name = pve1-fd
  Description = "Proxmox node pve1 — bareos-fd-proxmox plugin"
  Address = 192.168.20.200        # IP of the Proxmox node
  Password = "your-fd-password"   # must match bareos-fd's director password
  Maximum Concurrent Jobs = 1
}
```

### FileSet

One FileSet per VM — each references a single `guestid`:

`/etc/bareos/bareos-dir.d/fileset/FS-Proxmox-VM107.conf`:

```
FileSet {
  Name = "FS-Proxmox-VM107"
  Description = "VM 107 (jd2) via vzdump plugin"
  Include {
    Options {
      Signature = MD5
      Compression = LZO
    }
    Plugin = "python3:module_name=bareos_fd_proxmox:guestid=107:mode=stop"
  }
}
```

#### Plugin options

| Option | Default | Description |
|--------|---------|-------------|
| `guestid` | *(required)* | Proxmox VMID (integer) |
| `mode` | `stop` | vzdump mode: `stop`, `snapshot`, `suspend` |
| `restorepath` | `/var/lib/vz/dump` | Local path for restore-to-disk |
| `restoretodisk` | `false` | Restore to disk instead of streaming |
| `pctstorage` | *(empty)* | Proxmox storage for restore (e.g. `local:`) |
| `force` | `false` | Force restore even if guest exists |

### Job

`/etc/bareos/bareos-dir.d/job/Backup-Proxmox-VM107.conf`:

```
Job {
  Name = "Backup-Proxmox-VM107"
  Description = "Full backup of VM 107 (jd2) via Proxmox plugin"
  Type = Backup
  Level = Full
  Client = pve1-fd
  FileSet = "FS-Proxmox-VM107"
  Storage = File
  Pool = Full
  Messages = Standard
  Write Bootstrap = "/var/lib/bareos/%c.bsr"
  Priority = 10
  Maximum Concurrent Jobs = 1
}
```

---

## Complete working example — two VMs

> **Validated in production** — Bareos Director on `192.168.20.81`, Proxmox node `pve1`
> at `192.168.20.200`, two VMs:
> - VM 107 `jd2` — JobId 19 & 20: **Backup OK**, 0 errors, ~5 min
> - VM 117 `docker-host` — JobId 21: **Backup OK**, 0 errors, ~9 min, 5.75 GB transferred

**1. Proxmox node** (`192.168.20.200`):

```bash
# /etc/bareos/bareos-fd.d/client/myself.conf
Client {
  Name = pve1-fd
  Plugin Directory = "/usr/lib/bareos/plugins"
  Plugin Names = "python3"
}

# /etc/hosts
192.168.20.81  bareos

systemctl restart bareos-filedaemon
```

**2. Director** (`192.168.20.81`) — repeat the FileSet + Job block for each VM:

```bash
# /etc/bareos/bareos-dir.d/client/pve1-fd.conf
Client {
  Name = pve1-fd
  Address = 192.168.20.200
  Password = "your-password-here"
  Maximum Concurrent Jobs = 1
}

# ── VM 107 (jd2) ─────────────────────────────────────────────────────────
# /etc/bareos/bareos-dir.d/fileset/FS-Proxmox-VM107.conf
FileSet {
  Name = "FS-Proxmox-VM107"
  Include {
    Options { Signature = MD5; Compression = LZO }
    Plugin = "python3:module_name=bareos_fd_proxmox:guestid=107:mode=stop"
  }
}

# /etc/bareos/bareos-dir.d/job/Backup-Proxmox-VM107.conf
Job {
  Name = "Backup-Proxmox-VM107"
  Type = Backup; Level = Full; Client = pve1-fd
  FileSet = "FS-Proxmox-VM107"; Storage = File; Pool = Full
  Messages = Standard
  Write Bootstrap = "/var/lib/bareos/%c.bsr"
}

# ── VM 117 (docker-host) ──────────────────────────────────────────────────
# /etc/bareos/bareos-dir.d/fileset/FS-Proxmox-VM117.conf
FileSet {
  Name = "FS-Proxmox-VM117"
  Include {
    Options { Signature = MD5; Compression = LZO }
    Plugin = "python3:module_name=bareos_fd_proxmox:guestid=117:mode=stop"
  }
}

# /etc/bareos/bareos-dir.d/job/Backup-Proxmox-VM117.conf
Job {
  Name = "Backup-Proxmox-VM117"
  Type = Backup; Level = Full; Client = pve1-fd
  FileSet = "FS-Proxmox-VM117"; Storage = File; Pool = Full
  Messages = Standard
  Write Bootstrap = "/var/lib/bareos/%c.bsr"
}

# Reload Director (no restart needed for new job/fileset resources)
echo "reload" | bconsole
```

**3. Test run:**

```bash
# Run a backup and follow it
echo "run job=Backup-Proxmox-VM117 yes" | bconsole
# => Job queued. JobId=N

# Check result (replace N)
echo "list jobid=N" | bconsole
# Expected: jobstatus=T, SD Errors=0, FD termination status=OK
```

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `ipcc_send_rec: Unknown error -1` | GID not fixed | Verify `/usr/bin/vzdump-bareos` is installed and executable |
| `module_name without value` | Quoting error in FileSet | Ensure the Plugin line uses double quotes around the full value |
| `vzdump exited with code 255` | pmxcfs IPC failure | Check GID fix; run `vzdump-bareos <vmid> --stdout --mode stop >/dev/null` manually |
| `Failed to authenticate` | Cascade from above | Fix the primary error first |
| `Unknown option 'guest_id'` | Typo | Option is `guestid` (no underscore) |
