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

### Moment 3

- *What I asked for:* Help understanding why --trace was crashing with TypeError: unhashable type: 'dict'.
- *What came back:* AI explained I'd written inputs={...} literally (which is Python's Ellipsis wrapped in a set) instead of a real dict, and in another call had used curly braces as a set literal containing dicts, which can't be hashed.
- *What I changed:* Rewrote every trace.step() call to pass a proper {"key": value} dict matching each function's actual parameters.

### Moment 4

- *What I asked for:* Help understanding why 0 of 5 "before" tries satisfied criterion 4's "cost relative to the outfit" requirement.
- *What came back:* AI pointed out the create_fit_card prompt never actually asked the model to frame price that way — it only asked for price, platform, and occasion — so the model had no instruction to produce a cost comparison.
- *What I changed:* Added an explicit instruction to the prompt ("frame the price as what the whole look would cost"), which fixed it to 5/5 in the "after" run.

---

## Run Log — Before

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
| --------- | ------ | ----- | ----- | ----- | ----- | ----- | ------- |
| 1. Matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Impossible query stops before second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Session's `selected_item` matches item in `suggest_outfit` | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Fit card mentions cost + occasion, under 5 sentences | 3 of 5 | PASS | PASS | PASS | PASS | FAIL | MET (4/5) |
| 5. Price ceiling respected | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

Produced by `run_eval.py::run_once` → `agent.py::run_agent`.

**Criterion 1** — query: `vintage graphic tee under $30`

```text
stopped early: no
selected_item: Graphic Tee — 2003 Tour Bootleg Style ($24.0, depop)
search_results: 10
Fit card: Channeling major Y2K energy in this vintage-vibes Graphic Tee — 2003 Tour Bootleg Style (Black), found on Depop for just $24.00! I layered it under an oversized grey crewneck and dark wash baggy straight-leg jeans, finishing the look with edgy black combat boots and a black crossbody bag. It's the ultimate effortless streetwear fit for transitional weather, weekend coffee runs, or just hanging out. 🖤✨
```

**Criterion 2** — query: `designer ballgown size XXS under $5`

```text
stopped early: yes — No matches for 'designer ballgown' under $5.0 in size XXS — try raising the price, widening the size, or changing the description.
selected_item: (none)
search_results: 0
```

**Criterion 3** — query: `vintage graphic tee under $30`

```text
selected_item: Graphic Tee — 2003 Tour Bootleg Style ($24.0, depop)
[2] suggest_outfit
      in:  dict with keys: new_item, wardrobe
      out: Here are three outfit ideas featuring your new **Graphic Tee — 2003 Tour Bootleg Style (Black)**...
```

**Criterion 4** — query: `denim jacket under $50`

```text
Fit card: Scored this light wash cropped denim jacket on Poshmark for just $42 and I'm officially obsessed! Here I'm styling it doubled up with a white ribbed tank, dark wash baggy straight-leg jeans, chunky white sneakers, and a black crossbody bag. It's the ultimate effortless fit for weekend errands, grabbing iced coffee with friends, or a casual daytime date. ✨ Denim dreams really do come true! 👖💙
```

**Criterion 5** — query: `graphic tee under $20`

```text
out: 3 items: Mesh Long-Sleeve Top — Black ($15.0), Y2K Baby Tee — Butterfly Print ($18.0), Vintage Band Tee — Faded Grey ($19.0)
```

---

## Verdicts and Diagnoses

| # | Criterion                                                | Target | Verdict   | How I decided                                                   |
|---|----------------------------------------------------------|--------|-----------|-----------------------------------------------------------------|
| 1 | Matching query completes all three tools                 | 4 of 5 | MET (5/5) | All 5 tries completed search→outfit→fit card with no early stop |
| 2 | Impossible query stops before second tool                | 5 of 5 | MET (5/5) | All 5 tries stopped at the branch with search_results: 0        |
| 3 | `selected_item` matches item in `suggest_outfit`         | 5 of 5 | MET (5/5) | Same item title/price carried through all 5 tries' trace        |
| 4 | Fit card mentions cost + occasion, under 5 sentences     | 3 of 5 | MET (4/5) | 4 of 5 tries mentioned price and occasion under 5 sentences     |
| 5 | Price ceiling respected                                  | 5 of 5 | MET (5/5) | All 5 tries' returned listings stayed ≤ $20                     |

### Diagnoses

No misses this round — all 5 criteria met their targets. But criterion 4's target (3/5) didn't get a meaningful test: looking at the actual fit cards, none of the 5 tries mention cost 'relative to the outfit' as the criterion specifically requires — every fit card just states the item's standalone price. The criterion passed on a looser reading than what I originally wrote, which means the 4/5 result doesn't actually confirm the thing I meant to test. See the revision in `criteria.md`.

---

## Loop Trace

### Happy path

