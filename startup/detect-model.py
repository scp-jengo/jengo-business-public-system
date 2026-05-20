#!/usr/bin/env python3
"""
Jengo Business - AI Model Detector.

Checks which AI model integration is available on this machine.
Prints the best available option to stdout (one word):
  claudecode   — Claude Code CLI is installed
  codex        — OPENAI_API_KEY is set
  claude-api   — ANTHROPIC_API_KEY is set
  none         — nothing found

Priority: claudecode > codex > claude-api > none

Used by jengo.bat to determine which launcher to call.
"""

import os
import shutil
import sys


def detect() -> str:
    # 1. Claude Code CLI
    if shutil.which("claude") is not None:
        return "claudecode"

    # 2. OpenAI Codex (via API key)
    if os.environ.get("OPENAI_API_KEY", "").strip():
        return "codex"

    # 3. Anthropic API key (direct API mode)
    if os.environ.get("ANTHROPIC_API_KEY", "").strip():
        return "claude-api"

    return "none"


if __name__ == "__main__":
    result = detect()
    print(result)
    sys.exit(0 if result != "none" else 1)
