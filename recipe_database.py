"""
Recipe Database Engine for FridgeInventory.
Provides sub-millisecond local retrieval of 5,800+ authentic Indian recipes
in the exact RescueRecipe format with full Hindi translations, discrete steps,
chef pairing notes, chef zero-waste tips, and core main ingredient tokens.
"""

import gzip
import json
import logging
import os
import re
import shutil
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("fridge_inventory.recipes")

DB_PATH = "recipes.db"
GZ_PATH = "recipes.db.gz"

def ensure_recipe_database():
    """Ensures recipes.db is unpacked and ready for high-speed queries."""
    if not os.path.exists(DB_PATH) and os.path.exists(GZ_PATH):
        try:
            logger.info("Unpacking recipes.db.gz into local SQLite database...")
            with gzip.open(GZ_PATH, "rb") as f_in:
                with open(DB_PATH, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            logger.info("Successfully unpacked recipes.db (5,800+ recipes ready).")
        except Exception as e:
            logger.error(f"Failed to unpack recipes.db.gz: {e}")

# Ensure DB unpacked on module import
ensure_recipe_database()

def get_readonly_connection() -> Optional[sqlite3.Connection]:
    """Returns a SQLite connection for reading recipes."""
    if not os.path.exists(DB_PATH):
        ensure_recipe_database()
    if not os.path.exists(DB_PATH):
        return None
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception:
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"Cannot connect to recipes database: {e}")
            return None

