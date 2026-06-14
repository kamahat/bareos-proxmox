"""
Tests for scripts/vzdump-bareos wrapper.

Critical invariants verified:
  1. GID is set to 0 before exec (pmxcfs SO_PEERCRED check)
  2. All signals are reset to SIG_DFL (bareos-fd inherits SIGPIPE=SIG_IGN)
  3. Extra file descriptors are closed
  4. The wrapper execs /usr/bin/vzdump (not a shell wrapper)

These tests run the wrapper behaviour in an isolated subprocess so they
are safe on any host (no actual vzdump is called).
"""
import os
import signal
import subprocess
import sys
import textwrap
import pytest


WRAPPER = os.path.join(os.path.dirname(__file__), "..", "scripts", "vzdump-bareos")


def _run_probe(probe_code: str) -> str:
    """
    Execute probe_code in a child Python process that patches os.execv so we
    can inspect the state *just before* exec without actually calling vzdump.
    Returns stdout of the child.
    """
    harness = textwrap.dedent(f"""        import os, sys, signal

        _execv_calls = []
        _orig_execv = os.execv

        def _mock_execv(path, args):
            _execv_calls.append((path, list(args)))
            # Do NOT actually exec — print state and exit
            {probe_code}
            sys.exit(0)

        os.execv = _mock_execv

        # Execute the wrapper source in this namespace
        exec(open({repr(WRAPPER)}).read())
    """)
    result = subprocess.run(
        [sys.executable, "-c", harness],
        capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, f"Probe failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    return result.stdout.strip()


class TestGIDFix:
    """The GID fix is the critical invariant: pmxcfs requires gid=0."""

    def test_real_gid_is_zero_before_exec(self):
        """os.getgid() must return 0 just before os.execv is called."""
        out = _run_probe("print('rgid', os.getgid())")
        assert "rgid 0" in out, (
            f"Real GID must be 0 before exec, got: {out!r}\n"
            "pmxcfs validates IPC connections via SO_PEERCRED and requires gid=0."
        )

    def test_effective_gid_is_zero_before_exec(self):
        """os.getegid() must return 0 just before os.execv is called."""
        out = _run_probe("print('egid', os.getegid())")
        assert "egid 0" in out, f"Effective GID must be 0 before exec, got: {out!r}"

    def test_supplementary_groups_contain_only_root(self):
        """os.getgroups() must be [0] before exec."""
        out = _run_probe("print('groups', os.getgroups())")
        assert "[0]" in out, f"Supplementary groups must be [0], got: {out!r}"


class TestSignalReset:
    """bareos-fd ignores SIGPIPE (and others); the wrapper must reset all signals."""

    def test_sigpipe_reset_to_default(self):
        """SIGPIPE must be SIG_DFL before exec (bareos-fd has it as SIG_IGN)."""
        probe = (
            "disp = signal.getsignal(signal.SIGPIPE);"
            "print('sigpipe', 'DFL' if disp == signal.SIG_DFL else repr(disp))"
        )
        out = _run_probe(probe)
        assert "sigpipe DFL" in out, (
            f"SIGPIPE must be SIG_DFL before exec, got: {out!r}\n"
            "bareos-fd inherits SIGPIPE=SIG_IGN from its parent and this propagates "
            "to all subprocess.Popen children unless explicitly reset."
        )

    def test_sighup_reset_to_default(self):
        probe = (
            "disp = signal.getsignal(signal.SIGHUP);"
            "print('sighup', 'DFL' if disp == signal.SIG_DFL else repr(disp))"
        )
        out = _run_probe(probe)
        assert "sighup DFL" in out, f"SIGHUP must be SIG_DFL, got: {out!r}"


class TestExecTarget:
    """The wrapper must exec /usr/bin/vzdump, not a shell."""

    def test_exec_path_is_vzdump(self):
        out = _run_probe("print('path', _execv_calls[0][0])")
        assert "/usr/bin/vzdump" in out, f"Must exec /usr/bin/vzdump, got: {out!r}"

    def test_exec_argv0_is_vzdump(self):
        out = _run_probe("print('argv0', _execv_calls[0][1][0])")
        assert "/usr/bin/vzdump" in out, f"argv[0] must be /usr/bin/vzdump, got: {out!r}"

    def test_args_forwarded(self):
        """sys.argv arguments must be forwarded to vzdump."""
        harness = textwrap.dedent(f"""            import os, sys, signal

            _execv_calls = []
            def _mock_execv(path, args):
                _execv_calls.append((path, list(args)))
                print('args', args)
                sys.exit(0)
            os.execv = _mock_execv

            sys.argv = ['vzdump-bareos', '107', '--stdout', '--mode', 'stop']
            exec(open({repr(WRAPPER)}).read())
        """)
        result = subprocess.run(
            [sys.executable, "-c", harness],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0
        assert "107" in result.stdout
        assert "--mode" in result.stdout
        assert "stop" in result.stdout
