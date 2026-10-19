"""
Feature flag system with YAML config and env var overrides.
Flags control runtime behavior without code changes.
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_flag_store: Dict[str, bool] = {}
_loaded = False


def _find_config_path() -> Path:
    here = Path(__file__).resolve()
    backend_dir = here.parent.parent.parent
    return backend_dir / "config" / "feature_flags.yaml"


def _load_flags(config_path: Optional[Path] = None) -> Dict[str, bool]:
    global _flag_store, _loaded

    path = config_path or _find_config_path()
    raw: Dict[str, Any] = {}

    if path.exists():
        try:
            import yaml
            with open(path, "r") as f:
                raw = yaml.safe_load(f) or {}
        except ImportError:
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if ":" in line:
                        key, val = line.split(":", 1)
                        val = val.strip().lower()
                        raw[key.strip()] = val in ("true", "yes", "1")
        except Exception as exc:
            logger.warning("Failed to load feature flags from %s: %s", path, exc)

    for key, default_val in raw.items():
        env_name = f"FF_{key.upper()}"
        env_val = os.environ.get(env_name)
        if env_val is not None:
            _flag_store[key] = env_val.lower() in ("true", "1", "yes")
        else:
            _flag_store[key] = bool(default_val)

    _loaded = True
    _log_state()
    return _flag_store


def _log_state() -> None:
    parts = [f"{k}={'ON' if v else 'OFF'}" for k, v in sorted(_flag_store.items())]
    logger.info("Feature flags: %s", " | ".join(parts))


def get_flag(name: str, default: bool = False) -> bool:
    if not _loaded:
        _load_flags()
    return _flag_store.get(name, default)


def get_all_flags() -> Dict[str, bool]:
    if not _loaded:
        _load_flags()
    return dict(_flag_store)


def override_flag(name: str, value: bool) -> None:
    """Runtime override — useful for A/B test variant injection."""
    global _loaded
    if not _loaded:
        _load_flags()
    _flag_store[name] = value


def reload_flags(config_path: Optional[Path] = None) -> Dict[str, bool]:
    global _loaded
    _loaded = False
    return _load_flags(config_path)
