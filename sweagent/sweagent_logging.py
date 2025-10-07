"""Logging helpers for SWE-agent runtime."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("sweagent")


def configure_logging(verbose: bool = False) -> None:
    """Configure module-level logging handlers."""

    if logger.handlers:
        return

    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.setLevel(level)
    logger.addHandler(handler)


def write_json_log(path: Path, payload: dict[str, Any]) -> None:
    """Persist a JSON payload for auditing tool calls."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False)
        file.write("\n")

