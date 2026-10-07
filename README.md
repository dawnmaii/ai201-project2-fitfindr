# FitFindr

## What This Does

This program accepts a description of a wardrobe item along with size and a price limit as optional fields. It then searches a database of listings and selects an item that matches the description and constraint(s) given, after which it recommends an outfit with that item based on what the user already has in their wardrobe. Then, it generates a "fit card" or "caption", a short summary of the outfit generated with the chosen item.

---

## Tool Inventory

### `search_listings`

- **What it does:** Searches listings data for items that match a description, with the option to set price and size ceiling.
- **Inputs:** `description` (str), `size` (str, optional — None skips size filtering; matched case-insensitively against each part of the listing's size when split on /, so a request for "M" matches a listing sized "S/M"), `max_price` (float, optional — none skips price filtering)
- **Returns:** A list of dictionaries that each contain the following fields: id, title, description, category, style_tags (list), size, condition, price (float), colors (list), brand (str or None), platform.
- **When it has nothing:** Returns an empty list

### `suggest_outfit`

- **What it does:** Suggest one or two outfits, given a thrifted item and the user's wardrobe
- **Inputs:** `new_item` (dict), `wardrobe` (dict)
- **Returns:** A string suggesting outfits
- **When it has nothing:** Output cannot be empty, so it will return a string with general styling advice.

### `create_fit_card`

- **What it does:** Writes a short caption about the outfit chosen.
- **Inputs:** `outfit` (str), `new_item` (dict)
- **Returns:** A string representing a caption for an outfit.
- **When it has nothing:** If the outfit input is empty or whitespace, return a descriptive messages stating this. It is not possible to have an empty return output.

---

## Planning Loop

**Branch rule:** If `search_listings` returns an empty list, put a message in the session and stop. Otherwise take the first result and go to `suggest_outfit`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** Regex-based. re.search() pulls out a dollar amount (\$(\d+)) for max_price and a size token (size\s+(\S+)) for size, both optional — None if not found. The remaining text, after stripping out the matched price/size phrases with re.sub(), becomes the description.

**What moves through the session:** query → parsed into session["parsed"] (description, size, max_price) → fed into search_listings, result stored in session["search_results"] → branch: if empty, session["error"] is set and the run stops here; otherwise the first result becomes session["selected_item"] → session["selected_item"] + session["wardrobe"] go into suggest_outfit, result stored in session["outfit_suggestion"] → session["outfit_suggestion"] + session["selected_item"] go into create_fit_card, result stored in session["fit_card"].

---

## Sample Run

### One full query

```text
$ python agent.py
>> 
=== A query the data can match ===
  found:    Mesh Long-Sleeve Top — Black — $15.0 on depop
  outfit:   Since you just picked up the versatile **Mesh Long-Sleeve Top in Black**, you have a great base piece that can transition easily between edgy, casual, and smart-casual looks. 

Here are three outfit suggestions using the items from your wardrobe list:

### Outfit 1: The "Model Off-Duty" Edgy Look
*This outfit plays with transparency and layering, keeping the color palette monochromatic and cool.*
* **Top:** Mesh Long-Sleeve Top (Black) *layered over* White ribbed tank top (tops)
* **Bottoms:** Baggy straight-leg jeans, dark wash
* **Shoes:** Black combat boots
* **Accessories:** Black crossbody bag

**Why it works:** Wearing the white ribbed tank underneath the sheer black mesh top creates a sharp, high-contrast layered effect. Paired with the baggy dark-wash jeans and combat boots, it gives off an effortless, streetwear-inspired vibe.

---

### Outfit 2: High-Low Smart Casual
*A mix of tailored trousers and a grungy mesh top for a balanced, fashion-forward contrast.*
* **Top:** Mesh Long-Sleeve Top (Black)
* **Bottoms:** Wide-leg khaki trousers
* **Outerwear:** Vintage black denim jacket
* **Shoes:** Chunky white sneakers
* **Accessories:** Brown leather belt

**Why it works:** The structured, polished look of the wide-leg khaki trousers is instantly cooled down by the sheer black mesh top. Adding the vintage black denim jacket on top and grounding the look with chunky white sneakers ties the sporty and tailored elements together. Don't forget to thread the brown leather belt through the trousers to add a nice touch of contrast.

---

### Outfit 3: Cozily Textured Street Style
*Perfect for transitional weather, this look mixes textures (mesh, fleece, and denim).*
* **Top:** Oversized grey crewneck sweatshirt (worn *over* or *layered with* the Mesh Long-Sleeve Top so the mesh peeks out at the neck and cuffs)
* **Bottoms:** Baggy straight-leg jeans, dark wash
* **Outerwear:** Vintage black denim jacket (optional, for colder days)
* **Shoes:** Chunky white sneakers
* **Accessories:** Black crossbody bag

**Why it works:** Layering the sheer mesh top underneath an oversized crewneck allows the collar and cuffs of the mesh to peek through, adding subtle texture to a basic sweatshirt-and-jeans combo. Finish it off with chunky white sneakers for a comfortable, everyday fit.
  fit card: Channeling total model-off-duty energy in this vintage Depop find—the versatile Mesh Long-Sleeve Top in Black (grabbed for just $15!) layered over a classic white ribbed tank and baggy dark-wash jeans. 🖤✨ Grounded with black combat boots and a sleek crossbodybag, it’s the ultimate cool-girl streetwear fit for running weekend errands, grabbing iced coffee, or heading to a casual concert. Run, don't walk, to score gems like this! 🤌🏼🛍️ #DepopFinds #StreetwearStyle #ModelOffDuty #ThriftedFashion

=== A query it can't ===
  stopped: No matches for 'designer ballgown' under $5.0 in size XXS — try raising the price, widening the size, or changing the description.
  fit_card is None — it should still be None here

The second one should stop before the fit card. If both paths look the same,
the branch isn't doing anything yet.
```

### The three tools, tested one at a time

```text
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
[{'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'bandtee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_017', 'title': 'Mesh Long-Sleeve Top — Black', 'description': 'Sheer black mesh long-sleeve. Great for layering under a graphic tee or over a bralette. Stretchy material, fits true to size.', 'category': 'tops', 'style_tags': ['y2k', 'grunge', 'goth', 'layering'], 'size': 'S/M', 'condition': 'excellent', 'price': 15.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_002', 'title': 'Y2K Baby Tee —Butterfly Print', 'description': 'Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.', 'category': 'tops', 'style_tags': ['y2k', 'vintage', 'graphic tee', 'cottagecore'], 'size': 'S/M', 'condition': 'excellent', 'price': 18.0, 'colors': ['white', 'pink', 'purple'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_015', 'title': 'Vintage GraphicHoodie — Faded Black', 'description': 'Faded black pullover hoodie with barely-visible vintage graphic on the chest. Cozy interior. Somepilling but adds to the worn-in look.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'graphic', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 26.0, 'colors': ['black', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_033', 'title': 'Vintage Band Tee — Faded Grey', 'description': 'Faded grey band-style tee with distressed graphic. Crew neck. Fits boxy. Well-loved but no holes or major damage.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'band tee', 'graphic tee', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 19.0, 'colors': ['grey', 'charcoal'], 'brand': None, 'platform': 'depop'}]
```

```text
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"  
>> 
Here is a casual, vintage-inspired outfit built around your new **Vintage Levi's 501 Jeans in Medium Wash**:

### **The Outfit Breakdown**
* **Top:** White ribbed tank top
* **Outerwear:** Vintage black denim jacket (worn over the tank)
* **Shoes:** Chunky white sneakers
* **Accessories:** Brown leather belt & Black crossbody bag

---

### **Why This Works**
This look leans into effortless, off-duty 90s style. The medium wash of the Levi's 501s pairs naturally with the crisp white ribbed tankfor a classic, high-contrast base. Throwing on the vintage black denim jacket adds a cool, broken-in texture and creates a stylish double-denim contrast (blue jeans + black jacket). 

The chunky white sneakers tie in with the bright white of the tank top for a cohesive look, while the brown leather belt adds a touch ofwarmth to break up the blue and black. Finally, the black crossbody bag keeps it practical and ties into the black outerwear. 

### **How to Wear It**
Tuck the white ribbed tank slightly into the 501s to highlight the brown leather belt, let the black denim jacket hang loosely over yourshoulders or on your arms, slip on the chunky sneakers, and sling the crossbody bag across your front or side. Perfect for casual weekends, errands, or hanging out!
```

```text
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"  
>> 
Can you ever go wrong with a classic denim and sneaker combo? 👟👖 Rocking these Vintage Levi’s 501 Jeans in a timeless medium wash (scored on Depop for just $38!) paired with crisp white sneakers for the ultimate effortless look. It’s the absolute best fit for running weekend errands, grabbing iced coffee with friends, or a casual Sunday farmers market stroll. ☕️✨ Tap the link to shop the look before it’s gone!
```

---

## How I Used AI

### Moment 1

- *What I asked for:* Check the output and help me debug the `search_listings` size filter.
- *What came back:* Pointed out that `item['size'] == size` was too strict for a substring check if I wanted to consider additional qualifying sizes.
- *What I changed:* Decided to do a split on size based on the "/" character to do a proper substring check and filter for size.

### Moment 2

- *What I asked for:* I asked AI to review  my `run_agent` loop for any inconsistencies in syntax or logic.
- *What came back:* AI caught that I was referencing session['new_item'], a key that doesn't exist in the session dict, and that suggest_outfit was reading the local wardrobe parameter instead of session['wardrobe'].
- *What I changed:* After asking for further understanding on how these bugs occurred, I implemented the recommended fixes.

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
| --------- | ------ | ----- | ----- | ----- | ----- | ----- | ------- |
| 1.        |        |       |       |       |       |       |         |
| 2.        |        |       |       |       |       |       |         |
| 3.        |        |       |       |       |       |       |         |
| 4.        |        |       |       |       |       |       |         |
| 5.        |        |       |       |       |       |       |         |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```text

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|-----------|--------|---------|---------------|
| 1 |           |        |         |               |
| 2 |           |        |         |               |
| 3 |           |        |         |               |
| 4 |           |        |         |               |
| 5 |           |        |         |               |

### Diagnoses

---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

### Happy path

```text

```

### Empty search

```text

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->

---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
| --------- | ------ | ----- | ----- | ----- | ----- | ----- | ------- |
| 1.        |        |       |       |       |       |       |         |
| 2.        |        |       |       |       |       |       |         |
| 3.        |        |       |       |       |       |       |         |
| 4.        |        |       |       |       |       |       |         |
| 5.        |        |       |       |       |       |       |         |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->

---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->

<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
