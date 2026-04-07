"""WorkspaceSnapshot dataclass and loaders (fixture + live API)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class EditEvent:
    time: datetime
    magnitude: float  # fraction of content changed (0.0 - 1.0)


@dataclass
class PageNode:
    id: str
    title: str
    content: str
    last_edited_time: datetime
    created_time: datetime
    backlinks: list[str] = field(default_factory=list)
    outbound_links: list[str] = field(default_factory=list)
    parent_id: str | None = None
    edit_history: list[EditEvent] = field(default_factory=list)


@dataclass
class WorkspaceSnapshot:
    workspace_id: str
    snapshot_time: datetime
    pages: list[PageNode] = field(default_factory=list)

    def page_by_id(self, page_id: str) -> PageNode | None:
        for page in self.pages:
            if page.id == page_id:
                return page
        return None

    @property
    def page_ids(self) -> list[str]:
        return [p.id for p in self.pages]


def _parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def load_fixture(path: str | Path | None = None) -> WorkspaceSnapshot:
    """Load a WorkspaceSnapshot from the demo fixture JSON."""
    if path is None:
        path = Path(__file__).parent / "demo_workspace.json"
    else:
        path = Path(path)

    with open(path) as f:
        raw = json.load(f)

    pages = []
    for p in raw["pages"]:
        edit_history = [
            EditEvent(time=_parse_iso(e["time"]), magnitude=e["magnitude"])
            for e in p.get("edit_history", [])
        ]
        pages.append(
            PageNode(
                id=p["id"],
                title=p["title"],
                content=p["content"],
                last_edited_time=_parse_iso(p["last_edited_time"]),
                created_time=_parse_iso(p["created_time"]),
                backlinks=p.get("backlinks", []),
                outbound_links=p.get("outbound_links", []),
                parent_id=p.get("parent_id"),
                edit_history=edit_history,
            )
        )

    return WorkspaceSnapshot(
        workspace_id=raw["workspace_id"],
        snapshot_time=_parse_iso(raw["snapshot_time"]),
        pages=pages,
    )
