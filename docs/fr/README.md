# bareos-fd-proxmox-plugin

> 🇬🇧 **[English version](../../README.md)**

Plugin Bareos File Daemon pour **Proxmox VE** — sauvegarde les guests QEMU/LXC via
`vzdump --stdout`, sans fichier intermédiaire sur disque.

[![Build Debian package](https://github.com/kamahat/bareos-proxmox/actions/workflows/build-deb.yml/badge.svg)](https://github.com/kamahat/bareos-proxmox/actions/workflows/build-deb.yml)
[![Dernière version](https://img.shields.io/github/v/release/kamahat/bareos-proxmox)](https://github.com/kamahat/bareos-proxmox/releases/latest)

---

## ⚠️ Avertissement production

Ce plugin exécute `vzdump` en **root** sur un nœud Proxmox en production.
Consulter le document [Security & Formal Analysis](../../SECURITY.md) avant de déployer.
Chaque release est validée par une pipeline d'analyse statique (mypy + bandit + pytest).

---

## Liens rapides

| | |
|--|--|
| 📦 [Installation](installation.md) | Comment installer le package sur un nœud Proxmox |
| ⚙️ [Configuration](configuration.md) | Comment configurer Bareos Director et File Daemon |
| 🔒 [Sécurité](../../SECURITY.md) | Résultats de l'analyse formelle et invariants critiques |
| 🇬🇧 [English documentation](../../README.md) | Documentation en anglais |

---

## Le problème de GID (et la solution)

`bareos-fd` tourne avec `Gid=124` (le groupe `bareos`). `pmxcfs` — le démon du système de
fichiers cluster Proxmox — valide chaque connexion IPC via `SO_PEERCRED` et **exige `gid=0`**.
Sans correction, `vzdump` lancé par le plugin hérite `Gid=124` et échoue immédiatement :

```
ipcc_send_rec[1] failed: Unknown error -1   (x3 puis exit 255, puis timeout LogPipe 5 min)
```

Le wrapper `vzdump-bareos` (`/usr/bin/vzdump-bareos`) corrige cela en appelant
`os.setregid(0, 0)` + `os.setgroups([0])` avant `os.execv("/usr/bin/vzdump", ...)`.
Cet invariant est **vérifié automatiquement à chaque build** (`tests/test_wrapper.py`).

---

## Structure du dépôt

```
bareos-proxmox/
├── upstream/                  # source verbatim de bareos/bareos@0090141
├── patch/                     # notre patch minimal (diff)
├── src/                       # plugin patché (généré par CI)
├── scripts/vzdump-bareos      # wrapper GID-fix (installé dans /usr/bin/)
├── debian/                    # packaging Debian
├── tests/                     # suite de tests pytest
│   ├── conftest.py            # stubs pour les extensions C de bareos
│   ├── test_options.py        # parsing des options du plugin
│   └── test_wrapper.py        # invariants GID/signal/exec du wrapper
├── docs/
│   ├── en/                    # documentation anglaise
│   └── fr/                    # documentation française
├── SECURITY.md                # résultats de l'analyse formelle
└── .github/workflows/
    ├── build-deb.yml          # analyse → build → release
    ├── sync-upstream.yml      # sync upstream hebdomadaire + PR
    └── publish-apt.yml        # dépôt apt via GitHub Packages
```

---

## Résumé du patch

`patch/bareos_fd_proxmox.patch` ajoute au source upstream :

| Modification | Raison |
|-------------|--------|
| Option `mode` (défaut `stop`) | Passé en `--mode` à vzdump ; accepte `stop`, `snapshot`, `suspend` |
| Appelle `vzdump-bareos` au lieu de `vzdump` | Le wrapper gère la correction GID obligatoire |
| `start_new_session=True` dans `Popen` | Isole la session de processus de vzdump depuis bareos-fd |

---

## Licence

Source du plugin : GNU AGPL v3 (upstream, Bareos GmbH & Co. KG).
Wrapper, packaging, tests : MIT.
