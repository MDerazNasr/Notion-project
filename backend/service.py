"""Scoring pipeline orchestration for the NotionPulse backend."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import warnings

import networkx as nx
import numpy as np
from sklearn.exceptions import InconsistentVersionWarning

from crawler import NotionCrawler, build_graph
from embeddings import compute_semantic_features, embed_pages
from features import PageFeatures, extract_structural_features
from model import generate_labels, load_model, score_pages, train_model
from snapshot import WorkspaceSnapshot, load_fixture


@dataclass
class ScoredWorkspace:
    """Fully materialized workspace run used by API handlers."""

    workspace_id: str
    source: str
    snapshot: WorkspaceSnapshot
    graph: nx.DiGraph
    features: dict[str, PageFeatures]
    scores: dict[str, float]
    embeddings: dict[str, np.ndarray]
    model_info: dict[str, str]

    @property
    def ranked_page_ids(self) -> list[str]:
        return [
            page_id
            for page_id, _score in sorted(
                self.scores.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ]


class RunStore:
    """Small in-memory cache for the latest scored workspaces."""

    def __init__(self) -> None:
        self._runs: dict[str, ScoredWorkspace] = {}
        self._latest_key: str | None = None

    def put(self, run: ScoredWorkspace, *aliases: str) -> None:
        keys = {run.workspace_id, run.source, *aliases}
        for key in keys:
            if key:
                self._runs[key] = run
        self._latest_key = run.workspace_id

    def get(self, key: str | None = None) -> ScoredWorkspace | None:
        if key is None or key == "latest":
            if self._latest_key is None:
                return None
            return self._runs.get(self._latest_key)
        return self._runs.get(key)


_MODEL_CACHE: Any | None = None
_MODEL_INFO_CACHE: dict[str, str] | None = None


def _merge_semantic_features(
    features: dict[str, PageFeatures],
    semantic: dict[str, dict[str, float]],
) -> None:
    for page_id, values in semantic.items():
        feature = features[page_id]
        feature.cohere_drift = values["cohere_drift"]
        feature.self_neighbor_sim = values["self_neighbor_sim"]
        feature.cluster_outlier_score = values["cluster_outlier_score"]


def build_feature_set(
    snapshot: WorkspaceSnapshot,
    cohere_api_key: str | None = None,
) -> tuple[nx.DiGraph, dict[str, PageFeatures], dict[str, np.ndarray]]:
    """Build graph, structural features, embeddings, and semantic features."""
    graph = build_graph(snapshot)
    features = extract_structural_features(snapshot, graph)
    embeddings = embed_pages(snapshot, api_key=cohere_api_key)
    semantic = compute_semantic_features(snapshot, embeddings)
    _merge_semantic_features(features, semantic)
    return graph, features, embeddings


def get_or_train_model() -> tuple[Any, dict[str, str]]:
    """Load the bundled model or retrain from the demo fixture if needed."""
    global _MODEL_CACHE, _MODEL_INFO_CACHE

    if _MODEL_CACHE is not None and _MODEL_INFO_CACHE is not None:
        return _MODEL_CACHE, _MODEL_INFO_CACHE

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", InconsistentVersionWarning)
            _MODEL_CACHE = load_model()
        _MODEL_INFO_CACHE = {
            "source": "model.pkl",
            "evaluation_target": "minimize Brier score on self-supervised stale labels",
            "calibration": "Platt scaling",
        }
        return _MODEL_CACHE, _MODEL_INFO_CACHE
    except Exception as exc:
        training_snapshot = load_fixture()
        _graph, features, _embeddings = build_feature_set(training_snapshot)
        labels = generate_labels(training_snapshot)
        _MODEL_CACHE = train_model(features, labels)
        _MODEL_INFO_CACHE = {
            "source": "fixture-trained-fallback",
            "evaluation_target": "minimize Brier score on self-supervised stale labels",
            "calibration": "Platt scaling",
            "fallback_reason": str(exc),
        }
        return _MODEL_CACHE, _MODEL_INFO_CACHE


def build_scored_workspace(
    snapshot: WorkspaceSnapshot,
    source: str,
    cohere_api_key: str | None = None,
) -> ScoredWorkspace:
    """Run the scoring pipeline for a snapshot."""
    graph, features, embeddings = build_feature_set(snapshot, cohere_api_key)
    model, model_info = get_or_train_model()
    scores = score_pages(model, features)
    return ScoredWorkspace(
        workspace_id=snapshot.workspace_id,
        source=source,
        snapshot=snapshot,
        graph=graph,
        features=features,
        scores=scores,
        embeddings=embeddings,
        model_info=model_info,
    )


async def score_demo_workspace(
    cohere_api_key: str | None = None,
) -> ScoredWorkspace:
    """Score the hand-crafted demo fixture."""
    snapshot = load_fixture()
    return build_scored_workspace(
        snapshot=snapshot,
        source="demo",
        cohere_api_key=cohere_api_key,
    )


async def score_live_workspace(
    notion_token: str,
    cohere_api_key: str | None = None,
) -> ScoredWorkspace:
    """Crawl a live workspace and score it."""
    crawler = NotionCrawler(notion_token)
    snapshot = await crawler.crawl()
    return build_scored_workspace(
        snapshot=snapshot,
        source="live",
        cohere_api_key=cohere_api_key,
    )


def score_band(score: float) -> str:
    if score < 0.4:
        return "red"
    if score < 0.7:
        return "amber"
    return "green"


def summarize_signals(feature: PageFeatures) -> list[str]:
    """Generate compact dashboard-friendly signal summaries."""
    signals: list[str] = []

    if feature.days_since_edit >= 180:
        signals.append(f"Last edited {feature.days_since_edit:.0f} days ago")
    elif feature.days_since_edit <= 30:
        signals.append(f"Edited recently ({feature.days_since_edit:.0f} days ago)")

    if feature.neighbor_recency_gap >= 90:
        signals.append(
            f"Large recency gap vs linked pages ({feature.neighbor_recency_gap:.0f} days)"
        )

    if feature.inbound_backlinks == 0:
        signals.append("No inbound backlinks")
    elif feature.inbound_backlinks >= 5:
        signals.append(f"{feature.inbound_backlinks} inbound backlinks")

    if feature.is_orphan:
        signals.append("Orphaned page with no parent")

    if feature.cohere_drift >= 0.9:
        signals.append("High semantic drift from linked pages")
    elif feature.self_neighbor_sim >= 0.35:
        signals.append("High semantic coherence with neighbors")

    if feature.cluster_outlier_score >= 0.9:
        signals.append("Content is an outlier in its local cluster")

    if not signals:
        signals.append("Limited staleness signals detected")

    return signals[:3]


def page_similarity_breakdown(
    run: ScoredWorkspace,
    page_id: str,
) -> tuple[list[dict[str, float | str]], list[dict[str, float | str]]]:
    """Return the most similar and least similar linked pages."""
    page = run.snapshot.page_by_id(page_id)
    page_embedding = run.embeddings.get(page_id)

    if page is None or page_embedding is None:
        return [], []

    neighbors = set(page.backlinks) | set(page.outbound_links)
    comparisons: list[dict[str, float | str]] = []

    page_norm = float(np.linalg.norm(page_embedding))
    for neighbor_id in neighbors:
        neighbor = run.snapshot.page_by_id(neighbor_id)
        neighbor_embedding = run.embeddings.get(neighbor_id)
        if neighbor is None or neighbor_embedding is None:
            continue

        neighbor_norm = float(np.linalg.norm(neighbor_embedding))
        if page_norm == 0.0 or neighbor_norm == 0.0:
            similarity = 0.0
        else:
            similarity = float(
                np.dot(page_embedding, neighbor_embedding)
                / (page_norm * neighbor_norm)
            )

        comparisons.append(
            {
                "page_id": neighbor.id,
                "title": neighbor.title,
                "similarity": round(similarity, 4),
            }
        )

    comparisons.sort(key=lambda item: float(item["similarity"]), reverse=True)
    most_similar = comparisons[:3]
    least_similar = list(reversed(comparisons[-3:]))
    return most_similar, least_similar