```text
python app.py ask 'vintage graphic tee under $30' --trace     
[1] search_listings (via MCP)
      in:  dict with keys: description, size, max_price
      out: 10 items: Graphic Tee — 2003 Tour Bootleg Style, Y2K Baby Tee — Butterfly Print, Vintage Graphic Hoodie — Faded Black … +7 more
[2] suggest_outfit
      in:  dict with keys: new_item, wardrobe
      out: Here are a few ways to style your new **Graphic Tee — 2003 Tour Bootleg Style (in Black)** using the items fro…
[3] create_fit_card
      in:  dict with keys: outfit, new_item
      out: Channeling major Y2K/Retro-Grunge energy with this vintage-inspired 2003 Tour Bootleg Graphic Tee in black, sc…

  Found:    Graphic Tee — 2003 Tour Bootleg Style — $24.0 on depop

  Outfit:   Here are a few ways to style your new **Graphic Tee — 2003 Tour Bootleg Style (in Black)** using the items from your wardrobe, depending on the vibe you are going for:

### Outfit 1: The Ultimate Y2K/Retro-Grunge Look (Edgy & Casual)
*This look leans into the "bootleg tour" aesthetic by pairing the tee with distressed denim and chunky footwear.*
* **Top:** Graphic Tee — 2003 Tour Bootleg Style (Black)
* **Bottoms:** Baggy straight-leg jeans (dark wash)
* **Outerwear (Optional):** Vintage black denim jacket (worn off the shoulders or open)
* **Shoes:** Black combat boots
* **Accessories:** Brown leather belt, Black crossbody bag

### Outfit 2: Streetwear Layered Look (Cool & Comfortable)
*Perfect for cooler weather or an effortless street-style aesthetic. Layering the graphic tee over or under creates dimension.*
* **Top:** Graphic Tee (Black) layered over or under the White ribbed tank top (let the white peek out at the collar/hem)
* **Bottoms:** Baggy straight-leg jeans (dark wash)
* **Outerwear:** Oversized grey crewneck sweatshirt (worn draped over the shoulders or pulled on if it gets cold)
* **Shoes:** Chunky white sneakers
* **Accessories:** Black crossbody bag

### Outfit 3: High-Low Contrast (Smart-Casual / Street-Chic)
*Mixing the casual, vintage music merch vibe with tailored trousers creates a very fashion-forward, balanced silhouette.*
* **Top:** Graphic Tee — 2003 Tour Bootleg Style (Black) tucked in slightly
* **Bottoms:** Wide-leg khaki trousers
* **Outerwear:** Black cropped zip hoodie (worn unzipped over the tee)
* **Shoes:** Chunky white sneakers (to keep it sporty) or Black combat boots (for a sharper edge)
* **Accessories:** Brown leather belt (essential to pull the khakis together), Black crossbody bag

  Fit card: Channeling major Y2K/Retro-Grunge energy with this vintage-inspired 2003 Tour Bootleg Graphic Tee in black, scored on Depop! Styled here with edgy baggy dark-wash straight-leg jeans, a classic brown leather belt, a black crossbody bag, and chunky black combat boots to complete the ultimate edgy, casual fit. Throw on a distressed black denim jacket for that effortless off-duty look. Perfect for weekend concerts, thrifting trips, or hanging out with friends when you want to look effortlessly cool. 🎸🖤✨ 

#Y2Kstyle #DepopFinds #GraphicTee #RetroGrunge #Streetwear #BootlegTee

1 model calls this session, 1 served from cache, 497 prompt + 140 output tokens
```

### Empty search

```text
python app.py ask 'designer ballgown size XXS under $5' --trace                                                                                          
>> 
[1] search_listings (via MCP)
      in:  dict with keys: description, size, max_price
      out: [] (empty)

  No matches for 'designer ballgown' under $5.0 in size XXS — try raising the price, widening the size, or changing the description.

0 model calls this session
```

**On the MCP move:** Moved search_listings behind MCP: registered it in mcp_server.py with a public description and typed inputs, then swapped the direct call in agent.py::run_agent for call_tool('search_listings', {...}). The return value remained the same, so the branch and downstream tools needed no changes either. The only real issue was self-inflicted: I initially assigned the MCP result to a new variable instead of session['search_results'], which silently broke the branch (it always looked empty) until fixed.

---

## The Improvement

**What I changed:** Added an explicit instruction to `create_fit_card`'s prompt (`tools.py`): "Frame the price of the item as what the whole look would cost, instead of just stating the price alone."

**Which failure it was meant to fix:** Criterion 4's original wording required the fit card to mention cost "relative to the outfit," but 0 of 5 "before" tries did this — every fit card just stated the item's standalone price. The prompt never asked for that framing, so the model never produced it.

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
| --------------------------------------------------------------------------- | ------ | ----- | ----- | ----- | ----- | ----- | ----------- |
| 4. Fit card mentions cost relative to outfit + occasion, under 5 sentences | 3 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

**Did it help, and how do I know:** Yes — before the change, 0 of 5 fit cards framed the price relative to the whole outfit (all 5 just stated the item's price standalone). After adding the explicit instruction, all 5 of 5 tries now frame the price as the cost of the complete look (e.g., "the whole look comes together for just $42.00," "$42 total for the whole look"). This is a direct, measurable fix — the model does exactly what you ask it to when the prompt is explicit, and the fix traced cleanly back to the diagnosis.

---

## What's Still Broken

No criterion was missed this unit, but one real weakness surfaced repeatedly
in the eval data that none of my five criteria happen to test for:

`search_listings`'s keyword-overlap scoring can't distinguish an item *being*
a graphic tee from an item's description merely *mentioning* one — the Mesh
Long-Sleeve Top kept surfacing for tee queries throughout this unit's eval
runs because its description contains the phrase "graphic tee" incidentally
("great for layering under a graphic tee"). I'd fix this by weighting matches
in `style_tags`/`title` higher than matches in free-text `description`, since
the tags are a more reliable signal of what an item actually is.

I didn't fix it this unit because Milestone 5 only allows one measured
improvement, and I prioritized the fit card prompt fix since it was tied to
an actual criterion (4) rather than this — a correctness issue I noticed but
that none of my current criteria directly test for. That's also worth noting
as its own gap: my test coverage doesn't currently catch this failure mode at
all, which I'd want to write a sixth criterion for if I were continuing this
project further.

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
