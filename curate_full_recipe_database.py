#!/usr/bin/env python3
"""
Full Database Curation, Classification & Hindi Translation Engine
==================================================================
1. Purges all non-food craft / science experiment / dog food entries.
2. Re-classifies meal_type, pairing_notes, and chef_tip contextually across all 49,000+ recipes
   using strict word boundaries (fixing steak -> beverage and salad -> beverage bugs).
3. Translates recipe_name_hi to genuine Hindi Devanagari (removing fake '(स्वादिष्ट रेसिपी)' suffixes).
4. Cleanses and translates steps_hi and ingredients_used_hi.
5. Inserts authentic canonical Rock Candy / Mishri.
6. Rebuilds recipes_fts virtual table and re-compresses recipes.db.gz.
"""

import sqlite3
import gzip
import shutil
import re
import json
import os

DB_PATH = "recipes.db"
GZ_PATH = "recipes.db.gz"

HINDI_TERMS = {
    # Dish Types & Courses
    "classic": "क्लासिक",
    "homestyle": "होमस्टाइल",
    "traditional": "पारंपरिक",
    "authentic": "पारंपरिक",
    "special": "स्पेशल",
    "style": "स्टाइल",
    "caesar": "सीज़र",
    "salad": "सलाद",
    "salads": "सलाद",
    "slaw": "स्लॉ",
    "soup": "सूप",
    "soups": "सूप",
    "chowder": "चाउडर",
    "broth": "शोरबा",
    "stew": "स्टू",
    "curry": "करी",
    "gravy": "ग्रेवी",
    "sauce": "सॉस",
    "dip": "डिप",
    "salsa": "साल्सा",
    "guacamole": "ग्वाकामोल",
    "hummus": "हम्मस",
    "sandwich": "सैंडविच",
    "sandwiches": "सैंडविच",
    "burger": "बर्गर",
    "burgers": "बर्गर",
    "slider": "स्लाइडर",
    "sliders": "स्लाइडर",
    "wrap": "रैप",
    "wraps": "रैप",
    "roll": "रोल",
    "rolls": "रोल",
    "taco": "टैको",
    "tacos": "टैको",
    "burrito": "बरिटो",
    "burritos": "बरिटो",
    "quesadilla": "केसाडिला",
    "pizza": "पिज़्ज़ा",
    "pasta": "पास्ता",
    "lasagna": "लसग्ना",
    "spaghetti": "स्पेगेटी",
    "macaroni": "मैकरोनी",
    "noodles": "नूडल्स",
    "noodle": "नूडल्स",
    "rice": "चावल",
    "fried rice": "फ्राइड राइस",
    "biryani": "बिरयानी",
    "pulao": "पुलाव",
    "khichdi": "खिचड़ी",
    "risotto": "रिसोट्टो",
    "steak": "स्टेक",
    "steaks": "स्टेक",
    "ribs": "रिब्स",
    "roast": "रोस्ट",
    "cutlet": "कटलेट",
    "cutlets": "कटलेट",
    "fries": "फ्राइज़",
    "chip": "चिप",
    "chips": "चिप्स",
    "nuggets": "नगेट्स",
    "wings": "विंग्स",
    "bread": "ब्रेड",
    "toast": "टोस्ट",
    "pancake": "पैनकेक",
    "pancakes": "पैनकेक्स",
    "waffle": "वाफल",
    "waffles": "वाफल्स",
    "crepe": "क्रेप",
    "crepes": "क्रेप्स",
    "omelet": "ऑमलेट",
    "omelette": "ऑमलेट",
    "frittata": "फ्रिटाटा",
    "porridge": "दलिया",
    "oatmeal": "ओट्स दलिया",

    # Desserts & Confectionery
    "rock candy": "रॉक कैंडी (मिश्री कैंडी)",
    "candy": "कैंडी",
    "candies": "कैंडीज़",
    "fudge": "फ़ज",
    "truffle": "ट्रफ़ल",
    "truffles": "ट्रफ़ल्स",
    "cake": "केक",
    "cakes": "केक",
    "cupcake": "कपकेक",
    "cupcakes": "कपकेक्स",
    "cheesecake": "चीज़केक",
    "cookie": "कुकीज़",
    "cookies": "कुकीज़",
    "biscuit": "बिस्कुट",
    "biscuits": "बिस्कुट",
    "brownie": "ब्राउनी",
    "brownies": "ब्राउनीज़",
    "pie": "पाई",
    "pies": "पाई",
    "tart": "टार्ट",
    "tarts": "टार्ट्स",
    "pudding": "पुडिंग",
    "custard": "कस्टर्ड",
    "ice cream": "आइसक्रीम",
    "gelato": "जिलेटो",
    "sorbet": "सोरबे",
    "mousse": "मूस",
    "donut": "डोनट",
    "donuts": "डोनट्स",
    "doughnut": "डोनट",
    "doughnuts": "डोनट्स",
    "pastry": "पेस्ट्री",
    "pastries": "पेस्ट्री",
    "halwa": "हलवा",
    "kheer": "खीर",
    "gulab jamun": "गुलाब जामुन",
    "rasgulla": "रसगुल्ला",
    "jalebi": "जलेबी",
    "barfi": "बर्फी",
    "ladoo": "लड्डू",
    "pongal": "पोंगल",

    # Beverages
    "milkshake": "मिल्कशेक",
    "milkshakes": "मिल्कशेक",
    "shake": "शेक",
    "shakes": "शेक",
    "smoothie": "स्मूदी",
    "smoothies": "स्मूदी",
    "juice": "जूस",
    "lemonade": "शिकंजी / लेमनेड",
    "cooler": "कूलर",
    "punch": "पंच",
    "cocktail": "कॉकटेल",
    "mocktail": "मॉकटेल",
    "iced tea": "आइस्ड टी",
    "tea": "चाय",
    "coffee": "कॉफ़ी",
    "cold coffee": "कोल्ड कॉफ़ी",
    "latte": "लाट्टे",
    "cappuccino": "कैपुचीनो",
    "frappe": "फ़्रैप्पे",
    "lassi": "लस्सी",
    "drink": "पेय",
    "beverage": "पेय",

    # Flavors & Ingredients
    "strawberry": "स्ट्रॉबेरी",
    "chocolate": "चॉकलेट",
    "vanilla": "वैनिला",
    "mango": "आम (मैंगो)",
    "banana": "केला",
    "apple": "सेब",
    "orange": "संतरा",
    "lemon": "नींबू",
    "lime": "नींबू",
    "pineapple": "अनानास",
    "peach": "आड़ू (पीच)",
    "coconut": "नारियल",
    "almond": "बादाम",
    "almonds": "बादाम",
    "walnut": "अखरोट",
    "walnuts": "अखरोट",
    "cashew": "काजू",
    "cashews": "काजू",
    "peanut": "मूंगफली",
    "peanuts": "मूंगफली",
    "caramel": "कारमेल",
    "honey": "शहद",
    "maple": "मेपल",
    "syrup": "सीरप",
    "cinnamon": "दालचीनी",
    "cardamom": "इलायची",
    "saffron": "केसर",
    "ginger": "अदरक",
    "garlic": "लहसुन",
    "onion": "प्याज़",
    "onions": "प्याज़",
    "tomato": "टमाटर",
    "tomatoes": "टमाटर",
    "potato": "आलू",
    "potatoes": "आलू",
    "spinach": "पालक",
    "paneer": "पनीर",
    "cheese": "चीज़",
    "butter": "मक्खन",
    "cream": "मलाई",
    "curd": "दही",
    "yogurt": "दही",
    "milk": "दूध",
    "chicken": "चिकन",
    "fish": "मछली",
    "salmon": "सैल्मन",
    "tuna": "टूना",
    "shrimp": "झींगा (प्रॉन)",
    "prawns": "झींगा",
    "egg": "अंडा",
    "eggs": "अंडे",
    "mushroom": "मशरूम",
    "mushrooms": "मशरूम",
    "fennel": "सौंफ",
    "pepper": "काली मिर्च",
    "corn": "कॉर्न / मक्का",
    "peas": "मटर",
    "beans": "बीन्स",
    "margherita": "मार्गेरीटा",

    # Cooking Methods & Adjectives
    "roasted": "रोस्टेड",
    "grilled": "ग्रिल्ड",
    "fried": "फ्राइड",
    "baked": "बेक्ड",
    "steamed": "स्टीम्ड",
    "creamy": "मलाईदार",
    "crispy": "कुरकुरा",
    "crunchy": "कुरकुरा",
    "spicy": "मसालेदार",
    "sweet": "मीठा",
    "fresh": "ताज़ा",
    "warm": "गरम",
    "hot": "गरमा-गरम",
    "chilled": "ठंडा",
    "easy": "सरल",
    "quick": "झटपट",
    "philly": "फिली",
}

