"""
Bias Detection Agent.

Identifies three types of bias in text content:

1. Framing bias     — loaded/emotional language that shapes perception.
2. Selection bias   — what is absent; absence of counter-evidence or alternative views.
3. Source concentration — all sources from the same ideological cluster.

Returns a BiasReport with a list of detected patterns and a severity level.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BiasPattern:
    """A single detected bias pattern."""
    bias_type: str         # 'framing' | 'selection' | 'source_concentration'
    severity: str          # 'low' | 'medium' | 'high'
    description: str
    evidence: list[str] = field(default_factory=list)


@dataclass
class BiasReport:
    """Full result from BiasDetectAgent.detect()."""
    content_length: int
    patterns: list[BiasPattern]
    overall_severity: str   # 'none' | 'low' | 'medium' | 'high'
    summary: str
    details: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Framing bias: loaded language lexicon
# ---------------------------------------------------------------------------

_LOADED_LANGUAGE: dict[str, str] = {
    # Positive loading
    "heroic": "positive framing",
    "brilliant": "positive framing",
    "legendary": "positive framing",
    "inspirational": "positive framing",
    "brave patriots": "positive framing",
    "freedom fighters": "positive framing",
    # Negative loading
    "terrorist": "negative framing",
    "regime": "negative framing",
    "puppet": "negative framing",
    "radical": "negative framing",
    "extremist": "negative framing",
    "thug": "negative framing",
    "invasion": "negative framing",
    "swarm": "negative framing",
    "flood": "negative framing",
    "plague": "negative framing",
    "infestation": "negative framing",
    "evil": "negative framing",
    "wicked": "negative framing",
    "despicable": "negative framing",
    "treacherous": "negative framing",
    # Hedging that buries facts
    "some say": "epistemic hedge",
    "many believe": "epistemic hedge",
    "people are saying": "epistemic hedge",
    "it is claimed": "epistemic hedge",
    "allegedly": "epistemic hedge (may be appropriate or may minimise facts)",
}

_PROPAGANDA_TECHNIQUES: list[str] = [
    "the only solution",
    "everyone knows",
    "it is obvious that",
    "no reasonable person",
    "true patriots",
    "the real truth",
    "what they don't want you to know",
    "wake up",
    "sheeple",
    "fake news",
    "mainstream media lies",
    "deep state",
    "great replacement",
    "white genocide",
    "globalist",
    "zionist agenda",
]


# ---------------------------------------------------------------------------
# Selection bias: markers of absent perspectives
# ---------------------------------------------------------------------------

_BALANCE_MARKERS: list[str] = [
    "on the other hand",
    "however",
    "critics argue",
    "opponents say",
    "an alternative view",
    "in contrast",
    "dissenting",
    "counter-argument",
    "some disagree",
    "not everyone agrees",
]


# ---------------------------------------------------------------------------
# Source concentration: domain clusters
# ---------------------------------------------------------------------------

_IDEOLOGICAL_CLUSTERS: dict[str, list[str]] = {
    "right_wing_us": [
        "foxnews.com", "breitbart.com", "dailywire.com",
        "thefederalist.com", "nationalreview.com", "nypost.com",
    ],
    "left_wing_us": [
        "msnbc.com", "huffpost.com", "slate.com",
        "thenation.com", "motherjones.com",
    ],
    "russian_state": [
        "rt.com", "sputniknews.com", "tass.com", "ria.ru",
    ],
    "disinfo": [
        "infowars.com", "naturalnews.com", "globalresearch.ca",
        "thegatewaypundit.com",
    ],
}


def _cluster_of(url: str) -> str | None:
    url_lower = url.lower()
    for cluster, domains in _IDEOLOGICAL_CLUSTERS.items():
        if any(d in url_lower for d in domains):
            return cluster
    return None


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class BiasDetectAgent:
    """Detect framing bias, selection bias, and source concentration."""

    def detect(self, content: str) -> BiasReport:
        """
        Analyse content for bias patterns.

        Parameters
        ----------
        content:
            The text to analyse.  May include URLs (used for source
            concentration check).

        Returns
        -------
        BiasReport with list of BiasPattern instances and overall severity.
        """
        patterns: list[BiasPattern] = []
        content_lower = content.lower()

        # --- 1. Framing bias ---
        loaded_found: list[str] = []
        for phrase, framing_type in _LOADED_LANGUAGE.items():
            if phrase in content_lower:
                loaded_found.append(f"'{phrase}' ({framing_type})")

        propaganda_found: list[str] = []
        for phrase in _PROPAGANDA_TECHNIQUES:
            if phrase in content_lower:
                propaganda_found.append(f"'{phrase}'")

        if propaganda_found:
            patterns.append(BiasPattern(
                bias_type="framing",
                severity="high",
                description="Propaganda-technique language detected.",
                evidence=propaganda_found,
            ))
        elif len(loaded_found) >= 4:
            patterns.append(BiasPattern(
                bias_type="framing",
                severity="medium",
                description=f"Multiple ({len(loaded_found)}) loaded-language instances.",
                evidence=loaded_found[:6],
            ))
        elif loaded_found:
            patterns.append(BiasPattern(
                bias_type="framing",
                severity="low",
                description=f"{len(loaded_found)} loaded-language instance(s).",
                evidence=loaded_found,
            ))

        # --- 2. Selection bias ---
        balance_count = sum(1 for m in _BALANCE_MARKERS if m in content_lower)
        word_count = max(1, len(content.split()))

        # Long content without any balance markers suggests selection bias
        if word_count > 200 and balance_count == 0:
            patterns.append(BiasPattern(
                bias_type="selection",
                severity="medium",
                description=(
                    f"Content has {word_count} words but no balance markers "
                    f"(no 'however', 'critics argue', 'on the other hand', etc.). "
                    "Possible single-perspective framing."
                ),
                evidence=[],
            ))
        elif word_count > 500 and balance_count < 2:
            patterns.append(BiasPattern(
                bias_type="selection",
                severity="low",
                description=(
                    f"Long content ({word_count} words) with only {balance_count} "
                    "balance markers. Consider adding counter-perspectives."
                ),
                evidence=[],
            ))

        # --- 3. Source concentration ---
        # Extract URLs from content
        urls = re.findall(r"https?://[^\s\"'>]+", content)
        if urls:
            cluster_counts: dict[str, int] = {}
            for url in urls:
                c = _cluster_of(url)
                if c:
                    cluster_counts[c] = cluster_counts.get(c, 0) + 1

            total_clustered = sum(cluster_counts.values())
            if total_clustered >= 2:
                dominant = max(cluster_counts, key=lambda k: cluster_counts[k])
                dominant_share = cluster_counts[dominant] / len(urls)

                if dominant_share >= 0.75:
                    patterns.append(BiasPattern(
                        bias_type="source_concentration",
                        severity="high" if dominant in ("disinfo", "russian_state") else "medium",
                        description=(
                            f"{int(dominant_share * 100)}% of sources are from "
                            f"'{dominant}' cluster ({cluster_counts[dominant]}/{len(urls)} URLs)."
                        ),
                        evidence=[f"Cluster: {dominant}", f"Count: {cluster_counts[dominant]}"],
                    ))

        # --- Compute overall severity ---
        severity_rank = {"none": 0, "low": 1, "medium": 2, "high": 3}
        if not patterns:
            overall = "none"
        else:
            overall = max(p.severity for p in patterns, key=lambda s: severity_rank.get(s, 0))

        summary_parts = []
        if not patterns:
            summary_parts.append("No significant bias patterns detected.")
        else:
            type_counts = {}
            for p in patterns:
                type_counts[p.bias_type] = type_counts.get(p.bias_type, 0) + 1
            summary_parts.append(
                f"{len(patterns)} bias pattern(s) detected: "
                + ", ".join(f"{t} ({n})" for t, n in type_counts.items())
                + f". Overall severity: {overall}."
            )

        return BiasReport(
            content_length=len(content),
            patterns=patterns,
            overall_severity=overall,
            summary=" ".join(summary_parts),
            details={
                "word_count": word_count,
                "balance_markers_found": balance_count,
                "urls_found": len(urls) if urls else 0,
            },
        )
