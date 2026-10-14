"""
Your MCP server. 

    python mcp_server.py        starts the server (it will just sit there — that's right)
    python mcp_client.py        asks the server what it offers

"""

from mcp.server.fastmcp import FastMCP

from tools import search_listings as _search_listings_impl  # noqa: F401 — you'll use this below

# log_level="WARNING" keeps the server from printing an INFO line for every
# request. Without it your terminal fills with "Processing request of type
# CallToolRequest" and the output you actually care about scrolls away.
mcp = FastMCP("fitfindr", log_level="WARNING")


@mcp.tool() # decorator FastMCP
def search_listings(
    description: str,                 
    size: str | None = None,            
    max_price: float | None = None,     
) -> list[dict]:
    """
    This tool searches listings for clothing items by description/size/price and returns matches;
    if nothing matches, an empty list is returned instead. Description is mandatory, max price
    and size are optional.
    """
    return _search_listings_impl(description, size, max_price)

# Two notes on the block above.
#
# The registered name is the *function* name — so the block above registers
# "search_listings", which is exactly what call_tool("search_listings", ...)
# asks for. That is also why the import at the top of this file brings the real
# implementation in under an alias: without it, the registered function and the
# one it calls would be the same name, and the tool would call itself.
#
# FastMCP builds the input schema from your type hints, which is why the hints
# are not optional here. `description: str` becomes a required string;
# `max_price: float | None = None` becomes an optional number. Getting these
# wrong is the most common reason a call is rejected.


if __name__ == "__main__":
    mcp.run()
