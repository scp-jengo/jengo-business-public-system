#!/usr/bin/env python3
"""
Jengo Business - Identity Field Reader.

Reads a specific field from the loaded identity configuration.

Usage:
  python startup/get-identity.py <field_name>

  field_name can be a top-level key or a dotted path, e.g.:
    name
    layer
    identity.name
    constitutional_ai.l2_threshold

Prints the value to stdout.
Exits with code 1 if the field is not found or config is missing.

Used by jengo_claudecode.bat to extract identity metadata for display.
"""

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed.", file=sys.stderr)
    sys.exit(1)

CONFIG_PATH = Path.home() / ".jengo" / "config.yaml"


def _traverse(data: dict, dotted_key: str):
    """Traverse a nested dict using a dotted key path."""
    parts = dotted_key.split(".")
    node = data
    for part in parts:
        if not isinstance(node, dict):
            return None
        node = node.get(part)
        if node is None:
            return None
    return node


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: get-identity.py <field_name>", file=sys.stderr)
        sys.exit(1)

    field = sys.argv[1].strip()

    if not CONFIG_PATH.exists():
        print(f"ERROR: Config not found at {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            config = yaml.safe_load(fh) or {}
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    # Try direct key first, then dotted traversal, then look inside 'identity' sub-dict
    value = config.get(field)
    if value is None and "." in field:
        value = _traverse(config, field)
    if value is None:
        # Try under 'identity' sub-dict as a convenience
        identity = config.get("identity", {})
        if isinstance(identity, dict):
            value = identity.get(field)
    if value is None:
        # Try under 'device' sub-dict
        device = config.get("device", {})
        if isinstance(device, dict):
            value = device.get(field)

    if value is None:
        print(f"ERROR: Field '{field}' not found in configuration.", file=sys.stderr)
        sys.exit(1)

    print(str(value))


if __name__ == "__main__":
    main()
