"""Pytest configuration — mock the bareos C extensions so tests run without Bareos installed."""
import sys
import types

# ── stub BareosFdWrapper (wildcard-imported by the plugin) ────────────────
_wrapper = types.ModuleType("BareosFdWrapper")
for _k, _v in {
    "bRC_OK": 0, "bRC_Error": 1, "bRC_Skip": 2, "bRC_Term": 3,
    "bRC_Seen": 4, "bRC_Core": 5, "bRC_Stop": 6, "bRC_Cancel": 7, "bRC_Max": 8,
    "FT_REG": 1, "FT_LNKSAVED": 2, "FT_DIRBEGIN": 3, "FT_DIREND": 4,
    "FT_LNK": 5, "FT_SPEC": 6, "FT_NOACCESS": 7, "FT_NOFOLLOW": 8,
    "IO_OPEN": 1, "IO_READ": 2, "IO_WRITE": 3, "IO_CLOSE": 4, "IO_SEEK": 5,
    # BareosPlugin is a class decorator exported by BareosFdWrapper
    "BareosPlugin": lambda cls: cls,
    "bEventJobStart": 1, "bEventJobEnd": 2,
    "bEventStartBackupJob": 3, "bEventEndBackupJob": 4,
    "bEventStartRestoreJob": 5, "bEventEndRestoreJob": 6,
    "bEventLevel": 10, "bEventSince": 11,
    "bEventPluginCommand": 27, "bEventNewPluginOptions": 13,
}.items():
    setattr(_wrapper, _k, _v)
_wrapper.__all__ = [k for k in dir(_wrapper) if not k.startswith("_")]
sys.modules["BareosFdWrapper"] = _wrapper

# ── stub bareosfd ──────────────────────────────────────────────────────────
_bareosfd = types.ModuleType("bareosfd")
_bareosfd.M_INFO = 1
_bareosfd.M_WARNING = 2
_bareosfd.M_ERROR = 3
_bareosfd.M_FATAL = 4
_bareosfd.bRC_OK = 0
_bareosfd.bRC_Error = 1
_bareosfd.bRC_Skip = 2
_bareosfd.bRC_Term = 3
_bareosfd.bRC_Seen = 4
_bareosfd.bRC_Core = 5
_bareosfd.bRC_Stop = 6
_bareosfd.bRC_Cancel = 7
_bareosfd.bFileType = types.SimpleNamespace(FT_REG=1)
_bareosfd.JobMessage = lambda level, msg: None
_bareosfd.DebugMessage = lambda level, msg: None
sys.modules["bareosfd"] = _bareosfd

# ── stub BareosFdPluginBaseclass ───────────────────────────────────────────
_base_mod = types.ModuleType("BareosFdPluginBaseclass")


class _BaseClass:
    def __init__(self, plugindef):
        self.plugindef = plugindef


_base_mod.BareosFdPluginBaseclass = _BaseClass
sys.modules["BareosFdPluginBaseclass"] = _base_mod
