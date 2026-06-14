# Configuration — bareos-fd-proxmox-plugin

> 📦 [Installation ←](installation.md)

## Vue d'ensemble

La configuration est répartie sur deux machines :

| Où | Quoi |
|----|------|
| **Nœud Proxmox** (bareos-fd) | Définition du client, répertoire du plugin |
| **Bareos Director** | FileSet, Job, ressource Client |

---

## Nœud Proxmox — configuration bareos-fd

### `/etc/bareos/bareos-fd.d/client/myself.conf`

```
Client {
  Name = pve1-fd
  Plugin Directory = "/usr/lib/bareos/plugins"
  Plugin Names = "python3"
}
```

> Remplacer `pve1-fd` par le nom d'hôte du nœud + `-fd`.

### `/etc/hosts` sur le nœud Proxmox

Ajouter le nom d'hôte du Bareos Director :

```
192.168.20.81  bareos
```

### Redémarrage

```bash
systemctl restart bareos-filedaemon
# Vérifier l'absence d'erreurs
journalctl -u bareos-filedaemon -n 20
```

---

## Configuration du Bareos Director

### Ressource Client

`/etc/bareos/bareos-dir.d/client/pve1-fd.conf` :

```
Client {
  Name = pve1-fd
  Description = "Nœud Proxmox pve1 — plugin bareos-fd-proxmox"
  Address = 192.168.20.200        # IP du nœud Proxmox
  Password = "votre-mot-de-passe" # doit correspondre au mot de passe bareos-fd
  Maximum Concurrent Jobs = 1
}
```

### FileSet

`/etc/bareos/bareos-dir.d/fileset/FS-Proxmox-VM.conf` :

```
FileSet {
  Name = "FS-Proxmox-VM"
  Description = "VMs Proxmox via plugin vzdump"
  Include {
    Options {
      Signature = MD5
      Compression = LZO
    }
    Plugin = "python3:module_name=bareos_fd_proxmox:guestid=107:mode=stop"
  }
}
```

#### Options du plugin

| Option | Défaut | Description |
|--------|--------|-------------|
| `guestid` | *(obligatoire)* | VMID Proxmox (entier) |
| `mode` | `stop` | Mode vzdump : `stop`, `snapshot`, `suspend` |
| `restorepath` | `/var/lib/vz/dump` | Chemin local pour restauration sur disque |
| `restoretodisk` | `false` | Restaurer sur disque au lieu de streamer |
| `pctstorage` | *(vide)* | Storage Proxmox pour la restauration (ex. `local:`) |
| `force` | `false` | Forcer la restauration même si le guest existe déjà |

### Job

`/etc/bareos/bareos-dir.d/job/Backup-Proxmox-VM107.conf` :

```
Job {
  Name = "Backup-Proxmox-VM107"
  Description = "Sauvegarde complète de la VM 107 (jd2) via plugin Proxmox"
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

## Exemple complet fonctionnel

> Environnement : Director Bareos sur `192.168.20.81`, nœud Proxmox `pve1` sur
> `192.168.20.200`, VM 107 (`jd2`), mode `stop` (VM arrêtée pendant la sauvegarde),
> storage sur disque.

**1. Nœud Proxmox** (`192.168.20.200`) :

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

**2. Director** (`192.168.20.81`) :

```bash
# /etc/bareos/bareos-dir.d/client/pve1-fd.conf
Client {
  Name = pve1-fd
  Address = 192.168.20.200
  Password = "votre-mot-de-passe"
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

# Recharger le Director
systemctl reload bareos-director
```

**3. Test de sauvegarde :**

```bash
echo "run job=Backup-VM107 level=Full yes" | bconsole
# Attendre ~5 minutes (mode=stop met la VM hors tension), puis :
echo "llist jobs jobid=<N>" | bconsole
# Attendu : jobstatus=T, joberrors=0
```

---

## Résolution des problèmes

| Erreur | Cause | Solution |
|--------|-------|----------|
| `ipcc_send_rec: Unknown error -1` | GID non corrigé | Vérifier que `/usr/bin/vzdump-bareos` est installé et exécutable |
| `module_name without value` | Erreur de guillemets dans le FileSet | S'assurer que la ligne Plugin utilise des guillemets doubles autour de la valeur complète |
| `vzdump exited with code 255` | Échec IPC pmxcfs | Vérifier le fix GID ; tester manuellement `vzdump-bareos 107 --stdout --mode stop >/dev/null` |
| `Failed to authenticate` | Cascade de l'erreur précédente | Corriger l'erreur primaire d'abord |
| `Unknown option 'guest_id'` | Faute de frappe | L'option est `guestid` (sans underscore) |
