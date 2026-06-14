# Security & Formal Analysis

## Overview

This plugin runs on a Proxmox VE node with root privileges. Any bug in the
GID-fix logic could cause silent backup failures or a privilege confusion in
the pmxcfs IPC layer. The following static analysis and test suite are run on
every push and must pass before a release is tagged.

## Tools and results

| Tool | Version | Scope | Status |
|------|---------|-------|--------|
| **mypy** | ≥ 1.9 | `src/bareos_fd_proxmox.py` | ✅ No errors |
| **bandit** | ≥ 1.7 | `src/`, `scripts/` | ✅ No HIGH/MEDIUM issues |
| **pytest** | ≥ 8.0 | `tests/` | ✅ All tests pass |

Analysis runs in a clean `debian:trixie-slim` container on every CI build
(see `.github/workflows/build-deb.yml`, step **Analyse**).

## Critical invariants verified by tests

### Wrapper (`scripts/vzdump-bareos`)

| Invariant | Test | Why it matters |
|-----------|------|----------------|
| `os.getgid() == 0` before exec | `test_wrapper.py::TestGIDFix::test_real_gid_is_zero_before_exec` | pmxcfs validates SO_PEERCRED.gid; bareos-fd runs with gid=124 |
| `os.getegid() == 0` before exec | `test_wrapper.py::TestGIDFix::test_effective_gid_is_zero_before_exec` | Same constraint on effective GID |
| `os.getgroups() == [0]` | `test_wrapper.py::TestGIDFix::test_supplementary_groups_contain_only_root` | Supplementary groups must not include bareos(124) |
| `SIGPIPE == SIG_DFL` before exec | `test_wrapper.py::TestSignalReset::test_sigpipe_reset_to_default` | bareos-fd has SIGPIPE=SIG_IGN; vzdump must see SIG_DFL |
| exec target is `/usr/bin/vzdump` | `test_wrapper.py::TestExecTarget::test_exec_path_is_vzdump` | Must not exec a shell or intermediate binary |
| argv forwarded correctly | `test_wrapper.py::TestExecTarget::test_args_forwarded` | guestid, --mode must reach vzdump unchanged |

### Plugin (`src/bareos_fd_proxmox.py`)

| Invariant | Test | Why it matters |
|-----------|------|----------------|
| `mode` defaults to `stop` | `test_options.py::TestDefaults::test_mode_default_is_stop` | Safe default: VM stopped before backup |
| `guestid` parsed as `int` | `test_options.py::TestGuestId::test_guestid_parsed_as_int` | String would produce wrong vzdump argv |
| Missing `guestid` raises | `test_options.py::TestGuestId::test_missing_guestid_raises_on_check` | Fail-fast before any IO |
| Unknown option raises | `test_options.py::TestUnknownOption::test_unknown_key_raises` | Prevent silent misconfiguration |
| Wrapper used (not raw vzdump) | `test_options.py::TestVzdumpCmd::test_cmd_uses_vzdump_bareos_wrapper` | GID fix only active via wrapper |

## Bandit findings

All findings are **LOW** severity or intentional (see `pyproject.toml` `[tool.bandit]` skips):

- **B603** (`subprocess_without_shell_equals_true`): Skipped — intentional. Using a list
  argument to `Popen` without `shell=True` is the *secure* pattern; `shell=True` would be
  the vulnerability. Bareos upstream uses the same pattern.
- **B606** (`start_process_with_no_shell`): Same rationale.

No HIGH or MEDIUM severity findings.

## Vulnerability disclosure

To report a security issue, open a GitHub issue with the label `security`.
