# Acceptance criteria — FitFindr

---

## Capstone criteria (unit 9)

Each criterion gives a target, a test procedure, and the reason for the target. Pass rates are counted over the number of trials stated.

### 1. Forced failures are reported to the user and logged

**Target:** 5 of 5 forced failures (such as an MCP timeout) show the user an error message and write a record with `status: error` to `logs/runs.jsonl`.

**How to test:** Force 5 failures. For each one, check the error message in the CLI output (the text `app.py` prints from `session['error']`), or the `error` field of the JSON response from `serve.py`. Then check that `logs/runs.jsonl` has a new record with `status` set to `error`.

**Why this target:** The application did not handle MCP errors such as timeouts. A user had no way to know when or why a request failed, so every failure needs to be communicated. If all five failures follow the same code path, that is enough evidence the failure path works.

### 2. Rejected inputs are explained to the user and logged

**Target:** 5 of 5 bad inputs, one of each type below, are rejected with the status or HTTP code shown, each writes a record with `status: invalid` to `logs/runs.jsonl`, and each message names the specific problem.

| Input | Response |
| --- | --- |
| `size` with no value | HTTP 200, session `status: invalid` |
| `price` with no value | HTTP 200, session `status: invalid` |
| Empty query | HTTP 400, `error` field |
| Over-long query (over 300 characters) | HTTP 400, `error` field |
| Non-text query (such as a number) | HTTP 400, `error` field |

**How to test:** Submit the 5 inputs through `serve.py`. For each, check the HTTP code, the `status` or `error` field in the response, the message text, and the log record.

**Why this target:** The pipeline can produce several kinds of bad input, and each one needs its own explanation. If the user does not know what was wrong, they may resubmit the same query without changes, which wastes a request and a search attempt.

### 3. Each request produces exactly one complete run log record

**Target:** 20 of 20 requests produce exactly one record in `logs/runs.jsonl`, including failed and rejected requests. Every record has the fields below filled in as described.

- **Always present, never null:** `ts`, `source`, `query`, `status`, `stage_ms`, `duration_ms`, and `tokens`. An empty query is recorded as `""`, which counts as a value. `stage_ms` may be an empty object, and `tokens` is `0` on rejected requests.
- **May be null:**
  - `error` is null when `status` is `ok`. It holds the reason for every `invalid`, `no_match`, and `error` record.
  - `selected` is null unless a listing was found. It stays null for `no_match`, `invalid`, and failures before a listing was found.
  - `output` is null when the request was rejected before the agent ran, such as an empty, over-long, or non-text query.
  - `est_cost_usd` is null when `AI201_PRICE_PROMPT_PER_M` and `AI201_PRICE_OUTPUT_PER_M` are both unset, which is the default. When they are set, a request that went through the agent gets a number, and `0.0` if it made no model call (such as a bare `size` or `price`). Requests rejected before the agent ran (empty, over-long, or non-text) are always null.

**How to test:** Send 20 requests, mixing successful, failed, and rejected ones. Count the records written for each request, then check each record against the rules above.

**Why this target:** An unlogged request makes debugging harder, since we cannot tell whether the problem is on the user's side or the MCP's side. A record missing a required field has the same problem, because we cannot tell which part of the query failed. The nullable fields are null by design, so the check is that each null appears only in the cases listed above.

### 4. Queries with decimal prices or sizes match precisely

**Target:** 5 of 5 queries return a listing that meets every constraint in the query. The constraints are:

- **Price:** the listing's price is at or below the price cap in the query. Listing prices in `data/listings.json` are whole dollars, so a cap such as `under $30.50` should return any listing priced $30.00 or less.
- **Size:** the listing's size must include every part of the requested size, after case and slash normalization (`s/m` and `S/M` are the same). A request for `size S` is satisfied by an `S/M` listing, because that listing includes S. A request for `size S/M` is not satisfied by an `S` listing, because it lacks M. This is the rule `size_matches` in `tools.py` implements. Each size in a query must follow the word `size`, because a size without it is not parsed. For example, `pants W30 L30` returned W28 and W29 pants.

Inaccurate matches and empty results both count as failures.

