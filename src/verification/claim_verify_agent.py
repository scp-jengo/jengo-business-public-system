"""
Claim Verification Agent.

Checks whether provided sources support a given claim.
Returns: supported / unsupported / unverifiable with reasoning.

Approach (rule-based / heuristic — no LLM call required):
1. Check that at least one source has credibility tier <= 2.
2. Look for keyword overlap between claim and source URLs (rough proxy).
3. If no sources provided → unverifiable.
4. If sources are all tier 3/4 → unsupported (insufficient evidence).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .source_verify_agent import SourceVerifyAgent, VerificationResult as SourceResult


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ClaimVerificationResult:
    """Result from ClaimVerifyAgent."""
    claim: str
    verdict: str          # 'supported' | 'unsupported' | 'unverifiable'
    score: float          # 0.0 – 1.0 (confidence in verdict)
    reasoning: str
    source_results: list[SourceResult] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


# Re-export as VerificationResult for unified API (other agents use this name)
VerificationResult = ClaimVerificationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _keyword_overlap(claim: str, source_url: str) -> float:
    """
    Very rough proxy: count how many significant words from the claim
    appear in the source URL.  Returns a score 0-1.
    """
    stopwords = frozenset({
        "a", "an", "the", "is", "are", "was", "were", "be", "been",
        "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "shall", "and", "or", "but",
        "in", "on", "at", "to", "for", "of", "with", "by", "from",
        "that", "this", "it", "its",
    })

    claim_words = {
        w.lower().strip(".,;:!?\"'()")
        for w in claim.split()
        if len(w) > 3 and w.lower() not in stopwords
    }

    if not claim_words:
        return 0.0

    source_lower = source_url.lower()
    hits = sum(1 for w in claim_words if w in source_lower)
    return min(1.0, hits / len(claim_words))


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class ClaimVerifyAgent:
    """
    Verify whether provided sources support a claim.
    """

    def __init__(self) -> None:
        self._source_verifier = SourceVerifyAgent()

    def verify(self, claim: str, sources: list[str]) -> ClaimVerificationResult:
        """
        Check if sources support the claim.

        Parameters
        ----------
        claim:
            The claim text to verify.
        sources:
            List of source URLs or domain references.

        Returns
        -------
        ClaimVerificationResult with verdict: supported / unsupported / unverifiable.
        """
        if not sources:
            return ClaimVerificationResult(
                claim=claim,
                verdict="unverifiable",
                score=0.0,
                reasoning="No sources provided. Cannot verify without sources.",
            )

        # Verify each source
        source_results = [self._source_verifier.verify(s) for s in sources]
        details: dict[str, Any] = {}

        # High-credibility sources: tier 1 or 2
        credible_sources = [r for r in source_results if r.tier <= 2]
        blocked_sources = [r for r in source_results if r.tier == 4]

        details["total_sources"] = len(sources)
        details["credible_sources"] = len(credible_sources)
        details["blocked_sources"] = len(blocked_sources)

        # If all sources are blocked/tier-4 → unsupported
        if len(blocked_sources) == len(sources):
            return ClaimVerificationResult(
                claim=claim,
                verdict="unsupported",
                score=0.05,
                reasoning=(
                    f"All {len(sources)} provided source(s) are on the known-bad-actor list. "
                    "Cannot use these to support any claim."
                ),
                source_results=source_results,
                details=details,
            )

        # No credible sources → unverifiable
        if not credible_sources:
            return ClaimVerificationResult(
                claim=claim,
                verdict="unverifiable",
                score=0.25,
                reasoning=(
                    f"No credible (tier 1-2) sources found among {len(sources)} provided. "
                    "Claim cannot be verified with current sources."
                ),
                source_results=source_results,
                details=details,
            )

        # Compute keyword overlap for credible sources
        overlaps = [_keyword_overlap(claim, r.source) for r in credible_sources]
        avg_overlap = sum(overlaps) / len(overlaps) if overlaps else 0.0
        max_source_score = max(r.score for r in credible_sources)
        details["avg_keyword_overlap"] = round(avg_overlap, 4)
        details["max_credible_source_score"] = round(max_source_score, 4)

        # Composite confidence: source credibility (70%) + keyword overlap (30%)
        confidence = 0.70 * max_source_score + 0.30 * avg_overlap
        confidence = round(confidence, 4)

        if confidence >= 0.60:
            verdict = "supported"
            reasoning = (
                f"Claim is supported by {len(credible_sources)} credible source(s). "
                f"Source credibility score: {max_source_score:.2f}. "
                f"Keyword overlap: {avg_overlap:.2f}. Confidence: {confidence:.2f}."
            )
        elif confidence >= 0.35:
            verdict = "unverifiable"
            reasoning = (
                f"Partial evidence: {len(credible_sources)} credible source(s), "
                f"but keyword overlap is low ({avg_overlap:.2f}). "
                f"Cannot confidently verify claim with current sources. Confidence: {confidence:.2f}."
            )
        else:
            verdict = "unsupported"
            reasoning = (
                f"Insufficient evidence to support claim. "
                f"Credible sources: {len(credible_sources)}, "
                f"source score: {max_source_score:.2f}, "
                f"keyword overlap: {avg_overlap:.2f}. Confidence: {confidence:.2f}."
            )

        return ClaimVerificationResult(
            claim=claim,
            verdict=verdict,
            score=confidence,
            reasoning=reasoning,
            source_results=source_results,
            details=details,
        )
