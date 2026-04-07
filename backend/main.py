"""FastAPI entrypoint for the NotionPulse backend."""
from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from service import (
    RunStore,
    ScoredWorkspace,
    page_similarity_breakdown,
    score_band,
    score_demo_workspace,
    score_live_workspace,
    summarize_signals,
)

load_dotenv()

app = FastAPI(title="NotionPulse", version="0.1.0")
RUNS = RunStore()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScoreRequest(BaseModel):
    notion_token: str | None = Field(
        default=None,
        description="Notion integration token used for live workspace crawling.",
    )
    cohere_api_key: str | None = Field(
        default=None,
        description="Optional Cohere API key. Falls back to deterministic demo embeddings.",
    )
    demo_mode: bool = Field(
        default=False,
        description="Load the local fixture instead of crawling a live workspace.",
    )


class ModelInfo(BaseModel):
    source: str
    evaluation_target: str
    calibration: str
    fallback_reason: str | None = None


class ScorePage(BaseModel):
    page_id: str
    title: str
    reliability_score: float
    score_band: str
    last_edited_time: str
    days_since_edit: float
    headline_reason: str
    top_signals: list[str]


class ScoreResponse(BaseModel):
    workspace_id: str
    source: str
    snapshot_time: str
    page_count: int
    model: ModelInfo
    pages: list[ScorePage]


class FeatureValue(BaseModel):
    name: str
    value: float


class SimilarPage(BaseModel):
    page_id: str
    title: str
    similarity: float


class PageDetailResponse(BaseModel):
    workspace_id: str
    source: str
    page_id: str
    title: str
    reliability_score: float
    score_band: str
    last_edited_time: str
    structural_features: list[FeatureValue]
    semantic_features: list[FeatureValue]
    top_signals: list[str]
    most_similar_neighbors: list[SimilarPage]
    least_similar_neighbors: list[SimilarPage]


class GraphNode(BaseModel):
    page_id: str
    title: str
    reliability_score: float
    score_band: str


class GraphEdge(BaseModel):
    source: str
    target: str


class GraphResponse(BaseModel):
    workspace_id: str
    source: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]


def _resolve_key(source: str | None) -> str | None:
    if source in (None, "", "latest"):
        return None
    return source


async def _ensure_run(source: str | None = None) -> ScoredWorkspace:
    run = RUNS.get(_resolve_key(source))
    if run is not None:
        return run

    if source not in (None, "", "latest", "demo"):
        raise HTTPException(status_code=404, detail="Workspace run not found")

    demo_run = await score_demo_workspace(
        cohere_api_key=os.getenv("COHERE_API_KEY"),
    )
    RUNS.put(demo_run, "demo")
    return demo_run


def _serialize_score_response(run: ScoredWorkspace) -> ScoreResponse:
    pages: list[ScorePage] = []

    for page_id in run.ranked_page_ids:
        page = run.snapshot.page_by_id(page_id)
        feature = run.features[page_id]
        score = run.scores[page_id]
        signals = summarize_signals(feature)

        if page is None:
            continue

        pages.append(
            ScorePage(
                page_id=page.id,
                title=page.title,
                reliability_score=score,
                score_band=score_band(score),
                last_edited_time=page.last_edited_time.isoformat(),
                days_since_edit=round(feature.days_since_edit, 2),
                headline_reason=signals[0],
                top_signals=signals,
            )
        )

    return ScoreResponse(
        workspace_id=run.workspace_id,
        source=run.source,
        snapshot_time=run.snapshot.snapshot_time.isoformat(),
        page_count=len(pages),
        model=ModelInfo(**run.model_info),
        pages=pages,
    )


