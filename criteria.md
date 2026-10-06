# Acceptance criteria — FitFindr

---

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

---

## 5. Price ceiling is respected

If the user provides a price limit initially, every returned listing's price is less than or equal to `max_price` (5/5 tries).

**Why this target:** This is a hard filter in `search_listings`; there's no reason to expect anything less than 5/5.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