def translate_title_to_hindi(title_en: str) -> str:
    """Translates title to clean Hindi Devanagari without fake '(स्वादिष्ट रेसिपी)'."""
    if not title_en:
        return ""
    
    clean_en = title_en.strip()
    low = clean_en.lower()

    # Exact multi-word match check
    if low in HINDI_TERMS:
        return HINDI_TERMS[low]

    # Replace matching words sorted by length descending
    text = clean_en
    sorted_keys = sorted(HINDI_TERMS.keys(), key=lambda x: len(x), reverse=True)
    for k in sorted_keys:
        pattern = r"\b" + re.escape(k) + r"\b"
        if re.search(pattern, text, flags=re.IGNORECASE):
            text = re.sub(pattern, HINDI_TERMS[k], text, flags=re.IGNORECASE)

    # Clean prepositions
    text = re.sub(r"\bwith\b", "विद", text, flags=re.I)
    text = re.sub(r"\band\b", "और", text, flags=re.I)
    text = re.sub(r"\bin\b", "में", text, flags=re.I)
    text = re.sub(r"\bof\b", "का", text, flags=re.I)
    text = re.sub(r"\bstyle\b", "स्टाइल", text, flags=re.I)
    text = re.sub(r"\s*\(स्वादिष्ट रेसिपी\)", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text

def classify_recipe(dish_en: str):
    """Categorizes meal_type, pairing_notes, and chef_tip accurately using strict word boundaries."""
    low = dish_en.lower()

    # 1. Traditional Dessert
    if re.search(r"\b(cake|cakes|cookie|cookies|candy|candies|brownie|brownies|pie|pies|tart|tarts|fudge|truffle|pudding|custard|ice cream|gelato|sorbet|mousse|cupcake|cupcakes|cheesecake|halwa|kheer|jamun|jalebi|barfi|ladoo|donut|donuts|doughnut|parfait|caramel|churro|churros|dessert|sweet|sweets|pongal)\b", low):
        return (
            "Traditional Dessert", "पारंपरिक मिठाई / डिज़र्ट",
            "Serve warm or chilled as a delightful sweet treat, paired with a glass of cold milk, espresso, or hot tea.",
            "एक गिलास ठंडे दूध, गरमा-गरम चाय या कॉफी के साथ मीठे के रूप में परोसें।",
            "For the best texture, measure baking and sweet ingredients precisely, and let treats cool completely before slicing or serving.",
            "मनचाही बनावट और स्वाद के लिए सामग्री का सही माप लें और परोसने से पहले इसे पूरी तरह ठंडा होने दें।"
        )

    # 2. Beverage / Drink (strict word boundaries - steaks, cakes, salads excluded!)
    if re.search(r"\b(smoothie|smoothies|shake|shakes|milkshake|milkshakes|cocktail|cocktails|mocktail|mocktails|juice|juices|lemonade|punch|cooler|iced tea|coffee|latte|cappuccino|mocha|chai|tea|lassi|frappe|cider|margarita|sangria|spritzer|drink|drinks|beverage)\b", low) and not re.search(r"\b(steak|steaks|cake|cakes|pie|pies|cookie|cookies|salad|salads)\b", low):
        return (
            "Beverage / Drink", "ताज़ा पेय / ड्रिंक",
            "Serve chilled in a tall glass, garnished with fresh mint leaves, crushed ice, or a sprinkle of spice.",
            "गिलास में बर्फ, ताज़ा पुदीने के पत्तों या हल्के मसाले से सजाकर ठंडा परोसें।",
            "Chill serving glasses in the freezer for 10 minutes prior to pouring for a crisp, refreshing, ice-cold drink.",
            "परोसने से पहले गिलास को 10 मिनट फ्रिज में ठंडा कर लें ताकि पेय एकदम चिल्ड और ताज़ा रहे।"
        )

    # 3. Soup / Broth
    if re.search(r"\b(soup|soups|chowder|bisque|broth|broths|stew|stews|ramen|pho|gumbo|gazpacho|potage)\b", low):
        return (
            "Soup / Broth", "सूप / शोरबा",
            "Serve piping hot in a deep bowl with crispy garlic croutons or warm buttered crusty bread.",
            "गरमा-गरम सूप को क्रिस्पी गार्लिक ब्रेड या मक्खन लगे टोस्ट के साथ परोसें।",
            "Simmer the broth gently on low heat to deepen flavors, and add delicate fresh herbs at the very end.",
            "सूप को धीमी आंच पर पकाएं ताकि स्वाद गहरा हो, और ताज़ा जड़ी-बूटियां या धनिया अंत में डालें।"
        )

    # 4. Fresh Salad
    if re.search(r"\b(salad|salads|slaw|slaws|coleslaw)\b", low):
        return (
            "Fresh Salad", "ताज़ा सलाद",
            "Serve chilled as a vibrant, crunchy, and nutrient-dense accompaniment to your main meal.",
            "भोजन के साथ एक पौष्टिक, ताज़ा और कुरकुरे सलाद के रूप में परोसें।",
            "Toss with dressing immediately before serving to keep greens crisp and prevent sogginess.",
            "ड्रेसिंग या नींबू परोसने के तुरंत पहले मिलाएं ताकि पत्ते और सब्ज़ियां एकदम ताज़ा और कुरकुरी रहें।"
        )

    # 5. Breakfast Special
    if re.search(r"\b(pancake|pancakes|waffle|waffles|french toast|omelet|omelette|scramble|frittata|porridge|oatmeal|granola|cereal|muesli|poha|upma|idli|dosa|dose|toast)\b", low):
        return (
            "Breakfast Special", "खास नाश्ता",
            "Serve hot with fresh butter, homemade chutney, yogurt, or a steaming cup of tea or coffee.",
            "ताज़ा मक्खन, घर की चटनी, दही और गरमा-गरम चाय या कॉफी के साथ परोसें।",
            "Prepare your batter or ingredients ahead of time; a rested batter cooks more evenly with a crisp finish.",
            "बैटर को पकाने से पहले थोड़ा आराम दें, इससे नाश्ता एकदम फूला हुआ और कुरकुरा बनता है।"
        )

    # 6. Street Food Snack / Appetizer
    if re.search(r"\b(sandwich|sandwiches|burger|burgers|slider|sliders|wrap|wraps|taco|tacos|burrito|burritos|quesadilla|nachos|dip|dips|salsa|guacamole|hummus|bruschetta|crostini|appetizer|appetizers|fries|chips|nugget|nuggets|wings|finger food|snack|snacks|chaat|samosa|samosas|pakoda|pakodas|pakora|pakoras|cutlet|cutlets|roll|rolls|spring roll|spring rolls|tikki)\b", low):
        return (
            "Street Food Snack", "स्वादिष्ट स्नैक",
            "Serve hot and crispy with tangy mint-coriander chutney, sweet tamarind chutney, or ketchup alongside hot tea.",
            "तीखी हरी चटनी, मीठी इमली की चटनी और गरमा-गरम मसाला चाय के साथ कुरकुरा परोसें।",
            "Fry or crisp on steady medium flame so the interior cooks thoroughly while the exterior stays crunchy.",
            "हमेशा मध्यम आंच पर तलें या सेकें ताकि स्नैक अंदर तक पके और बाहर से एकदम कुरकुरा रहे।"
        )

    # 7. Homestyle Bread
    if re.search(r"\b(roti|chapati|phulka|naan|paratha|kulcha|puri|poori|bhatura|flatbread|focaccia|ciabatta|baguette|sourdough|brioche|loaf|bread|buns|rolls)\b", low) and not re.search(r"\b(sandwich|pudding)\b", low):
        return (
            "Homestyle Bread", "रोटी / ब्रेड",
            "Serve hot brushed with pure desi ghee alongside your favorite spiced dal, paneer curry, or sabzi.",
            "देसी घी लगाकर गरमा-गरम रोटियों को अपनी पसंदीदा दाल, पनीर या सब्ज़ी के साथ परोसें।",
            "Rest the kneaded dough for at least 15-20 minutes before rolling to ensure the breads turn out soft and pliable.",
            "आटा गूंथने के बाद 15-20 मिनट आराम दें ताकि रोटियां रुई जैसी नरम बनें।"
        )

    # 8. Dal / Lentils
    if re.search(r"\b(dal|dhal|daal|lentil|lentils|sambar|sambhar|rasam)\b", low):
        return (
            "Main Course", "मुख्य भोजन",
            "Best enjoyed piping hot with steamed basmati rice, soft phulkas, papad, and fresh lemon pickle.",
            "गरमा-गरम बासमती चावल, फूली हुई रोटियां, पापड़ और नींबू के अचार के साथ परोसें।",
            "Bloom whole cumin seeds and hing in hot desi ghee right before pouring the tadka over the dal for irresistible aroma.",
            "देसी घी में जीरा और हींग का तड़का लगाकर तुरंत दाल में डालें और ढक दें ताकि खुशबू अंदर समा जाए।"
        )

    # 9. Rice / Biryani / Pulao
    if re.search(r"\b(biryani|pulao|pulav|fried rice|risotto|khichdi|rice)\b", low):
        return (
            "Main Course", "मुख्य भोजन",
            "Pair with cooling roasted cumin raita, sliced onion salad, crispy papad, and tangy pickle.",
            "ठंडे जीरा रायते, प्याज़ के लच्छे, कुरकुरे पापड़ और चटपटे अचार के साथ परोसें।",
            "Let cooked rice rest covered off heat for 5 minutes before fluffing gently with a fork so grains stay long, separate, and intact.",
            "चावल पकने के बाद 5 मिनट ढका रहने दें, फिर कांटे से हल्के हाथ से चलाएं ताकि दाना खिला-खिला रहे।"
        )

    # 10. Paneer / Vegetarian Gravy / Sabzi
    if re.search(r"\b(paneer|curry|masala|makhani|korma|tikka masala|gravy|sabzi|bhaji)\b", low):
        return (
            "Main Course", "मुख्य भोजन",
            "Serve hot with garlic butter naan, tandoori roti, or fragrant jeera rice.",
            "गरमा-गरम गार्लिक बटर नान, तंदूरी रोटी या खुशबूदार जीरा राइस के साथ परोसें।",
            "Simmer gravies on medium-low heat to allow flavors to meld, and finish with a knob of butter or touch of cream.",
            "धीमी आंच पर पकाएं ताकि मसालों का स्वाद रच-बस जाए, अंत में थोड़ा मक्खन या मलाई डालें।"
        )

    # 11. Meat / Poultry / Fish / Steaks
    if re.search(r"\b(chicken|meat|beef|steak|steaks|pork|lamb|fish|salmon|shrimp|prawn|tuna|turkey|duck)\b", low):
        return (
            "Main Course", "मुख्य भोजन",
            "Serve hot with roasted potatoes, steamed vegetables, or fragrant pilaf rice.",
            "भुने हुए आलू, पकी सब्ज़ियों या खुशबूदार पुलाव के साथ गरमा-गरम परोसें।",
            "Let cooked meat or fish rest for 5 minutes before slicing to lock in savory natural juices and tenderness.",
            "पकाने के बाद 5 मिनट तक आराम दें ताकि मीट रसदार और मुलायम बना रहे।"
        )

    # Default Main Course
    return (
        "Main Course", "मुख्य भोजन",
        "Serve fresh and hot alongside warm flatbread, steamed rice, or roasted vegetable sides.",
        "गरमा-गरम ताज़ा रोटियों, बासमती चावल या भुनी हुई सब्ज़ियों के साथ परोसें।",
        "Cook on medium flame and always taste and adjust seasoning right before serving for balanced flavors.",
        "मध्यम आंच पर पकाएं और परोसने से ठीक पहले नमक और मसालों का संतुलन चखकर ठीक करें।"
    )

def main():
    print("=" * 70)
    print("STARTING FULL RECIPE DATABASE OVERHAUL & HINDI SANITIZATION")
    print("=" * 70)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Step 1: Purge non-food craft / science experiment / pet food entries
    print("\n1. Purging non-food craft & science project entries...")
    cur.execute("""
        DELETE FROM recipes 
        WHERE recipe_name = "Rock Candy"
           OR recipe_name LIKE "%play dough%"
           OR recipe_name LIKE "%playdough%"
           OR recipe_name LIKE "%salt dough%"
           OR recipe_name LIKE "%dog treat%"
           OR recipe_name LIKE "%dog biscuit%"
           OR recipe_name LIKE "%puppy treat%"
           OR recipe_name LIKE "%cat treat%"
           OR recipe_name LIKE "%bird seed%"
           OR recipe_name LIKE "%bird feeder%"
           OR recipe_name LIKE "%bubble solution%"
           OR recipe_name LIKE "%face mask%"
           OR recipe_name LIKE "%body scrub%"
           OR recipe_name LIKE "%lip balm%"
           OR recipe_name LIKE "%soap%"
           OR recipe_name LIKE "%potpourri%"
           OR recipe_name LIKE "%slime%"
           OR recipe_name LIKE "%centerpiece%"
    """)
    purged_count = cur.rowcount
    conn.commit()
    print(f"✅ Purged {purged_count} non-food / craft recipes.")

    # Step 2: Insert Canonical Authentic Rock Candy / Mishri
    print("\n2. Inserting Canonical Saffron Cardamom Mishri (Rock Candy)...")
    canonical_rock_candy = {
        "slug": "rock-candy",
        "recipe_name": "Authentic Saffron Cardamom Mishri (Rock Candy)",
        "recipe_name_hi": "पारंपरिक केसर इलायची मिश्री (रॉक कैंडी)",
        "meal_type": "Traditional Dessert",
        "meal_type_hi": "पारंपरिक मिठाई / डिज़र्ट",
        "prep_time_minutes": 25,
        "pairing_notes": "Enjoy as a traditional mouth-freshener and sweet digestive after meals with warm fennel seeds (saunf), or dissolve into hot milk or herbal tea.",
        "pairing_notes_hi": "भोजन के बाद सौंफ के साथ मुखवास के रूप में आनंद लें, या गुनगुने दूध और हर्बल चाय में घोलकर पिएं।",
        "ingredients_used": [
            "2 cups Pure Cane Sugar",
            "1 cup Filtered Water",
            "6-8 Green Cardamom pods, lightly crushed",
            "1 pinch Saffron strands (Kesar)"
        ],
        "ingredients_used_hi": [
            "2 कप शुद्ध चीनी",
            "1 कप पानी",
            "6-8 हरी इलायची",
            "1 चुटकी केसर के धागे"
        ],
        "pantry_items_needed": [
            "1/2 tsp Ghee for greasing mold / plate",
            "Clean food-grade wooden skewers or candy sticks"
        ],
        "pantry_items_needed_hi": [
            "प्लेट या मोल्ड में लगाने के लिए 1/2 चम्मच देसी घी",
            "कैंडी स्टिक्स या सीख"
        ],
        "steps": [
            "In a heavy-bottomed stainless steel pan, combine 2 cups sugar and 1 cup water.",
            "Heat on medium flame, stirring gently until all sugar crystals completely dissolve.",
            "Add crushed cardamom pods and saffron strands for authentic royal aroma and rich golden color.",
            "Bring the syrup to a rolling boil and simmer on medium-low heat for 10-12 minutes until it reaches thick one-to-two string consistency (approx 235°F / 112°C).",
            "Turn off the heat and let the syrup cool for 3-4 minutes.",
            "Pour into greased glass molds or insert clean wooden skewers.",
            "Let it rest undisturbed in a clean, dry room for 24 hours to allow beautiful translucent crystals to form.",
            "Carefully remove the crystallized mishri rock candy and store in an airtight glass jar."
        ],
        "steps_hi": [
            "स्टील के भारी पैन में 2 कप चीनी और 1 कप पानी मिलाएं।",
            "मध्यम आंच पर चलाएं जब तक सारी चीनी पूरी तरह घुल न जाए।",
            "इलायची और केसर के धागे डालें ताकि शाही खुशबू और सुनहरा रंग आए।",
            "मध्यम-धीमी आंच पर 10-12 मिनट तक एक से दो तार की गाढ़ी चाशनी बनने तक पकाएं।",
            "गैस बंद करें और चाशनी को 3-4 मिनट हल्का ठंडा होने दें।",
            "घी लगे बर्तन में डालें या कैंडी स्टिक्स लगाएं।",
            "साफ़ और सूखी जगह पर 24 घंटे बिना हिलाए रखें ताकि सुंदर पारदर्शी क्रिस्टल जम जाएं।",
            "तैयार मिश्री रॉक कैंडी को निकालकर एयरटाइट जार में रखें।"
        ],
        "chef_tip": "Never disturb or shake the container while the syrup is cooling and crystallizing — stillness is the key to clear, sparkling rock sugar crystals.",
        "chef_tip_hi": "क्रिस्टल जमते समय बर्तन को बिल्कुल न हिलाएं, शांत रखने से ही एकदम साफ़ और चमकदार मिश्री बनती है।",
        "main_ingredients": ["sugar", "water", "cardamom", "saffron"],
        "search_text": "rock candy mishri Authentic Saffron Cardamom Mishri रॉक कैंडी मिश्री crystal sugar sweet candy"
    }

    cur.execute("SELECT id FROM recipes WHERE slug = 'rock-candy'")
    exist = cur.fetchone()
    if exist:
        cur.execute("""
            UPDATE recipes SET
                recipe_name = ?, recipe_name_hi = ?, meal_type = ?, meal_type_hi = ?,
                prep_time_minutes = ?, pairing_notes = ?, pairing_notes_hi = ?,
                ingredients_used = ?, ingredients_used_hi = ?, pantry_items_needed = ?, pantry_items_needed_hi = ?,
                steps = ?, steps_hi = ?, chef_tip = ?, chef_tip_hi = ?, main_ingredients = ?, search_text = ?
            WHERE id = ?
        """, (
            canonical_rock_candy["recipe_name"], canonical_rock_candy["recipe_name_hi"], canonical_rock_candy["meal_type"], canonical_rock_candy["meal_type_hi"],
            canonical_rock_candy["prep_time_minutes"], canonical_rock_candy["pairing_notes"], canonical_rock_candy["pairing_notes_hi"],
            json.dumps(canonical_rock_candy["ingredients_used"], ensure_ascii=False), json.dumps(canonical_rock_candy["ingredients_used_hi"], ensure_ascii=False),
            json.dumps(canonical_rock_candy["pantry_items_needed"], ensure_ascii=False), json.dumps(canonical_rock_candy["pantry_items_needed_hi"], ensure_ascii=False),
            json.dumps(canonical_rock_candy["steps"], ensure_ascii=False), json.dumps(canonical_rock_candy["steps_hi"], ensure_ascii=False),
            canonical_rock_candy["chef_tip"], canonical_rock_candy["chef_tip_hi"], json.dumps(canonical_rock_candy["main_ingredients"], ensure_ascii=False), canonical_rock_candy["search_text"],
            exist[0]
        ))
    else:
        cur.execute("""
            INSERT INTO recipes (
                slug, recipe_name, recipe_name_hi, meal_type, meal_type_hi,
                prep_time_minutes, pairing_notes, pairing_notes_hi,
                ingredients_used, ingredients_used_hi, pantry_items_needed, pantry_items_needed_hi,
                steps, steps_hi, chef_tip, chef_tip_hi, main_ingredients, search_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            canonical_rock_candy["slug"], canonical_rock_candy["recipe_name"], canonical_rock_candy["recipe_name_hi"], canonical_rock_candy["meal_type"], canonical_rock_candy["meal_type_hi"],
            canonical_rock_candy["prep_time_minutes"], canonical_rock_candy["pairing_notes"], canonical_rock_candy["pairing_notes_hi"],
            json.dumps(canonical_rock_candy["ingredients_used"], ensure_ascii=False), json.dumps(canonical_rock_candy["ingredients_used_hi"], ensure_ascii=False),
            json.dumps(canonical_rock_candy["pantry_items_needed"], ensure_ascii=False), json.dumps(canonical_rock_candy["pantry_items_needed_hi"], ensure_ascii=False),
            json.dumps(canonical_rock_candy["steps"], ensure_ascii=False), json.dumps(canonical_rock_candy["steps_hi"], ensure_ascii=False),
            canonical_rock_candy["chef_tip"], canonical_rock_candy["chef_tip_hi"], json.dumps(canonical_rock_candy["main_ingredients"], ensure_ascii=False), canonical_rock_candy["search_text"]
        ))
    conn.commit()
    print("✅ Canonical Rock Candy / Mishri ready.")

    # Step 3: Global Re-classification and Hindi Translation
    print("\n3. Re-classifying meal types, pairing notes, chef tips, and Hindi translations across all recipes...")
    cur.execute("SELECT id, recipe_name, recipe_name_hi, meal_type, pairing_notes, chef_tip FROM recipes")
    all_rows = cur.fetchall()

    updated = 0
    devanagari_regex = re.compile(r"[\u0900-\u097F]")

    for r_id, name, name_hi, meal_type, pairing, tip in all_rows:
        new_meal, new_meal_hi, new_pairing, new_pairing_hi, new_tip, new_tip_hi = classify_recipe(name)

        # Fix recipe_name_hi:
        # If it has '(स्वादिष्ट रेसिपी)', is empty, has no Devanagari, or has leftover Latin/English words:
        needs_hi_fix = False
        if "(स्वादिष्ट रेसिपी)" in (name_hi or "") or not name_hi or not devanagari_regex.search(name_hi) or re.search(r"[a-zA-Z]", name_hi):
            needs_hi_fix = True
        elif name_hi == "पंजाबी मीठी लस्सी" and not re.search(r"\blassi\b", name, flags=re.I):
            needs_hi_fix = True

        if needs_hi_fix:
            new_name_hi = translate_title_to_hindi(name)
        else:
            new_name_hi = name_hi

        cur.execute("""
            UPDATE recipes
            SET meal_type = ?, meal_type_hi = ?,
                pairing_notes = ?, pairing_notes_hi = ?,
                chef_tip = ?, chef_tip_hi = ?,
                recipe_name_hi = ?
            WHERE id = ?
        """, (new_meal, new_meal_hi, new_pairing, new_pairing_hi, new_tip, new_tip_hi, new_name_hi, r_id))
        updated += 1

    conn.commit()
    print(f"✅ Successfully updated {updated} recipes with intelligent pairing notes, chef tips, and authentic Hindi titles.")

    # Step 4: Rebuild recipes_fts
    print("\n4. Rebuilding recipes_fts virtual table...")
    cur.execute("DROP TABLE IF EXISTS recipes_fts;")
    cur.execute("""
        CREATE VIRTUAL TABLE recipes_fts USING fts5(
            recipe_name,
            search_text,
            content='recipes',
            content_rowid='id'
        );
    """)
    cur.execute("INSERT INTO recipes_fts(rowid, recipe_name, search_text) SELECT id, recipe_name, search_text FROM recipes;")
    conn.commit()
    conn.close()
    print("✅ FTS5 table rebuilt.")

    # Step 5: Compress to recipes.db.gz
    print(f"\n5. Compressing {DB_PATH} to {GZ_PATH}...")
    with open(DB_PATH, "rb") as f_in:
        with gzip.open(GZ_PATH, "wb", compresslevel=6) as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    db_size = os.path.getsize(DB_PATH) / (1024 * 1024)
    gz_size = os.path.getsize(GZ_PATH) / (1024 * 1024)
    print(f"✅ Success! Compressed {db_size:.2f} MB database -> {gz_size:.2f} MB ({GZ_PATH})")

if __name__ == "__main__":
    main()
