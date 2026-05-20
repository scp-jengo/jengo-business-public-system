#!/usr/bin/env python3
"""
Jengo Business - Configuration Loader.

Reads ~/.jengo/config.yaml, validates required fields, prints a summary.
Exits with code 1 if the configuration is missing or invalid.

Called by jengo.bat during the startup sequence.
"""

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

REQUIRED_FIELDS = [
    "identity_name",   # top-level alias  OR
    # nested under 'identity':
    # identity.name
    # identity.layer
    # identity.type
]

CONFIG_PATH = Path.home() / ".jengo" / "config.yaml"


def _get_nested(data: dict, *keys: str):
    """Traverse nested dict; return None if any key is missing."""
    node = data
    for k in keys:
        if not isinstance(node, dict):
            return None
        node = node.get(k)
    return node


def validate(config: dict) -> list[str]:
    """Return a list of validation error strings (empty = valid)."""
    errors: list[str] = []

    # Accept either top-level 'identity_name' OR nested 'identity.name'
    identity_name = config.get("identity_name") or _get_nested(config, "identity", "name")
    if not identity_name:
        errors.append("Missing 'identity_name' or 'identity.name'.")

    # 'layer' can be top-level or nested
    layer = config.get("layer") or _get_nested(config, "identity", "layer")
    if not layer:
        errors.append("Missing 'layer' or 'identity.layer'.")

    # inheritance_chain_path can be explicit or inferred from standard location
    chain_path = config.get("inheritance_chain_path")
    if not chain_path:
        # Check standard location
        default_chain = Path.home() / ".jengo" / "inheritance-chain.yaml"
        if not default_chain.exists():
            errors.append(
                "Missing 'inheritance_chain_path' in config and "
                f"~/.jengo/inheritance-chain.yaml not found."
            )

    return errors


def main() -> None:
    if not CONFIG_PATH.exists():
        print(f"ERROR: Configuration file not found: {CONFIG_PATH}", file=sys.stderr)
        print("Run the setup wizard first: setup-wizard.bat onboarding", file=sys.stderr)
        sys.exit(1)

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            config = yaml.safe_load(fh)
    except Exception as exc:
        print(f"ERROR: Failed to parse {CONFIG_PATH}: {exc}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(config, dict):
        print(f"ERROR: {CONFIG_PATH} must be a YAML mapping.", file=sys.stderr)
        sys.exit(1)

    errors = validate(config)
    if errors:
        print("ERROR: Configuration validation failed:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    # Print summary
    identity = config.get("identity", {})
    name = config.get("identity_name") or identity.get("name", "(unknown)")
    layer = config.get("layer") or identity.get("layer", "(unknown)")
    version = config.get("version", "?")

    print(f"Configuration loaded: {CONFIG_PATH}")
    print(f"  Identity: {name}")
    print(f"  Layer:    {layer}")
    print(f"  Version:  {version}")

    # Print constitutional AI thresholds if present
    cai = config.get("constitutional_ai", {})
    if cai:
        print(f"  Constitutional AI thresholds:")
        print(f"    L1: {cai.get('l1_threshold', 0.7)}")
        print(f"    L2: {cai.get('l2_threshold', 0.6)}")
        print(f"    L3: {cai.get('l3_threshold', 0.6)}")


if __name__ == "__main__":
    main()
