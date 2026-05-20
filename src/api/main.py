"""
Jengo Business API — FastAPI application.

Routes:
  GET  /api/v1/health       — liveness check (no auth required)
  POST /api/v1/verify       — verify content (source + claim + bias + legal)
  POST /api/v1/evaluate     — constitutional AI evaluation of an action

Authentication: Bearer token (see src/api/auth.py).
Rate limiting:  60 req/min per client (see src/api/rate_limiting.py).

Start:
  python -m jengo.api.main
  or: uvicorn jengo.api.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .auth import get_current_user
from .rate_limiting import RateLimiter
from ..constitutional.three_layer_framework import (
    ThreeLayerFramework,
    ConstitutionalViolation,
)
from ..verification.source_verify_agent import SourceVerifyAgent
from ..verification.claim_verify_agent import ClaimVerifyAgent
from ..verification.bias_detect_agent import BiasDetectAgent
from ..verification.legal_review_agent import LegalReviewAgent

# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Jengo Business API",
    description=(
        "Constitutional AI evaluation, content verification, and agent orchestration. "
        "All endpoints require Bearer token authentication."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ---------------------------------------------------------------------------
# Singletons (created once at startup)
# ---------------------------------------------------------------------------

_rate_limiter = RateLimiter(max_requests=60, window_seconds=60)
_constitutional = ThreeLayerFramework()
_source_verifier = SourceVerifyAgent()
_claim_verifier = ClaimVerifyAgent()
_bias_detector = BiasDetectAgent()
_legal_reviewer = LegalReviewAgent()

# ---------------------------------------------------------------------------
# Rate-limiting middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Skip health endpoint
    if request.url.path == "/api/v1/health":
        return await call_next(request)

    client_id = request.client.host if request.client else "unknown"
    if not _rate_limiter.check(client_id):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded. Maximum 60 requests per minute."},
        )
    return await call_next(request)

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class VerifyRequest(BaseModel):
    content: str = Field(..., description="Text content to verify.")
    sources: list[str] = Field(
        default_factory=list,
        description="Optional list of source URLs supporting the content.",
    )
    claim: str | None = Field(
        default=None,
        description="Specific claim to verify against provided sources.",
    )


class VerifyResponse(BaseModel):
    source_results: list[dict[str, Any]]
    claim_result: dict[str, Any] | None
    bias_report: dict[str, Any]
    legal_review: dict[str, Any]
    overall_approved: bool
    summary: str


class EvaluateRequest(BaseModel):
    action: dict[str, Any] = Field(
        ...,
        description=(
            "Action dict to evaluate through constitutional AI. "
            "Must include 'type'. "
            "l2_active and l3_active will be injected automatically."
        ),
    )


class EvaluateResponse(BaseModel):
    approved: bool
    l1: dict[str, Any]
    l2: dict[str, Any]
    l3: dict[str, Any]
    reasoning: str
    details: dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    constitutional_ai: str
    version: str

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get(
    "/api/v1/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["System"],
)
async def health():
    """Liveness check.  No authentication required."""
    return HealthResponse(
        status="ok",
        constitutional_ai="L1/L2/L3 active",
        version="1.0.0",
    )


@app.post(
    "/api/v1/verify",
    response_model=VerifyResponse,
    summary="Verify content",
    tags=["Verification"],
)
async def verify_content(
    body: VerifyRequest,
    current_user: Annotated[str, Depends(get_current_user)],
):
    """
    Verify content by running source, claim, bias, and legal checks.

    Returns a consolidated verification report.
    """
    # Source verification
    source_results = []
    for source in body.sources:
        r = _source_verifier.verify(source)
        source_results.append({
            "source": r.source,
            "score": r.score,
            "tier": r.tier,
            "status": r.status,
            "reasoning": r.reasoning,
        })

    # Claim verification
    claim_result = None
    if body.claim:
        cr = _claim_verifier.verify(body.claim, body.sources)
        claim_result = {
            "claim": cr.claim,
            "verdict": cr.verdict,
            "score": cr.score,
            "reasoning": cr.reasoning,
        }

    # Bias detection
    bias = _bias_detector.detect(body.content)
    bias_report = {
        "overall_severity": bias.overall_severity,
        "summary": bias.summary,
        "pattern_count": len(bias.patterns),
        "patterns": [
            {
                "bias_type": p.bias_type,
                "severity": p.severity,
                "description": p.description,
            }
            for p in bias.patterns
        ],
    }

    # Legal review
    legal = _legal_reviewer.review(body.content)
    legal_review = {
        "risk_level": legal.risk_level,
        "recommendation": legal.recommendation,
        "reasoning": legal.reasoning,
        "flag_count": len(legal.flags),
        "flags": [
            {
                "category": f.category,
                "severity": f.severity,
                "description": f.description,
            }
            for f in legal.flags
        ],
    }

    # Overall: approved if legal allows publish/review and no high bias
    legal_ok = legal.recommendation != "block"
    bias_ok = bias.overall_severity != "high"
    overall_approved = legal_ok and bias_ok

    summary_parts = []
    if not overall_approved:
        if not legal_ok:
            summary_parts.append(f"Legal review: BLOCK ({legal.risk_level} risk).")
        if not bias_ok:
            summary_parts.append(f"Bias detection: HIGH severity.")
    else:
        summary_parts.append("Content passed verification checks.")

    return VerifyResponse(
        source_results=source_results,
        claim_result=claim_result,
        bias_report=bias_report,
        legal_review=legal_review,
        overall_approved=overall_approved,
        summary=" ".join(summary_parts) or "OK",
    )


@app.post(
    "/api/v1/evaluate",
    response_model=EvaluateResponse,
    summary="Constitutional AI evaluation",
    tags=["Constitutional AI"],
)
async def evaluate_action(
    body: EvaluateRequest,
    current_user: Annotated[str, Depends(get_current_user)],
):
    """
    Evaluate an action through the Three-Layer Constitutional AI Framework.

    l2_active and l3_active are injected automatically.
    """
    action = {
        **body.action,
        "l2_active": True,
        "l3_active": True,
    }

    try:
        result = _constitutional.evaluate_action(action)
    except ConstitutionalViolation as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Constitutional violation: {exc}",
        )

    return EvaluateResponse(
        approved=result["approved"],
        l1=result["l1"],
        l2=result["l2"],
        l3=result["l3"],
        reasoning=result["reasoning"],
        details=result.get("details", {}),
    )

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "jengo.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
