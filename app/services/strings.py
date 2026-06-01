"""
app/services/strings.py

USSD display strings per language.

TRANSLATION STATUS
------------------
English ("en") is complete and is the source of truth. Translators for
Dagbani ("dag") and Hausa ("hau") should replace every value still set to
"TODO" with the natural spoken-language equivalent of the English string
shown in the same key under "en".

USSD screens are read on basic feature phones, often aloud. Keep each
translation short, plain, and in words a farmer uses day to day. Avoid
jargon and acronyms (say "warehouse", not "GCX"). Spell words out so they
read naturally when spoken.

Keys whose values contain {placeholders} (like {bags}) MUST keep the
placeholder exactly as written — only translate the words around it.

NOTE TO TRANSLATORS: the English here was tightened to avoid repetition
and jargon. Translate the *meaning*, in the way a Northern Ghana cereal
farmer would actually say it — not word for word.
"""

STRINGS = {
    # ---------------------------------------------------------------
    # ENGLISH — complete, source of truth for translators
    # ---------------------------------------------------------------
    "en": {
        "welcome":        "Welcome to PostHarvest IQ",
        "select_crop":    "Choose your crop:",
        "maize":          "Maize",
        "millet":         "Millet",
        "sorghum":        "Sorghum",
        "select_dist":    "Choose your district:",

        # Decision headlines
        "store":          "STORE your crop",
        "sell_now":       "SELL NOW",
        "sell_partial":   "SELL HALF, STORE HALF",

        # Recommendation detail lines ({} placeholders must be kept)
        "earn_per_bag":   "Earn GHS {gain} more per bag if you store",
        "total_for_bags": "Total for {bags} bags: GHS {net}",
        "after_cost":     "(after storage cost)",
        # Reason line for SELL — explains WHY, does not repeat "sell"
        "sell_advice":    "Prices are high now. Waiting could earn you less.",

        # Storage / market lines
        "nearest":        "Nearest store",          # plain word, not "GCX"
        "store_location": "In {town}, {km} km away", # town + distance together
        "cost_per_month": "Cost: GHS {cost} per bag each month",
        "call":           "Call",
        "price_today":    "Price today: GHS {price} per bag",
        "nearest_market": "Nearest market: {town}, {km} km",

        # Partial action
        "sell_n_now":     "Sell {bags} bags now: GHS {amount}",
        "store_n_est":    "Store {bags} bags: about GHS {net} more",

        # No-storage / fallback (e.g. millet, which GCX does not store)
        "no_storage":     "No store found nearby for this crop.",
        "consider_sell":  "Selling may be your best option.",
        "call_mofa":      "Call MoFA: 118",
        "thanks":         "Thank you for using PostHarvest IQ.",
        "unavailable":    "Service busy. Please try again shortly.",
        "invalid":        "Wrong entry. Please try again.",
    },

    # ---------------------------------------------------------------
    # DAGBANI — translator: replace every "TODO" with the Dagbani for
    # the English value of the same key above.
    # ---------------------------------------------------------------
    "dag": {
        "welcome":        "TODO",
        "select_crop":    "TODO",
        "maize":          "Masara",
        "millet":         "TODO",
        "sorghum":        "TODO",
        "select_dist":    "TODO",

        "store":          "KPAGI ni masara",
        "sell_now":       "TODO",
        "sell_partial":   "TODO",

        "earn_per_bag":   "TODO",   # keep {gain}
        "total_for_bags": "TODO",   # keep {bags} and {net}
        "after_cost":     "TODO",
        "sell_advice":    "TODO",

        "nearest":        "TODO",
        "store_location": "TODO",   # keep {town} and {km}
        "cost_per_month": "TODO",   # keep {cost}
        "call":           "Sɔŋ",
        "price_today":    "TODO",   # keep {price}
        "nearest_market": "TODO",   # keep {town} and {km}

        "sell_n_now":     "TODO",   # keep {bags} and {amount}
        "store_n_est":    "TODO",   # keep {bags} and {net}

        "no_storage":     "TODO",
        "consider_sell":  "TODO",
        "call_mofa":      "TODO",
        "thanks":         "TODO",
        "unavailable":    "TODO",
        "invalid":        "TODO",
    },

    # ---------------------------------------------------------------
    # HAUSA — translator: replace every "TODO" with the Hausa for the
    # English value of the same key above.
    # ---------------------------------------------------------------
    "hau": {
        "welcome":        "TODO",
        "select_crop":    "Zaɓi amfanin gona:",
        "maize":          "Masara",
        "millet":         "TODO",
        "sorghum":        "TODO",
        "select_dist":    "Zaɓi gundumar:",

        "store":          "ADANA masararka",
        "sell_now":       "TODO",
        "sell_partial":   "TODO",

        "earn_per_bag":   "TODO",   # keep {gain}
        "total_for_bags": "TODO",   # keep {bags} and {net}
        "after_cost":     "TODO",
        "sell_advice":    "TODO",

        "nearest":        "Kusa",
        "store_location": "TODO",   # keep {town} and {km}
        "cost_per_month": "TODO",   # keep {cost}
        "call":           "Kira",
        "price_today":    "TODO",   # keep {price}
        "nearest_market": "TODO",   # keep {town} and {km}

        "sell_n_now":     "TODO",   # keep {bags} and {amount}
        "store_n_est":    "TODO",   # keep {bags} and {net}

        "no_storage":     "TODO",
        "consider_sell":  "TODO",
        "call_mofa":      "TODO",
        "thanks":         "TODO",
        "unavailable":    "TODO",
        "invalid":        "TODO",
    },
}


def t(lang: str, key: str) -> str:
    """
    Safe lookup. Falls back to English if a key is missing or still "TODO"
    in the requested language, so a half-finished translation never shows
    the literal word "TODO" on a farmer's screen.
    """
    en = STRINGS["en"]
    table = STRINGS.get(lang, en)
    val = table.get(key)
    if not val or val == "TODO":
        return en.get(key, key)
    return val