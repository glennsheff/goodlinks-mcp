# goodlinks-mcp

[![Latest release](https://img.shields.io/github/v/release/glennsheff/goodlinks-mcp?sort=semver)](https://github.com/glennsheff/goodlinks-mcp/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-macOS-lightgrey)](https://goodlinks.app)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)

An MCP server for [GoodLinks](https://goodlinks.app/), the Mac read-it-later app. Gives Claude access to your saved articles, tags, and highlights for research and reference — and lets it save new links back to your library.

Requires **GoodLinks 3.2+** (for the built-in API) and **macOS**.

## Tools

All tools talk to the GoodLinks local API on `localhost:9428`. Everything except `goodlinks_save_link` is read-only.

| Tool | Purpose |
| --- | --- |
| `goodlinks_search_links` | Full-featured search with filters (tags, starred, read, word count, date ranges, sort). The workhorse. |
| `goodlinks_get_list` | Fetch a built-in list: `unread`, `read`, `starred`, `untagged`, `highlighted`, `all`. |
| `goodlinks_get_link` | Fetch a single link's metadata by id or URL. |
| `goodlinks_get_current_link` | Fetch the link currently selected in GoodLinks. |
| `goodlinks_get_link_content` | Fetch the article body as markdown, plaintext, or html. Supports truncation. |
| `goodlinks_list_tags` | List every tag in your library. |
| `goodlinks_search_highlights` | Search saved highlights across the library. |
| `goodlinks_export_link_highlights` | Export one link's highlights as Markdown via your configured template. |
| `goodlinks_save_link` | Save a new link — or update an existing one. The API upserts by URL, so calling this with a URL that's already in your library updates that link instead of creating a duplicate. |

## Install — Claude Desktop (recommended)

This repo ships as a single `.mcpb` bundle that Claude Desktop installs in one click. No JSON editing.

1. **Enable the GoodLinks API.** GoodLinks → Settings → API. Toggle it on and copy the token.
2. **Download the latest `.mcpb`** from [Releases](https://github.com/glennsheff/goodlinks-mcp/releases) (or [build your own](#building-from-source)).
3. **Install.** Double-click the `.mcpb` or drag it onto Claude Desktop. The install dialog prompts for your **GoodLinks API Token** — it's stored in the macOS keychain, not a plaintext config file.
4. **Done.** The `goodlinks_*` tools appear in your next chat.

- **Update**: drop a newer `.mcpb` onto Claude Desktop.
- **Rotate token**: Claude Desktop → Settings → Extensions → GoodLinks → Configure. No reinstall needed.
- **Remove**: Settings → Extensions → GoodLinks → Uninstall.

## Install — Claude Code

```sh
claude mcp add goodlinks \
  --scope user \
  -e GOODLINKS_API_TOKEN=your-token \
  -- uv --directory /absolute/path/to/goodlinks-mcp run goodlinks-mcp
```

Use `--scope project` instead if you want the config checked into a repo as `.mcp.json`.

## Environment variables

Set by the `.mcpb` installer from the user-config form. Only needed directly if you're running from source.

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `GOODLINKS_API_TOKEN` | yes | — | Bearer token from GoodLinks → Settings → API. |
| `GOODLINKS_API_BASE_URL` | no | `http://localhost:9428/api/v1` | Override only if GoodLinks is on a non-default port. |

## Running from source

```sh
uv sync
GOODLINKS_API_TOKEN=your-token uv run goodlinks-mcp
```

The server speaks MCP over stdio and will sit waiting for a client.

## Building from source

Requires Node (for `npx`) and the repo cloned locally.

```sh
npx @anthropic-ai/mcpb pack
```

This produces a `.mcpb` file in the repo root (named after the parent folder). Install it the same way as a release download.

## Notes

- GoodLinks must be running for tools to work. You'll get a friendly error if it isn't.
- Search results default to 20 per call. Use `offset` to paginate; check `hasMore` to know when to stop.
- For long articles, pass `max_chars` to `goodlinks_get_link_content` to cap the response.
- The app icon in the install dialog is GoodLinks' own icon, pulled from `/Applications/GoodLinks.app`.

## Roadmap

- **v0.3**: edit existing links (`PATCH /links/{id}` — add/remove tags, toggle starred/read, edit title/summary), edit highlight notes (`PATCH /highlights/{id}`), and maybe a guarded delete tool (`DELETE /links`).
