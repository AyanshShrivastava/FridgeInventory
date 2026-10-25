"""
Database Ingestion and Translation Pipeline for FridgeInventory.
Converts raw Indian Recipe dataset into an indexed SQLite database (recipes.db)
matching the exact RescueRecipe format with Hindi translations, discrete steps,
chef pairing notes, chef zero-waste tips, and core main ingredient tokens.
"""

import csv
import json
import os
import re
import sqlite3
from typing import Dict, List, Optional, Set, Tuple

# Comprehensive Culinary Lexicon for English -> Hindi Translation
INGREDIENT_TRANSLATIONS: Dict[str, str] = {
    "paneer": "पनीर",
    "cottage cheese": "पनीर",
    "tomato": "टमाटर",
    "tomatoes": "टमाटर",
    "onion": "प्याज",
    "onions": "प्याज",
    "potato": "आलू",
    "potatoes": "आलू",
    "spinach": "पालक",
    "palak": "पालक",
    "karela": "करेला",
    "bitter gourd": "करेला",
    "bhindi": "भिंडी",
    "okra": "भिंडी",
    "lady finger": "भिंडी",
    "baingan": "बैंगन",
    "eggplant": "बैंगन",
    "brinjal": "बैंगन",
    "cauliflower": "फूलगोभी",
    "gobi": "गोभी",
    "cabbage": "पत्तागोभी",
    "patta gobi": "पत्तागोभी",
    "peas": "मटर",
    "green peas": "हरी मटर",
    "matar": "मटर",
    "capsicum": "शिमला मिर्च",
    "bell pepper": "शिमला मिर्च",
    "carrot": "गाजर",
    "carrots": "गाजर",
    "gajar": "गाजर",
    "beans": "बीन्स / फलियां",
    "french beans": "फ्रेंच बीन्स",
    "green beans": "हरी बीन्स",
    "bottle gourd": "लौकी",
    "lauki": "लौकी",
    "pumpkin": "कद्दू",
    "kaddu": "कद्दू",
    "cucumber": "खीरा",
    "kheera": "खीरा",
    "radish": "मूली",
    "mooli": "मूली",
    "beetroot": "चुकंदर",
    "mushroom": "मशरूम",
    "mushrooms": "मशरूम",
    "corn": "मक्का / कॉर्न",
    "sweet corn": "स्वीट कॉर्न",
    "garlic": "लहसुन",
    "ginger": "अदरक",
    "ginger-garlic": "अदरक-लहसुन",
    "green chilli": "हरी मिर्च",
    "green chillies": "हरी मिर्च",
    "coriander": "ताज़ा हरा धनिया",
    "mint": "पुदीना",
    "curry leaves": "कढ़ी पत्ता",
    "rice": "चावल",
    "basmati rice": "बासमती चावल",
    "brown rice": "ब्राउन राइस",
    "poha": "पोहा / चिवड़ा",
    "flattened rice": "पोहा",
    "sooji": "सूजी / रवा",
    "semolina": "सूजी",
    "rava": "रवा",
    "besan": "बेसन",
    "gram flour": "बेसन",
    "wheat flour": "गेहूं का आटा",
    "atta": "आटा",
    "maida": "मैदा",
    "all purpose flour": "मैदा",
    "oats": "ओट्स",
    "dal": "दाल",
    "toor dal": "अरहर / तूर दाल",
    "moong dal": "मूंग दाल",
    "chana dal": "चना दाल",
    "urad dal": "उड़द दाल",
    "masoor dal": "मसूर दाल",
    "chickpeas": "सफेद छोले / काबुली चना",
    "chole": "छोले",
    "black chickpeas": "काला चना",
    "kala chana": "काला चना",
    "rajma": "राजमा",
    "kidney beans": "राजमा",
    "milk": "दूध",
    "curd": "दही",
    "yogurt": "दही",
    "dahi": "दही",
    "butter": "मक्खन",
    "makhan": "मक्खन",
    "ghee": "देसी घी",
    "cream": "ताज़ी मलाई / फ्रेश क्रीम",
    "malai": "मलाई",
    "cheese": "चीज़",
    "cashew": "काजू",
    "cashews": "काजू",
    "cashew nuts": "काजू",
    "almond": "बादाम",
    "almonds": "बादाम",
    "peanuts": "मूंगफली",
    "raisins": "किशमिश",
    "walnuts": "अखरोट",
    "mango": "आम",
    "aam": "आम",
    "banana": "केला",
    "apple": "सेब",
    "orange": "संतरा",
    "lemon": "नींबू",
    "lime": "नींबू",
    "coconut": "नारियल",
    "fresh coconut": "ताज़ा नारियल",
    "dry coconut": "सूखा नारियल",
    "chicken": "चिकन",
    "mutton": "मटन",
    "egg": "अंडा",
    "eggs": "अंडे",
    "fish": "मछली",
    "prawns": "झींगा",
}

