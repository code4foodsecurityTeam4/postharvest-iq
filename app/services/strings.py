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
abbreviations that don't read well when spoken (e.g. spell out "month").

Keys whose values contain {placeholders} (like {bags}) MUST keep the
placeholder exactly as written — only translate the words around it.
"""

STRINGS = {
    # ---------------------------------------------------------------
    # ENGLISH — complete, source of truth for translators
    # ---------------------------------------------------------------
    "en": {
        "welcome":        "Welcome to PostHarvest IQ",
        "select_crop":    "Select your crop:",
        "maize":          "Maize",
        "millet":         "Millet",
        "sorghum":        "Sorghum",
        "select_dist":    "Select your district:",

        # Decision headlines
        "store":          "STORE your crop",
        "sell_now":       "SELL NOW",
        "sell_partial":   "SELL HALF, STORE HALF",

        # Recommendation detail lines ({} placeholders must be kept)
        "earn_per_bag":   "Earn GHS {gain} more per bag if you store",
        "total_for_bags": "Total for {bags} bags: GHS {net}",
        "after_cost":     "(after storage cost)",
        "sell_advice":    "Best to sell now. Prices are near their peak.",

        # Storage / market lines
        "nearest":        "Nearest storage",
        "cost_per_month": "Cost: GHS {cost} per bag per month",
        "call":           "Call",
        "price_per_bag":  "Price: GHS {price} per bag",
        "market_label":   "Market",
        "km_away":        "{km} km away",

        # Partial action
        "sell_n_now":     "Sell {bags} bags: GHS {amount} now",
        "store_n_est":    "Store {bags} bags: about GHS {net} more",

        # No-storage / fallback (e.g. millet, which GCX does not store)
        "no_storage":     "No verified storage for this crop nearby.",
        "consider_sell":  "Selling may be your best option.",
        "call_mofa":      "Call MoFA: 118",
        "thanks":         "Thank you for using PostHarvest IQ.",
        "unavailable":    "Service temporarily unavailable. Please try again shortly.",
        "invalid":        "Invalid input. Please try again.",
    },

    # ---------------------------------------------------------------
    # DAGBANI — translator: replace every "TODO" with the Dagbani for
    # the English value of the same key above.
    # ---------------------------------------------------------------
    "dag": {
        "welcome":      "Ni ti PostHarvest IQ",
        "select_crop":  "Yuli a bɔri di gbana:",
        "maize":        "Kaŋ (Maize)",
        "millet":       "Dawa (Millet)",
        "sorghum":      "Zumaya (Sorghum)",
        "select_dist":  "Yuli a tindana:",
        "store":        "KPAGI ni a gbana",
        "sell_now":     "DI a gbana ziŋ",
        "sell_partial": "DI bani — KPAGI bani",
        "price_rise":   "Ligdi zaai",
        "net_gain":     "Ni gbana kpɛm paai",
        "nearest":      "Kpɛng storage",
        "cost":         "GHS/bag/kpɛm",
        "call":         "Sɔŋ",
    },

    # ---------------------------------------------------------------
    # HAUSA — translator: replace every "TODO" with the Hausa for the
    # English value of the same key above.
    # ---------------------------------------------------------------
    "hau": {
         "welcome":      "Barka da zuwa PostHarvest IQ",
        "select_crop":  "Zaɓi amfanin gona:",
        "maize":        "Masara (Maize)",
        "millet":       "Gero (Millet)",
        "sorghum":      "Dawa (Sorghum)",
        "select_dist":  "Zaɓi gundumar:",
        "store":        "ADANA amfanin gona",
        "sell_now":     "SAYAR YANZU",
        "sell_partial": "SAYAR KASHI — ADANA KASHI",
        "price_rise":   "Tsammanin haɓakar farashi",
        "net_gain":     "Riba bayan adanawa",
        "nearest":      "Kusa da wurin adanawa",
        "cost":         "GHS/jaka/wata",
        "call":         "Kira",
    }
}
