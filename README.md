# goodlinks-mcp

A read-only MCP server for [GoodLinks](https://goodlinks.app/), the Mac read-it-later app. Gives Claude access to your saved articles, tags, and highlights for research and reference.

Requires **GoodLinks 3.2+** (for the built-in API) and **macOS**.

## Tools

All tools are read-only and talk to the GoodLinks local API on `localhost:9428`.

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

## Install — Claude Desktop (recommended)

This repo builds to a single `.mcpb` bundle that Claude Desktop installs in one click. No JSON editing.

1. **Enable the GoodLinks API.** GoodLinks → Settings → API. Toggle it on and copy the token.
2. **Grab a `.mcpb`**:
   - Download the latest from [Releases](https://github.com/glennsheff/goodlinks-mcp/releases), **or**
   - Build it yourself: `npx @anthropic-ai/mcpb pack` (produces `goodlinks-mcp-0.1.0.mcpb`).
3. **Install.** Double-click the `.mcpb`, or drag it onto Claude Desktop. The app prompts for the **GoodLinks API Token** in a proper form field (the token is stored in the OS keychain, not a plaintext config file).
4. **Done.** The `goodlinks_*` tools show up next time you start a chat.

To update: drop a newer `.mcpb` onto Claude Desktop. To remove: Settings → Extensions → uninstall.

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

## Notes

- GoodLinks must be running for tools to work. You'll get a friendly error if it isn't.
- If you rotate the API token, reinstall the `.mcpb` (or restart the host app after updating the env) so the new value is picked up.
- Search results default to 20 per call. Use `offset` to paginate; check `hasMore` to know when to stop.
- For long articles, pass `max_chars` to `goodlinks_get_link_content` to cap the response.

## Roadmap

- **v2**: optional write tool to save new links (`POST /links`). The API treats this as upsert-by-URL, so it doubles as "update an existing link."