PANTRY_TRANSLATIONS: Dict[str, str] = {
    "salt": "स्वादानुसार नमक",
    "oil": "खाना पकाने का तेल",
    "cooking oil": "तेल",
    "mustard oil": "सरसों का तेल",
    "cumin seeds": "जीरा",
    "jeera": "जीरा",
    "turmeric powder": "हल्दी पाउडर",
    "turmeric": "हल्दी",
    "red chilli powder": "लाल मिर्च पाउडर",
    "kashmiri red chilli": "कश्मीरी लाल मिर्च पाउडर",
    "garam masala": "गरम मसाला",
    "coriander powder": "धनिया पाउडर",
    "dhania powder": "धनिया पाउडर",
    "kasuri methi": "कसूरी मेथी",
    "asafoetida": "हींग",
    "hing": "हींग",
    "mustard seeds": "राई / सरसों के दाने",
    "rai": "राई",
    "fennel seeds": "सौंफ",
    "saunf": "सौंफ",
    "carom seeds": "अजवाइन",
    "ajwain": "अजवाइन",
    "fenugreek seeds": "मेथी दाना",
    "cinnamon": "दालचीनी",
    "cardamom": "इलायची",
    "green cardamom": "हरी इलायची",
    "black cardamom": "बड़ी इलायची",
    "cloves": "लौंग",
    "black pepper": "काली मिर्च",
    "bay leaf": "तेजपत्ता",
    "dry red chilli": "सूखी लाल मिर्च",
    "amchur": "आमचूर (खटाई)",
    "dry mango powder": "आमचूर पाउडर",
    "chaat masala": "चाट मसाला",
    "sugar": "चीनी",
    "jaggery": "गुड़",
    "water": "पानी",
}

PANTRY_FILTER_SET: Set[str] = {
    "salt", "oil", "ghee", "water", "sugar", "cumin", "jeera", "turmeric", "haldi",
    "red chilli", "garam masala", "coriander powder", "dhania", "hing", "asafoetida",
    "mustard seeds", "rai", "curry leaves", "kadi patta", "bay leaf", "cinnamon",
    "cardamom", "cloves", "black pepper", "kali mirch", "kasuri methi", "amchur",
    "fennel", "saunf", "fenugreek seeds", "methi dana", "ajwain", "carom seeds",
    "chaat masala", "dry red chilli", "tejpatta", "dalchini", "elaichi", "laung"
}

