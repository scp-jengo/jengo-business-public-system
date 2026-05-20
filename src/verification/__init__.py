"""
Verification Agents — source, claim, bias, legal review.

Public surface:
  SourceVerifyAgent     — verify domain credibility, return tier 1-4
  ClaimVerifyAgent      — check if sources support a claim
  BiasDetectAgent       — detect framing, selection, source-concentration bias
  LegalReviewAgent      — flag defamation, copyright, privacy risks
  VerificationResult    — shared result type (from source_verify_agent)
  ClaimVerificationResult — claim-specific result
  BiasReport, BiasPattern — bias detection results
  LegalReviewResult, LegalFlag — legal review results
"""

from .source_verify_agent import SourceVerifyAgent, VerificationResult
from .claim_verify_agent import ClaimVerifyAgent, ClaimVerificationResult
from .bias_detect_agent import BiasDetectAgent, BiasReport, BiasPattern
from .legal_review_agent import LegalReviewAgent, LegalReviewResult, LegalFlag

__all__ = [
    "SourceVerifyAgent",
    "VerificationResult",
    "ClaimVerifyAgent",
    "ClaimVerificationResult",
    "BiasDetectAgent",
    "BiasReport",
    "BiasPattern",
    "LegalReviewAgent",
    "LegalReviewResult",
    "LegalFlag",
]
