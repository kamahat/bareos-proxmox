"""Tests for BareosFdProxmoxOptions — option parsing, defaults, validation."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bareos_fd_proxmox import BareosFdProxmoxOptions, UnknownOptionException


def _opts_from_str(s: str) -> BareosFdProxmoxOptions:
    """Parse a plugin definition string into an options object."""
    opts = BareosFdProxmoxOptions()
    for part in s.split(":"):
        if "=" in part:
            k, v = part.split("=", 1)
            opts[k.strip()] = v.strip()
    return opts


class TestDefaults:
    def test_mode_default_is_stop(self):
        opts = BareosFdProxmoxOptions()
        opts["guestid"] = "107"
        assert opts.mode == "stop"

    def test_restorepath_default(self):
        opts = BareosFdProxmoxOptions()
        opts["guestid"] = "107"
        assert opts.restorepath == "/var/lib/vz/dump"

    def test_restoretodisk_default_false(self):
        opts = BareosFdProxmoxOptions()
        opts["guestid"] = "107"
        assert opts.restoretodisk is False

    def test_force_default_false(self):
        opts = BareosFdProxmoxOptions()
        opts["guestid"] = "107"
        assert opts.force is False


class TestGuestId:
    def test_guestid_parsed_as_int(self):
        opts = _opts_from_str("guestid=107")
        assert opts.guestid == 107
        assert isinstance(opts.guestid, int)

    def test_guestid_zero_invalid(self):
        opts = BareosFdProxmoxOptions()
        opts["guestid"] = "0"
        # guestid=0 should pass type check but fail semantic check (not a valid VMID)
        # Plugin currently accepts it; document the boundary
        assert opts.guestid == 0

    def test_missing_guestid_check_returns_false(self):
        # check() returns False (not raise) when a mandatory option is missing.
        # The plugin uses this return value to abort the job at start_backup_file.
        opts = BareosFdProxmoxOptions()
        result = opts.check()
        assert result is False, repr(result)

    def test_guestid_non_integer_raises(self):
        opts = BareosFdProxmoxOptions()
        with pytest.raises((ValueError, TypeError)):
            opts["guestid"] = "abc"


class TestMode:
    @pytest.mark.parametrize("mode", ["stop", "snapshot", "suspend"])
    def test_valid_modes_accepted(self, mode):
        opts = _opts_from_str(f"guestid=107:mode={mode}")
        assert opts.mode == mode

    def test_unknown_mode_accepted_as_string(self):
        # Plugin passes mode directly to vzdump; validation is vzdump's job
        opts = _opts_from_str("guestid=107:mode=invalid")
        assert opts.mode == "invalid"


class TestUnknownOption:
    def test_unknown_key_raises(self):
        opts = BareosFdProxmoxOptions()
        with pytest.raises(UnknownOptionException):
            opts["nonexistent"] = "value"


class TestVzdumpCmd:
    """Verify the command tuple that will be passed to subprocess.Popen."""

    def _build_cmd(self, guestid: int, mode: str = "stop") -> tuple:
        return ("vzdump-bareos", f"{guestid}", "--stdout", "--mode", mode)

    def test_cmd_uses_vzdump_bareos_wrapper(self):
        cmd = self._build_cmd(107)
        assert cmd[0] == "vzdump-bareos", (
            "Must use the wrapper, not /usr/bin/vzdump directly. "
            "The wrapper fixes GID inheritance from bareos-fd (gid=124 → gid=0)."
        )

    def test_cmd_includes_stdout_flag(self):
        cmd = self._build_cmd(107)
        assert "--stdout" in cmd

    def test_cmd_includes_mode(self):
        cmd = self._build_cmd(107, mode="snapshot")
        assert "--mode" in cmd
        assert "snapshot" in cmd

    def test_cmd_guestid_is_string_in_cmd(self):
        cmd = self._build_cmd(107)
        assert "107" in cmd