def row_to_recipe_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Converts a SQLite recipe row into the exact RescueRecipe dictionary format."""
    return {
        "recipe_name": row["recipe_name"],
        "recipe_name_hi": row["recipe_name_hi"],
        "meal_type": row["meal_type"],
        "meal_type_hi": row["meal_type_hi"],
        "prep_time_minutes": int(row["prep_time_minutes"]),
        "pairing_notes": row["pairing_notes"] or "",
        "pairing_notes_hi": row["pairing_notes_hi"] or "",
        "ingredients_used": json.loads(row["ingredients_used"]),
        "ingredients_used_hi": json.loads(row["ingredients_used_hi"]),
        "corrected_ingredients": [],
        "pantry_items_needed": json.loads(row["pantry_items_needed"]),
        "pantry_items_needed_hi": json.loads(row["pantry_items_needed_hi"]),
        "steps": json.loads(row["steps"]),
        "steps_hi": json.loads(row["steps_hi"]),
        "chef_tip": row["chef_tip"] or "",
        "chef_tip_hi": row["chef_tip_hi"] or "",
        "response": 0,
        "premade_code": 0,
        "is_premade": False,
        "premade_message": "",
        "premade_message_hi": "",
        "suggested_recipes": []
    }

def clean_search_term(s: str) -> str:
    """Normalizes input for culinary database matching."""
    s = s.strip().lower()
    s = re.sub(r"\b(how\s+to\s+make|how\s+to\s+cook|recipe\s+of|recipe\s+for|vidhi|kaise\s+banaye|make|cook|banao|banaye)\b", "", s).strip()
    s = re.sub(r"\b(fresh|raw|ripe|cut|chopped|boiled|cooked|piece|pieces|curry|sabzi)\b", "", s).strip()
    return s.strip(" ?.,!:")

# Common ingredient synonyms for smart matching
SYNONYM_MAP: Dict[str, List[str]] = {
    "palak": ["palak", "spinach"],
    "spinach": ["palak", "spinach"],
    "paneer": ["paneer", "cottage cheese", "cheese"],
    "tomato": ["tomato", "tomatoes", "tamatar"],
    "tomatoes": ["tomato", "tomatoes", "tamatar"],
    "potato": ["potato", "potatoes", "aloo", "alu"],
    "aloo": ["potato", "potatoes", "aloo", "alu"],
    "gobi": ["cauliflower", "gobi"],
    "cauliflower": ["cauliflower", "gobi"],
    "onion": ["onion", "onions", "pyaz", "kanda"],
    "onions": ["onion", "onions", "pyaz", "kanda"],
    "karela": ["karela", "bitter gourd"],
    "bitter gourd": ["karela", "bitter gourd"],
    "bhindi": ["bhindi", "okra", "lady finger"],
    "okra": ["bhindi", "okra"],
    "baingan": ["baingan", "eggplant", "brinjal"],
    "eggplant": ["baingan", "eggplant", "brinjal"],
    "dal": ["dal", "lentil", "lentils", "toor dal", "moong dal"],
    "rice": ["rice", "chawal", "basmati"],
    "peas": ["peas", "matar", "green peas"],
    "matar": ["peas", "matar", "green peas"],
    "mango": ["mango", "aam"],
    "curd": ["curd", "dahi", "yogurt"],
    "dahi": ["curd", "dahi", "yogurt"],
    "milk": ["milk", "doodh"],
    "butter": ["butter", "makhan"],
    "cream": ["cream", "malai"],
}

def search_recipe_by_dish(dish_query: str) -> Optional[Dict[str, Any]]:
    """
    Searches local database for an authentic recipe matching the dish name.
    Handles exact names, transliterations, and popular variations.
    """
    conn = get_readonly_connection()
    if not conn:
        return None

    clean = clean_search_term(dish_query)
    if not clean:
        conn.close()
        return None

    try:
        cur = conn.cursor()
        slug = re.sub(r"[^a-z0-9]+", "-", clean).strip("-")

        # 1. Exact slug match
        cur.execute("SELECT * FROM recipes WHERE slug = ? LIMIT 1;", (slug,))
        row = cur.fetchone()
        if row:
            conn.close()
            return row_to_recipe_dict(row)

        # 2. Exact or leading recipe name match
        cur.execute("SELECT * FROM recipes WHERE LOWER(recipe_name) = ? LIMIT 1;", (clean,))
        row = cur.fetchone()
        if row:
            conn.close()
            return row_to_recipe_dict(row)

        # 3. Substring match on recipe name (prioritizes shorter/standard names)
        cur.execute("""
            SELECT * FROM recipes 
            WHERE LOWER(recipe_name) LIKE ? 
            ORDER BY LENGTH(recipe_name) ASC 
            LIMIT 1;
        """, (f"%{clean}%",))
        row = cur.fetchone()
        if row:
            conn.close()
            return row_to_recipe_dict(row)

        # 4. Search text match across name and key components
        tokens = [t for t in clean.split() if len(t) >= 3]
        if tokens:
            where_clauses = ["search_text LIKE ?" for _ in tokens]
            params = [f"%{t}%" for t in tokens]
            query = f"SELECT * FROM recipes WHERE {' AND '.join(where_clauses)} ORDER BY LENGTH(recipe_name) ASC LIMIT 1;"
            cur.execute(query, params)
            row = cur.fetchone()
            if row:
                conn.close()
                return row_to_recipe_dict(row)

        conn.close()
        return None
    except Exception as e:
        logger.error(f"Error searching recipe by dish: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return None

def search_recipe_by_ingredients(items: List[str]) -> Optional[Dict[str, Any]]:
    """
    Finds the best authentic recipe from the database that rescues the user's expiring ingredients.
    Scores candidates by ingredient intersection and coverage.
    """
    if not items:
        return None

    conn = get_readonly_connection()
    if not conn:
        return None

    # Normalize input ingredients
    norm_tokens = set()
    for it in items:
        clean = clean_search_term(str(it))
        for token in clean.split():
            if len(token) >= 3:
                norm_tokens.add(token)
                if token in SYNONYM_MAP:
                    norm_tokens.update(SYNONYM_MAP[token])

    if not norm_tokens:
        conn.close()
        return None

    try:
        cur = conn.cursor()
        
        # Build query matching any of the normalized tokens
        clauses = []
        params = []
        for token in norm_tokens:
            clauses.append("search_text LIKE ?")
            params.append(f"%{token}%")

        sql = f"SELECT * FROM recipes WHERE {' OR '.join(clauses)} LIMIT 100;"
        cur.execute(sql, params)
        candidates = cur.fetchall()

        if not candidates:
            conn.close()
            return None

        # Score candidates based on match quality
        best_row = None
        best_score = -1

        user_token_set = set(t.lower() for t in norm_tokens)

        for row in candidates:
            try:
                main_ings = set(x.lower() for x in json.loads(row["main_ingredients"]))
            except Exception:
                main_ings = set()

            # Overlap between user expiring ingredients and recipe's core ingredients
            intersection = user_token_set & main_ings
            score = len(intersection) * 10

            # Bonus if recipe title directly contains user ingredients
            name_low = row["recipe_name"].lower()
            for ut in user_token_set:
                if ut in name_low:
                    score += 5

            # Deduct slight points for overly long non-traditional recipe titles
            score -= (len(row["recipe_name"]) / 50.0)

            if score > best_score:
                best_score = score
                best_row = row

        conn.close()

        # Require reasonable threshold of relevance
        if best_row and best_score >= 5:
            return row_to_recipe_dict(best_row)

        return None
    except Exception as e:
        logger.error(f"Error searching recipe by ingredients: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return None