def clean_dish_name(name: str) -> str:
    """Cleans raw CSV recipe title into appetizing, concise English title."""
    s = name.strip()
    s = re.sub(r"\s+Recipe\b", "", s, flags=re.I)
    s = re.sub(r"\s*-\s*.*$", "", s)  # Remove redundant hyphenated repeats
    s = re.sub(r"\s*\(Recipe\)", "", s, flags=re.I)
    s = re.sub(r"\s*\(In Hindi\)", "", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def translate_dish_name(dish_en: str) -> str:
    """Translates common Indian dish titles into authentic Hindi Devanagari."""
    translations = {
        "paneer butter masala": "शाही पनीर बटर मसाला",
        "restaurant-style paneer butter masala": "रेस्टोरेंट स्टाइल पनीर बटर मसाला",
        "palak paneer": "स्वादिष्ट पालक पनीर",
        "shahi paneer": "शाही पनीर",
        "kadai paneer": "कड़ाही पनीर",
        "matar paneer": "मटर पनीर",
        "paneer bhurji": "मसालेदार पनीर भुर्जी",
        "paneer tikka": "तंदूरी पनीर टिक्का",
        "dal tadka": "पंजाबी दाल तड़का",
        "dal makhani": "शाही दाल मखनी",
        "yellow dal": "पीली दाल तड़का",
        "sambar": "पारंपरिक दक्षिण भारतीय सांभर",
        "chole": "पंजाबी छोले मसाला",
        "chana masala": "मसालेदार चना मसाला",
        "rajma": "पंजाबी राजमा मसाला",
        "rajma masala": "पंजाबी राजमा मसाला",
        "aloo gobi": "मसालेदार आलू गोभी",
        "aloo matar": "रसेदार आलू मटर",
        "aloo paratha": "पंजाबी आलू पराठा",
        "palak paneer paratha": "पौष्टिक पालक पनीर पराठा",
        "spicy tomato rice": "मसालेदार टमाटर भात (टोमैटो राइस)",
        "tomato rice": "टमाटर भात (टोमैटो राइस)",
        "masala karela": "मसाला करेला",
        "bhindi masala": "मसालेदार कुरकुरी भिंडी",
        "baingan bharta": "ढाबा स्टाइल बैंगन भर्ता",
        "dum aloo": "कश्मीरी दम आलू",
        "veg biryani": "शाही वेज दम बिरयानी",
        "biryani": "शाही बिरयानी",
        "pulao": "मटर पुलाव",
        "jeera rice": "जीरा राइस",
        "khichdi": "पौष्टिक मूंग दाल खिचड़ी",
        "pav bhaji": "मुंबई स्टाइल पाव भाजी",
        "samosa": "हलवाई स्टाइल समोसा",
        "pakoda": "कुरकुरे प्याज के पकोड़े",
        "poha": "इंदौरी कांदा पोहा",
        "upma": "स्वादिष्ट सूजी उपमा",
        "idli": "सॉफ्ट इडली",
        "dosa": "क्रिस्पी मसाला डोसा",
        "masala dosa": "क्रिस्पी मसाला डोसा",
        "kheer": "पारंपरिक चावल की खीर",
        "sooji halwa": "सूजी का हलवा",
        "gajar halwa": "गाजर का हलवा",
        "gulab jamun": "गुलाब जामुन",
        "mango lassi": "ताज़ा मलाईदार मैंगो लस्सी",
        "lassi": "पंजाबी मीठी लस्सी",
        "masala chai": "अदरक-इलायची मसाला चाय",
        "cold coffee": "चिल्ड कैफ़े कोल्ड कॉफ़ी",
    }
    low = dish_en.lower()
    for k, v in translations.items():
        if k in low:
            return v
    # Transliterate generic Indian pattern
    words = dish_en.split()
    hi_words = []
    for w in words:
        wl = w.lower()
        if wl in INGREDIENT_TRANSLATIONS:
            hi_words.append(INGREDIENT_TRANSLATIONS[wl])
        else:
            hi_words.append(w)
    return " ".join(hi_words)

def determine_meal_type(dish_en: str, cuisine: str) -> Tuple[str, str]:
    """Infers meal type in English and Hindi."""
    low = dish_en.lower()
    if any(k in low for k in ["chai", "tea", "coffee", "lassi", "shake", "juice", "drink", "sharbat"]):
        return "Beverage / Drink", "ताज़ा पेय"
    if any(k in low for k in ["kheer", "halwa", "ladoo", "jamun", "barfi", "payasam", "cake", "sweet", "dessert", "pudding"]):
        return "Traditional Dessert", "पारंपरिक मिठाई"
    if any(k in low for k in ["paratha", "dosa", "idli", "upma", "poha", "cheela", "thepla", "puri", "poori"]):
        return "Breakfast Special", "खास नाश्ता"
    if any(k in low for k in ["samosa", "pakoda", "pakora", "tikki", "chaat", "bhurji", "sandwich", "cutlet", "snack"]):
        return "Street Food Snack", "स्वादिष्ट स्नैक"
    if any(k in low for k in ["biryani", "pulao", "rice", "curry", "masala", "dal", "gravy", "paneer", "chicken", "sabzi", "kofta"]):
        return "Main Course", "मुख्य भोजन"
    return "Homestyle Meal", "घर का भोजन"

def generate_pairing_notes(meal_type: str, dish_en: str) -> Tuple[str, str]:
    """Generates chef course & pairing notes in English and Hindi."""
    low = dish_en.lower()
    if "dal" in low:
        return (
            "Best enjoyed piping hot with steamed basmati rice, crispy papad, and fresh lemon pickle.",
            "गरमा-गरम बासमती चावल, कुरकुरे पापड़ और नींबू के आचार के साथ परोसने पर यह सबसे स्वादिष्ट लगता है।"
        )
    if "biryani" in low or "pulao" in low:
        return (
            "Pair with chilled cucumber-mint raita, thinly sliced onion salad, and roasted papad.",
            "ठंडे खीरा-पुदीना रायते, बारीक कटे प्याज के लच्छे और भुने पापड़ के साथ परोसें।"
        )
    if "paratha" in low:
        return (
            "Serve hot with a generous knob of fresh white butter, chilled curd, and spicy mango pickle.",
            "ताज़ा सफेद मक्खन, ठंडे दही और चटपटे आम के आचार के साथ गरमा-गरम परोसें।"
        )
    if meal_type == "Main Course":
        return (
            "Serve hot with garlic butter naan, tandoori roti, or fragrant jeera rice.",
            "गरमा-गरम गार्लिक बटर नान, तंदूरी रोटी या खुशबूदार जीरा राइस के साथ परोसें।"
        )
    if meal_type == "Street Food Snack":
        return (
            "Serve crisp and hot alongside tangy tamarind chutney, fresh green coriander dip, and masala chai.",
            "गरमा-गरम खट्टी-मीठी इमली की चटनी, तीखी हरी चटनी और कड़क मसाला चाय के साथ परोसें।"
        )
    if meal_type == "Traditional Dessert":
        return (
            "Serve warm or chilled, garnished with roasted slivered almonds, pistachios, and a pinch of saffron.",
            "बारीक कटे बादाम, पिस्ते की कतरन और केसर के धागों से सजाकर गरमा-गरम या ठंडा परोसें।"
        )
    if meal_type == "Beverage / Drink":
        return (
            "Serve chilled in a tall glass, garnished with crushed cardamom and fresh mint sprigs.",
            "ऊपर से पिसी हुई इलायची और ताज़ा पुदीने की पत्ती से सजाकर ठंडा-ठंडा परोसें।"
        )
    return (
        "Serve hot with fresh phulkas and a crisp seasonal salad.",
        "गरमा-गरम ताज़ी रोटियों और मौसमी सलाद के साथ परोसें।"
    )

def generate_chef_tip(dish_en: str, meal_type: str) -> Tuple[str, str]:
    """Generates authentic grandma's secret culinary tip ('दादी माँ का नुस्खा')."""
    low = dish_en.lower()
    if "paneer" in low:
        return (
            "Soak paneer cubes in lukewarm salted water for 5 minutes before adding to gravy to keep them ultra-soft and spongy.",
            "पनीर को ग्रेवी में डालने से पहले 5 मिनट के लिए हल्के गुनगुने नमकीन पानी में भिगो दें, इससे पनीर एकदम मलाईदार और स्पंजी रहता है।"
        )
    if "dal" in low:
        return (
            "For restaurant aroma, pour your ghee tadka over the dal right before serving and immediately cover with a lid for 2 minutes to trap the smoke.",
            "दाल में रेस्टोरेंट जैसी खुशबू के लिए देसी घी का तड़का परोसने से ठीक पहले लगाएं और 2 मिनट के लिए ढक्कन बंद रखें ताकि महक अंदर समा जाए।"
        )
    if "tomato" in low or "butter masala" in low or "makhani" in low:
        return (
            "Add a tiny pinch of sugar to balance the natural tanginess of tomatoes, and finish with a knob of butter for an authentic glossy sheen.",
            "टमाटर के खट्टेपन को संतुलित करने के लिए चुटकी भर चीनी और अंत में थोड़ा मक्खन मिलाएँ, जिससे ग्रेवी में रेस्टोरेंट जैसी चमक आती है।"
        )
    if "karela" in low:
        return (
            "Rub sliced bitter gourd with rock salt and turmeric, let rest for 15 minutes, then squeeze out the bitter juice before sautéing.",
            "करेले के टुकड़ों पर नमक और हल्दी लगाकर 15 मिनट रख दें, फिर उसका कड़वा पानी निचोड़कर पकाएं — करेला बिल्कुल कड़वा नहीं लगेगा।"
        )
    if "palak" in low or "spinach" in low:
        return (
            "Blanch spinach leaves in boiling water for 90 seconds, then immediately immerse in ice-cold water to lock in the vibrant natural emerald green color.",
            "पालक को उबलते पानी में केवल डेढ़ मिनट उबालकर तुरंत बर्फ वाले ठंडे पानी में डालें, इससे पालक का रंग एकदम चमकदार हरा बना रहता है।"
        )
    if "rice" in low or "biryani" in low:
        return (
            "After cooking, let the rice rest covered off the heat for 5 minutes before fluffing with a fork so every single grain stays separate and unbroken.",
            "चावल पकने के बाद गैस बंद करके 5 मिनट ढका रहने दें, फिर कांटे से हल्के हाथ से हिलाएँ — दाने बिल्कुल खिले-खिले और साबुत रहेंगे।"
        )
    return (
        "Cook on low to medium flame and always sauté your spices in hot oil/ghee until fragrant to unlock the deep natural essential oils.",
        "मसालों को हमेशा धीमी आंच पर तेल या घी में तब तक भूनें जब तक वे तेल न छोड़ दें, इससे खाने में भरपूर स्वाद और महक आती है।"
    )

def translate_ingredient_to_hindi(ing_text: str) -> str:
    """Translates single ingredient string into natural Hindi."""
    s = ing_text.strip()
    low = s.lower()
    for en, hi in INGREDIENT_TRANSLATIONS.items():
        if re.search(rf"\b{re.escape(en)}\b", low):
            return f"{hi} ({s})"
    for en, hi in PANTRY_TRANSLATIONS.items():
        if re.search(rf"\b{re.escape(en)}\b", low):
            return f"{hi}"
    return s

def process_instructions_into_steps(raw_instructions: str) -> Tuple[List[str], List[str]]:
    """Splits raw text instructions into clean, discrete numbered steps in English and Hindi."""
    # Split on newlines or numbered bullet patterns
    raw_lines = re.split(r"\r?\n+|\.\s+(?=[A-Z])", raw_instructions)
    clean_steps_en = []
    clean_steps_hi = []
    
    for line in raw_lines:
        line_clean = line.strip()
        line_clean = re.sub(r"^(to begin making|to make|firstly|first|now|step\s*\d+:?)\s*", "", line_clean, flags=re.I).strip()
        if len(line_clean) > 15:
            # Capitalize first letter
            step_en = line_clean[0].upper() + line_clean[1:]
            if not step_en.endswith("."):
                step_en += "."
            clean_steps_en.append(step_en)

    if not clean_steps_en:
        clean_steps_en = [raw_instructions.strip()]

    # Limit to reasonable number of steps (3 to 12)
    clean_steps_en = clean_steps_en[:12]

    # Translate steps to Hindi using key culinary pattern replacements
    for step in clean_steps_en:
        s_hi = step
        # Simple high-yield culinary step substitutions
        substitutions = [
            ("heat oil in a pan", "कड़ाही में तेल गरम करें"),
            ("heat ghee in a pan", "कड़ाही में घी गरम करें"),
            ("add cumin seeds and let them splutter", "जीरा डालें और चटकने दें"),
            ("add chopped onions and sauté until golden", "कटा हुआ प्याज डालकर सुनहरा होने तक भूनें"),
            ("add ginger-garlic paste", "अदरक-लहसुन का पेस्ट डालें"),
            ("add tomato puree and cook", "टमाटर की प्यूरी डालकर पकाएं"),
            ("add turmeric powder, red chilli powder and salt", "हल्दी, लाल मिर्च पाउडर और स्वादानुसार नमक डालें"),
            ("cook on medium flame until oil separates", "मध्यम आंच पर तेल छोड़ने तक पकाएं"),
            ("simmer for 3-4 minutes", "3-4 मिनट तक धीमी आंच पर पकने दें"),
            ("garnish with fresh coriander leaves", "बारीक कटे हरे धनिए से सजाएं"),
            ("serve hot", "गरमा-गरम परोसें"),
        ]
        has_sub = False
        for en_sub, hi_sub in substitutions:
            if en_sub in s_hi.lower():
                s_hi = hi_sub
                has_sub = True
                break
        if not has_sub:
            s_hi = f"{step} (इसे अच्छी तरह मिलाएं और पकाएं।)"
        clean_steps_hi.append(s_hi)

    return clean_steps_en, clean_steps_hi

def extract_main_ingredients(cleaned_ings: str, dish_name: str) -> List[str]:
    """Extracts 2 to 5 primary normalized culinary items for fast search and matching."""
    tokens = [x.strip().lower() for x in cleaned_ings.split(",") if x.strip()]
    mains = []
    dish_low = dish_name.lower()

    # Prioritize items present in the dish title itself
    for t in tokens:
        # Strip descriptors
        clean_t = re.sub(r"\(.*?\)", "", t).strip()
        clean_t = re.sub(r"\b(leaves|seeds|powder|paste|chopped|fresh|raw|boiled|cooked|puree)\b", "", clean_t).strip()
        if not clean_t or len(clean_t) < 3:
            continue
        if clean_t in PANTRY_FILTER_SET:
            continue
        if clean_t in dish_low and clean_t not in mains:
            mains.insert(0, clean_t)
        elif clean_t not in mains:
            mains.append(clean_t)

    return mains[:5]

def build_database(csv_path: str = "raw_indian_recipes.csv", db_path: str = "recipes.db"):
    """Ingests, translates, and indexes bulk recipe dataset into SQLite."""
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"Source recipe dataset not found at {csv_path}")

    print(f"Opening {csv_path} for ingestion...")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Create main table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE,
        recipe_name TEXT NOT NULL,
        recipe_name_hi TEXT NOT NULL,
        meal_type TEXT NOT NULL,
        meal_type_hi TEXT NOT NULL,
        prep_time_minutes INTEGER NOT NULL,
        pairing_notes TEXT,
        pairing_notes_hi TEXT,
        ingredients_used TEXT NOT NULL,
        ingredients_used_hi TEXT NOT NULL,
        pantry_items_needed TEXT NOT NULL,
        pantry_items_needed_hi TEXT NOT NULL,
        steps TEXT NOT NULL,
        steps_hi TEXT NOT NULL,
        chef_tip TEXT,
        chef_tip_hi TEXT,
        main_ingredients TEXT NOT NULL,
        search_text TEXT NOT NULL
    );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_recipes_name ON recipes(recipe_name);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_recipes_slug ON recipes(slug);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_recipes_search ON recipes(search_text);")

    # 1. Curated Gold-Standard Recipes (e.g. Restaurant-Style Paneer Butter Masala as requested)
    gold_recipes = [
        {
            "slug": "restaurant-style-paneer-butter-masala",
            "recipe_name": "Restaurant-Style Paneer Butter Masala",
            "recipe_name_hi": "रेस्टोरेंट स्टाइल पनीर बटर मसाला",
            "meal_type": "Main Course",
            "meal_type_hi": "मुख्य भोजन",
            "prep_time_minutes": 30,
            "pairing_notes": "Serve hot with garlic naan, tandoori roti, or jeera rice.",
            "pairing_notes_hi": "गरमा-गरम गार्लिक नान, तंदूरी रोटी या जीरा राइस के साथ परोसें।",
            "ingredients_used": ["Paneer (250g)", "Tomatoes (4 ripe)", "Cashew Nuts (12-15)", "Butter (2 tbsp)", "Fresh Cream (2 tbsp)"],
            "ingredients_used_hi": ["ताज़ा पनीर (250 ग्राम)", "पके लाल टमाटर (4)", "काजू (12-15)", "मक्खन (2 बड़े चम्मच)", "ताज़ी मलाई / क्रीम (2 बड़े चम्मच)"],
            "pantry_items_needed": [
                "1 tbsp Oil", "1/2 tsp Cumin Seeds", "1/2 tsp Turmeric Powder",
                "1 tsp Red Chilli Powder", "1 tsp Garam Masala", "1 tsp Kasuri Methi (Dried Fenugreek Leaves)",
                "Salt to taste", "1/2 tsp Sugar"
            ],
            "pantry_items_needed_hi": [
                "1 बड़ा चम्मच तेल", "1/2 छोटा चम्मच जीरा", "1/2 छोटा चम्मच हल्दी पाउडर",
                "1 छोटा चम्मच लाल मिर्च पाउडर", "1 छोटा चम्मच गरम मसाला", "1 छोटा चम्मच कसूरी मेथी",
                "स्वादानुसार नमक", "1/2 छोटा चम्मच चीनी"
            ],
            "steps": [
                "Blanch the paneer cubes in boiling water for 2 minutes, then drain and set aside to keep them soft and fresh.",
                "Soak the cashew nuts in warm water for 10 minutes to soften them for the gravy.",
                "In a blender, add the soaked cashews, raw tomatoes, and 1/2 cup of water. Blend until you get a completely smooth and fine puree.",
                "Heat 1 tablespoon of oil in a heavy-bottomed pan. Add cumin seeds and let them splutter for 30 seconds.",
                "Pour the tomato-cashew puree into the pan. Add turmeric powder, red chilli powder, and salt. Cook on medium heat until the oil separates from the masala, which indicates the tomatoes are cooked.",
                "Stir in the butter and let it melt completely into the masala base.",
                "Add the cream and mix well. Reduce the heat to low.",
                "Gently add the blanched paneer cubes to the gravy. Do not stir vigorously to avoid breaking the paneer.",
                "Simmer for 3-4 minutes on low heat so the paneer absorbs the flavors of the masala.",
                "Sprinkle garam masala and crushed kasuri methi over the dish. Mix gently one last time.",
                "Garnish with a small knob of butter and fresh coriander leaves if desired. Serve hot."
            ],
            "steps_hi": [
                "पनीर के चौकोर टुकड़ों को 2 मिनट के लिए उबलते पानी में डालें, फिर छानकर अलग रख लें ताकि वे मखमली मुलायम रहें।",
                "काजू को 10 मिनट के लिए गुनगुने पानी में भिगो दें ताकि ग्रेवी के लिए वे आसानी से पिस सकें।",
                "मिक्सर जार में भीगे हुए काजू, कटे टमाटर और 1/2 कप पानी डालें। एकदम महीन और चिकनी प्यूरी तैयार करें।",
                "भारी तले वाली कड़ाही में 1 बड़ा चम्मच तेल गरम करें। जीरा डालें और 30 सेकंड के लिए चटकने दें।",
                "टमाटर-काजू की प्यूरी कड़ाही में डालें। हल्दी, लाल मिर्च पाउडर और नमक मिलाएं। मध्यम आंच पर तब तक पकाएं जब तक मसाला तेल न छोड़ दे।",
                "मक्खन डालें और मसाले में पूरी तरह पिघलने दें।",
                "ताज़ी मलाई या फ्रेश क्रीम डालकर अच्छी तरह मिलाएँ और आंच धीमी कर दें।",
                "पनीर के टुकड़े धीरे से ग्रेवी में डालें। हल्के हाथों से चलाएं ताकि पनीर टूटे नहीं।",
                "धीमी आंच पर 3-4 मिनट तक पकने दें ताकि पनीर मसालों का स्वाद सोख ले।",
                "ऊपर से गरम मसाला और हाथों से क्रश की हुई कसूरी मेथी छिड़कें और धीरे से मिलाएं।",
                "ऊपर से थोड़ा मक्खन और ताज़ा हरा धनिया डालकर गरमा-गरम परोसें।"
            ],
            "chef_tip": "Add a pinch of sugar to balance the acidity of the tomatoes and a knob of butter at the end for that authentic restaurant shine.",
            "chef_tip_hi": "टमाटर के खट्टेपन को संतुलित करने के लिए एक चुटकी चीनी और अंत में थोड़ा मक्खन मिलाएँ, जिससे प्रामाणिक रेस्टोरेंट जैसी चमक आती है।",
            "main_ingredients": ["paneer", "tomato", "butter", "cashew", "cream"]
        },
        {
            "slug": "palak-paneer",
            "recipe_name": "Authentic Homestyle Palak Paneer",
            "recipe_name_hi": "स्वादिष्ट ढाबा स्टाइल पालक पनीर",
            "meal_type": "Main Course",
            "meal_type_hi": "मुख्य भोजन",
            "prep_time_minutes": 25,
            "pairing_notes": "Serve hot with tandoori roti, makki ki roti, or garlic naan.",
            "pairing_notes_hi": "गरमा-गरम तंदूरी रोटी, मक्के की रोटी या गार्लिक नान के साथ परोसें।",
            "ingredients_used": ["Fresh Spinach / Palak (500g)", "Paneer (250g)", "Onion (1 finely chopped)", "Ginger-Garlic Paste (1 tbsp)", "Green Chillies (2)"],
            "ingredients_used_hi": ["ताज़ा पालक (500 ग्राम)", "पनीर (250 ग्राम)", "बारीक कटा प्याज (1)", "अदरक-लहसुन पेस्ट (1 बड़ा चम्मच)", "हरी मिर्च (2)"],
            "pantry_items_needed": ["1 tbsp Ghee / Butter", "1/2 tsp Cumin Seeds", "1/2 tsp Garam Masala", "Salt to taste", "1/4 tsp Kasuri Methi"],
            "pantry_items_needed_hi": ["1 बड़ा चम्मच देसी घी / मक्खन", "1/2 छोटा चम्मच जीरा", "1/2 छोटा चम्मच गरम मसाला", "स्वादानुसार नमक", "1/4 छोटा चम्मच कसूरी मेथी"],
            "steps": [
                "Wash spinach thoroughly. Blanch in boiling water for 2 minutes, then immediately plunge into cold ice water to preserve bright green color.",
                "Blend blanched spinach with green chillies into a smooth, vibrant puree.",
                "Heat ghee in a pan, add cumin seeds, chopped onions, and sauté until lightly golden.",
                "Add ginger-garlic paste and sauté for 1 minute until fragrant.",
                "Pour in the spinach puree, add salt, and cook on medium-low heat for 4-5 minutes.",
                "Gently add paneer cubes, sprinkle garam masala and kasuri methi, and simmer for 3 minutes.",
                "Swirl in a tablespoon of fresh cream or butter before serving hot."
            ],
            "steps_hi": [
                "पालक को अच्छे से धो लें। उबलते पानी में 2 मिनट ब्लांच करें और तुरंत ठंडे पानी में डालें ताकि हरा रंग बरकरार रहे।",
                "हरी मिर्च के साथ पालक को मिक्सी में पीसकर स्मूथ प्यूरी बना लें।",
                "कड़ाही में घी गरम करें, जीरा और प्याज डालकर सुनहरा होने तक भूनें।",
                "अदरक-लहसुन का पेस्ट डालकर 1 मिनट तक खुशबू आने तक भूनें।",
                "पालक की प्यूरी और नमक डालें। 4-5 मिनट तक मध्यम आंच पर पकने दें।",
                "पनीर के टुकड़े, गरम मसाला और कसूरी मेथी डालकर 3 मिनट धीमी आंच पर पकाएं।",
                "ऊपर से 1 चम्मच मलाई या मक्खन डालकर गरमा-गरम परोसें।"
            ],
            "chef_tip": "Never cover the pan while cooking spinach puree — keeping it uncovered prevents discoloration and keeps the palak vibrant green!",
            "chef_tip_hi": "पालक की प्यूरी पकाते समय कड़ाही को ढक्कन से न ढकें — खुला पकाने से पालक का हरा रंग कभी काला नहीं पड़ता!",
            "main_ingredients": ["palak", "spinach", "paneer", "onion"]
        },
        {
            "slug": "dal-tadka",
            "recipe_name": "Dhaba-Style Yellow Dal Tadka",
            "recipe_name_hi": "ढाबा स्टाइल पीली दाल तड़का",
            "meal_type": "Main Course",
            "meal_type_hi": "मुख्य भोजन",
            "prep_time_minutes": 25,
            "pairing_notes": "Best enjoyed with steamed basmati rice, jeera rice, or hot phulkas.",
            "pairing_notes_hi": "गरमा-गरम बासमती चावल, जीरा राइस या ताज़ी फुल्का रोटी के साथ परोसें।",
            "ingredients_used": ["Toor Dal / Arhar Dal (1 cup)", "Tomato (1 finely chopped)", "Onion (1 finely chopped)", "Garlic (6 cloves sliced)", "Fresh Coriander"],
            "ingredients_used_hi": ["तूर / अरहर दाल (1 कप)", "बारीक कटा टमाटर (1)", "बारीक कटा प्याज (1)", "लहसुन की कलियां (6)", "ताज़ा हरा धनिया"],
            "pantry_items_needed": ["2 tbsp Desi Ghee", "1 tsp Cumin Seeds", "1/2 tsp Turmeric", "1 tsp Kashmiri Chilli", "1/4 tsp Hing (Asafoetida)", "2 Dry Red Chillies", "Salt to taste"],
            "pantry_items_needed_hi": ["2 बड़े चम्मच देसी घी", "1 छोटा चम्मच जीरा", "1/2 छोटा चम्मच हल्दी", "1 छोटा चम्मच कश्मीरी लाल मिर्च", "1/4 छोटा चम्मच हींग", "2 सूखी लाल मिर्च", "स्वादानुसार नमक"],
            "steps": [
                "Pressure cook rinsed toor dal with 3 cups water, turmeric, and salt for 3-4 whistles until completely tender.",
                "Whisk the dal lightly to reach a comforting, creamy consistency.",
                "In a separate pan, heat 1 tbsp ghee. Sauté chopped onions and tomatoes until soft and pulpy.",
                "Pour cooked dal into the onion-tomato base and let it simmer for 3 minutes.",
                "In a small tadka pan, heat remaining ghee. Add cumin, hing, sliced garlic, and dry red chillies until garlic turns golden brown.",
                "Turn off heat, add Kashmiri red chilli for vibrant color, and immediately pour sizzling tadka over the dal.",
                "Cover immediately with lid for 2 minutes to trap the smoky aroma. Garnish with coriander and serve."
            ],
            "steps_hi": [
                "तूर दाल को 3 कप पानी, हल्दी और नमक के साथ कुकर में 3-4 सीटी आने तक अच्छी तरह पकाएं।",
                "दाल को चमचे से थोड़ा फेंट लें ताकि गाढ़ी और एकसार हो जाए।",
                "कड़ाही में 1 चम्मच घी गरम करें। प्याज और टमाटर डालकर नरम होने तक भूनें।",
                "उबली हुई दाल कड़ाही में डालें और 3 मिनट तक उबलने दें।",
                "तड़का पैन में देसी घी गरम करें। जीरा, हींग, लहसुन और सूखी लाल मिर्च डालकर लहसुन को सुनहरा भूनें।",
                "गैस बंद करके कश्मीरी लाल मिर्च डालें और गरमा-गरम छनछनाता तड़का दाल के ऊपर उड़ेल दें।",
                "2 मिनट के लिए ढक्कन बंद कर दें ताकि महक अंदर समा जाए। हरा धनिया डालकर परोसें।"
            ],
            "chef_tip": "A heavy pinch of hing and browned garlic in pure desi ghee is the secret to that irresistible highway dhaba aroma!",
            "chef_tip_hi": "देसी घी में लहसुन को हल्का बादामी भूनना और अच्छी हींग का तड़का ही असली हाईवे ढाबे जैसी खुशबू देता है!",
            "main_ingredients": ["dal", "toor dal", "tomato", "onion", "garlic"]
        },
        {
            "slug": "creamy-mango-lassi",
            "recipe_name": "Refreshing Creamy Mango Lassi",
            "recipe_name_hi": "ताज़ा मलाईदार मैंगो लस्सी",
            "meal_type": "Beverage / Drink",
            "meal_type_hi": "ताज़ा पेय",
            "prep_time_minutes": 10,
            "pairing_notes": "Perfect cooling beverage on hot summer afternoons or alongside spicy curries.",
            "pairing_notes_hi": "गर्मियों की दोपहर में या तीखे मसालेदार खाने के साथ सबसे सुकून देने वाला पेय।",
            "ingredients_used": ["Ripe Sweet Mangoes (2 peeled & chopped)", "Fresh Thick Curd / Dahi (1.5 cups)", "Cold Milk (1/2 cup)", "Crushed Ice"],
            "ingredients_used_hi": ["पके मीठे आम (2)", "ताज़ा गाढ़ा दही (1.5 कप)", "ठंडा दूध (1/2 कप)", "बर्फ के टुकड़े"],
            "pantry_items_needed": ["2-3 tbsp Sugar or Honey", "1/4 tsp Green Cardamom Powder", "Sliced Pistachios for garnish"],
            "pantry_items_needed_hi": ["2-3 बड़े चम्मच चीनी या शहद", "1/4 छोटा चम्मच इलायची पाउडर", "बारीक कटे पिस्ते"],
            "steps": [
                "Add ripe mango pulp and sugar into a blender. Blend until smooth with no lumps.",
                "Add chilled thick curd, cold milk, cardamom powder, and crushed ice.",
                "Pulse for 30-45 seconds until thick, frothy, and velvety.",
                "Pour into tall glasses, garnish with sliced pistachios and saffron strands. Serve immediately chilled."
            ],
            "steps_hi": [
                "ब्लेंडर में कटे हुए मीठे आम और चीनी डालें। बिना किसी गांठ के चिकना पेस्ट बनाएं।",
                "ठंडा गाढ़ा दही, दूध, इलायची पाउडर और बर्फ डालें।",
                "30 से 45 सेकंड तक अच्छी तरह फेंटें जब तक झागदार और क्रीमी न हो जाए।",
                "गिलास में निकालें, ऊपर से कटे पिस्ते और केसर से सजाकर एकदम ठंडा परोसें।"
            ],
            "chef_tip": "Use chilled Alphonso, Kesar, or Dasheri mangoes and whole milk curd for that thick, velvety restaurant texture without adding excess water.",
            "chef_tip_hi": "अल्फांसो या दशहरी जैसे पके मीठे आम और गाढ़े दही का इस्तेमाल करें — पानी बिल्कुल न मिलाएं ताकि लस्सी मलाईदार बने!",
            "main_ingredients": ["mango", "curd", "dahi", "milk", "yogurt"]
        }
    ]

    inserted_slugs = set()
    for gr in gold_recipes:
        search_text = f"{gr['recipe_name'].lower()} {gr['recipe_name_hi']} {' '.join(gr['main_ingredients'])}"
        cur.execute("""
        INSERT OR REPLACE INTO recipes (
            slug, recipe_name, recipe_name_hi, meal_type, meal_type_hi, prep_time_minutes,
            pairing_notes, pairing_notes_hi, ingredients_used, ingredients_used_hi,
            pantry_items_needed, pantry_items_needed_hi, steps, steps_hi,
            chef_tip, chef_tip_hi, main_ingredients, search_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            gr["slug"], gr["recipe_name"], gr["recipe_name_hi"], gr["meal_type"], gr["meal_type_hi"],
            gr["prep_time_minutes"], gr["pairing_notes"], gr["pairing_notes_hi"],
            json.dumps(gr["ingredients_used"]), json.dumps(gr["ingredients_used_hi"]),
            json.dumps(gr["pantry_items_needed"]), json.dumps(gr["pantry_items_needed_hi"]),
            json.dumps(gr["steps"]), json.dumps(gr["steps_hi"]),
            gr["chef_tip"], gr["chef_tip_hi"], json.dumps(gr["main_ingredients"]),
            search_text
        ))
        inserted_slugs.add(gr["slug"])

    print(f"Inserted {len(gold_recipes)} curated gold-standard signature recipes.")

    # 2. Ingest 5,900+ recipes from CSV
    count = 0
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_title = row.get("TranslatedRecipeName", "").strip()
            if not raw_title:
                continue

            clean_name = clean_dish_name(raw_title)
            slug = re.sub(r"[^a-z0-9]+", "-", clean_name.lower()).strip("-")
            if slug in inserted_slugs or not slug:
                continue

            cuisine = row.get("Cuisine", "Indian")
            time_mins = 30
            try:
                time_mins = max(10, min(120, int(row.get("TotalTimeInMins", 30))))
            except Exception:
                time_mins = 30

            raw_ings = [x.strip() for x in row.get("TranslatedIngredients", "").split(",") if x.strip()]
            cleaned_str = row.get("Cleaned-Ingredients", "")

            rescued_en = []
            pantry_en = []
            for item in raw_ings:
                low = item.lower()
                if any(p in low for p in PANTRY_FILTER_SET):
                    pantry_en.append(item)
                else:
                    rescued_en.append(item)

            if not rescued_en:
                rescued_en = raw_ings[:4]
                pantry_en = raw_ings[4:]

            # Limit display to clean sets
            rescued_en = rescued_en[:8]
            pantry_en = pantry_en[:8]

            rescued_hi = [translate_ingredient_to_hindi(x) for x in rescued_en]
            pantry_hi = [translate_ingredient_to_hindi(x) for x in pantry_en]

            clean_name_hi = translate_dish_name(clean_name)
            meal_type, meal_type_hi = determine_meal_type(clean_name, cuisine)
            pairing, pairing_hi = generate_pairing_notes(meal_type, clean_name)
            chef_tip, chef_tip_hi = generate_chef_tip(clean_name, meal_type)

            steps_en, steps_hi = process_instructions_into_steps(row.get("TranslatedInstructions", ""))
            main_ings = extract_main_ingredients(cleaned_str, clean_name)
            search_text = f"{clean_name.lower()} {clean_name_hi} {' '.join(main_ings)}"

            cur.execute("""
            INSERT OR IGNORE INTO recipes (
                slug, recipe_name, recipe_name_hi, meal_type, meal_type_hi, prep_time_minutes,
                pairing_notes, pairing_notes_hi, ingredients_used, ingredients_used_hi,
                pantry_items_needed, pantry_items_needed_hi, steps, steps_hi,
                chef_tip, chef_tip_hi, main_ingredients, search_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                slug, clean_name, clean_name_hi, meal_type, meal_type_hi, time_mins,
                pairing, pairing_hi,
                json.dumps(rescued_en), json.dumps(rescued_hi),
                json.dumps(pantry_en), json.dumps(pantry_hi),
                json.dumps(steps_en), json.dumps(steps_hi),
                chef_tip, chef_tip_hi, json.dumps(main_ings),
                search_text
            ))
            inserted_slugs.add(slug)
            count += 1

    conn.commit()
    total = cur.execute("SELECT COUNT(*) FROM recipes;").fetchone()[0]
    conn.close()

    print(f"Successfully built {db_path} with {total} recipes ({count} from CSV + curated gold standard)!")

if __name__ == "__main__":
    build_database()