**How to test:** Run these five queries. Before running, confirm in `data/listings.json` that each one has at least one listing meeting all its constraints. If one does not, replace the query. Do not lower the target.

1. `tee under $30.50`: decimal price cap
2. `tee size S/M`: slash-format size
3. `jeans size W30 L30 under $38.50`: waist and length pair with a decimal cap (the listing is priced $38.00)
4. `jeans size W30 L30`: waist and length pair (the same listing, $38.00)
5. `boots size US 8.5 under $44.50`: US size with a decimal cap (the listing is priced $44.00)

Do not use a size that is not in the data, such as `W30 L40` or `UK 7.5`. A correct matcher is expected to return nothing for those, so they test the data, not the matching.

**Why this target:** Size and decimal matching used to be either too strict or missing entirely, so queries returned no matches or the wrong ones. Each query in the set has a listing in the data that meets all its constraints, so a correct matcher should return one every time. A miss means the matching logic is wrong, not the data. The target is 5 of 5, not 3 of 5, for that reason.

### 5. Requests are paced to stay under the 15-per-minute API limit

**Target:** Across 10 back-to-back runs, the number of requests in any 60-second window never exceeds 15. This is a hard API limit, so a single violation fails the criterion.

**How to test:**

1. Set `AI201_CACHE=0` for the whole test. With the cache on, a repeated query returns a saved answer without a model call, so the test could pass without any request being paced.
2. Run `app.py ask` 10 times back to back with queries that each make model calls.
3. Delete `logs/request_times.jsonl` before the test, so it holds only this test's requests. `generate.py` appends one line, `{"t": <unix time>}`, for each request it sends. Unlike `logs/rate_state.json`, which keeps only the last 60 seconds, this file is never pruned. After the 10 runs, find the peak: for each timestamp, count the timestamps from it up to 60 seconds later. Count across the whole file, not run by run, because a 60-second window can span two runs. The highest count must be 15 or less.
4. As an outside check, compare the total request count with the requests shown on the Google AI Studio usage page for the same period. The log is written by the same code that paces requests, so it cannot show a request that code never recorded.

**Why this target:** Users may submit several requests in a row. The MCP uses Gemini's free-tier API, which rate-limits quickly when requests are not paced. Pacing keeps the application responsive without long waits or sudden rejections.

---

## Earlier project criteria (units 3–4)

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:** Searching based on the query alone at least requires matching by keyword. Phrasing will vary across queries for the same concept, so we can't expect perfection here.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:** A query that matches no listings should return an empty list; the agent should recognize the empty list as a sign to go to the second branch of the planning loop (returning a message recommending changes). It should never proceed and suggest an outfit based on an empty list.

---

## 3. Session's "selected_item" property matches the item presented in "suggest_outfit"

Also in 5 of 5 tries, the item present in `suggest_outfit` should match the item in `selected_item` in terms of ID.

**Why this target:** Whatever goes into `selected_item` will be re-used later down the pipeline, from `suggest_outfit` to `fit_card`. The item has to be consistent; it shouldn't be made up if it doesn't exist. nor changed once selected by the user.

---

## 4. Fit card is informative about the outfit itself

In 3/5 times, the fit card should mention the cost of the selected item relative to the outfit, followed by what occasion(s) said outfit would be good for. Overall, the fit card should be less than five sentences.

**Why this target:** The model will generate a different output every time, so it's important to give enough room for it to make mistakes while also giving the output some structure via this criterion. Five sentences, if used wisely, should be sufficient for a holistic review of the outfit generated.

>**Revised in unit 4:** The fit card should mention the selected item's price at least once, in 4/5 tries.
>
> **Why revised:** "Cost relative to the outfit" wasn't something `create_fit_card`'s prompt actually asks the model to compute — none of the 5 tries produced a cost comparison, only a standalone price mention. The original criterion was testing something the tool was never built to produce. The revised version measures what the tool actually does.

---

## 5. Price ceiling is respected

If the user provides a price limit initially, every returned listing's price is less than or equal to `max_price` (5/5 tries).

**Why this target:** This is a hard filter in `search_listings`; there's no reason to expect anything less than 5/5.

---
