"""Block 2, first half: call the memory tools over MCP.

    python mcp_server.py &          # in one terminal
    PORT=8001 python mcp_server.py & # and a second instance
    python 01_mcp_client.py

Three things happen here and the third is the one to watch.
"""

from __future__ import annotations

import asyncio

# MCP specification revision 2026-07-28.
from mcp.client import Client

SUBJECT = "A. Muller"


def text_of(result) -> str:
    content = getattr(result, "content", result)
    if isinstance(content, list) and content:
        return getattr(content[0], "text", str(content[0]))
    return str(content)


async def call(port: int, tool: str, **args):
    async with Client(f"http://127.0.0.1:{port}/mcp") as client:
        return await client.call_tool(tool, args)


async def main() -> int:
    """Three steps, and the third has a warning attached.

    1. Connect to :8000 and print the tool catalog. Seeing it arrive over
       HTTP is what makes the boundary real: these tools are not in this
       process.

    2. Call open_case and then remember on :8000. Watch
       artifacts/memory_store.json change while it runs.

    3. Redeem the SAME handle on :8001, the second instance, and recall from
       it.

    The warning: step 3 on its own does not prove the protocol is stateless.
    It would work under the old session-based protocol too, because each
    call opens its own connection and the state is on disk. It shows that a
    file is a file. 02_stateless.py is the demonstration that actually
    distinguishes the two, and it is the next thing you run.
    """
    async with Client("http://127.0.0.1:8000/mcp") as client:
        catalog = await client.list_tools()
    tools = getattr(catalog, "tools", catalog)
    print("tools discovered on :8000:")
    for tool in tools:
        print(f"  {tool.name}: {tool.description}")

    handle = text_of(await call(8000, "open_case", subject=SUBJECT))
    print(f"\ncase opened on :8000: {handle}")
    fact_handle = text_of(await call(
        8000, "remember", subject=SUBJECT, kind="maintenance",
        fact="reported a broken heater",
    ))
    print(f"fact remembered on :8000: {fact_handle}")

    resolved_subject = text_of(await call(
        8001, "case_subject", handle=handle,
    ))
    facts = await call(
        8001, "recall", subject=resolved_subject,
        query="broken heater", k=3,
    )
    print(f"case resolved on :8001: {resolved_subject}")
    print(f"recall from :8001: {text_of(facts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
