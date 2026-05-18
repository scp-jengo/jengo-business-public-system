#!/usr/bin/env python3
"""
Jengo Business - Onboarding Wizard
Creates new organization or individual identity
"""

import os
import sys
import yaml
import json
from pathlib import Path
from datetime import datetime
import subprocess

class OnboardingWizard:
    """Guides user through creating new identity"""

    def __init__(self):
        self.identity = {}
        self.config = {}
        self.repos = {}

    def run(self):
        """Main wizard flow"""
        print("=" * 60)
        print("JENGO BUSINESS - ONBOARDING WIZARD")
        print("=" * 60)
        print()

        # Step 1: Identity type
        identity_type = self.ask_identity_type()

        if identity_type == 'organization':
            self.onboard_organization()
        elif identity_type == 'individual':
            self.onboard_individual()
        else:
            print("Invalid choice. Exiting.")
            sys.exit(1)

        # Step 2: Create repositories
        self.create_repositories()

        # Step 3: Generate configuration
        self.generate_config()

        # Step 4: Generate launch scripts
        self.generate_launch_scripts()

        print()
        print("=" * 60)
        print("ONBOARDING COMPLETE")
        print("=" * 60)
        print()
        print(f"Identity: {self.identity['name']}")
        print(f"Type: {self.identity['type']}")
        print(f"Layer: {self.identity['layer']}")
        print()
        print("Repositories created:")
        for repo_name, repo_path in self.repos.items():
            print(f"  - {repo_name}: {repo_path}")
        print()
        print("Configuration saved to:")
        print(f"  {Path.home() / '.jengo' / 'config.yaml'}")
        print()
        print("Next steps:")
        print("  1. Review configuration")
        print("  2. Customize policies in system repo")
        print("  3. Launch: jengo_claudecode.bat")
        print()

    def ask_identity_type(self):
        """Ask if creating organization or individual identity"""
        print("What are you creating?")
        print()
        print("  1. Organization (company, news outlet, team)")
        print("  2. Individual (personal use)")
        print()

        while True:
            choice = input("Enter choice (1 or 2): ").strip()
            if choice == '1':
                return 'organization'
            elif choice == '2':
                return 'individual'
            else:
                print("Invalid choice. Please enter 1 or 2.")

    def onboard_organization(self):
        """Onboard new organization"""
        print()
        print("=" * 60)
        print("ORGANIZATION ONBOARDING")
        print("=" * 60)
        print()

        # Basic info
        org_name = input("Organization name: ").strip()
        org_slug = input("Organization slug (for repos, e.g. 'altnews'): ").strip().lower()
        org_purpose = input("Primary purpose: ").strip()

        print()
        print("GitHub configuration:")
        github_org = input(f"GitHub organization (default: {org_slug}): ").strip() or org_slug
        github_token = input("GitHub personal access token (for repo creation): ").strip()

        print()
        print("Values and mission:")
        values = []
        print("Enter organizational values (one per line, empty line to finish):")
        while True:
            value = input("  - ").strip()
            if not value:
                break
            values.append(value)

        # Store identity
        self.identity = {
            'type': 'organization',
            'name': org_name,
            'slug': org_slug,
            'layer': org_slug,
            'purpose': org_purpose,
            'values': values,
            'github_org': github_org,
            'github_token': github_token,
            'created': datetime.now().isoformat()
        }

        # Repo names
        self.repos = {
            'identity': f"jengo-business-{org_slug}-identity",
            'knowledge': f"jengo-business-{org_slug}-knowledge",
            'system': f"jengo-business-{org_slug}-system",
            'world': f"jengo-business-{org_slug}-world",
            'registry': f"jengo-business-{org_slug}-registry"
        }

        print()
        print("Will create repositories:")
        for repo_name in self.repos.values():
            print(f"  - {github_org}/{repo_name}")
        print()
        confirm = input("Proceed? (y/n): ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            sys.exit(0)

    def onboard_individual(self):
        """Onboard new individual"""
        print()
        print("=" * 60)
        print("INDIVIDUAL ONBOARDING")
        print("=" * 60)
        print()

        # Basic info
        name = input("Your name: ").strip()
        username = input("Username (for repos): ").strip().lower()
        purpose = input("Primary use case: ").strip()

        print()
        print("GitHub configuration:")
        github_user = input(f"GitHub username (default: {username}): ").strip() or username
        github_token = input("GitHub personal access token: ").strip()

        # Privacy
        print()
        print("Privacy settings:")
        print("  1. Private repositories (recommended)")
        print("  2. Public repositories")
        repo_visibility = input("Choose (1 or 2): ").strip()
        private = repo_visibility == '1'

        # Store identity
        self.identity = {
            'type': 'individual',
            'name': name,
            'username': username,
            'layer': username,
            'purpose': purpose,
            'github_user': github_user,
            'github_token': github_token,
            'private_repos': private,
            'created': datetime.now().isoformat()
        }

        # Repo names
        self.repos = {
            'identity': f"jengo-business-{username}-identity",
            'knowledge': f"jengo-business-{username}-knowledge",
            'system': f"jengo-business-{username}-system",
            'world': f"jengo-business-{username}-world"
        }

        print()
        print("Will create repositories:")
        for repo_name in self.repos.values():
            visibility = "PRIVATE" if private else "PUBLIC"
            print(f"  - {github_user}/{repo_name} ({visibility})")
        print()
        confirm = input("Proceed? (y/n): ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            sys.exit(0)

    def create_repositories(self):
        """Create GitHub repositories"""
        print()
        print("Creating repositories...")

        is_org = self.identity['type'] == 'organization'
        owner = self.identity.get('github_org') if is_org else self.identity.get('github_user')
        token = self.identity['github_token']
        private = self.identity.get('private_repos', False)

        # Create local directory
        base_dir = Path.home() / 'jengo-business' / self.identity['layer']
        base_dir.mkdir(parents=True, exist_ok=True)

        for repo_type, repo_name in self.repos.items():
            print(f"  Creating {repo_name}...")

            repo_dir = base_dir / repo_name

            # Initialize git repo
            repo_dir.mkdir(exist_ok=True)
            os.chdir(repo_dir)

            subprocess.run(['git', 'init'], check=True, capture_output=True)

            # Create initial files from templates
            self.populate_repo(repo_dir, repo_type)

            # Initial commit
            subprocess.run(['git', 'add', '.'], check=True, capture_output=True)
            subprocess.run(['git', 'commit', '-m', 'Initial commit from Jengo onboarding'],
                         check=True, capture_output=True)

            # Create GitHub repo
            create_cmd = [
                'gh', 'repo', 'create',
                f"{owner}/{repo_name}",
                '--source=.',
                f"--{'private' if private else 'public'}",
                '--push'
            ]

            result = subprocess.run(create_cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"    ✓ Created and pushed to GitHub")
                self.repos[repo_type] = str(repo_dir)
            else:
                print(f"    ✗ Failed: {result.stderr}")
                print(f"    Local repo created at: {repo_dir}")
                self.repos[repo_type] = str(repo_dir)

    def populate_repo(self, repo_dir: Path, repo_type: str):
        """Populate repository with initial files from templates"""

        # Load templates
        template_dir = Path(__file__).parent.parent.parent / 'templates' / repo_type

        if repo_type == 'identity':
            self.create_identity_files(repo_dir)
        elif repo_type == 'knowledge':
            self.create_knowledge_files(repo_dir)
        elif repo_type == 'system':
            self.create_system_files(repo_dir)
        elif repo_type == 'world':
            self.create_world_files(repo_dir)
        elif repo_type == 'registry':
            self.create_registry_files(repo_dir)

    def create_identity_files(self, repo_dir: Path):
        """Create identity repository files"""

        # CORE_IDENTITY.md
        identity_content = f"""# Core Identity — {self.identity['name']}

**Identity Type:** {self.identity['type']}
**Layer:** {self.identity['layer']}
**Created:** {self.identity['created']}

---

## Inheritance Chain

This identity inherits from:
- scp-jengo/jengo-business-public-identity
- scp-jengo/jengo-business-public-knowledge
- scp-jengo/jengo-business-public-system
- scp-jengo/jengo-business-public-world

---

## Purpose

{self.identity.get('purpose', 'TBD')}

---

## Values

{self._format_values()}

---

**Version:** 1.0.0
**Status:** Active
"""

        (repo_dir / 'CORE_IDENTITY.md').write_text(identity_content)

        # README
        readme_content = f"""# {self.identity['name']} - Identity Layer

Identity repository for {self.identity['name']}.

Created: {datetime.now().strftime('%Y-%m-%d')}
Type: {self.identity['type']}

---

**Part of Jengo Business hierarchical knowledge federation**
"""
        (repo_dir / 'README.md').write_text(readme_content)

        # State directory
        state_dir = repo_dir / 'state'
        state_dir.mkdir(exist_ok=True)

        (state_dir / '.gitkeep').touch()

    def create_knowledge_files(self, repo_dir: Path):
        """Create knowledge repository files"""
        (repo_dir / 'README.md').write_text(f"# {self.identity['name']} - Knowledge Layer\n\nKnowledge base for {self.identity['name']}.")
        (repo_dir / 'patterns').mkdir(exist_ok=True)
        (repo_dir / 'frameworks').mkdir(exist_ok=True)
        (repo_dir / 'contributions').mkdir(exist_ok=True)
        (repo_dir / 'patterns' / '.gitkeep').touch()

    def create_system_files(self, repo_dir: Path):
        """Create system repository files"""
        (repo_dir / 'README.md').write_text(f"# {self.identity['name']} - System Layer\n\nSystem configuration for {self.identity['name']}.")
        (repo_dir / 'policies').mkdir(exist_ok=True)
        (repo_dir / 'config').mkdir(exist_ok=True)
        (repo_dir / 'policies' / '.gitkeep').touch()

    def create_world_files(self, repo_dir: Path):
        """Create world repository files"""
        (repo_dir / 'README.md').write_text(f"# {self.identity['name']} - World Layer\n\nWorld model for {self.identity['name']}.")
        (repo_dir / 'entities').mkdir(exist_ok=True)
        (repo_dir / 'relationships').mkdir(exist_ok=True)
        (repo_dir / 'entities' / '.gitkeep').touch()

    def create_registry_files(self, repo_dir: Path):
        """Create registry repository files"""
        (repo_dir / 'README.md').write_text(f"# {self.identity['name']} - Registry Layer\n\nService registry for {self.identity['name']}.")

        # Empty registries
        (repo_dir / 'users.registry.json').write_text('{}')
        (repo_dir / 'departments.registry.json').write_text('{}')
        (repo_dir / 'devices.registry.json').write_text('{}')

    def _format_values(self):
        """Format values list as markdown"""
        values = self.identity.get('values', [])
        if not values:
            return "- TBD"
        return '\n'.join(f"- {v}" for v in values)

    def generate_config(self):
        """Generate ~/.jengo/config.yaml"""
        config_dir = Path.home() / '.jengo'
        config_dir.mkdir(exist_ok=True)

        config = {
            'version': '1.0.0',
            'identity': {
                'name': self.identity['name'],
                'type': self.identity['type'],
                'layer': self.identity['layer']
            },
            'repositories': self.repos,
            'inheritance_chain': [
                {'name': 'public-identity', 'repo': 'https://github.com/scp-jengo/jengo-business-public-identity.git'},
                {'name': 'public-knowledge', 'repo': 'https://github.com/scp-jengo/jengo-business-public-knowledge.git'},
                {'name': 'public-system', 'repo': 'https://github.com/scp-jengo/jengo-business-public-system.git'},
                {'name': 'public-world', 'repo': 'https://github.com/scp-jengo/jengo-business-public-world.git'},
                {'name': 'current-identity', 'path': self.repos.get('identity', '')}
            ],
            'constitutional_ai': {
                'l1_threshold': 0.7,
                'l2_threshold': 0.6,
                'l3_threshold': 0.6
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
    wizard = OnboardingWizard()
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
