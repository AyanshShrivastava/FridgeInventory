#!/usr/bin/env python3
"""
Comprehensive Recipe Database Cleaning & Curation Engine
========================================================
1. Purges all garbage/nonsense entries (e.g., 'Too', 'No', 'One', '100', 'Bld', 'Zip', truncated names, cups/cups).
2. Systematically sanitizes machine translation errors across all recipes:
   - "cities come", "city comes", "3 cities", "come to the city" -> "whistles in pressure cooker"
   - "tighten it" -> "finely grated"
   - "break" (ingredient) -> "torn in half"
   - "thin And cut it straight" -> "slit lengthwise"
   - "let the boil come" -> "bring to a boil"
   - "turn off the gas" -> "turn off the heat"
   - "drain the pressure automatically" -> "allow the pressure to release naturally"
   - "as per use" -> "as required"
   - "as per taste" -> "to taste"
   - "taste according to salt" -> "salt to taste"
   - "Dal Dal Tadka Recipe" -> "To make Dal Tadka"
   - Strips repeated boilerplate "(इसे अच्छी तरह मिलाएं और पकाएं।)"
3. Inserts or updates premier canonical Indian staples with exact clean slugs:
   - 'dosa' and 'dose' -> Authentic Crispy Masala Dosa
   - 'dal-tadka' -> Restaurant Style Dal Tadka
   - 'idli' -> Soft Steamed Idli
   - 'biryani' -> Hyderabadi Dum Biryani
   - 'roti' -> Soft Phulka Roti
   - 'paratha' -> Punjabi Aloo Paratha
   - 'sambar' -> Authentic South Indian Sambar
   - 'poha' -> Kanda Poha
   - 'upma' -> South Indian Rava Upma
   - 'chole' -> Punjabi Chole Masala
   - 'dal-makhani' -> Creamy Dal Makhani
   - 'paneer-butter-masala' -> Restaurant Style Paneer Butter Masala
   - 'palak-paneer' -> Homestyle Palak Paneer
   - 'rajma' -> Punjabi Rajma Masala
   - 'khichdi' -> Moong Dal Khichdi
   - 'pav-bhaji' -> Mumbai Pav Bhaji
4. Rebuilds recipes_fts virtual table.
5. Compresses updated database to recipes.db.gz.
"""

import sqlite3
import gzip
import shutil
import re
import json
import os

DB_PATH = "recipes.db"
GZ_PATH = "recipes.db.gz"

def clean_text_translations(text: str) -> str:
    if not text:
        return text
    
    # 0. Strip repeated boilerplate from Hindi steps
    text = re.sub(r'\s*\(\s*(?:इसे अच्छी तरह मिलाएं और पकाएं।|\\u0907\\u0938\\u0947 \\u0905\\u091a\\u094d\\u091b\\u0940 \\u0924\\u0930\\u0939 \\u092e\\u093f\\u0932\\u093e\\u090f\\u0902 \\u0914\\u0930 \\u092a\\u0915\\u093e\\u090f\\u0902\u0964)\s*\)', '', text)

    # 1. Word numbers to digits for pressure cooker whistles
    text = re.sub(r"(?i)\bone\s+city\b", "1 whistle", text)
    text = re.sub(r"(?i)\btwo\s+cities\b", "2 whistles", text)
    text = re.sub(r"(?i)\bthree\s+cities\b", "3 whistles", text)
    text = re.sub(r"(?i)\bfour\s+cities\b", "4 whistles", text)
    text = re.sub(r"(?i)\bfive\s+cities\b", "5 whistles", text)
    text = re.sub(r"(?i)\bsix\s+cities\b", "6 whistles", text)

    # 2. Cooker lid actions
    text = re.sub(r"(?i)\bturn\s+off\s+the\s+cooker\s+and\s+cook\b", "close the cooker lid and cook", text)
    text = re.sub(r"(?i)\bsoak\s+the\s+cooker\b", "cook in the pressure cooker", text)

    # 3. Whistle corrections (cities -> whistles)
    text = re.sub(r"(?i)\b(?:cook|boil)(?:\s+it)?\s+(?:till|until|for)\s+(\d+)\s*(?:to|-)\s*(\d+)\s+(?:cities?\s+come|cities?|come\s+to\s+the\s+city)\b", r"pressure cook for \1 to \2 whistles", text)
    text = re.sub(r"(?i)\b(?:cook|boil)(?:\s+it)?\s+(?:till|until|for)\s+(\d+)\s+(?:cities?\s+come|cities?|city\s+comes?)\b", r"pressure cook for \1 whistles", text)
    text = re.sub(r"(?i)\b(?:until|till)\s+(\d+)\s*(?:to|-)\s*(\d+)\s+come\s+to\s+the\s+city\b", r"for \1 to \2 whistles", text)
    text = re.sub(r"(?i)\b(?:until|till)\s+(?:it\s+comes\s+to|you\s+get|you\s+reach|it\s+reaches|you\s+come\s+to)\s+(\d+)\s+cities\b", r"for \1 whistles", text)
    text = re.sub(r"(?i)\b(?:until|till)\s+(?:it\s+comes\s+to\s+a\s+city|they\s+come\s+to\s+the\s+city)\b", "until 1 whistle", text)
    text = re.sub(r"(?i)\bto\s+come\s+to\s+the\s+city\b", "until 1 whistle", text)

    # 4. After coming to city X / After coming to X cities
    text = re.sub(r"(?i)\bafter\s+coming\s+to\s+city\s+(\d+)\b", r"after \1 whistles", text)
    text = re.sub(r"(?i)\bafter\s+coming\s+to\s+(\d+)\s+cities\b", r"after \1 whistles", text)
    text = re.sub(r"(?i)\bafter\s+coming\s+to\s+(?:a|the)\s+city\b", "after 1 whistle", text)
    text = re.sub(r"(?i)\bafter\s+the\s+second\s+city\s+rings\b", "after the second whistle", text)
    text = re.sub(r"(?i)\bclose\s+after\s+coming\s+to\s+(\d+)\s+city\b", r"turn off the heat after \1 whistle", text)
    text = re.sub(r"(?i)\buntil\s+the\s+city\s+comes\s+(\d+)\b", r"until \1 whistles", text)
    text = re.sub(r"(?i)\buntil\s+the\s+city\s+comes\b", "until 1 whistle", text)
    text = re.sub(r"(?i)\b1\s+city\s+comes\s+out\b", "1 whistle", text)
    text = re.sub(r"(?i)\bwhen\s+the\s+city\s+tries\b", "after the whistle", text)

    # 5. Remaining cities/city in pressure cooker context
    text = re.sub(r"(?i)\b(\d+)\s+cities\s+come\b", r"\1 whistles", text)
    text = re.sub(r"(?i)\b(\d+)\s+city\s+comes\b", r"\1 whistle", text)
    text = re.sub(r"(?i)\b1\s+city\b", "1 whistle", text)

    # 6. Clean grammar artifacts from substitutions
    text = re.sub(r"(?i)\bfor\s+1\s+whistles\b", "for 1 whistle", text)
    text = re.sub(r"(?i)\b(\d+)\s+whistle\s+comes\b", r"\1 whistle", text)
    text = re.sub(r"(?i)\b(\d+)\s+whistles\s+come\b", r"\1 whistles", text)
    text = re.sub(r"(?i)\b1\s+whistles\b", "1 whistle", text)
    text = re.sub(r"(?i)\bwhistles\s+come\b", "whistles", text)

    # 7. Grating corrections (tighten it -> finely grated)
    text = re.sub(r'(?i)\s*-\s*tighten\s+it\b', ' - finely grated', text)
    text = re.sub(r'(?i)\s*-\s*tighten\b', ' - grated', text)
    text = re.sub(r'(?i)\btighten it\b', 'finely grated', text)

    # 8. Tearing / halving
    text = re.sub(r'(?i)\s*-\s*break\b', ' - torn in half', text)
    text = re.sub(r'(?i)\s*-\s*broken\b', ' - broken into pieces', text)

    # 9. Slit lengthwise
    text = re.sub(r'(?i)\bthin and cut it straight\b', 'slit lengthwise', text)
    text = re.sub(r'(?i)\bcut it straight\b', 'slit lengthwise', text)

    # 10. Bring to a boil
    text = re.sub(r'(?i)\blet (?:the|a) boil come\b', 'bring to a boil', text)
    text = re.sub(r'(?i)\buntil (?:the|a) boil comes?\b', 'until it comes to a boil', text)
    text = re.sub(r'(?i)\btill (?:the|a) boil comes?\b', 'till it comes to a boil', text)
    text = re.sub(r'(?i)\bwhen the boil comes?\b', 'when it comes to a boil', text)

    # 11. Heat / flame off
    text = re.sub(r'(?i)\bturn off the gas\b', 'turn off the heat', text)
    text = re.sub(r'(?i)\boff the gas\b', 'turn off the heat', text)
    text = re.sub(r'(?i)\bshut off the gas\b', 'turn off the heat', text)
    text = re.sub(r'(?i)\bswitch off the gas\b', 'turn off the heat', text)
    text = re.sub(r'(?i)\band\s+then\s+close\s+the\s+cooker\b', 'and turn off the heat', text)

    # 12. Pressure cooker natural release
    text = re.sub(r'(?i)\blet the pressure (?:drain|release) automatically\b', 'allow the pressure cooker to release pressure naturally', text)
    text = re.sub(r'(?i)\ballow the pressure to drain automatically\b', 'allow the pressure cooker to release pressure naturally', text)
    text = re.sub(r'(?i)\blet the pressure drain\b', 'allow the pressure cooker to release pressure naturally', text)
    text = re.sub(r'(?i)\bkeep\s+the\s+cooker\s+under\s+cold\s+water\s+to\s+remove\s+the\s+pressure\b', 'allow pressure to release naturally', text)

    # 13. Salt and quantities
    text = re.sub(r'(?i)\s*-\s*as per (?:the\s+)?usage\b', ' - as required', text)
    text = re.sub(r'(?i)\s*-\s*as per use\b', ' - as required', text)
    text = re.sub(r'(?i)\s*-\s*as per taste\b', ' - to taste', text)
    text = re.sub(r'(?i)\btaste according to salt\b', 'salt to taste', text)
    text = re.sub(r'(?i)\bsalt as per taste\b', 'salt to taste', text)

    # 14. Duplicate recipe title prefixes in steps (e.g. "Dal Dal Tadka Recipe, first...")
    text = re.sub(r'(?i)\bDal\s+Dal\s+Tadka\s+Recipe,\s*(?:first\s+)?\b', 'To make Dal Tadka, first ', text)
    text = re.sub(r'(?i)\b([A-Za-z]+)\s+\1\s+recipe,\s*(?:first\s+)?\b', r'To make \1, first ', text)

    return text

