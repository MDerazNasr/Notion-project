"""Structural and semantic feature extraction for page scoring."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import networkx as nx

from snapshot import PageNode, WorkspaceSnapshot


@dataclass
class PageFeatures:
    """Feature vector for a single page."""
    page_id: str
    # Structural features
    days_since_edit: float
    edit_frequency: float
    inbound_backlinks: int
    neighbor_recency_gap: float
    is_orphan: int
    # Semantic features (filled later by embeddings pipeline)
    cohere_drift: float = 0.0
    self_neighbor_sim: float = 0.0
    cluster_outlier_score: float = 0.0

    def to_vector(self) -> list[float]:
        return [
            self.days_since_edit,
            self.edit_frequency,
            float(self.inbound_backlinks),
            self.neighbor_recency_gap,
            float(self.is_orphan),
            self.cohere_drift,
            self.self_neighbor_sim,
            self.cluster_outlier_score,
        ]

    @staticmethod
    def feature_names() -> list[str]:
        return [
            "days_since_edit",
            "edit_frequency",
            "inbound_backlinks",
            "neighbor_recency_gap",
            "is_orphan",
            "cohere_drift",
            "self_neighbor_sim",
            "cluster_outlier_score",
        ]


def _days_between(a: datetime, b: datetime) -> float:
    return abs((a - b).total_seconds()) / 86400.0


def _edit_frequency(page: PageNode, now: datetime) -> float:
    """Edits per month over trailing 90 days."""
    cutoff = now.timestamp() - (90 * 86400)
    recent_edits = [
        e for e in page.edit_history
        if e.time.timestamp() >= cutoff
    ]
    return len(recent_edits) / 3.0  # 3 months


def _neighbor_recency_gap(
    page: PageNode,
    snapshot: WorkspaceSnapshot,
    now: datetime,
) -> float:
    """Max days between this page's edit and any linked page's edit."""
    linked_ids = set(page.outbound_links) | set(page.backlinks)
    if not linked_ids:
        return 0.0

    page_edit_days = _days_between(page.last_edited_time, now)
    max_gap = 0.0

    for linked_id in linked_ids:
        linked = snapshot.page_by_id(linked_id)
        if linked is None:
            continue
        linked_days = _days_between(linked.last_edited_time, now)
        gap = abs(page_edit_days - linked_days)
        max_gap = max(max_gap, gap)

    return max_gap


def extract_structural_features(
    snapshot: WorkspaceSnapshot,
    graph: nx.DiGraph,
) -> dict[str, PageFeatures]:
    """Extract structural features for every page in the snapshot."""
    now = snapshot.snapshot_time
    features: dict[str, PageFeatures] = {}

    for page in snapshot.pages:
        is_orphan = (
            1 if len(page.backlinks) == 0 and page.parent_id is None else 0
        )

        features[page.id] = PageFeatures(
            page_id=page.id,
            days_since_edit=_days_between(page.last_edited_time, now),
            edit_frequency=_edit_frequency(page, now),
            inbound_backlinks=len(page.backlinks),
            neighbor_recency_gap=_neighbor_recency_gap(page, snapshot, now),
            is_orphan=is_orphan,
        )

    return features
