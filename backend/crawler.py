"""Live Notion API crawler that produces a WorkspaceSnapshot."""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

import httpx
import networkx as nx

from snapshot import EditEvent, PageNode, WorkspaceSnapshot

NOTION_API_VERSION = "2026-03-11"
NOTION_BASE = "https://api.notion.com/v1"
# Notion rate limit: 3 requests per second
RATE_LIMIT_DELAY = 0.34


class NotionCrawler:
    """Crawls a Notion workspace and builds a WorkspaceSnapshot."""

    def __init__(self, token: str):
        self.token = token
        self._last_request_time = 0.0
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=NOTION_BASE,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Notion-Version": NOTION_API_VERSION,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def _rate_limited_get(
        self, path: str, params: dict | None = None
    ) -> dict:
        """GET with rate limiting and exponential backoff on 429."""
        client = await self._get_client()
        backoff = 1.0

        for attempt in range(5):
            elapsed = time.monotonic() - self._last_request_time
            if elapsed < RATE_LIMIT_DELAY:
                await asyncio.sleep(RATE_LIMIT_DELAY - elapsed)

            self._last_request_time = time.monotonic()
            resp = await client.get(path, params=params)

            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", backoff))
                await asyncio.sleep(retry_after)
                backoff *= 2
                continue

            resp.raise_for_status()
            return resp.json()

        raise RuntimeError(f"Rate limited after 5 retries on {path}")

    async def _paginate(self, path: str, params: dict | None = None) -> list[dict]:
        """Paginate through a Notion list endpoint."""
        results = []
        start_cursor = None

        while True:
            req_params = dict(params or {})
            if start_cursor:
                req_params["start_cursor"] = start_cursor

            data = await self._rate_limited_get(path, req_params)
            results.extend(data.get("results", []))

            if not data.get("has_more"):
                break
            start_cursor = data.get("next_cursor")

        return results

    async def _fetch_all_pages(self) -> list[dict]:
        """Fetch all pages accessible to the integration."""
        return await self._paginate("/search", {"filter": {"property": "object", "value": "page"}})

    async def _fetch_all_databases(self) -> list[dict]:
        """Fetch all databases accessible to the integration."""
        return await self._paginate("/search", {"filter": {"property": "object", "value": "database"}})

    async def _fetch_blocks(self, page_id: str) -> list[dict]:
        """Fetch all child blocks of a page."""
        return await self._paginate(f"/blocks/{page_id}/children")

    def _extract_title(self, page: dict) -> str:
        """Extract plain text title from a Notion page object."""
        props = page.get("properties", {})
        for prop in props.values():
            if prop.get("type") == "title":
                title_parts = prop.get("title", [])
                return "".join(t.get("plain_text", "") for t in title_parts)
        return "Untitled"

    def _extract_text_from_blocks(self, blocks: list[dict]) -> str:
        """Concatenate plain text from all block types."""
        parts = []
        for block in blocks:
            block_type = block.get("type", "")
            type_data = block.get(block_type, {})

            # Most block types store text in rich_text
            rich_text = type_data.get("rich_text", [])
            if rich_text:
                text = "".join(rt.get("plain_text", "") for rt in rich_text)
                parts.append(text)

            # Code blocks
            if block_type == "code":
                caption = type_data.get("caption", [])
                if caption:
                    parts.append(
                        "".join(c.get("plain_text", "") for c in caption)
                    )

        return "\n".join(parts)

    def _extract_links_from_blocks(self, blocks: list[dict]) -> list[str]:
        """Extract page mention links from blocks."""
        links = []
        for block in blocks:
            block_type = block.get("type", "")
            type_data = block.get(block_type, {})
            rich_text = type_data.get("rich_text", [])

            for rt in rich_text:
                mention = rt.get("mention")
                if mention and mention.get("type") == "page":
                    page_id = mention["page"].get("id")
                    if page_id:
                        links.append(page_id)
        return links

    def _parse_time(self, iso_str: str | None) -> datetime:
        if not iso_str:
            return datetime.now(timezone.utc)
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))

    async def crawl(self) -> WorkspaceSnapshot:
        """Crawl the workspace and return a snapshot."""
        raw_pages = await self._fetch_all_pages()
        raw_dbs = await self._fetch_all_databases()

        # Build a set of all known page IDs
        all_page_ids = {p["id"] for p in raw_pages}

        # Fetch blocks for each page to get content and links
        page_nodes = []
        outbound_map: dict[str, list[str]] = {}

        for raw in raw_pages:
            page_id = raw["id"]
            blocks = await self._fetch_blocks(page_id)

            content = self._extract_text_from_blocks(blocks)
            outbound = self._extract_links_from_blocks(blocks)
            # Only keep links to pages we know about
            outbound = [lid for lid in outbound if lid in all_page_ids]
            outbound_map[page_id] = outbound

            # Parent extraction
            parent_info = raw.get("parent", {})
            parent_id = None
            if parent_info.get("type") == "page_id":
                parent_id = parent_info["page_id"]
            elif parent_info.get("type") == "database_id":
                parent_id = parent_info["database_id"]

            page_nodes.append(
                PageNode(
                    id=page_id,
                    title=self._extract_title(raw),
                    content=content,
                    last_edited_time=self._parse_time(
                        raw.get("last_edited_time")
                    ),
                    created_time=self._parse_time(raw.get("created_time")),
                    backlinks=[],
                    outbound_links=outbound,
                    parent_id=parent_id,
                    edit_history=[],
                )
            )

        # Compute backlinks from outbound links
        backlink_map: dict[str, list[str]] = {p.id: [] for p in page_nodes}
        for node in page_nodes:
            for target_id in node.outbound_links:
                if target_id in backlink_map:
                    backlink_map[target_id].append(node.id)

        for node in page_nodes:
            node.backlinks = backlink_map.get(node.id, [])

        snapshot = WorkspaceSnapshot(
            workspace_id="live",
            snapshot_time=datetime.now(timezone.utc),
            pages=page_nodes,
        )

        if self._client:
            await self._client.aclose()
            self._client = None

        return snapshot


def build_graph(snapshot: WorkspaceSnapshot) -> nx.DiGraph:
    """Build a NetworkX directed graph from a WorkspaceSnapshot."""
    g = nx.DiGraph()

    for page in snapshot.pages:
        g.add_node(page.id, title=page.title)

    for page in snapshot.pages:
        for target_id in page.outbound_links:
            g.add_edge(page.id, target_id)
        # Backlinks represent edges from other pages to this page
        for source_id in page.backlinks:
            g.add_edge(source_id, page.id)

    return g
