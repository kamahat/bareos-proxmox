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

`/etc/bareos/bareos-dir.d/fileset/FS-Proxmox-VM.conf`:

```
FileSet {
  Name = "FS-Proxmox-VM"
  Description = "Proxmox VMs via vzdump plugin"
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
  FileSet = "FS-Proxmox-VM"
  Storage = File
  Pool = Full
  Messages = Standard
  Write Bootstrap = "/var/lib/bareos/%c.bsr"
  Priority = 10
  Maximum Concurrent Jobs = 1
}
```

---

## Complete working example

> Environment: Bareos Director on `192.168.20.81`, Proxmox node `pve1` at `192.168.20.200`,
> VM 107 (`jd2`), mode `stop` (VM powered off during backup), storage on disk.

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

**2. Director** (`192.168.20.81`):

```bash
# /etc/bareos/bareos-dir.d/client/pve1-fd.conf
Client {
  Name = pve1-fd
  Address = 192.168.20.200
  Password = "your-password-here"
  Maximum Concurrent Jobs = 1
}

# /etc/bareos/bareos-dir.d/fileset/FS-Proxmox-VM107.conf
FileSet {
  Name = "FS-Proxmox-VM107"
  Include {
    Options { Signature = MD5; Compression = LZO }
    Plugin = "python3:module_name=bareos_fd_proxmox:guestid=107:mode=stop"
  }
}

# /etc/bareos/bareos-dir.d/job/Backup-VM107.conf
Job {
  Name = "Backup-VM107"
  Type = Backup
  Level = Full
  Client = pve1-fd
  FileSet = "FS-Proxmox-VM107"
  Storage = File
  Pool = Full
  Messages = Standard
  Write Bootstrap = "/var/lib/bareos/%c.bsr"
}

# Reload Director
systemctl reload bareos-director
```

**3. Test run:**

```bash
echo "run job=Backup-VM107 level=Full yes" | bconsole
# Wait ~5 minutes (mode=stop pauses the VM), then:
echo "llist jobs jobid=<N>" | bconsole
# Expected: jobstatus=T, joberrors=0
```

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `ipcc_send_rec: Unknown error -1` | GID not fixed | Verify `/usr/bin/vzdump-bareos` is installed and executable |
| `module_name without value` | Quoting error in FileSet | Ensure the Plugin line uses double quotes around the full value |
| `vzdump exited with code 255` | pmxcfs IPC failure | Check GID fix; run `vzdump-bareos 107 --stdout --mode stop >/dev/null` manually |
| `Failed to authenticate` | Cascade from above | Fix the primary error first |
| `Unknown option 'guest_id'` | Typo | Option is `guestid` (no underscore) |
