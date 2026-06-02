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
        # SELL recommendation money lines (mirror the STORE screen)
        "sell_now_price": "GHS {price} per bag",
        "sell_now_total": "{bags} bags = GHS {total} today",

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
        "welcome":        "Ni kpem PostHarvest IQ",
        "select_crop":    "Yuli ni fo ŋun dali:",
        "maize":          "Masara",
        "millet":         "Daawa",
        "sorghum":        "Chiŋ",
        "select_dist":    "Yuli ni fo ŋun distrik:",
 
        "store":          "KPAGI ni masara",
        "sell_now":       "NYƐƐRI SAHA YIN",
        "sell_partial":   "NYƐƐRI BAARIGI, KPAGI BAARIGI",
 
        "earn_per_bag":   "Fo na bɔri GHS {gain} paɣa baŋ mali kpagi",
        "total_for_bags": "Bagi {bags} kpeŋ: GHS {net}",
        "after_cost":     "(kpagim toɣo ti bɔri)",
        "sell_advice":    "Nyɛɛri daa bee nyaŋa. A mali kpagi a nyɛɛri a yɛla bia.",
        "sell_now_price": "GHS {price} baŋ kpem",
        "sell_now_total": "Bagi {bags} = GHS {total} yini",
 
        "nearest":        "Kpagili ti kpɛŋ",
        "store_location": "{town}, {km} km",
        "cost_per_month": "Toɣo: GHS {cost} baŋ kpem kodili",
        "call":           "Sɔŋ",
        "price_today":    "Nyɛɛri daa: GHS {price} baŋ",
        "nearest_market": "Zaŋ ti kpɛŋ: {town}, {km} km",
 
        "sell_n_now":     "Nyɛɛri bagi {bags} yini: GHS {amount}",
        "store_n_est":    "Kpagi bagi {bags}: GHS {net} paɣa",
 
        "no_storage":     "Kpagili ka bo ni fo ŋun dali kɔŋ.",
        "consider_sell":  "Nyɛɛri ni bee fo nyaŋa yɛla.",
        "call_mofa":      "Sɔŋ MoFA: 118",
        "thanks":         "Ti wuhibi fo PostHarvest IQ ni.",
        "unavailable":    "Sɛrvisi mali doli. Gbɛ saha.",
        "invalid":        "Fo yuli ka nɔŋ. Gbɛ saha.",
    },

    # ---------------------------------------------------------------
    # HAUSA 
    # ---------------------------------------------------------------
    "hau": {
        "welcome":        "Barka da zuwa PostHarvest IQ",
        "select_crop":    "Zaɓi amfanin gona:",
        "maize":          "Masara",
        "millet":         "Gero",
        "sorghum":        "Dawa",
        "select_dist":    "Zaɓi gundumar:",
 
        "store":          "ADANA masararka",
        "sell_now":       "SAYAR YANZU",
        "sell_partial":   "SAYAR RABI, ADANA RABI",
 
        "earn_per_bag":   "Za ka sami GHS {gain} ƙari a buhu idan ka adana",
        "total_for_bags": "Jimlar buhu {bags}: GHS {net}",
        "after_cost":     "(bayan kuɗin adanawa)",
        "sell_advice":    "Farashin ya yi yawa yanzu. Jira na iya rage kuɗinka.",
        "sell_now_price": "GHS {price} a kowace buhu",
        "sell_now_total": "Buhu {bags} = GHS {total} yau",
 
        "nearest":        "Kusa",
        "store_location": "{town}, nesa {km} km",
        "cost_per_month": "Kuɗi: GHS {cost} a buhu a wata",
        "call":           "Kira",
        "price_today":    "Farashi yau: GHS {price} a buhu",
        "nearest_market": "Kasuwa mafi kusa: {town}, {km} km",
 
        "sell_n_now":     "Sayar buhu {bags} yanzu: GHS {amount}",
        "store_n_est":    "Adana buhu {bags}: kusan GHS {net} ƙari",
 
        "no_storage":     "Ba a sami wurin adanawa kusa ba.",
        "consider_sell":  "Sayarwa na iya zama mafi kyau a gare ka.",
        "call_mofa":      "Kira MoFA: 118",
        "thanks":         "Na gode da amfani da PostHarvest IQ.",
        "unavailable":    "Sabis ɗin yana da cunkoso. Da fatan sake gwadawa.",
        "invalid":        "Zaɓin ba daidai ba ne. Da fatan sake gwadawa.",
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