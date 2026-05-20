"""
Legal Review Agent.

Flags potential legal risks in text content:
  - Defamation indicators (false statements of fact about identified individuals)
  - Copyright concerns (reproduced text patterns)
  - Privacy violations (PII exposure)

Returns:
  risk_level: none | low | medium | high
  flags: list of detected issues
  recommendation: publish | review | block
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class LegalFlag:
    """A single legal risk flag."""
    category: str      # 'defamation' | 'copyright' | 'privacy'
    severity: str      # 'low' | 'medium' | 'high'
    description: str
    evidence: str = ""


@dataclass
class LegalReviewResult:
    """Result from LegalReviewAgent.review()."""
    risk_level: str       # 'none' | 'low' | 'medium' | 'high'
    flags: list[LegalFlag]
    recommendation: str   # 'publish' | 'review' | 'block'
    reasoning: str
    details: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Defamation markers
# ---------------------------------------------------------------------------

_DEFAMATION_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    # (pattern, severity, description)
    (
        re.compile(r"\b(is|are|was|were)\s+a\s+(criminal|murderer|rapist|paedophile|terrorist|fraud|thief)\b", re.I),
        "high",
        "Direct criminal label applied to a person without hedging.",
    ),
    (
        re.compile(r"\b(committed|perpetrated|carried out)\s+(fraud|murder|rape|theft|terrorism)\b", re.I),
        "high",
        "Allegation of serious criminal act without attribution to official finding.",
    ),
    (
        re.compile(r"\b(lied|is lying|is a liar|fabricated|made up)\b", re.I),
        "medium",
        "Accusation of deliberate falsehood — potential defamation if about a named individual.",
    ),
    (
        re.compile(r"\b(corrupt|bribed|embezzled|stole from|defrauded)\b", re.I),
        "medium",
        "Corruption allegation — requires sourcing and legal review.",
    ),
]

# ---------------------------------------------------------------------------
# Copyright markers
# ---------------------------------------------------------------------------

_COPYRIGHT_INDICATORS: list[tuple[re.Pattern, str]] = [
    (
        re.compile(r"©\s*\d{4}", re.I),
        "Copyright symbol with year found — check if text is reproduced without licence.",
    ),
    (
        re.compile(r"all rights reserved", re.I),
        "'All rights reserved' phrase — may indicate reproduced proprietary content.",
    ),
    (
        re.compile(r"reprinted with permission", re.I),
        "Permission language — verify that permission is actually granted.",
    ),
]

_LONG_QUOTE_PATTERN = re.compile(r'["“”]([^"“”]{200,})["“”]')

# ---------------------------------------------------------------------------
# Privacy / PII markers
# ---------------------------------------------------------------------------

_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_PHONE_PATTERN = re.compile(
    r"\b(?:\+?31|0)[-.\s]?(?:\d[-.\s]?){9}\b"          # Dutch
    r"|\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"  # US/CA
    r"|\b\+\d{1,3}[-.\s]\d{4,14}\b"                    # international
)
_BSN_PATTERN = re.compile(r"\b\d{8,9}\b")   # Dutch BSN (approximate)
_IBAN_PATTERN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{4,30}\b")
_PASSPORT_PATTERN = re.compile(r"\b[A-Z]{1,2}\d{6,9}\b")


# ---------------------------------------------------------------------------
# Severity rank helper
# ---------------------------------------------------------------------------

_SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}


def _max_severity(flags: list[LegalFlag]) -> str:
    if not flags:
        return "none"
    return max(f.severity for f in flags, key=lambda s: _SEVERITY_RANK.get(s, 0))


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class LegalReviewAgent:
    """
    Scan content for potential legal risks.

    Note: This is a heuristic scanner, not a legal opinion.
    Always have actual legal counsel review high-risk content.
    """

    def review(self, content: str) -> LegalReviewResult:
        """
        Review content for legal risks.

        Parameters
        ----------
        content:
            The text (article, post, script, etc.) to review.

        Returns
        -------
        LegalReviewResult with risk_level, flags, and recommendation.
        """
        flags: list[LegalFlag] = []

        # --- Defamation ---
        for pattern, severity, description in _DEFAMATION_PATTERNS:
            matches = pattern.findall(content)
            if matches:
                flags.append(LegalFlag(
                    category="defamation",
                    severity=severity,
                    description=description,
                    evidence=str(matches[:3]),
                ))

        # --- Copyright ---
        for pattern, description in _COPYRIGHT_INDICATORS:
            if pattern.search(content):
                flags.append(LegalFlag(
                    category="copyright",
                    severity="medium",
                    description=description,
                ))

        long_quotes = _LONG_QUOTE_PATTERN.findall(content)
        if long_quotes:
            flags.append(LegalFlag(
                category="copyright",
                severity="medium",
                description=(
                    f"{len(long_quotes)} long quoted passage(s) (>200 chars). "
                    "Verify fair use or licensing for reproduced text."
                ),
                evidence=f"First passage: {long_quotes[0][:80]}...",
            ))

        # --- Privacy / PII ---
        emails = _EMAIL_PATTERN.findall(content)
        if emails:
            flags.append(LegalFlag(
                category="privacy",
                severity="medium",
                description=f"{len(emails)} email address(es) found. Publishing personal emails may violate GDPR/AVG.",
                evidence=str(emails[:2]),
            ))

        phones = _PHONE_PATTERN.findall(content)
        if phones:
            flags.append(LegalFlag(
                category="privacy",
                severity="medium",
                description=f"{len(phones)} phone number(s) found. Publishing personal numbers requires consent.",
                evidence=str(phones[:2]),
            ))

        ibans = _IBAN_PATTERN.findall(content)
        if ibans:
            flags.append(LegalFlag(
                category="privacy",
                severity="high",
                description=f"{len(ibans)} IBAN/bank account number(s) found. Publishing financial identifiers is high risk.",
                evidence=str(ibans[:1]),
            ))

        bsns = _BSN_PATTERN.findall(content)
        if len(bsns) > 3:   # Some 8-9 digit numbers will be dates etc.; require several
            flags.append(LegalFlag(
                category="privacy",
                severity="high",
                description="Multiple 8-9 digit numbers found — possible Dutch BSN (citizen service numbers). Do not publish.",
                evidence=str(bsns[:2]),
            ))

        # --- Determine outcome ---
        risk_level = _max_severity(flags)
        details = {
            "flag_count": len(flags),
            "defamation_flags": sum(1 for f in flags if f.category == "defamation"),
            "copyright_flags": sum(1 for f in flags if f.category == "copyright"),
            "privacy_flags": sum(1 for f in flags if f.category == "privacy"),
        }

        if risk_level == "none":
            recommendation = "publish"
            reasoning = "No legal risk indicators found. Content appears safe to publish."
        elif risk_level == "low":
            recommendation = "review"
            reasoning = (
                f"{len(flags)} low-severity flag(s). "
                "Review recommended before publishing."
            )
        elif risk_level == "medium":
            recommendation = "review"
            reasoning = (
                f"{len(flags)} flag(s) including medium-severity issues. "
                "Legal review required before publishing."
            )
        else:  # high
            recommendation = "block"
            reasoning = (
                f"{len(flags)} flag(s) including high-severity issues. "
                "Do not publish without explicit legal clearance."
            )

        return LegalReviewResult(
            risk_level=risk_level,
            flags=flags,
            recommendation=recommendation,
            reasoning=reasoning,
            details=details,
        )
