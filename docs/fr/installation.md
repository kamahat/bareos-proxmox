# Installation — bareos-fd-proxmox-plugin

> ⚙️ [Configuration →](configuration.md)

## Prérequis

- Proxmox VE 7+ (testé sur PVE 8/9)
- Bareos File Daemon **25.x** installé sur le nœud Proxmox
- Package `bareos-filedaemon-python3-plugin` installé
- Python 3.10+
- Accès root sur le nœud Proxmox

> **Important :** Le plugin **doit** être installé sur le **nœud Proxmox lui-même** (pas sur
> un serveur Bareos dédié). `vzdump` doit s'exécuter localement sur le nœud où résident les VMs.

## Étape 1 — Installer Bareos File Daemon sur le nœud Proxmox

Si pas encore installé :

```bash
# Ajouter le dépôt Bareos (adapter à votre version de Bareos)
wget -q https://download.bareos.org/bareos/release/25/Debian_13/Release.key \
     -O /etc/apt/keyrings/bareos.gpg
echo "deb [signed-by=/etc/apt/keyrings/bareos.gpg] \
  https://download.bareos.org/bareos/release/25/Debian_13 /" \
  > /etc/apt/sources.list.d/bareos.list

apt-get update
apt-get install bareos-filedaemon bareos-filedaemon-python3-plugin
```

## Étape 2 — Installer bareos-fd-proxmox-plugin

**Option A — Téléchargement depuis GitHub Releases (recommandé)**

```bash
LATEST=$(curl -sSf https://api.github.com/repos/kamahat/bareos-proxmox/releases/latest \
         | grep '"tag_name"' | cut -d'"' -f4)
wget "https://github.com/kamahat/bareos-proxmox/releases/download/${LATEST}/bareos-fd-proxmox-plugin_${LATEST#v}_all.deb"
apt install ./bareos-fd-proxmox-plugin_*.deb
```

**Option B — Dépôt apt (recommandé pour les mises à jour récurrentes)**

```bash
# Importer la clé GPG
curl -fsSL https://kamahat.github.io/bareos-proxmox/apt-signing-key.asc \
  | gpg --dearmor > /etc/apt/keyrings/bareos-proxmox.gpg

# Ajouter le dépôt
echo "deb [signed-by=/etc/apt/keyrings/bareos-proxmox.gpg] \
  https://kamahat.github.io/bareos-proxmox stable main" \
  > /etc/apt/sources.list.d/bareos-proxmox.list

# Installer
apt-get update
apt-get install bareos-fd-proxmox-plugin
```

**Option C — Compilation depuis les sources**

```bash
git clone https://github.com/kamahat/bareos-proxmox.git
cd bareos-proxmox
apt-get install build-essential debhelper devscripts
dpkg-buildpackage -us -uc -b
apt install ../bareos-fd-proxmox-plugin_*.deb
```

## Étape 3 — Vérifier l'installation

Le package installe :

| Fichier | Rôle |
|---------|------|
| `/usr/lib/bareos/plugins/bareos_fd_proxmox.py` | Plugin Python Bareos |
| `/usr/bin/vzdump-bareos` | Wrapper GID-fix (critique — voir [SECURITY.md](../../SECURITY.md)) |
| `/etc/systemd/system/bareos-filedaemon.service.d/proxmox.conf` | Ajoute `SupplementaryGroups=root` |

```bash
# Vérifier la présence des fichiers
ls -la /usr/lib/bareos/plugins/bareos_fd_proxmox.py
ls -la /usr/bin/vzdump-bareos
cat /etc/systemd/system/bareos-filedaemon.service.d/proxmox.conf

# Vérifier que bareos-fd a redémarré et charge le plugin
systemctl status bareos-filedaemon
journalctl -u bareos-filedaemon --since "5 minutes ago"
```

## Étape 4 — Autoriser bareos-fd à se connecter au Director

Sur le nœud Proxmox, ajouter une entrée TLS-PSK dans bareos-fd pour votre Director
(voir [Configuration →](configuration.md)).

## Désinstallation

```bash
apt remove bareos-fd-proxmox-plugin
systemctl restart bareos-filedaemon
```
