#!/usr/bin/env python3
"""
Jengo Business - System Prompt Builder.

Builds a system prompt from the loaded identity configuration.
  1. Reads ~/.jengo/config.yaml to find the device layer path.
  2. Reads CORE_IDENTITY.md from the device layer directory.
  3. Prepends a constitutional AI framework summary.
  4. Prints the full system prompt to stdout.

Used by jengo_claudecode.bat:
  python startup/build-system-prompt.py > %TEMP%/jengo-system-prompt.txt

Exits with code 0 even if CORE_IDENTITY.md is not found (uses defaults).
"""

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed.", file=sys.stderr)
    sys.exit(1)

CONFIG_PATH = Path.home() / ".jengo" / "config.yaml"

CONSTITUTIONAL_SUMMARY = """## Constitutional AI Framework — ACTIVE

You are operating under the Jengo Three-Layer Constitutional AI Framework.
All actions must pass three simultaneous evaluations before execution:

**L1 — Rational Layer**
Evaluates logical consistency, goal alignment, reality grounding, and
consequence modeling. Threshold: ≥ 0.7.

**L2 — Empathic Layer (THE BRAKE) — NON-BYPASSABLE**
Evaluates harm potential to any party, cost-feeling (does the system register
what is being sacrificed?), stop conditions, and reversibility.
This layer CANNOT be disabled or bypassed. Threshold: ≥ 0.6.

**L3 — Social Layer**
Evaluates reciprocity (creates vs extracts value), feedback loop health,
and wholeness vs fragmentation. Threshold: ≥ 0.6.

An action is approved only if ALL THREE layers pass their thresholds.
L2 failure always blocks, regardless of L1/L3 scores.

---
"""


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except Exception:
        return {}


def _find_identity_md(config: dict) -> str | None:
    """
    Try to locate CORE_IDENTITY.md from the config.

    Checks:
    1. repositories.device-identity path
    2. Any path value in repositories
    3. inheritance_chain last entry's path
    """
    repos = config.get("repositories", {})
    if isinstance(repos, dict):
        # Prefer device-identity
        device_path = repos.get("device-identity") or repos.get("identity")
        if device_path:
            md = Path(device_path) / "CORE_IDENTITY.md"
            if md.exists():
                return md.read_text(encoding="utf-8")

        # Try all repo paths
        for path_val in repos.values():
            if isinstance(path_val, str):
                md = Path(path_val) / "CORE_IDENTITY.md"
                if md.exists():
                    return md.read_text(encoding="utf-8")

    # Try last entry in inheritance_chain
    chain = config.get("inheritance_chain", [])
    if isinstance(chain, list):
        for entry in reversed(chain):
            path_val = entry.get("path")
            if path_val:
                md = Path(path_val) / "CORE_IDENTITY.md"
                if md.exists():
                    return md.read_text(encoding="utf-8")

    return None


def build_prompt() -> str:
    config = _load_config()
    identity = config.get("identity", {})

    name = config.get("identity_name") or identity.get("name", "Jengo Agent")
    layer = config.get("layer") or identity.get("layer", "unknown")

    identity_md = _find_identity_md(config)

    parts = [
        CONSTITUTIONAL_SUMMARY,
        f"## Identity\n\n**Name:** {name}\n**Layer:** {layer}\n",
    ]

    if identity_md:
        parts.append(f"## Core Identity (from CORE_IDENTITY.md)\n\n{identity_md}\n")
    else:
        parts.append(
            "## Core Identity\n\n"
            "No CORE_IDENTITY.md found in device layer. "
            "Operating with default identity.\n"
        )

    # Append constitutional AI thresholds
    cai = config.get("constitutional_ai", {})
    if cai:
        parts.append(
            "## Constitutional AI Thresholds\n\n"
            f"- L1 threshold: {cai.get('l1_threshold', 0.7)}\n"
            f"- L2 threshold: {cai.get('l2_threshold', 0.6)}\n"
            f"- L3 threshold: {cai.get('l3_threshold', 0.6)}\n"
        )

    return "\n".join(parts)


if __name__ == "__main__":
    prompt = build_prompt()
    print(prompt)
    sys.exit(0)
