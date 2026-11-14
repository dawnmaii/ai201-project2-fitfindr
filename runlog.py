"""
Run log for FitFindr: one JSON object per line in logs/runs.jsonl.

Why a file and not print(): a printed line disappears when the terminal closes,
and nothing can count or filter it afterwards. A JSON line with named fields can
be read back, counted, and checked against a criterion.

Why one function (run_logged) for both serve.py and app.py: the record has to
look the same whether a run came from the web or the command line, and two
copies of the timing code would drift apart.
"""

import json
import os
import sys
import threading
import time
from datetime import datetime, timezone

import config

LOG_PATH = config.ROOT / "logs" / "runs.jsonl"

# Prices are per million tokens, set from the pricing page for the model you
# run. They default to 0, which means "log the tokens, don't estimate a dollar
# figure". Setting them in your .env turns on est_cost_usd.
PRICE_PROMPT_PER_M = float(os.getenv("AI201_PRICE_PROMPT_PER_M", "0"))
PRICE_OUTPUT_PER_M = float(os.getenv("AI201_PRICE_OUTPUT_PER_M", "0"))

# serve.py already runs one request at a time, so this lock is not strictly
# needed there. It costs nothing and protects the file if two writers ever
# overlap, for example if someone later runs the CLI alongside the server.
_write_lock = threading.Lock()


def now_iso() -> str:
    """UTC timestamp to the millisecond. UTC so a log from a host in another zone still sorts correctly."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def estimate_cost(tokens: dict):
    """Dollar estimate from token counts. Returns None when prices aren't set, so a missing price isn't logged as a free run."""
    if not PRICE_PROMPT_PER_M and not PRICE_OUTPUT_PER_M:
        return None
    return round(
        tokens["prompt"] / 1_000_000 * PRICE_PROMPT_PER_M
        + tokens["output"] / 1_000_000 * PRICE_OUTPUT_PER_M,
        8,
    )


def record_run(record: dict) -> None:
    """
    Append one record to the log.

    Logging must never break a request, so a write error is caught. It is
    printed to stderr rather than swallowed silently, because a log that fails
    without saying so is the "absence" failure the unit warns about.
    """
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False, default=str)
        with _write_lock, LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as exc:  # noqa: BLE001
        print(f"  [runlog] could not write a record: {exc}", file=sys.stderr, flush=True)


def record_rejected(query, source: str, reason: str) -> None:
    """
    Log a request that was refused before the agent ran (empty, too long).

    A rejected input is still a request someone made, so it gets a record too.
    Without one, a flood of bad requests would be invisible in the log.
    """
    # Same fields as a normal run, so one reader can process every line. Nothing
    # ran, so timing and token counts are zero rather than missing.
    record_run({
        "ts": now_iso(),
        "source": source,
        "query": query,
        "status": "invalid",
        "error": reason,
        "selected": None,
        "output": None,
        "stage_ms": {},
        "duration_ms": 0.0,
        "tokens": {"prompt": 0, "output": 0, "total": 0},
        "est_cost_usd": None,
    })


def run_logged(query, wardrobe, source: str):
    """
    Run the agent once and write exactly one record, whatever happens.

    Returns (session, failure). Exactly one of the two is set:
      - session: the finished session dict from run_agent(). Its own `error`
        field may still be set, for example when the search service was down.
      - failure: a string, when run_agent() raised. Nothing else was returned.

    Why the write is in `finally`: a run that crashes is the run most worth
    finding in the log. Putting the write after the try would skip it.
    """
    from agent import run_agent
    from generate import token_counts

    started = now_iso()
    t0 = time.perf_counter()
    before = token_counts()  # the counter is cumulative, so we take a difference per run

    session = None
    failure = None
    try:
        session = run_agent(query, wardrobe)
    except Exception as exc:  # noqa: BLE001 — the caller decides how to report it
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        duration_ms = round((time.perf_counter() - t0) * 1000, 1)
        after = token_counts()
        # Per-run tokens are the difference between the counter before and after.
        # This is only correct because serve.py runs one request at a time and
        # the CLI runs one query at a time. Two overlapping runs would share a
        # counter and each would log the other's tokens.
        tokens = {
            "prompt": after["prompt"] - before["prompt"],
            "output": after["output"] - before["output"],
            "total": after["total"] - before["total"],
        }

        # session is None only when run_agent raised. The error text comes from
        # `failure`; the other fields are empty because the run never produced them.
        if session is None:
            status = "error"
            error = failure or "run was interrupted before it finished"
            output = None
            selected = None
            stage_ms = {}
        else:
            # The agent sets session["status"] to "ok", "no_match", or "error".
            status = session.get("status", "ok")
            error = session.get("error")
            output = session.get("fit_card") or session.get("error")
            selected = (session.get("selected_item") or {}).get("title")
            stage_ms = session.get("stage_ms", {})

        # Write the record for this run. The field names here are the ones the
        # module docstring lists, so a reader can rely on them for every line.
        record_run({
            "ts": started,
            "source": source,
            "query": query,
            "status": status,
            "error": error,
            "selected": selected,
            "output": output,
            "stage_ms": stage_ms,
            "duration_ms": duration_ms,
            "tokens": tokens,
            "est_cost_usd": estimate_cost(tokens),
        })

    return session, failure
