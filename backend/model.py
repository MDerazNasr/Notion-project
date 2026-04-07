"""GBM training, Platt scaling, and scoring pipeline."""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import cross_val_predict

from features import PageFeatures
from snapshot import PageNode, WorkspaceSnapshot

MODEL_PATH = Path(__file__).parent / "model.pkl"

# Self-supervised labeling thresholds
DORMANCY_DAYS = 60
EDIT_MAGNITUDE_THRESHOLD = 0.4


def generate_labels(snapshot: WorkspaceSnapshot) -> dict[str, int]:
    """Generate self-supervised staleness labels from edit history.

    The proxy: a page that received a large edit (magnitude > 0.4) after a
    dormant period (no edits for 60+ days) is retrospectively labeled as
    having been stale. Pages without this pattern are labeled fresh.

    Additional heuristic: pages with no edits in 270+ days or whose last
    edit was trivial (< 0.1) after 180+ days of inactivity are also stale.
    """
    labels: dict[str, int] = {}

    for page in snapshot.pages:
        history = sorted(page.edit_history, key=lambda e: e.time)
        was_stale = False

        for i in range(1, len(history)):
            prev = history[i - 1]
            curr = history[i]
            gap_days = (curr.time - prev.time).total_seconds() / 86400.0

            if gap_days >= DORMANCY_DAYS and curr.magnitude >= EDIT_MAGNITUDE_THRESHOLD:
                was_stale = True
                break

        days_since_last = (
            snapshot.snapshot_time - page.last_edited_time
        ).total_seconds() / 86400.0

        # Pages untouched for 270+ days
        if days_since_last > 270:
            was_stale = True

        # Pages with only trivial recent edits after long gaps
        if days_since_last > 180 and history:
            last_edit = history[-1]
            if last_edit.magnitude < 0.1:
                was_stale = True

        labels[page.id] = 1 if was_stale else 0

    return labels


def train_model(
    features: dict[str, PageFeatures],
    labels: dict[str, int],
) -> CalibratedClassifierCV:
    """Train a GBM with Platt scaling for calibrated probability output."""
    page_ids = sorted(features.keys())
    X = np.array([features[pid].to_vector() for pid in page_ids])
    y = np.array([labels[pid] for pid in page_ids])

    base_model = GradientBoostingClassifier(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.1,
        min_samples_leaf=2,
        random_state=42,
    )

    # Platt scaling via sigmoid calibration
    # Use cv=3 since dataset is small (28 pages)
    calibrated = CalibratedClassifierCV(
        base_model, method="sigmoid", cv=3
    )
    calibrated.fit(X, y)

    # Evaluate with cross-validated predictions
    cv_probs = cross_val_predict(
        CalibratedClassifierCV(
            GradientBoostingClassifier(
                n_estimators=100,
                max_depth=3,
                learning_rate=0.1,
                min_samples_leaf=2,
                random_state=42,
            ),
            method="sigmoid",
            cv=3,
        ),
        X,
        y,
        cv=3,
        method="predict_proba",
    )
    brier = brier_score_loss(y, cv_probs[:, 1])
    print(f"Brier score (3-fold CV): {brier:.4f}")

    return calibrated


def save_model(model: CalibratedClassifierCV, path: Path = MODEL_PATH):
    with open(path, "wb") as f:
        pickle.dump(model, f)


def load_model(path: Path = MODEL_PATH) -> CalibratedClassifierCV:
    with open(path, "rb") as f:
        return pickle.load(f)


def score_pages(
    model: CalibratedClassifierCV,
    features: dict[str, PageFeatures],
) -> dict[str, float]:
    """Score pages, returning calibrated staleness probability per page."""
    page_ids = sorted(features.keys())
    X = np.array([features[pid].to_vector() for pid in page_ids])
    probs = model.predict_proba(X)[:, 1]

    # Reliability = 1 - staleness probability
    return {pid: round(1.0 - float(prob), 4) for pid, prob in zip(page_ids, probs)}
