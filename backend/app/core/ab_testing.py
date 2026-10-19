"""
A/B testing framework with deterministic hash-based bucketing.
Assigns sessions to experiment variants and logs assignments.
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ABTestManager:
    def __init__(self, config_path: Optional[Path] = None, log_path: Optional[Path] = None):
        backend_dir = Path(__file__).resolve().parent.parent.parent
        self._config_path = config_path or backend_dir / "config" / "ab_tests.yaml"
        self._log_path = log_path or backend_dir / "data" / "ab_test_log.jsonl"
        self._experiments: Dict[str, Dict[str, Any]] = {}
        self._load_config()

    def _load_config(self) -> None:
        if not self._config_path.exists():
            return
        try:
            import yaml
            with open(self._config_path, "r") as f:
                data = yaml.safe_load(f) or {}
        except ImportError:
            data = self._parse_yaml_fallback(self._config_path)
        except Exception as exc:
            logger.warning("Failed to load A/B config: %s", exc)
            return
        self._experiments = data.get("experiments", {})

    @staticmethod
    def _parse_yaml_fallback(path: Path) -> Dict[str, Any]:
        """Minimal YAML-like parser for when PyYAML is not installed."""
        try:
            import yaml
            with open(path, "r") as f:
                return yaml.safe_load(f) or {}
        except ImportError:
            return {}

    def get_active_experiments(self) -> List[str]:
        return [name for name, cfg in self._experiments.items() if cfg.get("enabled")]

    def assign(self, experiment_name: str, session_id: str) -> Optional[Dict[str, Any]]:
        exp = self._experiments.get(experiment_name)
        if not exp or not exp.get("enabled"):
            return None

        variants = exp.get("variants", {})
        if not variants:
            return None

        bucket = int(hashlib.sha256(f"{experiment_name}:{session_id}".encode()).hexdigest(), 16) % 100

        cumulative = 0
        chosen_variant: Optional[str] = None
        chosen_config: Optional[Dict[str, Any]] = None

        for variant_name, variant_cfg in variants.items():
            cumulative += variant_cfg.get("weight", 0)
            if bucket < cumulative and chosen_variant is None:
                chosen_variant = variant_name
                chosen_config = variant_cfg

        if chosen_variant is None:
            last_name = list(variants.keys())[-1]
            chosen_variant = last_name
            chosen_config = variants[last_name]

        assignment = {
            "experiment": experiment_name,
            "variant": chosen_variant,
            "flags": chosen_config.get("flags", {}),
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._log_assignment(assignment)
        return assignment

    def assign_all(self, session_id: str) -> Dict[str, Dict[str, Any]]:
        results: Dict[str, Dict[str, Any]] = {}
        for name in self.get_active_experiments():
            result = self.assign(name, session_id)
            if result:
                results[name] = result
        return results

    def get_flag_overrides(self, session_id: str) -> Dict[str, bool]:
        overrides: Dict[str, bool] = {}
        for assignment in self.assign_all(session_id).values():
            overrides.update(assignment.get("flags", {}))
        return overrides

    def _log_assignment(self, assignment: Dict[str, Any]) -> None:
        try:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._log_path, "a") as f:
                f.write(json.dumps(assignment) + "\n")
        except Exception as exc:
            logger.warning("Failed to log A/B assignment: %s", exc)

    def get_results(self) -> Dict[str, Dict[str, int]]:
        results: Dict[str, Dict[str, int]] = {}
        if not self._log_path.exists():
            return results
        try:
            with open(self._log_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    exp = entry.get("experiment", "unknown")
                    variant = entry.get("variant", "unknown")
                    if exp not in results:
                        results[exp] = {}
                    results[exp][variant] = results[exp].get(variant, 0) + 1
        except Exception as exc:
            logger.warning("Failed to read A/B log: %s", exc)
        return results


_manager: Optional[ABTestManager] = None


def get_ab_manager() -> ABTestManager:
    global _manager
    if _manager is None:
        _manager = ABTestManager()
    return _manager
