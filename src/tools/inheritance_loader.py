"""
Inheritance Loader.

Reads inheritance-chain.yaml, loads each layer in order, merges
configurations (later layers override earlier ones), and returns a
LoadedIdentity.

CLI entrypoint:
  python -m jengo.tools.inheritance_loader --load   # load and print summary
  python -m jengo.tools.inheritance_loader --sync   # sync remotes then load

inheritance-chain.yaml schema::

    version: '1.0.0'
    layer: my-layer
    parent_layer: parent-layer
    inheritance:
      - name: public-identity
        repo: https://github.com/scp-jengo/jengo-business-public-identity.git
      - name: my-identity
        path: /home/user/jengo-business/my-identity
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .knowledge_sync import KnowledgeSync


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class LayerConfig:
    """Configuration loaded from one layer."""
    name: str
    source_path: str
    data: dict[str, Any]


@dataclass
class LoadedIdentity:
    """Merged identity from all inheritance chain layers."""
    layer: str
    parent_layer: str | None
    config: dict[str, Any]           # merged configuration
    layers_loaded: list[LayerConfig]  # individual layers, in order
    warnings: list[str] = field(default_factory=list)

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class InheritanceLoader:
    """
    Load and merge the inheritance chain into a unified configuration.

    Later layers override earlier layers (child overrides parent).
    """

    def __init__(self) -> None:
        self._syncer = KnowledgeSync()

    def load(self, config_path: str) -> LoadedIdentity:
        """
        Read inheritance-chain.yaml and merge all layers.

        Parameters
        ----------
        config_path:
            Path to the inheritance-chain.yaml file.

        Returns
        -------
        LoadedIdentity with merged configuration.
        """
        chain_path = Path(config_path).resolve()
        if not chain_path.exists():
            raise FileNotFoundError(f"Inheritance chain file not found: {chain_path}")

        with open(chain_path, "r", encoding="utf-8") as fh:
            chain_config = yaml.safe_load(fh)

        if not isinstance(chain_config, dict):
            raise ValueError(f"Expected a YAML mapping in '{chain_path}'")

        layer = chain_config.get("layer", "unknown")
        parent_layer = chain_config.get("parent_layer")
        entries = chain_config.get("inheritance", [])

        layers: list[LayerConfig] = []
        warnings: list[str] = []
        merged: dict[str, Any] = {}

        for entry in entries:
            name = entry.get("name", "unnamed")
            path_str = entry.get("path")

            if not path_str:
                warnings.append(
                    f"Layer '{name}' has no local 'path' — skipped (run --sync first)."
                )
                continue

            layer_path = Path(path_str)
            if not layer_path.exists():
                warnings.append(f"Layer '{name}' path '{layer_path}' not found — skipped.")
                continue

            layer_data = self._load_layer(layer_path)
            layers.append(LayerConfig(
                name=name,
                source_path=str(layer_path),
                data=layer_data,
            ))
            # Merge: later overrides earlier
            _deep_merge(merged, layer_data)

        # Always include chain-level keys
        merged.setdefault("layer", layer)
        merged.setdefault("parent_layer", parent_layer)

        return LoadedIdentity(
            layer=layer,
            parent_layer=parent_layer,
            config=merged,
            layers_loaded=layers,
            warnings=warnings,
        )

    def sync_and_load(self, config_path: str) -> LoadedIdentity:
        """Sync remotes, then load."""
        chain_path = Path(config_path).resolve()
        if chain_path.exists():
            with open(chain_path, "r", encoding="utf-8") as fh:
                chain_config = yaml.safe_load(fh) or {}
            entries = chain_config.get("inheritance", [])
            self._syncer.sync(entries)

        return self.load(config_path)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load_layer(self, layer_path: Path) -> dict[str, Any]:
        """
        Load configuration from a layer directory.

        Looks for (in order):
          config.yaml, config.yml, jengo.yaml, jengo.yml
        Returns empty dict if none found.
        """
        for filename in ("config.yaml", "config.yml", "jengo.yaml", "jengo.yml"):
            config_file = layer_path / filename
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as fh:
                    data = yaml.safe_load(fh)
                    return data if isinstance(data, dict) else {}

        # Also check for CORE_IDENTITY.md presence (signals a valid layer)
        identity_md = layer_path / "CORE_IDENTITY.md"
        if identity_md.exists():
            return {"_has_identity_md": True, "_layer_path": str(layer_path)}

        return {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _deep_merge(base: dict, override: dict) -> None:
    """Merge override into base in-place.  Nested dicts are merged recursively."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def _default_chain_path() -> str:
    """Find inheritance-chain.yaml in standard locations."""
    candidates = [
        Path.home() / ".jengo" / "inheritance-chain.yaml",
        Path.cwd() / "inheritance-chain.yaml",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return str(Path.home() / ".jengo" / "inheritance-chain.yaml")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Jengo Inheritance Loader",
        prog="python -m jengo.tools.inheritance_loader",
    )
    parser.add_argument(
        "--load",
        action="store_true",
        help="Load the inheritance chain and print a summary.",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Sync remote repos, then load.",
    )
    parser.add_argument(
        "--config",
        default=_default_chain_path(),
        help="Path to inheritance-chain.yaml (default: ~/.jengo/inheritance-chain.yaml).",
    )
    args = parser.parse_args()

    if not args.load and not args.sync:
        parser.print_help()
        sys.exit(0)

    loader = InheritanceLoader()

    try:
        if args.sync:
            print("Syncing inheritance chain from remotes...")
            identity = loader.sync_and_load(args.config)
        else:
            identity = loader.load(args.config)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Layer:        {identity.layer}")
    print(f"Parent layer: {identity.parent_layer or '(none)'}")
    print(f"Layers loaded: {len(identity.layers_loaded)}")
    for lc in identity.layers_loaded:
        print(f"  - {lc.name}  ({lc.source_path})")
    if identity.warnings:
        print("Warnings:")
        for w in identity.warnings:
            print(f"  ! {w}")


if __name__ == "__main__":
    main()
