"""
Knowledge Sync.

Synchronises repos in the inheritance chain by running git pull (if the
repo is already cloned) or git clone (if it does not exist yet).

Each entry in the inheritance chain is a dict with:
  name  — human-readable label
  repo  — HTTPS/SSH URL (for remote repos)
  path  — local path (for local repos)

Either 'repo' or 'path' must be present.  If both are present, 'path'
is used as the local clone destination for the remote 'repo'.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RepoSyncStatus:
    """Sync result for a single repo."""
    name: str
    path: str
    success: bool
    action: str   # 'pulled' | 'cloned' | 'skipped' | 'failed'
    message: str


@dataclass
class SyncResult:
    """Result of KnowledgeSync.sync()."""
    total: int
    synced: int
    failed: int
    repos: list[RepoSyncStatus]

    @property
    def all_ok(self) -> bool:
        return self.failed == 0


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class KnowledgeSync:
    """
    Sync all repos in the inheritance chain.

    Parameters
    ----------
    base_dir:
        Root directory under which repos are cloned.
        Defaults to ~/jengo-sync/.
    timeout:
        Timeout in seconds for each git operation.  Default: 60.
    """

    def __init__(
        self,
        base_dir: str | None = None,
        timeout: int = 60,
    ) -> None:
        self._base = Path(base_dir) if base_dir else Path.home() / "jengo-sync"
        self._timeout = timeout

    def sync(self, inheritance_chain: list[dict]) -> SyncResult:
        """
        Pull or clone each repo in the chain.

        Parameters
        ----------
        inheritance_chain:
            List of dicts with 'name' and either 'repo' (URL) or 'path' (local).

        Returns
        -------
        SyncResult with per-repo status.
        """
        statuses: list[RepoSyncStatus] = []

        for entry in inheritance_chain:
            name = entry.get("name", "unnamed")
            repo_url = entry.get("repo")
            local_path_str = entry.get("path")

            if not repo_url and not local_path_str:
                statuses.append(RepoSyncStatus(
                    name=name, path="", success=False,
                    action="failed",
                    message="Entry has neither 'repo' nor 'path' key.",
                ))
                continue

            # Determine local path
            if local_path_str:
                local_path = Path(local_path_str)
            else:
                # Clone into base_dir / name
                local_path = self._base / name.replace("/", "_").replace(" ", "_")

            status = self._sync_one(name, repo_url, local_path)
            statuses.append(status)

        synced = sum(1 for s in statuses if s.success)
        failed = sum(1 for s in statuses if not s.success)

        return SyncResult(
            total=len(inheritance_chain),
            synced=synced,
            failed=failed,
            repos=statuses,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _sync_one(
        self,
        name: str,
        repo_url: str | None,
        local_path: Path,
    ) -> RepoSyncStatus:
        """Clone or pull a single repo."""

        # Local-only entry (no remote URL)
        if not repo_url:
            if local_path.exists():
                return RepoSyncStatus(
                    name=name, path=str(local_path), success=True,
                    action="skipped",
                    message="Local path exists; no remote URL to sync.",
                )
            return RepoSyncStatus(
                name=name, path=str(local_path), success=False,
                action="failed",
                message=f"Local path '{local_path}' does not exist and no remote URL provided.",
            )

        git_dir = local_path / ".git"

        if git_dir.exists():
            # Pull
            return self._git_pull(name, local_path)
        else:
            # Clone
            return self._git_clone(name, repo_url, local_path)

    def _git_pull(self, name: str, repo_dir: Path) -> RepoSyncStatus:
        try:
            result = subprocess.run(
                ["git", "-C", str(repo_dir), "pull", "--ff-only"],
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            if result.returncode == 0:
                return RepoSyncStatus(
                    name=name, path=str(repo_dir), success=True,
                    action="pulled",
                    message=result.stdout.strip() or "Already up to date.",
                )
            return RepoSyncStatus(
                name=name, path=str(repo_dir), success=False,
                action="failed",
                message=f"git pull failed: {result.stderr.strip()}",
            )
        except subprocess.TimeoutExpired:
            return RepoSyncStatus(
                name=name, path=str(repo_dir), success=False,
                action="failed",
                message=f"git pull timed out after {self._timeout}s.",
            )
        except Exception as exc:
            return RepoSyncStatus(
                name=name, path=str(repo_dir), success=False,
                action="failed",
                message=str(exc),
            )

    def _git_clone(self, name: str, repo_url: str, dest: Path) -> RepoSyncStatus:
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            result = subprocess.run(
                ["git", "clone", "--depth=1", repo_url, str(dest)],
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            if result.returncode == 0:
                return RepoSyncStatus(
                    name=name, path=str(dest), success=True,
                    action="cloned",
                    message=f"Cloned from {repo_url}",
                )
            return RepoSyncStatus(
                name=name, path=str(dest), success=False,
                action="failed",
                message=f"git clone failed: {result.stderr.strip()}",
            )
        except subprocess.TimeoutExpired:
            return RepoSyncStatus(
                name=name, path=str(dest), success=False,
                action="failed",
                message=f"git clone timed out after {self._timeout}s.",
            )
        except Exception as exc:
            return RepoSyncStatus(
                name=name, path=str(dest), success=False,
                action="failed",
                message=str(exc),
            )
