"""
Source Verification Agent.

Checks domain validity, credibility signals, and known-bad-actor lists.
Returns a score 0-1 and a tier (1-4) matching the niet-achterlijk-protocol:

  Tier 1 — verified, high-credibility primary source
  Tier 2 — credible secondary source; requires corroboration
  Tier 3 — unverified or low-credibility; significant scrutiny required
  Tier 4 — known bad actor, known disinfo outlet, or invalid domain

The tier system mirrors the Jengo knowledge tiers used in analysis notebooks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class VerificationResult:
    """Result from any verification agent."""
    source: str
    score: float          # 0.0 – 1.0
    tier: int             # 1 = best, 4 = worst
    status: str           # 'verified' | 'credible' | 'unverified' | 'blocked'
    reasoning: str
    details: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Static lists (would be loaded from config/database in production)
# ---------------------------------------------------------------------------

_KNOWN_BAD_ACTORS: frozenset[str] = frozenset({
    # Known disinfo / propaganda outlets
    "infowars.com",
    "naturalnews.com",
    "globalresearch.ca",
    "breitbart.com",
    "rt.com",
    "sputniknews.com",
    "dailystormer.com",
    "stormfront.org",
    "thegatewaypundit.com",
    "worldnewsdailyreport.com",
    "empirenews.net",
    "huzlers.com",
})

_HIGH_CREDIBILITY_DOMAINS: frozenset[str] = frozenset({
    # Major news organisations with editorial standards
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "bbc.co.uk",
    "nytimes.com",
    "theguardian.com",
    "washingtonpost.com",
    "nos.nl",
    "nrc.nl",
    "fd.nl",
    "volkskrant.nl",
    "trouw.nl",
    # Academic / scientific
    "nature.com",
    "science.org",
    "thelancet.com",
    "nejm.org",
    "pubmed.ncbi.nlm.nih.gov",
    "scholar.google.com",
    # Government / intergovernmental
    "un.org",
    "who.int",
    "ec.europa.eu",
    "rijksoverheid.nl",
    "cbs.nl",
    "cpb.nl",
})

_TLD_CREDIBILITY: dict[str, float] = {
    ".gov": 0.90,
    ".edu": 0.85,
    ".org": 0.70,
    ".com": 0.60,
    ".net": 0.55,
    ".io": 0.50,
    ".info": 0.40,
    ".biz": 0.35,
    ".xyz": 0.30,
}

_DOMAIN_PATTERN = re.compile(
    r"^(?:https?://)?(?:www\.)?([a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.[a-zA-Z]{2,}).*$"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_domain(source: str) -> str | None:
    """Extract the bare domain (without www.) from a URL or domain string."""
    source = source.strip().lower()
    match = _DOMAIN_PATTERN.match(source)
    if match:
        return match.group(1)
    # Maybe it's already just a domain
    if "." in source and " " not in source:
        return source
    return None


def _tld_score(domain: str) -> float:
    for tld, score in _TLD_CREDIBILITY.items():
        if domain.endswith(tld):
            return score
    return 0.50


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class SourceVerifyAgent:
    """
    Verify a source URL or domain.

    Tiers:
      1 — High-credibility, verified (score >= 0.80)
      2 — Credible, some corroboration advised (score 0.55 – 0.79)
      3 — Low credibility or unknown (score 0.30 – 0.54)
      4 — Known bad actor or invalid (score < 0.30)
    """

    def verify(self, source: str) -> VerificationResult:
        """
        Verify a source.

        Parameters
        ----------
        source:
            A URL, domain name, or textual source reference.

        Returns
        -------
        VerificationResult with score (0-1) and tier (1-4).
        """
        domain = _extract_domain(source)
        details: dict[str, Any] = {"raw_source": source, "extracted_domain": domain}

        if domain is None:
            return VerificationResult(
                source=source,
                score=0.10,
                tier=4,
                status="blocked",
                reasoning="Could not extract a valid domain from the provided source string.",
                details=details,
            )

        # Check 1: Known bad actors
        if domain in _KNOWN_BAD_ACTORS:
            return VerificationResult(
                source=source,
                score=0.05,
                tier=4,
                status="blocked",
                reasoning=f"Domain '{domain}' is on the known-bad-actor list. Do not use as source.",
                details={**details, "bad_actor": True},
            )

        # Check 2: High-credibility whitelist
        if domain in _HIGH_CREDIBILITY_DOMAINS:
            return VerificationResult(
                source=source,
                score=0.92,
                tier=1,
                status="verified",
                reasoning=f"Domain '{domain}' is on the high-credibility whitelist.",
                details={**details, "whitelisted": True},
            )

        # Check 3: Heuristic scoring
        tld_score = _tld_score(domain)
        details["tld_score"] = tld_score

        # Penalise very short or numeric domains (often low-quality)
        parts = domain.split(".")
        if len(parts[0]) < 3:
            tld_score = max(0.2, tld_score - 0.15)
            details["short_domain_penalty"] = True

        # Reward known journalistic subdomains
        if any(kw in domain for kw in ("news", "press", "media", "journal", "research")):
            tld_score = min(0.85, tld_score + 0.10)
            details["journalistic_bonus"] = True

        score = round(tld_score, 4)

        if score >= 0.80:
            tier, status = 1, "verified"
        elif score >= 0.55:
            tier, status = 2, "credible"
        elif score >= 0.30:
            tier, status = 3, "unverified"
        else:
            tier, status = 4, "blocked"

        reasoning = (
            f"Heuristic evaluation of '{domain}': TLD score {tld_score:.2f}. "
            f"Tier {tier} ({status})."
        )

        return VerificationResult(
            source=source,
            score=score,
            tier=tier,
            status=status,
            reasoning=reasoning,
            details=details,
        )