def _feature_breakdown(run: ScoredWorkspace, page_id: str) -> PageDetailResponse:
    page = run.snapshot.page_by_id(page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found in current run")

    feature = run.features[page_id]
    score = run.scores[page_id]
    most_similar, least_similar = page_similarity_breakdown(run, page_id)

    return PageDetailResponse(
        workspace_id=run.workspace_id,
        source=run.source,
        page_id=page.id,
        title=page.title,
        reliability_score=score,
        score_band=score_band(score),
        last_edited_time=page.last_edited_time.isoformat(),
        structural_features=[
            FeatureValue(name="days_since_edit", value=round(feature.days_since_edit, 4)),
            FeatureValue(name="edit_frequency", value=round(feature.edit_frequency, 4)),
            FeatureValue(name="inbound_backlinks", value=float(feature.inbound_backlinks)),
            FeatureValue(
                name="neighbor_recency_gap",
                value=round(feature.neighbor_recency_gap, 4),
            ),
            FeatureValue(name="is_orphan", value=float(feature.is_orphan)),
        ],
        semantic_features=[
            FeatureValue(name="cohere_drift", value=round(feature.cohere_drift, 4)),
            FeatureValue(
                name="self_neighbor_sim",
                value=round(feature.self_neighbor_sim, 4),
            ),
            FeatureValue(
                name="cluster_outlier_score",
                value=round(feature.cluster_outlier_score, 4),
            ),
        ],
        top_signals=summarize_signals(feature),
        most_similar_neighbors=[
            SimilarPage(**neighbor) for neighbor in most_similar
        ],
        least_similar_neighbors=[
            SimilarPage(**neighbor) for neighbor in least_similar
        ],
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/score", response_model=ScoreResponse)
async def score(request: ScoreRequest) -> ScoreResponse:
    cohere_api_key = request.cohere_api_key or os.getenv("COHERE_API_KEY")

    if request.demo_mode:
        run = await score_demo_workspace(cohere_api_key=cohere_api_key)
        RUNS.put(run, "demo")
        return _serialize_score_response(run)

    notion_token = request.notion_token or os.getenv("NOTION_TOKEN")
    if not notion_token:
        raise HTTPException(
            status_code=400,
            detail="Missing Notion token. Provide notion_token or set NOTION_TOKEN.",
        )

    run = await score_live_workspace(
        notion_token=notion_token,
        cohere_api_key=cohere_api_key,
    )
    RUNS.put(run, "live")
    return _serialize_score_response(run)


@app.post("/score/demo", response_model=ScoreResponse)
async def score_demo() -> ScoreResponse:
    run = await score_demo_workspace(
        cohere_api_key=os.getenv("COHERE_API_KEY"),
    )
    RUNS.put(run, "demo")
    return _serialize_score_response(run)


@app.get("/scores", response_model=ScoreResponse)
async def scores(
    source: str | None = Query(
        default=None,
        description="Optional run selector. Use demo, live, workspace id, or latest.",
    ),
) -> ScoreResponse:
    run = await _ensure_run(source)
    return _serialize_score_response(run)


@app.get("/page/{page_id}", response_model=PageDetailResponse)
async def page_detail(
    page_id: str,
    source: str | None = Query(
        default=None,
        description="Optional run selector. Use demo, live, workspace id, or latest.",
    ),
) -> PageDetailResponse:
    run = await _ensure_run(source)
    return _feature_breakdown(run, page_id)


@app.get("/graph", response_model=GraphResponse)
async def graph(
    source: str | None = Query(
        default=None,
        description="Optional run selector. Use demo, live, workspace id, or latest.",
    ),
) -> GraphResponse:
    run = await _ensure_run(source)

    nodes = [
        GraphNode(
            page_id=page_id,
            title=run.snapshot.page_by_id(page_id).title,
            reliability_score=run.scores[page_id],
            score_band=score_band(run.scores[page_id]),
        )
        for page_id in run.ranked_page_ids
        if run.snapshot.page_by_id(page_id) is not None
    ]
    edges = [
        GraphEdge(source=source_id, target=target_id)
        for source_id, target_id in run.graph.edges()
    ]

    return GraphResponse(
        workspace_id=run.workspace_id,
        source=run.source,
        nodes=nodes,
        edges=edges,
    )
