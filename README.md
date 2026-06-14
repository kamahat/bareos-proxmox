# bareos-fd-proxmox-plugin

Bareos File Daemon plugin for Proxmox VE - backs up VMs via `vzdump --stdout`.

## Why this repo

The Proxmox plugin ships in the [bareos/bareos](https://github.com/bareos/bareos) source tree
but is not distributed in the community Debian packages. This repo applies a minimal patch and
builds a ready-to-install `.deb`.

## The GID problem (and the fix)

`bareos-fd` runs with `Gid=124` (the `bareos` group). `pmxcfs` validates every IPC connection
via `SO_PEERCRED` and **requires `gid=0`**. Without a fix, `vzdump` launched by the plugin
inherits `Gid=124` and fails immediately:

```
ipcc_send_rec[1] failed: Unknown error -1   (x3 then exit 255)
```

The wrapper `vzdump-bareos` (`/usr/local/bin/vzdump-bareos`) fixes this by calling
`os.setregid(0, 0)` + `os.setgroups([0])` before `exec /usr/bin/vzdump`.

## Installation

```bash
wget https://github.com/kamahat/bareos-proxmox/releases/latest/download/bareos-fd-proxmox-plugin_1.0.0_all.deb
apt install ./bareos-fd-proxmox-plugin_1.0.0_all.deb
```

Configure bareos-fd on the Proxmox node (`/etc/bareos/bareos-fd.d/client/myself.conf`):

```
Client {
  Name = <hostname>-fd
  Plugin Directory = "/usr/lib/bareos/plugins"
  Plugin Names = "python3"
}
```

Director FileSet:

```
Plugin = "python3:module_name=bareos_fd_proxmox:guestid=<VMID>:mode=stop"
```

Available modes: `stop` (default, safest), `snapshot` (live VM, requires QEMU guest agent),
`suspend`.

## How it works

```
GitHub Action (weekly)          GitHub Action (on push / tag)
       |                                   |
       v                                   v
fetch upstream source          apply patch -> build .deb -> release
       |
compare to patch/
       |
  changed? -> open PR
```

## Patch summary

`patch/bareos_fd_proxmox.patch` adds:

- `mode` option (default `stop`) passed as `--mode` to vzdump
- calls `vzdump-bareos` instead of `vzdump` (wrapper handles GID fix)
- `start_new_session=True` in both `subprocess.Popen` calls

## Source

Upstream: `bareos/bareos@0090141`
Path: `core/src/plugins/filed/python/proxmox/bareos-fd-proxmox.py`
