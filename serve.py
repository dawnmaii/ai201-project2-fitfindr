#!/usr/bin/env python3
"""
FitFindr over HTTP. ← UNIT 9

    python serve.py                       run it on your machine
    gunicorn serve:app                    run it the way a host runs it

Everything else in this repo exits after one command. A host has nothing to
keep running, so a command line cannot be deployed. This file is the smallest
thing that can: it starts a web server, waits, and hands each request to the
same `run_agent()` your CLI calls. **No new agent logic lives here.** If your
loop works from `python app.py ask`, it works from here; if it doesn't, fix it
there, not in this file.

Two routes:

    POST /ask       {"query": "vintage graphic tee under $30",
                     "wardrobe": {...}}     ← wardrobe is optional
    GET  /health    is it awake?

`/ask` returns the session dict from `run_agent()` as JSON, unchanged — the
same keys you print from the command line, including `error`. Read
`session["error"]` first, exactly as you do everywhere else.

It runs **one request at a time**, and one route is deliberately slower than a
web server has to be. The reason is worth reading before you deploy: see the
note above `_one_at_a_time` below — it also decides which gunicorn worker you
can use.

Unit 9 addition: every request now writes one record to logs/runs.jsonl, through
`runlog.run_logged()`, including refused input and failed runs. Read that file
for the record format; the fields are described in runlog.py.
"""

import os
import sys
import threading

# config first, and before anything that talks to the model: it loads your .env
# and fixes the Windows console encoding for every module that imports it.
import config  # noqa: F401

from flask import Flask, jsonify, request

from utils.data_loader import get_example_wardrobe
# What's new (unit 9): run_logged runs the agent and writes the log record for
# it, so this route no longer calls run_agent directly. record_rejected logs
# requests refused before the agent starts. MAX_QUERY_CHARS is the input cap.
from runlog import run_logged, record_rejected
from config import MAX_QUERY_CHARS

app = Flask(__name__)


# ── one request at a time ─────────────────────────────────────────────────────
# Here's why this exists.
#
# A web server will happily run two requests at once. Two things in this repo
# assume otherwise:
#
#   • If you moved a tool onto MCP in unit 4, `mcp_client.call_tool` starts
#     `mcp_server.py` as a separate process over stdio, one per call. Two
#     overlapping requests means two extra Python interpreters, and the free
#     tier you're deploying to has 512 MB for all of it. That is the reason
#     that would still be here even if everything else were perfect.
#   • `generate.py`'s pacing window and its call counter are plain module
#     globals — deliberately, because that file is teaching pacing and quota,
#     not locking. Two threads sharing them means the per-minute limiter is
#     counting something that isn't true.
#
# What the lock covers is exactly the agent run: the part that spawns
# processes and calls the model. Reading the request, rejecting a bad one, and
# turning the answer into JSON all happen outside it — so a request with a
# malformed body comes straight back with a 400 instead of queueing behind
# somebody else's agent.
#
# Serialising the runs costs you nothing here — this is one user asking one
# question — and it keeps the deployed behaviour identical to the CLI's. When
# that stops being an acceptable trade, the fix is a real queue, not a bigger
# lock.
#
# The same constraint decides your start command, and this is the part that
# bites in deployment rather than on your machine. `mcp_client.call_tool`
# wraps `asyncio.run()`, and `asyncio.run()` refuses to start when an event
# loop is already running. An async worker always has one running. So under
# `gunicorn -k gevent` (or `-k eventlet`, or `serve:app` wrapped for an ASGI
# server like uvicorn) EVERY MCP call fails with "asyncio.run() cannot be
# called from a running event loop" — not some of them under load, all of
# them, every time, in a place your laptop never showed you.
#
#     gunicorn serve:app              ← right: the DEFAULT sync worker
#     gunicorn -k gevent serve:app    ← breaks every MCP call you make

_one_at_a_time = threading.Lock()


@app.get("/health")
def health():
    """Is the server awake? A host pings something like this to find out."""
    return jsonify({"status": "ok"})


