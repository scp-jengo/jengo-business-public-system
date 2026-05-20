"""
Tools — knowledge sync and inheritance loading.

Public surface:
  KnowledgeSync      — pull/clone repos in an inheritance chain
  InheritanceLoader  — load and merge layer configs into a unified identity
  SyncResult, RepoSyncStatus — sync result types
  LoadedIdentity, LayerConfig — loader result types
"""

from .knowledge_sync import KnowledgeSync, SyncResult, RepoSyncStatus
from .inheritance_loader import InheritanceLoader, LoadedIdentity, LayerConfig

__all__ = [
    "KnowledgeSync",
    "SyncResult",
    "RepoSyncStatus",
    "InheritanceLoader",
    "LoadedIdentity",
    "LayerConfig",
]
