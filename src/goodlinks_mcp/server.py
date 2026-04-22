"""Read-only MCP server for GoodLinks."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from goodlinks_mcp.client import GoodLinksClient, GoodLinksError


mcp = FastMCP("goodlinks")

# Lazily constructed so that missing env vars surface as a friendly error on
# the first tool call rather than crashing at server startup.
_client: GoodLinksClient | None = None


def _get_client() -> GoodLinksClient:
    global _client
    if _client is None:
        _client = GoodLinksClient()
    return _client


def _truncate(text: str, max_chars: int | None) -> dict[str, Any]:
    """Return content plus a truncation flag so the model knows when to page."""
    if max_chars is None or len(text) <= max_chars:
        return {"content": text, "truncated": False, "length": len(text)}
    return {
        "content": text[:max_chars],
        "truncated": True,
        "length": len(text),
        "returned_chars": max_chars,
    }


# --- Tools ---------------------------------------------------------------


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "openWorldHint": False,
        "title": "Search GoodLinks articles",
    }
)
async def goodlinks_search_links(
    search: Annotated[
        str | None,
        Field(
            default=None,
            description="Free-text search across title, summary, content, URL, and author.",
        ),
    ] = None,
    tags: Annotated[
        list[str] | None,
        Field(
            default=None,
            description="Filter by one or more tags. Only links with at least one of these tags are returned.",
        ),
    ] = None,
    starred: Annotated[
        bool | None,
        Field(default=None, description="If set, filter by starred state."),
    ] = None,
    read: Annotated[
        bool | None,
        Field(default=None, description="If set, filter by read state."),
    ] = None,
    tagged: Annotated[
        bool | None,
        Field(default=None, description="If set, filter to only tagged or only untagged links."),
    ] = None,
    highlighted: Annotated[
        bool | None,
        Field(default=None, description="If set, filter to only links with or without highlights."),
    ] = None,
    word_count_min: Annotated[
        int | None,
        Field(default=None, ge=0, description="Minimum article word count."),
    ] = None,
    word_count_max: Annotated[
        int | None,
        Field(default=None, ge=0, description="Maximum article word count."),
    ] = None,
    added_after: Annotated[
        str | None,
        Field(
            default=None,
            description="ISO-8601 UTC timestamp. Only links added after this time.",
        ),
    ] = None,
    added_before: Annotated[
        str | None,
        Field(
            default=None,
            description="ISO-8601 UTC timestamp. Only links added before this time.",
        ),
    ] = None,
    read_after: Annotated[
        str | None,
        Field(default=None, description="ISO-8601 UTC timestamp. Only links read after this time."),
    ] = None,
    read_before: Annotated[
        str | None,
        Field(default=None, description="ISO-8601 UTC timestamp. Only links read before this time."),
    ] = None,
    sort: Annotated[
        Literal[
            "newestSaved",
            "oldestSaved",
            "newestRead",
            "oldestRead",
            "shortest",
            "longest",
            "titleA",
            "titleZ",
        ]
        | None,
        Field(default=None, description="Sort order. Defaults to newestSaved."),
    ] = None,
    limit: Annotated[
        int,
        Field(default=20, ge=1, le=1000, description="Max results to return (1-1000)."),
    ] = 20,
    offset: Annotated[
        int,
        Field(default=0, ge=0, description="Number of results to skip for pagination."),
    ] = 0,
) -> dict[str, Any]:
    """Search the GoodLinks library with rich filters.

    Returns an object with `data` (list of link metadata) and `hasMore`
    (whether more results are available beyond this page). Each link includes
    id, url, title, summary, author, tags, wordCount, starred, highlighted,
    addedAt, modifiedAt, readAt. Use `goodlinks_get_link_content` on a
    returned id to fetch the full article text.
    """
    params: dict[str, Any] = {
        "search": search,
        "starred": _bool_param(starred),
        "read": _bool_param(read),
        "tagged": _bool_param(tagged),
        "highlighted": _bool_param(highlighted),
        "wordCountMin": word_count_min,
        "wordCountMax": word_count_max,
        "addedAfter": added_after,
        "addedBefore": added_before,
        "readAfter": read_after,
        "readBefore": read_before,
        "sort": sort,
        "limit": limit,
        "offset": offset,
    }
    if tags:
        # httpx serialises list values as repeated query params, which matches
        # the GoodLinks "tag can be specified multiple times" convention.
        params["tag"] = tags
    try:
        return await _get_client().search_links(params)
    except GoodLinksError as exc:
        raise RuntimeError(str(exc)) from exc


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "openWorldHint": False,
        "title": "Get links from a built-in list",
    }
)
async def goodlinks_get_list(
    list_name: Annotated[
        Literal["unread", "read", "starred", "untagged", "highlighted", "all"],
        Field(description="Which built-in list to read from."),
    ],
    search: Annotated[
        str | None,
        Field(default=None, description="Optional free-text filter within the list."),
    ] = None,
    tags: Annotated[
        list[str] | None,
        Field(
            default=None,
            description="Optional tag filter. Ignored when list_name is 'untagged'.",
        ),
    ] = None,
    include_read: Annotated[
        bool | None,
        Field(
            default=None,
            description="For starred/untagged/highlighted lists, include read links. Defaults to false.",
        ),
    ] = None,
    limit: Annotated[
        int,
        Field(default=20, ge=1, le=1000, description="Max results (1-1000)."),
    ] = 20,
    offset: Annotated[
        int,
        Field(default=0, ge=0, description="Results to skip for pagination."),
    ] = 0,
) -> dict[str, Any]:
    """Get links from a GoodLinks built-in list (unread, starred, etc.).

    Links are sorted newest-saved-first. Returns the same shape as
    `goodlinks_search_links`.
    """
    params: dict[str, Any] = {
        "search": search,
        "includeRead": _bool_param(include_read),
        "limit": limit,
        "offset": offset,
    }
    if tags:
        params["tag"] = tags
    try:
        return await _get_client().get_list(list_name, params)
    except GoodLinksError as exc:
        raise RuntimeError(str(exc)) from exc


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "openWorldHint": False,
        "title": "Get a single link by ID or URL",
    }
)
async def goodlinks_get_link(
    link_id: Annotated[
        str | None,
        Field(default=None, description="The GoodLinks link id."),
    ] = None,
    url: Annotated[
        str | None,
        Field(
            default=None,
            description="The full URL of the link. Use this when you don't know the id.",
        ),
    ] = None,
) -> dict[str, Any]:
    """Fetch a single link's metadata by id or URL.

    Exactly one of `link_id` or `url` must be provided.
    """
    if bool(link_id) == bool(url):
        raise RuntimeError("Provide exactly one of `link_id` or `url`.")
    try:
        if link_id:
            return await _get_client().get_link(link_id)
        return await _get_client().get_link_by_url(url)  # type: ignore[arg-type]
    except GoodLinksError as exc:
        raise RuntimeError(str(exc)) from exc


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "openWorldHint": False,
        "title": "Get the currently selected link in GoodLinks",
    }
)
async def goodlinks_get_current_link() -> dict[str, Any]:
    """Return the link currently selected in the GoodLinks app, if any."""
    try:
        return await _get_client().get_current_link()
    except GoodLinksError as exc:
        raise RuntimeError(str(exc)) from exc


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "openWorldHint": False,
        "title": "Get an article's full content",
    }
)
async def goodlinks_get_link_content(
    link_id: Annotated[str, Field(description="The GoodLinks link id.")],
    format: Annotated[
        Literal["markdown", "plaintext", "html"],
        Field(default="markdown", description="Content format. Defaults to markdown."),
    ] = "markdown",
    max_chars: Annotated[
        int | None,
        Field(
            default=None,
            ge=1,
            description="If set, truncate the returned content to this many characters. Useful for long articles.",
        ),
    ] = None,
) -> dict[str, Any]:
    """Fetch the full article body for a saved link.

    Returns `{content, truncated, length, returned_chars?}`. `length` is the
    full character count of the article; `truncated` indicates whether the
    returned `content` was cut short by `max_chars`.
    """
    try:
        text = await _get_client().get_link_content(link_id, format)
    except GoodLinksError as exc:
        raise RuntimeError(str(exc)) from exc
    return _truncate(text, max_chars)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "openWorldHint": False,
        "title": "List all tags",
    }
)
async def goodlinks_list_tags() -> list[str]:
    """List every tag that has at least one link, including hierarchical paths."""
    try:
        return await _get_client().get_tags()
    except GoodLinksError as exc:
        raise RuntimeError(str(exc)) from exc


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "openWorldHint": False,
        "title": "Search highlights",
    }
)
async def goodlinks_search_highlights(
    q: Annotated[
        str | None,
        Field(default=None, description="Free-text search across highlight content and notes."),
    ] = None,
    link_id: Annotated[
        str | None,
        Field(default=None, description="If set, only return highlights from this link."),
    ] = None,
    content: Annotated[
        str | None,
        Field(default=None, description="Substring match on highlight content."),
    ] = None,
    note: Annotated[
        str | None,
        Field(default=None, description="Substring match on highlight note."),
    ] = None,
    created_after: Annotated[
        str | None,
        Field(default=None, description="ISO-8601 UTC timestamp."),
    ] = None,
    created_before: Annotated[
        str | None,
        Field(default=None, description="ISO-8601 UTC timestamp."),
    ] = None,
    sort: Annotated[
        Literal["newest", "oldest", "linkID", "content", "note"] | None,
        Field(default=None, description="Sort order. Defaults to newest."),
    ] = None,
    limit: Annotated[
        int,
        Field(default=20, ge=1, le=1000, description="Max results (1-1000)."),
    ] = 20,
    offset: Annotated[
        int,
        Field(default=0, ge=0, description="Results to skip for pagination."),
    ] = 0,
) -> dict[str, Any]:
    """Search saved highlights across the library.

    Each result includes id, linkID, content, markdownContent, note, and
    createdAt. Use `linkID` to trace a highlight back to its source article
    via `goodlinks_get_link`.
    """
    params: dict[str, Any] = {
        "q": q,
        "linkID": link_id,
        "content": content,
        "note": note,
        "createdAfter": created_after,
        "createdBefore": created_before,
        "sort": sort,
        "limit": limit,
        "offset": offset,
    }
    try:
        return await _get_client().search_highlights(params)
    except GoodLinksError as exc:
        raise RuntimeError(str(exc)) from exc


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "openWorldHint": False,
        "title": "Export a link's highlights",
    }
)
async def goodlinks_export_link_highlights(
    link_id: Annotated[str, Field(description="The GoodLinks link id.")],
) -> str:
    """Export all highlights for a single link as Markdown.

    Uses the export template configured in GoodLinks settings.
    """
    try:
        return await _get_client().export_link_highlights(link_id)
    except GoodLinksError as exc:
        raise RuntimeError(str(exc)) from exc


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
        "title": "Save a link to GoodLinks",
    }
)
async def goodlinks_save_link(
    url: Annotated[
        str,
        Field(
            description="HTTP/HTTPS URL to save. Max 2000 chars.",
            max_length=2000,
        ),
    ],
    title: Annotated[
        str | None,
        Field(
            default=None,
            max_length=200,
            description="Optional title. Max 200 chars. Newlines are converted to spaces.",
        ),
    ] = None,
    summary: Annotated[
        str | None,
        Field(
            default=None,
            max_length=400,
            description="Optional summary. Max 400 chars. Newlines are converted to spaces.",
        ),
    ] = None,
    tags: Annotated[
        list[str] | None,
        Field(
            default=None,
            description="Optional tags. Each tag max 100 chars. Passing an empty list clears tags.",
        ),
    ] = None,
    starred: Annotated[
        bool | None,
        Field(default=None, description="Mark as starred. Defaults to false for new links."),
    ] = None,
    read: Annotated[
        bool | None,
        Field(default=None, description="Mark as read. Defaults to false for new links."),
    ] = None,
    added_at: Annotated[
        str | None,
        Field(
            default=None,
            description="ISO-8601 timestamp for when the link was added. Defaults to now; future times are clamped.",
        ),
    ] = None,
) -> dict[str, Any]:
    """Save a link to GoodLinks, or update an existing link if one with the same URL already exists.

    This is upsert-by-URL: posting the same URL twice updates the existing
    link rather than creating a duplicate. Returns the complete link object
    including `id`, `addedAt`, `modifiedAt`, and all other metadata.
    """
    payload: dict[str, Any] = {"url": url}
    if title is not None:
        payload["title"] = title
    if summary is not None:
        payload["summary"] = summary
    if tags is not None:
        payload["tags"] = tags
    if starred is not None:
        payload["starred"] = starred
    if read is not None:
        payload["read"] = read
    if added_at is not None:
        payload["addedAt"] = added_at
    try:
        return await _get_client().save_link(payload)
    except GoodLinksError as exc:
        raise RuntimeError(str(exc)) from exc


# --- Helpers -------------------------------------------------------------


def _bool_param(value: bool | None) -> str | None:
    """GoodLinks expects 'true'/'false' strings in query params."""
    if value is None:
        return None
    return "true" if value else "false"


def main() -> None:
    """Entry point for the `goodlinks-mcp` script."""
    mcp.run()


if __name__ == "__main__":
    main()
