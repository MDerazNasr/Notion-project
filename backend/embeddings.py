"""Cohere embedding pipeline with SQLite cache."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import numpy as np

from snapshot import PageNode, WorkspaceSnapshot

EMBED_MODEL = "embed-english-v3.0"
EMBED_INPUT_TYPE = "search_document"
MAX_TOKENS = 512
DB_PATH = Path(__file__).parent / "embeddings_cache.db"


def _init_cache(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS embeddings (
            cache_key TEXT PRIMARY KEY,
            embedding BLOB,
            model TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    return conn


def _cache_key(page_id: str, last_edited: str) -> str:
    """Key on page_id + last_edited_time so unchanged pages never re-embed."""
    raw = f"{page_id}:{last_edited}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _truncate_for_embedding(text: str) -> str:
    """Concatenate first and last 256 tokens if text exceeds MAX_TOKENS.

    Rough heuristic: 1 token ~ 4 chars. This captures the intro and
    conclusion, which tend to be most representative of page intent.
    """
    chars_limit = MAX_TOKENS * 4
    if len(text) <= chars_limit:
        return text
    half = chars_limit // 2
    return text[:half] + "\n...\n" + text[-half:]


def embed_pages(
    snapshot: WorkspaceSnapshot,
    api_key: str | None = None,
    db_path: Path = DB_PATH,
) -> dict[str, np.ndarray]:
    """Embed all pages, using cache for unchanged pages.

    Returns a dict mapping page_id to embedding vector.
    """
    conn = _init_cache(db_path)
    results: dict[str, np.ndarray] = {}
    to_embed: list[PageNode] = []

    # Check cache first
    for page in snapshot.pages:
        key = _cache_key(page.id, page.last_edited_time.isoformat())
        row = conn.execute(
            "SELECT embedding FROM embeddings WHERE cache_key = ?", (key,)
        ).fetchone()

        if row is not None:
            results[page.id] = np.frombuffer(row[0], dtype=np.float32)
        else:
            to_embed.append(page)

    if to_embed and api_key:
        import cohere

        co = cohere.Client(api_key)
        texts = [
            _truncate_for_embedding(p.content or p.title) for p in to_embed
        ]

        # Cohere accepts up to 96 texts per call
        batch_size = 96
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            resp = co.embed(
                texts=batch,
                model=EMBED_MODEL,
                input_type=EMBED_INPUT_TYPE,
            )
            all_embeddings.extend(resp.embeddings)

        for page, emb in zip(to_embed, all_embeddings):
            vec = np.array(emb, dtype=np.float32)
            results[page.id] = vec

            key = _cache_key(page.id, page.last_edited_time.isoformat())
            conn.execute(
                "INSERT OR REPLACE INTO embeddings (cache_key, embedding, model) VALUES (?, ?, ?)",
                (key, vec.tobytes(), EMBED_MODEL),
            )

        conn.commit()

    elif to_embed and not api_key:
        # Fallback: generate deterministic pseudo-embeddings for demo/testing
        rng = np.random.RandomState(42)
        for page in to_embed:
            # Seed on page ID for reproducibility
            seed = int(hashlib.md5(page.id.encode()).hexdigest()[:8], 16)
            page_rng = np.random.RandomState(seed)
            vec = page_rng.randn(1024).astype(np.float32)
            vec = vec / np.linalg.norm(vec)
            results[page.id] = vec

    conn.close()
    return results


def compute_semantic_features(
    snapshot: WorkspaceSnapshot,
    embeddings: dict[str, np.ndarray],
) -> dict[str, dict[str, float]]:
    """Compute semantic features from embeddings.

    Returns dict mapping page_id to {cohere_drift, self_neighbor_sim,
    cluster_outlier_score}.
    """
    features: dict[str, dict[str, float]] = {}

    # Precompute all embedding norms for cosine similarity
    def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
        dot = float(np.dot(a, b))
        na = float(np.linalg.norm(a))
        nb = float(np.linalg.norm(b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    # Group pages by parent for cluster analysis
    cluster_map: dict[str, list[str]] = {}
    for page in snapshot.pages:
        cid = page.parent_id or "root"
        cluster_map.setdefault(cid, []).append(page.id)

    # Compute cluster centroids
    cluster_centroids: dict[str, np.ndarray] = {}
    for cid, page_ids in cluster_map.items():
        vecs = [embeddings[pid] for pid in page_ids if pid in embeddings]
        if vecs:
            cluster_centroids[cid] = np.mean(vecs, axis=0)

    for page in snapshot.pages:
        if page.id not in embeddings:
            features[page.id] = {
                "cohere_drift": 0.0,
                "self_neighbor_sim": 0.0,
                "cluster_outlier_score": 0.0,
            }
            continue

        page_emb = embeddings[page.id]

        # cohere_drift: 1 - mean cosine similarity with direct link neighbors
        neighbor_ids = set(page.outbound_links) | set(page.backlinks)
        if neighbor_ids:
            sims = [
                cosine_sim(page_emb, embeddings[nid])
                for nid in neighbor_ids
                if nid in embeddings
            ]
            cohere_drift = 1.0 - (sum(sims) / len(sims)) if sims else 0.0
        else:
            cohere_drift = 0.0

        # self_neighbor_sim: cosine sim between page embedding and mean of
        # neighbor embeddings
        if neighbor_ids:
            neighbor_vecs = [
                embeddings[nid]
                for nid in neighbor_ids
                if nid in embeddings
            ]
            if neighbor_vecs:
                mean_neighbor = np.mean(neighbor_vecs, axis=0)
                self_neighbor_sim = cosine_sim(page_emb, mean_neighbor)
            else:
                self_neighbor_sim = 0.0
        else:
            self_neighbor_sim = 0.0

        # cluster_outlier_score: distance from page embedding to its cluster
        # centroid (using k-nearest within cluster)
        cid = page.parent_id or "root"
        if cid in cluster_centroids:
            centroid = cluster_centroids[cid]
            cluster_outlier_score = 1.0 - cosine_sim(page_emb, centroid)
        else:
            cluster_outlier_score = 0.0

        features[page.id] = {
            "cohere_drift": cohere_drift,
            "self_neighbor_sim": self_neighbor_sim,
            "cluster_outlier_score": cluster_outlier_score,
        }

    return features
