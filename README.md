# Jengo Business - Public System Layer

**Core system implementation: Constitutional AI, policy engine, agent orchestration**

This repository contains the actual implementation code that runs Jengo Business instances.

---

## What This Repo Contains

- ✅ Constitutional AI implementation (L1/L2/L3)
- ✅ Policy engine (YAML-based)
- ✅ Agent orchestration (LangGraph)
- ✅ Startup scripts (jengo.bat, jengo_claudecode.bat, jengo_codex.bat)
- ✅ Setup wizard (onboarding + machine configuration)
- ✅ API endpoints (REST)
- ✅ Verification agents (source, claim, bias, legal)

---

## Quick Start

### First Time Setup

```bash
# Run setup wizard
setup-wizard.bat onboarding

# This will:
# 1. Ask for organization/individual details
# 2. Create your identity repository
# 3. Configure inheritance chain
# 4. Generate launch scripts
```

### Launch

```bash
# Launch with Claude Code (recommended)
jengo_claudecode.bat

# Launch with OpenAI Codex
jengo_codex.bat

# Auto-detect best available
jengo.bat
```

---

## Repository Structure

```
jengo-business-public-system/
├── README.md
├── startup/
│   ├── jengo.bat                     # Generic launcher
│   ├── jengo_claudecode.bat         # Claude Code launcher
│   ├── jengo_codex.bat              # OpenAI Codex launcher
│   ├── setup-wizard.bat             # First-time setup
│   ├── setup-wizard.py              # Setup wizard implementation
│   └── onboarding/
│       ├── organization-onboard.py  # Org onboarding
│       ├── individual-onboard.py    # Personal onboarding
│       └── machine-config.py        # Device configuration
├── src/
│   ├── constitutional/
│   │   ├── __init__.py
│   │   ├── three_layer_framework.py
│   │   ├── l1_rational.py
│   │   ├── l2_empathic.py
│   │   ├── l3_social.py
│   │   └── mesa_optimizer_check.py
│   ├── policy/
│   │   ├── __init__.py
│   │   ├── policy_engine.py
│   │   ├── yaml_parser.py
│   │   ├── approval_workflow.py
│   │   └── audit_trail.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py
│   │   ├── task_decomposer.py
│   │   └── skill_executor.py
│   ├── verification/
│   │   ├── __init__.py
│   │   ├── source_verify_agent.py
│   │   ├── claim_verify_agent.py
│   │   ├── bias_detect_agent.py
│   │   └── legal_review_agent.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── auth.py
│   │   ├── rate_limiting.py
│   │   └── endpoints/
│   └── tools/
│       ├── knowledge_sync.py
│       └── inheritance_loader.py
├── deployment/
│   ├── docker/
│   │   ├── Dockerfile
│   │   └── docker-compose.yml
│   ├── aws/
│   └── azure/
├── tests/
├── requirements.txt
└── LICENSE
```

---

## Launch Modes

### Claude Code (Recommended)

```bash
jengo_claudecode.bat
```

Launches Jengo with Claude Code CLI for interactive development.

### OpenAI Codex

```bash
jengo_codex.bat
```

Launches Jengo with OpenAI Codex integration.

### Generic

```bash
jengo.bat
```

Auto-detects best available model and launches.

---

## Setup Wizard

### Onboarding Mode (First Time)

```bash
setup-wizard.bat onboarding
```

**For Organizations:**
- Creates organization identity repository
- Configures inheritance from public layer
- Sets up contribution policies
- Generates department templates

**For Individuals:**
- Creates personal identity repository
- Configures privacy settings
- Sets up personal preferences
- Generates device templates

### Machine Mode (New Device)

```bash
setup-wizard.bat machine
```

- Detects existing identity from parent layer
- Creates device-specific repository
- Configures git remotes
- Generates launch scripts for this machine

---

## Configuration

After setup, configuration lives in:

```
~/.jengo/
├── config.yaml              # Main configuration
├── inheritance-chain.yaml   # Layer definitions
└── credentials.encrypted    # API keys, secrets
```

---

## Constitutional AI

All agents run through constitutional framework:

```python
from jengo.constitutional import ThreeLayerIntelligence

constitutional = ThreeLayerIntelligence(config)

# Evaluate action
result = constitutional.evaluate_action({
    'type': 'verification_task',
    'action': 'verify_source',
    'source': 'example.com'
})

if result['approved']:
    # Execute action
    pass
else:
    # Blocked - examine reasoning
    print(result['reasoning'])
```

See `src/constitutional/` for implementation.

---

## Policy Engine

Define policies in YAML:

```yaml
# policies/source-verification.yaml
id: source-verification
name: Source Verification Policy
enabled: true

rules:
  - check: source_credibility
    threshold: 0.7
    action: require_approval_if_below

  - check: claim_verification
    require_sources: 2
    action: block_if_unverified
```

Load and enforce:

```python
from jengo.policy import PolicyEngine

engine = PolicyEngine(policy_dir='./policies')
result = engine.check_action(action)
```

---

## API

REST API runs on port 8000 by default:

```bash
# Start API server
python -m jengo.api.main

# Test
curl http://localhost:8000/api/v1/verify \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"content": "Article to verify..."}'
```

---

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Run linter
flake8 src/

# Type check
mypy src/
```

---

## Support

- **Documentation:** https://docs.scp-jengo.org
- **Issues:** https://github.com/scp-jengo/jengo-business-public-system/issues
- **API Docs:** https://api.scp-jengo.org/docs

---

**Status:** Production
**Version:** 1.0.0
**License:** MIT (core) + Commercial (enterprise features)
