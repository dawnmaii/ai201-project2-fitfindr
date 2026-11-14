"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. 

"""

import config
import re
import time
import trace
from tools import search_listings, suggest_outfit, create_fit_card
from generate import ModelUnavailable
# What's new (unit 9): MCPError is the one error the search step can raise.
# It is imported so run_agent can catch it by name, not with a bare except.
from mcp_client import call_tool, MCPError


# ── query parsing (unit 9) ────────────────────────────────────────────────────
# What's new: the parser checks what it's given instead of guessing. A keyword
# the user writes must be followed by a value of the right kind, or the query is
# refused with a message saying what's missing. Before, "size" with nothing after
# it was silently ignored, and "$30.50" was read as $30.

# A price: "$30", "$30.50", "under $30", "below $30", "price $30", "price 30".
# The number takes up to two decimal places. Without the $ or a price word, a
# bare number is not a price, so "2003 Tour Bootleg" never becomes a price cap.
PRICE_RE = re.compile(
    r"(?:\b(?:under|below|less than|price)\s+\$?|\$\s*)(\d+(?:\.\d{1,2})?)\b",
    re.IGNORECASE,
)

# A size: "size M", "size XS/S", "size S\XS", "size 8", "size W30". The value is
# letters and/or digits, optionally joined by "/" or "\" (both mean "or").
# Letters are typical for tops; numbers are needed for shoes ("US 8") and waist
# sizes ("W30"), so a value of letters only would refuse real listings.
# One size part, tried in this order (the first alternative that fits wins):
#   "US 8", "US 8.5"        letters, a space, then a number (shoe sizes)
#   "W30", "W30 L30"        a letter-and-number waist/length pair
#   "8", "8.5"              a plain number
#   "M", "XS"               letters only
# Each alternative is needed: without the spaced ones, "US 8" was cut to "US" and
# the "8" leaked into the search text.
_SIZE_PART = (
    r"(?:[A-Za-z]+\s+\d+(?:\.\d+)?"
    r"|[A-Za-z]+\d+(?:\.\d+)?(?:\s+[A-Za-z]+\d+(?:\.\d+)?)?"
    r"|\d+(?:\.\d+)?"
    r"|[A-Za-z]+)"
)
SIZE_RE = re.compile(
    r"\bsize\s+(" + _SIZE_PART + r"(?:\s*[/\\]\s*" + _SIZE_PART + r")*)",
    re.IGNORECASE,
)

# Words that can follow "size" in ordinary English ("size of the tee") but are
# not sizes. Without this list, "size of" would be searched as a size.
NOT_A_SIZE = {"of", "the", "a", "an", "and", "or", "with", "in", "is"}


def parse_query(query: str) -> dict:
    """
    Split a query into description, size and max_price.

    Raises ValueError with a message the user can act on when the query is
    malformed. The caller turns that into a session error, and nothing is
    searched.
    """
    # The first "size" phrase whose value is a real size. Skipping filler means
    # "size of the tee, size M" uses "M", not "of".
    size_match = next(
        (m for m in SIZE_RE.finditer(query) if m.group(1).lower() not in NOT_A_SIZE),
        None,
    )
    size = size_match.group(1).strip() if size_match else None

    # Every "size" word must be followed by a real size, not only the first one.
    # Checking each occurrence means "size of the tee size M" is refused: the
    # first "size" has nothing real after it, so it can't slip into the description.
    for word in re.finditer(r"\bsize\b", query, re.IGNORECASE):
        found = SIZE_RE.match(query, word.start())
        if found is None or found.group(1).lower() in NOT_A_SIZE:
            raise ValueError("'size' needs a size after it, e.g. 'size M', 'size XS/S' or 'size 8'.")

    price_match = PRICE_RE.search(query)
    max_price = float(price_match.group(1)) if price_match else None

    # The same rule for "price": each occurrence needs a number after it.
    for word in re.finditer(r"\bprice\b", query, re.IGNORECASE):
        if PRICE_RE.match(query, word.start()) is None:
            raise ValueError("'price' needs a number after it, e.g. 'price $30' or 'under $30'.")

    # The description is the query with the size phrase and the price phrase cut
    # out. Cutting by position removes exactly the matched text and nothing else.
    # Only one of each is removed; a second one stays, which is the honest result.
    cuts = sorted(m.span() for m in (size_match, price_match) if m is not None)
    pieces, last = [], 0
    for start, end in cuts:
        pieces.append(query[last:start])
        last = end
    pieces.append(query[last:])
    description = re.sub(r"\s+", " ", " ".join(pieces)).strip()

    # Nothing left to search for (e.g. the query was only "$30"). Refuse here, so
    # the search never runs with an empty description and matches everything.
    if not description:
        raise ValueError("Tell me what to look for, e.g. 'vintage graphic tee under $30'.")

    return {"description": description, "size": size, "max_price": max_price}



# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
        # What's new (unit 9): how the run ended. The run log reads this, so a
        # refused search and a broken service are recorded as different things.
        #   "ok"       the full pipeline ran
        #   "no_match" the search ran and found nothing (a normal answer, not a fault)
        #   "invalid"  the query was malformed; nothing was searched
        #   "error"    something failed and the run stopped early
        "status": "ok",
        # What's new (unit 9): seconds spent in each stage, in milliseconds.
        # Filled in as each stage finishes, so a failed run still shows how far it got.
        "stage_ms": {},
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    """
    # 1. Start a session with new_session().
    session = new_session(query, wardrobe)

    # 2. Count the times round the loop
    count = 1
    # call trace.check_iterations(count) on each one before you go again
    trace.check_iterations(count)  # type: ignore[attr-defined]

    # 3. Parse the query into a description, a size, and a max_price.
    # What's new (unit 9): a malformed query ends here, before any search runs.
    # It is marked "invalid", which the run log counts apart from real errors.
    try:
        parsed = parse_query(query)
    except ValueError as exc:
        session["status"] = "invalid"
        session["error"] = str(exc)
        return session
    description = parsed["description"]
    size = parsed["size"]
    max_price = parsed["max_price"]
                        
    session["parsed"] = {"description": description, "size": size, "max_price": max_price}

    # 4. Call search_listings() with what you parsed. Put the results in session["search_results"].
    # What's new (unit 9): the search runs over MCP, which can fail in ways the
    # tool itself never sees: the server won't start, the call times out, or the
    # tool returns an error. Before, any of those raised out of run_agent and
    # the request crashed. Now the failure is written into session["error"] and
    # the run ends cleanly, so the caller gets a readable answer and the log gets
    # a record.
    t0 = time.perf_counter()
    try:
        session["search_results"] = call_tool("search_listings", {"description": description, "size": size, "max_price": max_price})
    except MCPError as exc:
        session["stage_ms"]["search"] = round((time.perf_counter() - t0) * 1000, 1)
        session["status"] = "error"
        session["error"] = f"The listing search failed: {exc}"
        return session
    session["stage_ms"]["search"] = round((time.perf_counter() - t0) * 1000, 1)
    trace.step("search_listings (via MCP)", inputs={"description": description, "size": size, "max_price": max_price}, returned=session["search_results"])

    # If nothing came back:
    if not session["search_results"]:
        # put a message in session["error"] saying what the user could change — "No results" is not that message
        parts = [f"No matches for '{session['parsed']['description']}'"]
        if session['parsed']['max_price'] is not None:
            parts.append(f"under ${session['parsed']['max_price']}")
        if session['parsed']['size'] is not None:
            parts.append(f"in size {session['parsed']['size']}")
        parts.append("— try raising the price, widening the size, or changing the description.")
        session["error"] = " ".join(parts)
        # What's new (unit 9): an empty search is a normal answer, not a fault.
        # It is logged as "no_match" so it can be counted apart from real errors.
        session["status"] = "no_match"
        # return the session
        return session
        # do NOT call suggest_outfit with nothing
    else:
        session["selected_item"] = session["search_results"][0]
        # What's new (unit 9): each model-backed step is timed on its own, so a
        # slow run can be traced to the step that was slow.
        t0 = time.perf_counter()
        try:
            session["outfit_suggestion"] = suggest_outfit(session["selected_item"], session["wardrobe"]) # type: ignore[arg-type]
            session["stage_ms"]["outfit"] = round((time.perf_counter() - t0) * 1000, 1)
            trace.step("suggest_outfit", inputs={"new_item": session["selected_item"], "wardrobe": session["wardrobe"]}, returned=session["outfit_suggestion"])

            t0 = time.perf_counter()
            session["fit_card"] = create_fit_card(session["outfit_suggestion"], session["selected_item"]) # type: ignore[arg-type]
            session["stage_ms"]["fit_card"] = round((time.perf_counter() - t0) * 1000, 1)
            trace.step("create_fit_card", inputs={"outfit": session["outfit_suggestion"], "new_item": session["selected_item"]}, returned=session["fit_card"])

        except ModelUnavailable as exc:
            session["status"] = "error"
            session["error"] =  f"The styling service is temporarily unavailable: ({exc})"
            return session
        except Exception as exc:  # noqa: BLE001
            # What's new (unit 9): anything else from the model step (an empty
            # reply, a malformed response, a safety block) ends the run here with
            # a message. The listing was already found, so the message says so.
            # Before, this raised out of run_agent and the request crashed.
            session["status"] = "error"
            session["error"] = (
                f"The styling step failed ({type(exc).__name__}: {exc}). "
                f"The listing was found; try the query again."
            )
            return session
        return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