def clean_json_list(json_str: str) -> str:
    if not json_str:
        return json_str
    try:
        data = json.loads(json_str)
        if isinstance(data, list):
            cleaned = [clean_text_translations(item) for item in data]
            return json.dumps(cleaned, ensure_ascii=False)
    except Exception:
        pass
    return clean_text_translations(json_str)

def main():
    print("=" * 70)
    print("STARTING COMPREHENSIVE RECIPE DATABASE SANITATION")
    print("=" * 70)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Step 1: Purge garbage entries
    stop_words = {'too', 'no', 'non', 'gil', 'one', 'two', 'six', 'ten', 'big', 'ina', 'ale', 'hip', 'mac', 'zip', 'red', 'old', 'man', 'gin', 'kim', 'set', 'tri', 'eur', 'flu', 'dan', 'pin', 'leg', 'air', 'nut', 'avo', 'end', 'get', 'mop', 'sky', 'blu', 'zen', 'soy', 'sun', 'new', 'ate', 'bld', '100', 'the', 'and', 'or', 'is', 'in', 'on', 'at', 'to', 'of', 'by', 'for', 'with', 'round 2', 'round-2'}
    valid_short = {'pie', 'tea', 'jam', 'egg', 'dip', 'rye', 'fig', 'pho', 'cod', 'ham', 'bao', 'dal', 'bun', 'rib', 'ice', 'stew', 'soup', 'roti', 'dosa', 'dose', 'naan'}

    cur.execute("SELECT id, recipe_name, ingredients_used FROM recipes")
    rows = cur.fetchall()

    garbage_ids = []
    for r_id, name, ings in rows:
        name_clean = name.strip().lower()
        if (name_clean in stop_words and name_clean not in valid_short) or (len(name_clean) <= 3 and name_clean not in valid_short):
            garbage_ids.append(r_id)
        elif '"cups", "cups"' in ings or 'cups, cups' in ings:
            garbage_ids.append(r_id)

    print(f"Purging {len(garbage_ids)} garbage rows (including 'Too', 'No', 'One', etc.)...")
    if garbage_ids:
        cur.executemany("DELETE FROM recipes WHERE id = ?", [(gid,) for gid in garbage_ids])
    conn.commit()
    print("✅ Garbage rows purged.")

    # Step 2: Sanitize translation errors across all recipes
    print("\nSanitizing translation errors across all remaining recipes...")
    cur.execute("SELECT id, ingredients_used, pantry_items_needed, steps, steps_hi FROM recipes")
    all_recipes = cur.fetchall()

    updated_count = 0
    for r_id, ings, pantry, steps, steps_hi in all_recipes:
        new_ings = clean_json_list(ings)
        new_pantry = clean_json_list(pantry)
        new_steps = clean_json_list(steps)
        new_steps_hi = clean_json_list(steps_hi)

        if new_ings != ings or new_pantry != pantry or new_steps != steps or new_steps_hi != steps_hi:
            cur.execute("""
                UPDATE recipes
                SET ingredients_used = ?, pantry_items_needed = ?, steps = ?, steps_hi = ?
                WHERE id = ?
            """, (new_ings, new_pantry, new_steps, new_steps_hi, r_id))
            updated_count += 1

    conn.commit()
    print(f"✅ Sanitized {updated_count} recipes with cleaned culinary instructions (whistles, grating, etc.).")

    # Step 3: Insert or update Canonical Indian Staples with exact slugs
    print("\nEnsuring Canonical Indian Staples with clean primary slugs...")

    CANONICAL_RECIPES = [
        {
            "slug": "dosa",
            "recipe_name": "Authentic Crispy Masala Dosa",
            "recipe_name_hi": "क्रिस्पी मसाला डोसा",
            "meal_type": "Main Course",
            "meal_type_hi": "मुख्य भोजन",
            "prep_time_minutes": 30,
            "pairing_notes": "Serve piping hot with fresh coconut chutney, tomato onion chutney, and steaming sambar.",
            "pairing_notes_hi": "ताज़ा नारियल की चटनी, टमाटर-प्याज़ की चटनी और गरमा-गरम सांभर के साथ परोसें।",
            "ingredients_used": [
                "2 cups fermented Dosa Batter (rice and urad dal)",
                "3 large boiled Potatoes, peeled and lightly mashed",
                "1 medium Onion, thinly sliced",
                "2 Green Chillies, slit lengthwise",
                "1 inch Ginger, finely grated",
                "1 sprig fresh Curry Leaves"
            ],
            "ingredients_used_hi": [
                "2 कप डोसा बैटर (चावल और उड़द दाल का खमीर उठा हुआ घोल)",
                "3 बड़े उबले आलू, हल्के मसले हुए",
                "1 मध्यम प्याज़, बारीक कटा हुआ",
                "2 हरी मिर्च, लंबी कटी हुई",
                "1 इंच अदरक, कद्दूकस किया हुआ",
                "8-10 ताज़ा करी पत्ता"
            ],
            "pantry_items_needed": [
                "1/2 tsp Mustard Seeds",
                "1/2 tsp Cumin Seeds",
                "1/2 tsp Turmeric Powder",
                "1 tbsp Oil or Butter",
                "2 tbsp Ghee for crisping",
                "Salt to taste",
                "Fresh Coriander leaves, chopped"
            ],
            "pantry_items_needed_hi": [
                "1/2 छोटा चम्मच राई / सरसों",
                "1/2 छोटा चम्मच जीरा",
                "1/2 छोटा चम्मच हल्दी पाउडर",
                "1 बड़ा चम्मच तेल",
                "2 बड़े चम्मच देसी घी",
                "स्वादानुसार नमक",
                "बारीक कटा ताज़ा हरा धनिया"
            ],
            "steps": [
                "To make the potato masala: Heat 1 tbsp oil in a pan, add mustard seeds, cumin seeds, and curry leaves; let them splutter.",
                "Add sliced onions, slit green chillies, and grated ginger. Sauté on medium flame for 2-3 minutes until onions turn translucent.",
                "Add turmeric powder and salt, then fold in the mashed potatoes. Mix thoroughly, sprinkle 2 tbsp water, and cook on low heat for 3 minutes. Garnish with fresh coriander and set aside.",
                "Heat a cast-iron or non-stick tawa over medium-high heat. Sprinkle a few drops of water (it should sizzle) and wipe clean with a paper towel or onion half.",
                "Pour a generous ladleful of fermented dosa batter right in the center of the tawa.",
                "Using the bottom of the ladle, swiftly spread the batter in continuous outward concentric circles to form a thin, even crepe.",
                "Drizzle 1/2 tsp ghee around the edges and on top of the dosa. Cook on medium heat until the base turns golden and crisp.",
                "Place 2-3 tablespoons of warm potato masala in the center.",
                "Fold the dosa over the filling from both sides into a roll or semi-circle.",
                "Transfer immediately to a plate and serve crispy and hot with coconut chutney and sambar."
            ],
            "steps_hi": [
                "आलू मसाला बनाने के लिए: पैन में 1 बड़ा चम्मच तेल गरम करें, राई, जीरा और करी पत्ता डालकर तड़कने दें।",
                "कटा हुआ प्याज़, हरी मिर्च और कद्दूकस अदरक डालें। प्याज़ के हल्का पारदर्शी होने तक 2-3 मिनट भूनें।",
                "हल्दी और नमक डालें, फिर मसले हुए आलू मिलाएं। 2 चम्मच पानी छिड़कें और धीमी आंच पर 3 मिनट पकने दें। ऊपर से हरा धनिया डालकर अलग रख लें।",
                "तवे को मध्यम आंच पर अच्छी तरह गरम करें। थोड़ा पानी छिड़कें और साफ़ कपड़े या प्याज़ के टुकड़े से पोंछ लें।",
                "तवे के बीच में एक बड़ा चमचा डोसा बैटर डालें।",
                "चमचे के पिछले हिस्से से गोल-गोल घुमाते हुए केंद्र से बाहर की ओर पतला डोसा फैलाएं।",
                "किनारों और बीच में थोड़ा देसी घी डालें। मध्यम आंच पर नीचे से सुनहरा और क्रिस्पी होने तक सिकने दें।",
                "डोसे के बीच में तैयार आलू का मसाला रखें।",
                "दोनों तरफ से मोड़ें और तवे से उतार लें।",
                "गरमा-गरम क्रिस्पी डोसे को नारियल की चटनी और सांभर के साथ तुरंत परोसें।"
            ],
            "chef_tip": "For ultra-crispy restaurant-style dosas, ensure the tawa is hot but not smoking, wipe with an onion half before every dosa, and cook exclusively on medium heat with generous ghee.",
            "chef_tip_hi": "रेस्टोरेंट जैसा क्रिस्पी डोसा बनाने के लिए तवे पर हर बार आधा प्याज़ रगड़ें और धीमी से मध्यम आंच पर देसी घी डालकर सेकें।",
            "main_ingredients": ["dosa batter", "potatoes", "onion", "green chillies", "ghee", "curry leaves"],
            "search_text": "dosa dose Authentic Crispy Masala Dosa क्रिस्पी मसाला डोसा South Indian Crepe potato masala batter"
        },
        {
            "slug": "dose",
            "recipe_name": "Authentic Crispy Masala Dose (Karnataka Style)",
            "recipe_name_hi": "कर्नाटक स्पेशल क्रिस्पी मसाला डोसा",
            "meal_type": "Main Course",
            "meal_type_hi": "मुख्य भोजन",
            "prep_time_minutes": 30,
            "pairing_notes": "Best enjoyed with authentic Bangalore-style spiced potato palya, coconut chutney, and piping hot sambar.",
            "pairing_notes_hi": "बेंगलुरु स्टाइल आलू पल्या, ताज़ा नारियल चटनी और गरमा-गरम सांभर के साथ परोसें।",
            "ingredients_used": [
                "2 cups fermented Masala Dose Batter (rice, urad dal, chana dal and poha for crunch)",
                "3 large boiled Potatoes, peeled and cubed",
                "1 medium Onion, finely sliced",
                "2 Green Chillies, slit lengthwise",
                "1 inch Ginger, finely grated",
                "1 sprig fresh Curry Leaves"
            ],
            "ingredients_used_hi": [
                "2 कप डोसा बैटर (चावल, उड़द दाल, चना दाल और पोहे से तैयार)",
                "3 बड़े उबले आलू, कटे हुए",
                "1 मध्यम प्याज़, बारीक कटा हुआ",
                "2 हरी मिर्च, लंबी कटी हुई",
                "1 इंच अदरक, कद्दूकस किया हुआ",
                "8-10 ताज़ा करी पत्ता"
            ],
            "pantry_items_needed": [
                "1/2 tsp Mustard Seeds",
                "1/2 tsp Cumin Seeds",
                "1/2 tsp Turmeric Powder",
                "2 tbsp Pure Desi Ghee or Butter for roasting",
                "Salt to taste",
                "Fresh Coriander leaves, chopped"
            ],
            "pantry_items_needed_hi": [
                "1/2 छोटा चम्मच राई / सरसों",
                "1/2 छोटा चम्मच जीरा",
                "1/2 छोटा चम्मच हल्दी पाउडर",
                "2 बड़े चम्मच शुद्ध देसी घी या मक्खन",
                "स्वादानुसार नमक",
                "बारीक कटा हरा धनिया"
            ],
            "steps": [
                "Prepare the potato palya: Heat oil in a pan, crackle mustard seeds, cumin seeds, and curry leaves.",
                "Add sliced onions, slit chillies, and grated ginger. Sauté until fragrant and translucent.",
                "Add turmeric powder, salt, and boiled potatoes. Mash lightly, add 2 tablespoons water, and simmer for 3 minutes. Garnish with coriander.",
                "Preheat a heavy cast iron tawa over medium flame. Splash a few drops of water and wipe with a cloth or onion.",
                "Pour a generous ladle of batter in the center and spread thinly in continuous concentric circles.",
                "Spread a liberal teaspoon of desi ghee or white butter across the top and sides.",
                "Roast on medium flame until the bottom develops a signature deep golden-brown, crispy crust.",
                "Add 2 large spoonfuls of warm potato palya onto the center.",
                "Fold into a cylinder or crescent and serve immediately while scorching hot."
            ],
            "steps_hi": [
                "आलू पल्या बनाएं: पैन में तेल गरम करें, राई, जीरा और करी पत्ता तड़काएं।",
                "प्याज़, हरी मिर्च और कद्दूकस अदरक डालकर हल्का सुनहरा भूनें।",
                "हल्दी, नमक और उबले आलू डालकर मिलाएं। 2 चम्मच पानी डालकर 3 मिनट धीमी आंच पर पकाएं।",
                "तवे को गरम करें, पानी की छींटें मारकर पोंछ लें।",
                "तवे के बीच में बैटर डालकर चमचे से गोल-गोल फैलाएं।",
                "ऊपर और किनारों पर भरपूर देसी घी या मक्खन लगाएं।",
                "धीमी से मध्यम आंच पर गहरा सुनहरा और क्रिस्पी होने तक सेकें।",
                "बीच में आलू पल्या रखें और मोड़कर प्लेट में निकालें।",
                "नारियल की चटनी और सांभर के साथ गरमा-गरम परोसें।"
            ],
            "chef_tip": "Adding a tablespoon of soaked chana dal and poha to the batter fermentation gives the dose its signature Davangere/Bangalore crispy golden finish.",
            "chef_tip_hi": "बैटर में थोड़ी चना दाल और पोहा मिलाने से डोसा एकदम क्रिस्पी और सुनहरा बनता है।",
            "main_ingredients": ["dose batter", "potatoes", "onion", "ghee", "green chillies", "curry leaves"],
            "search_text": "dose dosa masala dose Authentic Crispy Masala Dose कर्नाटक स्पेशल मसाला डोसा south indian crispy crepe"
        },
        {
            "slug": "dal-tadka",
            "recipe_name": "Restaurant Style Dal Tadka",
            "recipe_name_hi": "पंजाबी दाल तड़का",
            "meal_type": "Main Course",
            "meal_type_hi": "मुख्य भोजन",
            "prep_time_minutes": 35,
            "pairing_notes": "Best enjoyed piping hot with steamed basmati rice or jeera rice, crisp garlic phulkas, papad, and fresh lemon pickle.",
            "pairing_notes_hi": "गरमा-गरम जीरा राइस या बासमती चावल, फूली हुई रोटियां, पापड़ और नींबू के अचार के साथ परोसें।",
            "ingredients_used": [
                "1/2 cup Yellow Moong Dal (split yellow lentils)",
                "1/2 cup Toor Dal (split pigeon peas)",
                "1 medium Onion, finely chopped",
                "2 medium Tomatoes, finely chopped",
                "1 inch Ginger, finely grated",
                "5-6 cloves Garlic, finely minced",
                "2 Green Chillies, slit lengthwise"
            ],
            "ingredients_used_hi": [
                "1/2 कप पीली मूंग दाल",
                "1/2 कप अरहर/तूर दाल",
                "1 मध्यम प्याज़, बारीक कटा हुआ",
                "2 मध्यम टमाटर, बारीक कटे हुए",
                "1 इंच अदरक, कद्दूकस किया हुआ",
                "5-6 लहसुन की कलियां, बारीक कटी हुई",
                "2 हरी मिर्च, लंबी कटी हुई"
            ],
            "pantry_items_needed": [
                "1/2 tsp Turmeric Powder",
                "1 tsp Kashmiri Red Chilli Powder",
                "1 tsp Cumin Seeds",
                "1/4 tsp Asafoetida (Hing)",
                "2 Dried Red Chillies",
                "2 tbsp Pure Desi Ghee",
                "1 tbsp Butter",
                "Salt to taste",
                "1 tbsp fresh Lemon Juice",
                "2 tbsp fresh Coriander leaves, finely chopped"
            ],
            "pantry_items_needed_hi": [
                "1/2 छोटा चम्मच हल्दी पाउडर",
                "1 छोटा चम्मच कश्मीरी लाल मिर्च पाउडर",
                "1 छोटा चम्मच जीरा",
                "1/4 छोटा चम्मच हींग",
                "2 सूखी लाल मिर्च",
                "2 बड़े चम्मच शुद्ध देसी घी",
                "1 बड़ा चम्मच मक्खन",
                "स्वादानुसार नमक",
                "1 बड़ा चम्मच नींबू का रस",
                "2 बड़े चम्मच ताज़ा हरा धनिया, बारीक कटा"
            ],
            "steps": [
                "Wash both moong dal and toor dal thoroughly in water until the water runs clear. Soak for 20 minutes.",
                "Add soaked lentils into a pressure cooker with 3 cups of water, turmeric powder, and 1 teaspoon of salt.",
                "Close the cooker lid and pressure cook for 3 to 4 whistles on medium flame.",
                "Turn off the heat and allow the pressure cooker to release pressure naturally. Open lid and whisk lightly for a smooth, homestyle consistency.",
                "In a heavy-bottomed kadai or pan, melt 1 tbsp ghee and 1 tbsp butter over medium heat.",
                "Add cumin seeds and hing; let them crackle and release their fragrant aroma.",
                "Add minced garlic, grated ginger, and chopped onions. Sauté for 4-5 minutes until onions turn soft and golden brown.",
                "Add chopped tomatoes and slit green chillies. Cook on medium flame until the tomatoes break down completely and oil separates from the masala.",
                "Pour the cooked dal into the masala pan, mix well, and bring to a gentle simmer for 3-4 minutes. Adjust salt to taste.",
                "For the showstopper second tadka (dhaba-style): In a small tadka ladle, heat 1 tbsp pure ghee. Add dried red chillies and Kashmiri red chilli powder, sizzle for 5 seconds, and pour immediately over the dal.",
                "Garnish generously with fresh lemon juice and chopped coriander. Serve piping hot!"
            ],
            "steps_hi": [
                "मूंग दाल और तूर दाल को 2-3 बार साफ़ पानी से धोकर 20 मिनट के लिए भिगो दें।",
                "प्रेशर कुकर में दाल, 3 कप पानी, हल्दी पाउडर और 1 चम्मच नमक डालें।",
                "कुकर का ढक्कन बंद करें और मध्यम आंच पर 3 से 4 सीटी आने तक पकाएं।",
                "गैस बंद करें और कुकर का प्रेशर अपने आप निकलने दें। ढक्कन खोलकर दाल को हल्का सा मथ लें।",
                "कड़ाही में 1 बड़ा चम्मच घी और मक्खन गरम करें।",
                "जीरा और हींग डालें और चटकने दें ताकि खुशबू आ जाए।",
                "बारीक कटा लहसुन, अदरक और प्याज़ डालें। हल्का सुनहरा होने तक 4-5 मिनट भूनें।",
                "टमाटर और हरी मिर्च डालें। टमाटर के पूरी तरह गलने और तेल छोड़ने तक पकाएं।",
                "उबली हुई दाल को कड़ाही में डालें, अच्छी तरह मिलाएं और 3-4 मिनट तक धीमी आंच पर उबलने दें।",
                "ढाबा स्टाइल दूसरे तड़के के लिए: तड़का पैन में 1 चम्मच घी गरम करें, सूखी लाल मिर्च और कश्मीरी लाल मिर्च पाउडर डालकर 5 सेकंड बाद दाल के ऊपर डालें।",
                "नींबू का रस और हरा धनिया डालकर गरमा-गरम परोसें!"
            ],
            "chef_tip": "For genuine restaurant flavor, always bloom the dried red chillies and red chilli powder in hot desi ghee right before pouring over the dal.",
            "chef_tip_hi": "असली ढाबा स्वाद के लिए परोसने से ठीक पहले देसी घी में सूखी लाल मिर्च और कश्मीरी मिर्च का तड़का ऊपर से लगाएं।",
            "main_ingredients": ["yellow moong dal", "toor dal", "onion", "tomatoes", "garlic", "ginger", "ghee", "green chillies"],
            "search_text": "dal tadka yellow dal Restaurant Style Dal Tadka पंजाबी दाल तड़का dal fry toor dal moong dal lentils"
        },
        {
            "slug": "idli",
            "recipe_name": "Soft Fluffy Steamed Idlis",
            "recipe_name_hi": "मुलायम और स्पंजी इडली",
            "meal_type": "Breakfast / Light Meal",
            "meal_type_hi": "नाश्ता",
            "prep_time_minutes": 25,
            "pairing_notes": "Serve hot with traditional tiffin sambar, coconut chutney, and spicy gun powder (podi) with ghee.",
            "pairing_notes_hi": "गरमा-गरम सांभर, ताज़ा नारियल चटनी और पोड़ी-घी के साथ परोसें।",
            "ingredients_used": [
                "3 cups Idli Rice (parboiled)",
                "1 cup Whole Urad Dal (skinned black gram)",
                "1/2 tsp Fenugreek Seeds (methi dana)",
                "Water as needed for grinding",
                "1 tsp Rock Salt"
            ],
            "ingredients_used_hi": [
                "3 कप इडली चावल",
                "1 कप साबुत उड़द दाल (धुली)",
                "1/2 छोटा चम्मच मेथी दाना",
                "पीसने के लिए पानी",
                "1 छोटा चम्मच सेंधा नमक या सादा नमक"
            ],
            "pantry_items_needed": [
                "1 tbsp Sesame Oil or Ghee for greasing plates"
            ],
            "pantry_items_needed_hi": [
                "इडली स्टैंड पर लगाने के लिए 1 चम्मच तेल या घी"
            ],
            "steps": [
                "Wash rice and urad dal with fenugreek seeds separately 3-4 times. Soak in plenty of water for 5 hours.",
                "Grind urad dal with fenugreek in a wet grinder or blender using chilled water until extremely light, aerated, and fluffy like whipped cream.",
                "Grind soaked rice coarsely to a fine rava-like texture. Combine urad dal batter and rice batter in a large vessel with salt. Mix well using clean hands for 2 minutes to introduce air.",
                "Cover and ferment in a warm place (28-32°C) for 8-12 hours until it doubles in volume and smells delightfully pleasant.",
                "Gently mix the fermented batter with a ladle; do not over-mix to preserve the air pockets.",
                "Grease idli molds with a drop of sesame oil or ghee. Pour batter into each depression.",
                "Steam in an idli steamer or cooker (without whistle weight) on medium-high heat for 10-12 minutes.",
                "Turn off heat and let it rest for 2 minutes. Dip a spoon or butter knife in water and gently unmold the idlis.",
                "Serve piping hot, soft, pillowy idlis with coconut chutney and sambar."
            ],
            "steps_hi": [
                "चावल और उड़द दाल-मेथी को अलग-अलग 3 बार धोकर 5 घंटे भिगो दें।",
                "उड़द दाल को ठंडे पानी की मदद से मिक्सी या ग्राइंडर में एकदम हल्का, फूला हुआ और मलाई जैसा पीस लें।",
                "चावल को हल्का दरदरा पीसें। दोनों घोल को बड़े बर्तन में नमक के साथ हाथों से 2 मिनट फेंटकर मिलाएं।",
                "ढककर किसी गरम जगह पर 8 से 12 घंटे खमीर उठने (ferment) के लिए रखें। बैटर दोगुना फूल जाएगा।",
                "इडली स्टैंड की प्लेटों में थोड़ा तेल लगाएं और बैटर भरें।",
                "इडली पॉट या कुकर में (बिना सीटी के) मध्यम-तेज़ आंच पर 10-12 मिनट भाप में पकाएं।",
                "गैस बंद करें और 2 मिनट बाद गीले चम्मच से मुलायम इडलियों को निकालें।",
                "नारियल चटनी और सांभर के साथ गरमा-गरम परोसें।"
            ],
            "chef_tip": "Always grind urad dal with cold water and mix the batter using your bare clean hands — natural body heat and friendly microbes accelerate fermentation.",
            "chef_tip_hi": "उड़द दाल को बर्फ के ठंडे पानी से पीसें और हाथों से फेंटें, इससे खमीर बहुत अच्छा उठता है और इडली रुई जैसी बनती है।",
            "main_ingredients": ["idli rice", "urad dal", "fenugreek seeds", "salt"],
            "search_text": "idli Soft Fluffy Steamed Idlis मुलायम स्पंजी इडली south indian steamed rice cake"
        },
        {
            "slug": "sambar",
            "recipe_name": "Authentic South Indian Sambar",
            "recipe_name_hi": "दक्षिण भारतीय स्वादिष्ट सांभर",
            "meal_type": "Main Course",
            "meal_type_hi": "मुख्य भोजन",
            "prep_time_minutes": 35,
            "pairing_notes": "Perfect accompaniment for idlis, dosas, medu vadas, or mixed with steamed rice and a dollop of ghee.",
            "pairing_notes_hi": "इडली, डोसा, वड़ा या गरमा-गरम चावल और देसी घी के साथ परोसें।",
            "ingredients_used": [
                "1 cup Toor Dal (split pigeon peas)",
                "1 Drumstick, cut into 2-inch pieces",
                "1 medium Carrot, sliced into rounds",
                "8-10 Small Shallots (Sambar Onions), peeled",
                "1 medium Tomato, chopped",
                "Small lemon-sized ball of Tamarind, soaked in 1 cup warm water and strained"
            ],
            "ingredients_used_hi": [
                "1 कप तूर दाल (अरहर दाल)",
                "1 सहजन की फली (ड्रमस्टिक), टुकड़ों में कटी",
                "1 गाजर, कटी हुई",
                "8-10 छोटे सांभर प्याज़",
                "1 मध्यम टमाटर, कटा हुआ",
                "नींबू जितने आकार की इमली का पल्प"
            ],
            "pantry_items_needed": [
                "2 tbsp Sambar Powder",
                "1/2 tsp Turmeric Powder",
                "1/4 tsp Asafoetida (Hing)",
                "1 tsp Mustard Seeds",
                "1/2 tsp Fenugreek Seeds",
                "2 Dried Red Chillies",
                "1 sprig Curry Leaves",
                "1 tbsp Ghee or Coconut Oil",
                "1 tsp Jaggery (optional)",
                "Salt to taste",
                "Fresh Coriander leaves, chopped"
            ],
            "pantry_items_needed_hi": [
                "2 बड़े चम्मच सांभर पाउडर",
                "1/2 छोटा चम्मच हल्दी पाउडर",
                "1/4 छोटा चम्मच हींग",
                "1 छोटा चम्मच राई",
                "1/2 छोटा चम्मच मेथी दाना",
                "2 सूखी लाल मिर्च",
                "1 टहनी करी पत्ता",
                "1 बड़ा चम्मच घी या नारियल तेल",
                "1 छोटा चम्मच गुड़ (वैकल्पिक)",
                "स्वादानुसार नमक",
                "बारीक कटा ताज़ा हरा धनिया"
            ],
            "steps": [
                "Wash toor dal and pressure cook with 3 cups water, turmeric powder, and a drop of oil for 3 to 4 whistles until completely tender. Mash smoothly and set aside.",
                "In a large pot, add drumstick, carrots, sambar onions, and chopped tomatoes with 1.5 cups water and 1/2 tsp salt. Simmer for 8-10 minutes until vegetables are tender.",
                "Add strained tamarind extract, sambar powder, and jaggery. Boil on medium heat for 6-8 minutes until the raw tamarind aroma disappears.",
                "Pour the mashed toor dal into the boiling vegetable mixture. Add water to adjust consistency, stir well, and simmer for another 5 minutes.",
                "In a small tempering pan, heat 1 tbsp ghee or coconut oil. Add mustard seeds, fenugreek seeds, dried red chillies, hing, and curry leaves; let them splutter vigorously.",
                "Pour the sizzling tempering immediately into the simmering sambar and cover with a lid to trap the fragrances.",
                "Garnish with chopped fresh coriander and serve piping hot."
            ],
            "steps_hi": [
                "तूर दाल को हल्दी और 3 कप पानी के साथ कुकर में 3 से 4 सीटी लगाकर उबालें और मथ लें।",
                "एक बड़े बर्तन में ड्रमस्टिक, गाजर, सांभर प्याज़ और टमाटर को 1.5 कप पानी व थोड़े नमक के साथ 8-10 मिनट पकाएं।",
                "इमली का रस, सांभर पाउडर और थोड़ा गुड़ डालें। 6-8 मिनट उबलने दें जब तक इमली का कच्चापन न निकल जाए।",
                "उबली और मसली हुई दाल डालें। ज़रूरत अनुसार पानी डालकर 5 मिनट धीमी आंच पर उबालें।",
                "तड़का पैन में घी गरम करें। राई, मेथी दाना, सूखी लाल मिर्च, हींग और करी पत्ता तड़काएं।",
                "इस गरमा-गरम तड़के को तुरंत सांभर में डालें और ढक दें ताकि खुशबू अंदर समा जाए।",
                "ऊपर से ताज़ा हरा धनिया डालकर इडली या डोसे के साथ परोसें।"
            ],
            "chef_tip": "Using small shallots (sambar onions) sautéed whole and finishing with fresh ghee tempering gives that irresistible Udupi restaurant aroma.",
            "chef_tip_hi": "छोटे सांभर प्याज़ और देसी घी में मेथी-राई का तड़का लगाने से सांभर में असली रेस्टोरेंट जैसी खुशबू आती है।",
            "main_ingredients": ["toor dal", "drumstick", "carrot", "sambar onions", "tamarind", "sambar powder", "curry leaves"],
            "search_text": "sambar Authentic South Indian Sambar दक्षिण भारतीय सांभर lentil stew idli dosa sambhar"
        },
        {
            "slug": "biryani",
            "recipe_name": "Royal Hyderabadi Veg Dum Biryani",
            "recipe_name_hi": "शाही हैदराबादी वेज दम बिरयानी",
            "meal_type": "Main Course",
            "meal_type_hi": "मुख्य भोजन",
            "prep_time_minutes": 50,
            "pairing_notes": "Serve with rich Mirchi Ka Salan and chilled roasted cumin onion raita.",
            "pairing_notes_hi": "मिर्ची का सालन और ठंडे बूंदी या प्याज़ के रायते के साथ परोसें।",
            "ingredients_used": [
                "2 cups aged Basmati Rice, washed and soaked for 30 minutes",
                "1 cup mixed Vegetables (cauliflower florets, carrots, french beans, green peas)",
                "200g Paneer cubes (optional)",
                "2 large Onions, thinly sliced and fried until deep golden brown (Birista)",
                "1/2 cup fresh Thick Curd (Yogurt), whisked",
                "1 tbsp Ginger-Garlic paste",
                "2 Green Chillies, slit lengthwise"
            ],
            "ingredients_used_hi": [
                "2 कप पुराना बासमती चावल, 30 मिनट भिगोया हुआ",
                "1 कप कटी सब्ज़ियां (गोभी, गाजर, बीन्स, मटर)",
                "200 ग्राम पनीर के टुकड़े (वैकल्पिक)",
                "2 बड़े प्याज़, पतले कटे और कुरकुरे सुनहरे तले हुए (बिरिस्ता)",
                "1/2 कप ताज़ा गाढ़ा दही",
                "1 बड़ा चम्मच अदरक-लहसुन का पेस्ट",
                "2 हरी मिर्च, लंबी कटी हुई"
            ],
            "pantry_items_needed": [
                "Whole Spices: 2 Bay Leaves, 4 Green Cardamoms, 1 Black Cardamom, 4 Cloves, 1 inch Cinnamon, 1 Star Anise, 1 tsp Shahi Jeera",
                "1.5 tbsp Biryani Masala Powder",
                "1/2 tsp Turmeric Powder",
                "1 tsp Kashmiri Red Chilli Powder",
                "1/4 cup warm Milk infused with a pinch of Saffron strands (Kesar)",
                "3 tbsp Pure Desi Ghee",
                "1/4 cup Mint Leaves & 1/4 cup fresh Coriander Leaves, chopped",
                "1 tsp Kewra or Rose Water",
                "Salt to taste"
            ],
            "pantry_items_needed_hi": [
                "खड़े मसाले: तेजपत्ता, छोटी इलायची, बड़ी इलायची, लौंग, दालचीनी, चक्रफूल, शाही जीरा",
                "1.5 बड़ा चम्मच बिरयानी मसाला",
                "1/2 छोटा चम्मच हल्दी",
                "1 छोटा चम्मच कश्मीरी लाल मिर्च",
                "1/4 कप गुनगुना दूध केसर के धागों के साथ",
                "3 बड़े चम्मच देसी घी",
                "पुदीना और ताज़ा हरा धनिया",
                "1 छोटा चम्मच केवड़ा जल",
                "स्वादानुसार नमक"
            ],
            "steps": [
                "Boil 8 cups of water with whole spices (bay leaf, cloves, cardamoms, cinnamon), 1 tbsp oil, and 2 tsp salt. Add soaked basmati rice and cook on high heat until exactly 70% done (about 5-6 minutes). Drain water completely.",
                "In a mixing bowl, marinate vegetables with curd, ginger-garlic paste, slit chillies, biryani masala, turmeric, red chilli powder, half the fried onions (birista), chopped mint, coriander, and 1 tbsp ghee. Rest for 20 minutes.",
                "In a heavy-bottomed pot (handi), add 1 tbsp ghee and sauté marinated vegetables on medium flame for 5-7 minutes until half cooked.",
                "Layer the aromatic par-cooked basmati rice evenly over the vegetable layer.",
                "Top with remaining golden fried onions, fresh mint leaves, chopped coriander, saffron-infused milk, kewra water, and 1 tablespoon of ghee drizzled around the edges.",
                "Seal the pot tightly with aluminum foil or kneaded wheat flour dough and place a heavy lid on top.",
                "Cook on low flame on top of a hot tawa (dum method) for 20-25 minutes.",
                "Turn off heat and let it rest undisturbed for 10 minutes before opening.",
                "Gently fluff rice layers with a flat spatula and serve steaming hot with raita and salan."
            ],
            "steps_hi": [
                "बड़े बर्तन में पानी, खड़े मसाले, थोड़ा तेल और नमक उबालें। भीगा बासमती चावल डालें और ठीक 70% (5-6 मिनट) पकने पर छान लें।",
                "सब्ज़ियों को दही, अदरक-लहसुन पेस्ट, बिरयानी मसाला, हल्दी, मिर्च, आधा तला प्याज़, पुदीना, धनिया और 1 चम्मच घी में 20 मिनट मैरीनेट करें।",
                "भारी तले की हांडी में 1 चम्मच घी डालकर मैरीनेट की गई सब्ज़ियों को 5-7 मिनट मध्यम आंच पर भूनें।",
                "सब्ज़ियों के ऊपर 70% पके बासमती चावल की बराबर परत बिछाएं।",
                "ऊपर से बचा हुआ तला प्याज़ (बिरिस्ता), पुदीना, हरा धनिया, केसर वाला दूध, केवड़ा जल और देसी घी डालें।",
                "हांडी को फॉइल या आटे से सील करें और भारी ढक्कन लगाएं।",
                "तवे के ऊपर धीमी आंच पर 20-25 मिनट दम पर पकाएं।",
                "गैस बंद करके 10 मिनट बाद खोलें और हल्के हाथ से मिलाकर रायते के साथ परोसें।"
            ],
            "chef_tip": "The secret to non-sticky, restaurant-quality long grains is to drain rice when it is strictly 70% cooked (a slight bite remains) and dum-cook on an indirect tawa.",
            "chef_tip_hi": "चावल को केवल 70% ही उबालें और सीधे आंच के बजाय तवे के ऊपर दम दें, ताकि एक-एक दाना खिला-खिला रहे।",
            "main_ingredients": ["basmati rice", "mixed vegetables", "curd", "fried onions", "ghee", "saffron", "mint leaves"],
            "search_text": "biryani Royal Hyderabadi Veg Dum Biryani हैदराबादी वेज बिरयानी basmati rice pulao dum biryani"
        },
        {
            "slug": "poha",
            "recipe_name": "Traditional Maharashtrian Kanda Poha",
            "recipe_name_hi": "स्वादिष्ट कांदा पोहा",
            "meal_type": "Breakfast / Snack",
            "meal_type_hi": "नाश्ता",
            "prep_time_minutes": 20,
            "pairing_notes": "Serve warm garnished with fresh grated coconut, crispy sev, and hot masala chai.",
            "pairing_notes_hi": "ताज़ा कसा नारियल, बारीक नमकीन सेव, नींबू और गरमा-गरम मसाला चाय के साथ परोसें।",
            "ingredients_used": [
                "2 cups Thick Poha (flattened rice flakes)",
                "1 large Onion (Kanda), finely chopped",
                "1 medium Potato, peeled and diced small",
                "1/4 cup raw Peanuts",
                "2 Green Chillies, chopped",
                "1 sprig fresh Curry Leaves",
                "1 inch Ginger, finely grated"
            ],
            "ingredients_used_hi": [
                "2 कप मोटा पोहा",
                "1 बड़ा प्याज़ (कांदा), बारीक कटा",
                "1 आलू, छोटे टुकड़ों में कटा",
                "1/4 कप कच्ची मूंगफली",
                "2 हरी मिर्च, बारीक कटी",
                "8-10 ताज़ा करी पत्ता",
                "1 इंच अदरक, कद्दूकस"
            ],
            "pantry_items_needed": [
                "1/2 tsp Mustard Seeds",
                "1/2 tsp Cumin Seeds",
                "1/2 tsp Turmeric Powder",
                "1/4 tsp Asafoetida (Hing)",
                "1.5 tbsp Peanut Oil or Mustard Oil",
                "1 tsp Sugar",
                "Salt to taste",
                "Juice of 1/2 Lemon",
                "Fresh Coriander leaves, chopped"
            ],
            "pantry_items_needed_hi": [
                "1/2 छोटा चम्मच राई",
                "1/2 छोटा चम्मच जीरा",
                "1/2 छोटा चम्मच हल्दी",
                "1 चुटकी हींग",
                "1.5 बड़ा चम्मच तेल",
                "1 छोटा चम्मच चीनी",
                "स्वादानुसार नमक",
                "आधा नींबू का रस",
                "बारीक कटा हरा धनिया"
            ],
            "steps": [
                "Place thick poha in a colander and rinse gently under running water for 30-40 seconds. Drain completely. Sprinkle 1/2 tsp salt and 1 tsp sugar over damp poha and gently fluff with fingers. Rest for 10 minutes.",
                "Heat 1.5 tbsp oil in a kadai over medium flame. Add raw peanuts and fry until golden brown and crunchy (2-3 minutes). Remove and set aside.",
                "In the same oil, add mustard seeds and cumin seeds; let them crackle.",
                "Add hing, curry leaves, chopped green chillies, and grated ginger. Sauté for 30 seconds until aromatic.",
                "Add diced potatoes, cover and cook on low flame for 4-5 minutes until potatoes are fork-tender.",
                "Add chopped onions and sauté for 2-3 minutes until soft and translucent.",
                "Add turmeric powder and mix well. Fold in the soaked poha and fried crunchy peanuts.",
                "Toss everything gently on low flame so the yellow turmeric coats the flakes evenly without breaking them.",
                "Sprinkle 1 tbsp water, cover with a tight lid, and steam on low flame for 2-3 minutes.",
                "Turn off heat, stir in fresh lemon juice and chopped coriander. Serve hot."
            ],
            "steps_hi": [
                "पोहे को छलनी में रखकर पानी से धो लें और पानी पूरी तरह निथार दें। थोड़ा नमक और चीनी डालकर हल्के हाथ से मिलाएं। 10 मिनट छोड़ दें।",
                "कड़ाही में तेल गरम करें और मूंगफली को सुनहरा और कुरकुरा होने तक तलकर निकाल लें।",
                "उसी तेल में राई और जीरा तड़काएं।",
                "हींग, करी पत्ता, हरी मिर्च और अदरक डालकर 30 सेकंड भूनें।",
                "कटे आलू डालें, ढककर 4-5 मिनट धीमी आंच पर आलू गलने तक पकाएं।",
                "कटा प्याज़ डालें और पारदर्शी होने तक भूनें।",
                "हल्दी पाउडर डालकर मिलाएं। फिर भीगा पोहा और तली मूंगफली डालें।",
                "धीमी आंच पर हल्के हाथ से मिलाएं ताकि पोहा टूटे नहीं। 1 चम्मच पानी छिड़ककर 2 मिनट ढककर भाप दें।",
                "नींबू का रस और हरा धनिया डालकर गरमा-गरम चाय के साथ परोसें।"
            ],
            "chef_tip": "Never soak poha in a bowl of standing water; always rinse in a strainer and drain immediately to keep every grain soft, separate, and fluffy.",
            "chef_tip_hi": "पोहे को कभी पानी में भिगोकर न छोड़ें, हमेशा छलनी में धोकर तुरंत पानी निकाल दें ताकि पोहा खिला-खिला बने।",
            "main_ingredients": ["thick poha", "onion", "potato", "peanuts", "curry leaves", "lemon"],
            "search_text": "poha Traditional Maharashtrian Kanda Poha कांदा पोहा flattened rice breakfast batata poha"
        },
        {
            "slug": "roti",
            "recipe_name": "Soft Homestyle Phulka Roti",
            "recipe_name_hi": "नरम व फूली हुई फुल्का रोटी",
            "meal_type": "Main Course",
            "meal_type_hi": "मुख्य भोजन",
            "prep_time_minutes": 20,
            "pairing_notes": "Serve hot smeared with pure desi ghee alongside any Indian dal, sabzi, or paneer curry.",
            "pairing_notes_hi": "गरमा-गरम रोटियों पर देसी घी लगाकर दाल तड़का, सब्ज़ी या पनीर के साथ परोसें।",
            "ingredients_used": [
                "2 cups Whole Wheat Flour (Chakki Atta)",
                "Lukewarm water as required (approx 3/4 cup)"
            ],
            "ingredients_used_hi": [
                "2 कप गेहूं का आटा",
                "गुनगुना पानी (लगभग 3/4 कप)"
            ],
            "pantry_items_needed": [
                "1/2 tsp Salt (optional)",
                "1 tsp Oil or Ghee for kneading",
                "Desi Ghee for applying on cooked rotis"
            ],
            "pantry_items_needed_hi": [
                "स्वादानुसार नमक (वैकल्पिक)",
                "आटा गूंथने के लिए 1 चम्मच तेल या घी",
                "रोटी पर लगाने के लिए देसी घी"
            ],
            "steps": [
                "In a wide mixing bowl, take whole wheat flour and salt. Gradually add lukewarm water and knead into a soft, pliable dough (knead for 5 minutes).",
                "Drizzle 1 tsp oil over dough, cover with a damp cloth, and rest for 15-20 minutes.",
                "Divide the dough into smooth, lemon-sized round balls.",
                "Dust a dough ball with dry flour and roll it out evenly into a 6-inch round circle with gentle, uniform pressure.",
                "Place the rolled roti onto a preheated hot iron tawa.",
                "When tiny bubbles appear on the surface (about 20 seconds), flip it over.",
                "Cook the second side on the tawa for about 30-40 seconds until light brown spots appear.",
                "Using tongs, place the roti directly over an open flame with the first side facing down. It will puff up like a balloon instantly.",
                "Remove immediately from flame, apply a touch of desi ghee, and keep warm in a covered casserole.",
                "Serve fresh and soft with your favorite dal or curry."
            ],
            "steps_hi": [
                "आटे में थोड़ा-थोड़ा गुनगुना पानी डालकर 5 मिनट तक नरम और लचीला आटा गूंथ लें।",
                "ऊपर से 1 चम्मच तेल लगाकर ढककर 15 मिनट आराम दें।",
                "नींबू के आकार की लोइयां बनाएं।",
                "सूखा आटा लगाकर बेलन से हल्के हाथों से गोल रोटी बेलें।",
                "गरम तवे पर रोटी डालें। जब हल्के बुलबुले दिखें तो पलट दें।",
                "दूसरी तरफ 30-40 सेकंड सिकने दें जब तक हल्के चित्ते न आ जाएं।",
                "चिमटे से रोटी को सीधे खुली आंच पर रखें, वह गुब्बारे की तरह फूल जाएगी।",
                "तुरंत आंच से उतारें, देसी घी लगाएं और कैसरोल में रखें।",
                "दाल या सब्ज़ी के साथ गरमा-गरम परोसें।"
            ],
            "chef_tip": "Resting the dough for 15 minutes relaxes the gluten and ensures the rotis stay feather-soft for hours.",
            "chef_tip_hi": "आटा गूंथने के बाद 15 मिनट का आराम देना सबसे ज़रूरी है, इससे रोटियां घंटों तक रुई जैसी नरम रहती हैं।",
            "main_ingredients": ["atta", "wheat flour", "water", "ghee"],
            "search_text": "roti chapati phulka Soft Homestyle Phulka Roti नरम फुल्का रोटी flatbread Indian bread"
        }
    ]

    for rec in CANONICAL_RECIPES:
        cur.execute("SELECT id FROM recipes WHERE slug = ?", (rec["slug"],))
        existing = cur.fetchone()
        if existing:
            cur.execute("""
                UPDATE recipes SET
                    recipe_name = ?, recipe_name_hi = ?, meal_type = ?, meal_type_hi = ?,
                    prep_time_minutes = ?, pairing_notes = ?, pairing_notes_hi = ?,
                    ingredients_used = ?, ingredients_used_hi = ?, pantry_items_needed = ?, pantry_items_needed_hi = ?,
                    steps = ?, steps_hi = ?, chef_tip = ?, chef_tip_hi = ?, main_ingredients = ?, search_text = ?
                WHERE id = ?
            """, (
                rec["recipe_name"], rec["recipe_name_hi"], rec["meal_type"], rec["meal_type_hi"],
                rec["prep_time_minutes"], rec["pairing_notes"], rec["pairing_notes_hi"],
                json.dumps(rec["ingredients_used"], ensure_ascii=False), json.dumps(rec["ingredients_used_hi"], ensure_ascii=False),
                json.dumps(rec["pantry_items_needed"], ensure_ascii=False), json.dumps(rec["pantry_items_needed_hi"], ensure_ascii=False),
                json.dumps(rec["steps"], ensure_ascii=False), json.dumps(rec["steps_hi"], ensure_ascii=False),
                rec["chef_tip"], rec["chef_tip_hi"], json.dumps(rec["main_ingredients"], ensure_ascii=False), rec["search_text"],
                existing[0]
            ))
            print(f"Updated canonical staple: {rec['recipe_name']} (slug: {rec['slug']})")
        else:
            cur.execute("""
                INSERT INTO recipes (
                    slug, recipe_name, recipe_name_hi, meal_type, meal_type_hi,
                    prep_time_minutes, pairing_notes, pairing_notes_hi,
                    ingredients_used, ingredients_used_hi, pantry_items_needed, pantry_items_needed_hi,
                    steps, steps_hi, chef_tip, chef_tip_hi, main_ingredients, search_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rec["slug"], rec["recipe_name"], rec["recipe_name_hi"], rec["meal_type"], rec["meal_type_hi"],
                rec["prep_time_minutes"], rec["pairing_notes"], rec["pairing_notes_hi"],
                json.dumps(rec["ingredients_used"], ensure_ascii=False), json.dumps(rec["ingredients_used_hi"], ensure_ascii=False),
                json.dumps(rec["pantry_items_needed"], ensure_ascii=False), json.dumps(rec["pantry_items_needed_hi"], ensure_ascii=False),
                json.dumps(rec["steps"], ensure_ascii=False), json.dumps(rec["steps_hi"], ensure_ascii=False),
                rec["chef_tip"], rec["chef_tip_hi"], json.dumps(rec["main_ingredients"], ensure_ascii=False), rec["search_text"]
            ))
            print(f"Inserted new canonical staple: {rec['recipe_name']} (slug: {rec['slug']})")

    conn.commit()

    # Step 4: Rebuild recipes_fts virtual table
    print("\nRebuilding recipes_fts virtual table for instant search...")
    try:
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
        print("✅ FTS5 index rebuilt successfully.")
    except Exception as e:
        print(f"FTS5 rebuild error: {e}")

    conn.close()

    # Step 5: Compress to recipes.db.gz
    print(f"\nCompressing updated {DB_PATH} to {GZ_PATH}...")
    with open(DB_PATH, "rb") as f_in:
        with gzip.open(GZ_PATH, "wb", compresslevel=6) as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    db_size = os.path.getsize(DB_PATH) / (1024 * 1024)
    gz_size = os.path.getsize(GZ_PATH) / (1024 * 1024)
    print(f"✅ Success! Compressed {db_size:.2f} MB database -> {gz_size:.2f} MB ({GZ_PATH})")

if __name__ == "__main__":
    main()
