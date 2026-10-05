import logging
import sys

from mcp.server.mcpserver import MCPServer

from domain_tools import MySQLStore, notice_detail, search_notices, supplier_summary

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("s0571_rel")

mcp = MCPServer("s0571_rel")
store = MySQLStore()


@mcp.tool()
def search_notices_tool(query: str, limit: int = 5) -> dict:
    """Search grocery recall notices in s0571_rel by product name or notice source. Returns {ok, data, error}."""
    log.info("search_notices query=%r limit=%r", query, limit)
    return search_notices({"query": query, "limit": limit}, store)


@mcp.tool()
def notice_detail_tool(notice_id: int) -> dict:
    """Look up one recall notice by id with its supplier. Returns {ok, data, error}."""
    log.info("notice_detail notice_id=%r", notice_id)
    return notice_detail({"notice_id": notice_id}, store)


@mcp.tool()
def supplier_summary_tool(supplier_id: int) -> dict:
    """Aggregate for one supplier: notice count and total affected units. Returns {ok, data, error}."""
    log.info("supplier_summary supplier_id=%r", supplier_id)
    return supplier_summary({"supplier_id": supplier_id}, store)


if __name__ == "__main__":
    mcp.run(transport="stdio")
