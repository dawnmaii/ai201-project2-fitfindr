"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import config  # noqa: F401 — you'll use this in search_listings
from generate import generate
from utils.data_loader import load_listings


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.
    """
    # 1. Load every listing with load_listings().
    listings = load_listings()
    # 2. Filter by max_price and by size, when each is provided.
    filtered_list = [item for item in listings if (max_price is None or item['price'] <= max_price) and (size is None or size.lower() in item['size'].lower().split('/'))]
    # 3. Score what's left by keyword overlap with `description`.
    scored_items = []
    normal_description = description.lower().split()
    for item in filtered_list:
        item_words = item['title'].lower().split() + item['description'].lower().split() + [tag.lower() for tag in item['style_tags']]
        overlap = len(set(normal_description) & set(item_words))
        # 4. Drop anything scoring zero.
        if overlap > 0:
            scored_items.append((overlap, item))
    # 5. Sort by score, highest first, and return the listing dicts — at most config.SEARCH_RESULT_LIMIT of them.
    sorted_items = sorted(scored_items, key=lambda scored: scored[0], reverse=True)
    top_items = sorted_items[:config.SEARCH_RESULT_LIMIT]
    result = [item for (score, item) in top_items]
    return result


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.
    """
    # 1. Check whether wardrobe['items'] is empty.
    # 2. If it is, ask the model for general styling ideas for this item.
    if not wardrobe['items']:
        prompt = f"Someone just got {new_item['title']}, a {new_item['category']} in {new_item['colors']}. Suggest general outfit ideas, since they don't have other items logged yet."
    else:
    # 3. If it isn't, format the wardrobe items into the prompt and ask for specific combinations naming pieces the user already owns.
        wardrobe_description = ", ".join([f"{item['name']} ({item['category']})" for item in wardrobe['items']])
        prompt = f"Based on the {new_item['title']}, a {new_item['category']} in {new_item['colors']} the user just bought, suggest an outfit based on {wardrobe_description}."
    # 4. Return the model's response.
    return generate(prompt)

# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time
    """
    # 1. Guard against an empty or whitespace-only `outfit`.
    if outfit.strip():
    # 2. Build a prompt with the item details and the outfit.
    # 3. Call generate() and return the response.
        return generate(f"The user has made an {outfit} featuring {new_item['title']} at {new_item['price']}, found on {new_item['platform']}! Please write an Instagram-like caption for this outfit, mentioning all item details and what the outfit would be good for. Keep it under five sentences.")
    else:
        return "You entered an empty outfit, or your outfit consists of only whitespace. Fix this first."
