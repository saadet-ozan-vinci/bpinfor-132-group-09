"""The persistent memory tools, served over stateless MCP HTTP.

Run from the repository root with `python -m app.mcp_server`. The server uses
the MCP specification revision 2026-07-28 and listens on port 8000 by default.
"""

from __future__ import annotations

import asyncio
import os

from mcp.server import MCPServer  # MCP specification revision 2026-07-28.

from .memory import MemoryStore

app = MCPServer("memory-desk")


def load_store() -> MemoryStore:
    """Load current disk state for each request so instances share updates."""
    return MemoryStore.load()


@app.tool()
def remember(subject: str, kind: str, fact: str) -> str:
    """Store a durable fact about one subject and return its opaque handle.

    Do not use for temporary details or information the subject asked to
    forget. Facts expire 90 days after creation.
    """
    return load_store().write(subject, kind, fact)


@app.tool()
def recall(subject: str, query: str, k: int = 3) -> list[str]:
    """Find up to k matching personal facts for this subject only.

    An empty list means no matching fact was found. This searches remembered
    personal facts, not the commune information corpus.
    """
    return load_store().search_memory(subject, query, k)


@app.tool()
def forget(handle: str) -> bool:
    """Delete the remembered fact named by handle.

    Returns false if the handle is unknown. This cannot remove information
    already copied into an active conversation.
    """
    return load_store().forget(handle)


@app.tool()
def open_case(subject: str) -> str:
    """Open a case and return its opaque handle for later tool calls."""
    return load_store().open_case(subject)


@app.tool()
def case_subject(handle: str) -> str:
    """Resolve a case handle to its subject or report an unknown handle."""
    subject = load_store().subject_of(handle)
    if subject is None:
        raise ValueError(f"No case exists for handle {handle!r}")
    return subject


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print("MCP revision 2026-07-28, streamable HTTP, stateless")
    print(f"http://127.0.0.1:{port}/mcp")
    # This revision has no session handshake or Mcp-Session-Id. Do not rely on
    # the SDK default, which may serve the earlier session-based behavior.
    asyncio.run(app.run_streamable_http_async(
        host="127.0.0.1", port=port, stateless_http=True))