@app.post("/ask")
def ask():
    """
    Run the agent on one query.

    In:   {"query": "...", "wardrobe": {...}}   wardrobe optional — leave it
                                                out and you get the same
                                                example wardrobe the CLI uses.
    Out:  the session dict from run_agent(), as JSON.
    """
    # What's new (unit 9): check the shape of the body before reading any field.
    # Why: the old code called .strip() on whatever "query" held. A number or a
    # list there raised AttributeError, which Flask turned into an HTML 500 page,
    # and nothing was logged because the crash happened before run_logged.
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        record_rejected("", "http", "body is not a JSON object")
        return jsonify({"error": "Send a JSON object with a 'query' field."}), 400

    raw_query = payload.get("query")
    if raw_query is not None and not isinstance(raw_query, str):
        reason = f"'query' must be text, not {type(raw_query).__name__}"
        record_rejected(str(raw_query)[:200], "http", reason)
        return jsonify({"error": reason + "."}), 400

    query = (raw_query or "").strip()
    if not query:
        # What's new (unit 9): a refused request is logged too. Without this, a
        # client sending empty bodies would leave no trace at all.
        record_rejected(query, "http", "empty query")
        # 400 rather than a stack trace: the caller can act on this one.
        return jsonify({"error": "Your query is empty. Send JSON with a non-empty 'query' "
                                 'field, e.g. {"query": "vintage graphic tee under $30"}.'}), 400

    # What's new (unit 9): reject an over-long query before the agent runs. Why:
    # the query becomes the search description and part of the model prompt, so
    # a very long input costs tokens and gives a worse search. Logged as "invalid"
    # so the rejection is countable.
    if len(query) > MAX_QUERY_CHARS:
        reason = f"query is {len(query)} characters; the limit is {MAX_QUERY_CHARS}"
        record_rejected(query[:200], "http", reason)
        return jsonify({"error": f"Query too long: {reason}. Shorten it and try again."}), 400

    wardrobe = payload.get("wardrobe")
    if not isinstance(wardrobe, dict):
        wardrobe = get_example_wardrobe()

    # A queued request should look like a queued request. Without this the
    # second caller just sits there, and "slow" and "waiting its turn" are
    # indistinguishable from the outside — which is how people conclude the
    # deployment is broken when it is behaving exactly as designed.
    #
    # This is NOT the logging you add in the follow-along. It prints nothing
    # on the normal path, carries no timing and counts nothing; it says only
    # that this request had to wait. `locked()` can be a moment out of date,
    # so the note is occasionally missed — which costs nothing, because
    # nothing depends on it.
    if _one_at_a_time.locked():
        print(
            "  [serve] another request is still running. This one is waiting "
            "its turn — serve.py handles one at a time, on purpose.",
            file=sys.stderr,
            flush=True,
        )

    # What's new (unit 9): run_logged writes the record whether the run works or
    # crashes. It returns (session, failure), and failure is set only when the
    # agent itself raised. Errors the agent handles (a failed search, say) come
    # back inside session["error"] as before.
    with _one_at_a_time:
        session, failure = run_logged(query, wardrobe, "http")

    # Outside the lock: building a response is not work the next caller should
    # be waiting on.
    if failure is not None:
        return jsonify({"error": failure}), 500

    return jsonify(session)


if __name__ == "__main__":
    # PORT and 0.0.0.0 are not decoration. A host tells you which port to
    # listen on through PORT, and it reaches your process from outside the
    # container — bind 127.0.0.1 and nothing but the container itself can
    # connect, which looks exactly like a broken app from the browser.
    port = int(os.getenv("PORT", "5000"))

    # Never on by default. Flask's debugger executes code typed into a browser,
    # and a deployed app with it on is a stranger's shell. Set AI201_DEBUG=1 in
    # your own terminal when you want the reloader.
    debug = os.getenv("AI201_DEBUG", "0") == "1"

    print(f"\nFitFindr is listening on http://localhost:{port}")
    print("It runs one request at a time — a second one waits for the first.")
    print("Ask it something (single quotes, as always):\n")
    print(
        f"  curl -X POST http://localhost:{port}/ask \\\n"
        f"    -H 'Content-Type: application/json' \\\n"
        f"    -d '{{\"query\": \"vintage graphic tee under $30\"}}'\n"
    )
    print("Ctrl-C to stop.\n")

    app.run(host="0.0.0.0", port=port, debug=debug)
