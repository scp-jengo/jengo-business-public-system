#!/usr/bin/env python3
"""
Jengo Business - Machine Configuration Wizard
Configures new device when identity already exists in parent layer
"""

import os
import sys
import yaml
import json
from pathlib import Path
from datetime import datetime
import subprocess
import socket

class MachineConfigWizard:
    """Guides user through configuring new device for existing identity"""

    def __init__(self):
        self.identity = {}
        self.device = {}
        self.config = {}

    def run(self):
        """Main wizard flow"""
        print("=" * 60)
        print("JENGO BUSINESS - MACHINE CONFIGURATION")
        print("=" * 60)
        print()
        print("This wizard configures a new device for an existing identity.")
        print()

        # Step 1: Detect or ask for existing identity
        parent_identity = self.find_parent_identity()

        if not parent_identity:
            print("ERROR: No existing identity found")
            print()
            print("Please run onboarding wizard first:")
            print("  setup-wizard.bat onboarding")
            sys.exit(1)

        # Step 2: Device information
        self.collect_device_info()

        # Step 3: Create device repository
        self.create_device_repo()

        # Step 4: Generate configuration
        self.generate_config()

        # Step 5: Generate launch scripts
        self.generate_launch_scripts()

        print()
        print("=" * 60)
        print("MACHINE CONFIGURATION COMPLETE")
        print("=" * 60)
        print()
        print(f"Identity: {self.identity['name']}")
        print(f"Device: {self.device['name']}")
        print(f"Hostname: {self.device['hostname']}")
        print()
        print("Repository created:")
        print(f"  {self.device['repo_path']}")
        print()
        print("Configuration saved to:")
        print(f"  {Path.home() / '.jengo' / 'config.yaml'}")
        print()
        print("Next steps:")
        print("  1. Launch: jengo_claudecode.bat")
        print("  2. Knowledge will sync from parent layers automatically")
        print()

    def find_parent_identity(self):
        """Find existing identity in parent layer"""
        print("Looking for existing identity...")
        print()

        # Check for config in home directory
        config_file = Path.home() / '.jengo' / 'config.yaml'
        if config_file.exists():
            with open(config_file) as f:
                existing_config = yaml.safe_load(f)

            print("Found existing configuration:")
            print(f"  Identity: {existing_config['identity']['name']}")
            print(f"  Type: {existing_config['identity']['type']}")
            print(f"  Layer: {existing_config['identity']['layer']}")
            print()

            use_existing = input("Use this identity? (y/n): ").strip().lower()
            if use_existing == 'y':
                self.identity = existing_config['identity']
                self.identity['repos'] = existing_config.get('repositories', {})
                return self.identity

        # Manual input
        print("Enter your existing identity information:")
        print()

        github_org = input("GitHub organization/username: ").strip()
        layer = input("Layer (e.g., 'altnews-editorial-maria'): ").strip()

        # Try to clone identity repo
        identity_repo = f"https://github.com/{github_org}/jengo-business-{layer}-identity.git"

        print()
        print(f"Trying to access: {identity_repo}")

        temp_dir = Path.home() / '.jengo-temp'
        temp_dir.mkdir(exist_ok=True)

        try:
            result = subprocess.run(
                ['git', 'clone', '--depth=1', identity_repo, str(temp_dir / 'identity')],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                # Read identity
                identity_file = temp_dir / 'identity' / 'CORE_IDENTITY.md'
                if identity_file.exists():
                    content = identity_file.read_text()

                    # Parse basic info (simple extraction)
                    name = layer  # Fallback

                    self.identity = {
                        'name': name,
                        'layer': layer,
                        'github_org': github_org,
                        'identity_repo': identity_repo
                    }

                    print(f"  ✓ Found identity: {name}")
                    return self.identity
            else:
                print(f"  ✗ Could not access repository")
                print(f"  Error: {result.stderr}")

        except Exception as e:
            print(f"  ✗ Error: {e}")

        finally:
            # Cleanup
            if temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)

        return None

    def collect_device_info(self):
        """Collect device information"""
        print()
        print("=" * 60)
        print("DEVICE CONFIGURATION")
        print("=" * 60)
        print()

        # Auto-detect
        hostname = socket.gethostname()
        username = os.getenv('USERNAME') or os.getenv('USER') or 'unknown'

        print(f"Detected hostname: {hostname}")
        print(f"Detected username: {username}")
        print()

        device_name = input(f"Device name (default: {hostname}): ").strip() or hostname
        device_type = input("Device type (laptop/desktop/server): ").strip() or "laptop"

        self.device = {
            'name': device_name,
            'hostname': hostname,
            'username': username,
            'type': device_type,
            'layer': f"{self.identity['layer']}-{device_name}",
            'created': datetime.now().isoformat()
        }

        print()
        print("Device configuration:")
        print(f"  Name: {self.device['name']}")
        print(f"  Type: {self.device['type']}")
        print(f"  Full layer: {self.device['layer']}")
        print()

        confirm = input("Proceed? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Cancelled.")
            sys.exit(0)

    def create_device_repo(self):
        """Create device-specific repository"""
        print()
        print("Creating device repository...")

        github_org = self.identity['github_org']
        layer = self.device['layer']
        repo_name = f"jengo-business-{layer}-identity"

        # Create local directory
        base_dir = Path.home() / 'jengo-business'
        repo_dir = base_dir / repo_name
        repo_dir.mkdir(parents=True, exist_ok=True)

        # Initialize git repo
        os.chdir(repo_dir)
        subprocess.run(['git', 'init'], check=True, capture_output=True)

        # Create initial files
        self.populate_device_repo(repo_dir)

        # Initial commit
        subprocess.run(['git', 'add', '.'], check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit - device setup'],
                     check=True, capture_output=True)

        # Create GitHub repo (private by default for device layer)
        create_cmd = [
            'gh', 'repo', 'create',
            f"{github_org}/{repo_name}",
            '--source=.',
            '--private',
            '--push'
        ]

        result = subprocess.run(create_cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"  ✓ Created and pushed to GitHub: {github_org}/{repo_name}")
        else:
            print(f"  ✗ Failed to create GitHub repo: {result.stderr}")
            print(f"  Local repo created at: {repo_dir}")

        self.device['repo_path'] = str(repo_dir)
        self.device['repo_url'] = f"https://github.com/{github_org}/{repo_name}.git"

    def populate_device_repo(self, repo_dir: Path):
        """Populate device repository with initial files"""

        # CORE_IDENTITY.md
        identity_content = f"""# Core Identity — {self.device['name']} (Device)

**Device Name:** {self.device['name']}
**Hostname:** {self.device['hostname']}
**Type:** {self.device['type']}
**Layer:** {self.device['layer']}
**Created:** {self.device['created']}

---

## Parent Identity

Inherits from: {self.identity['layer']}

---

## Inheritance Chain

This device loads knowledge from:
1. scp-jengo/jengo-business-public-* (public foundation)
2. {self.identity['github_org']}/jengo-business-{self.identity['layer']}-* (parent identity)
3. This device repository (device-specific state)

---

## Device Information

**Hostname:** {self.device['hostname']}
**Username:** {self.device['username']}
**Type:** {self.device['type']}

---

**Version:** 1.0.0
**Status:** Active
"""

        (repo_dir / 'CORE_IDENTITY.md').write_text(identity_content)

        # README
        readme = f"""# {self.device['name']} - Device Identity

Device-specific repository for {self.device['name']}.

**Parent Identity:** {self.identity['layer']}
**Created:** {datetime.now().strftime('%Y-%m-%d')}

---

This repository contains device-specific state and configuration.
Knowledge is inherited from parent layers.
"""
        (repo_dir / 'README.md').write_text(readme)

        # State directory
        state_dir = repo_dir / 'state'
        state_dir.mkdir(exist_ok=True)
        (state_dir / '.gitkeep').touch()

        # Inheritance config
        inheritance = {
            'version': '1.0.0',
            'layer': self.device['layer'],
            'parent_layer': self.identity['layer'],
            'inheritance': [
                {'name': 'public-identity', 'repo': 'https://github.com/scp-jengo/jengo-business-public-identity.git'},
                {'name': 'public-knowledge', 'repo': 'https://github.com/scp-jengo/jengo-business-public-knowledge.git'},
                {'name': 'public-system', 'repo': 'https://github.com/scp-jengo/jengo-business-public-system.git'},
                {'name': 'public-world', 'repo': 'https://github.com/scp-jengo/jengo-business-public-world.git'},
                {'name': 'parent-identity', 'repo': self.identity.get('identity_repo', 'TBD')},
                {'name': 'device-identity', 'path': str(repo_dir)}
            ]
        }

        (repo_dir / 'inheritance-chain.yaml').write_text(
            yaml.dump(inheritance, default_flow_style=False, sort_keys=False)
        )

    def generate_config(self):
        """Generate ~/.jengo/config.yaml"""
        config_dir = Path.home() / '.jengo'
        config_dir.mkdir(exist_ok=True)

        config = {
            'version': '1.0.0',
            'identity': {
                'name': self.identity['name'],
                'layer': self.device['layer'],
                'parent_layer': self.identity['layer'],
                'device_name': self.device['name']
            },
            'device': self.device,
            'repositories': {
                'device-identity': self.device['repo_path']
            },
            'inheritance_chain': [
                {'name': 'public-identity', 'repo': 'https://github.com/scp-jengo/jengo-business-public-identity.git'},
                {'name': 'public-knowledge', 'repo': 'https://github.com/scp-jengo/jengo-business-public-knowledge.git'},
                {'name': 'public-system', 'repo': 'https://github.com/scp-jengo/jengo-business-public-system.git'},
                {'name': 'public-world', 'repo': 'https://github.com/scp-jengo/jengo-business-public-world.git'},
                {'name': 'parent-identity', 'repo': self.identity.get('identity_repo', '')},
                {'name': 'device-identity', 'path': self.device['repo_path']}
            ],
            'constitutional_ai': {
                'l1_threshold': 0.7,
                'l2_threshold': 0.6,
                'l3_threshold': 0.6
            },
            'sync': {
                'frequency': 'daily',
                'auto_pull': True
            }
        }

        config_file = config_dir / 'config.yaml'
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        print(f"  ✓ Configuration saved to {config_file}")

    def generate_launch_scripts(self):
        """Generate launch scripts in current directory"""
        print()
        print("Generating launch scripts...")

        # Copy scripts from system repo
        system_startup = Path(__file__).parent.parent

        for script in ['jengo.bat', 'jengo_claudecode.bat', 'jengo_codex.bat']:
            src = system_startup / script
            dst = Path.cwd() / script
            if src.exists():
                dst.write_text(src.read_text())
                print(f"  ✓ Created {script}")

if __name__ == '__main__':
    wizard = MachineConfigWizard()
    try:
        wizard.run()
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
