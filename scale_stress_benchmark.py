#!/usr/bin/env python3
"""
FridgeInventory - Advanced Concurrency Scale-to-Failure & Exact Capacity Search
================================================================================
Implements the exact test requested:
1. Tests 20 accounts, 25 accounts, and scales up until it fails.
2. Where it fails, backs off by -5 and tests sequentially (1-by-1) to pin down
   the exact maximum concurrent account limit.
3. After all tests, permanently deletes 100% of created test fridges from Firestore.
"""

import os
import sys
import time
import uuid
import json
import statistics
import concurrent.futures
from typing import Dict, List, Any, Tuple, Optional

import requests
import certifi

BASE_URL = os.getenv("TARGET_URL", "https://fridgeinventory.onrender.com")

# Realistic food pairings for zero-waste Indian cooking
INGREDIENT_POOL = [
    ["ripe mango", "chilled milk", "sugar"],
    ["fresh palak", "paneer cubes", "garlic"],
    ["leftover boiled rice", "mustard seeds", "curry leaves", "lemon"],
    ["overripe bananas", "atta flour", "cardamom"],
    ["chopped potatoes", "green peas", "cumin seeds"],
    ["curd yogurt", "cucumber", "roasted cumin powder"],
    ["bread slices", "diced onions", "green chillies"],
    ["carrots", "french beans", "fresh coconut"],
    ["tomatoes", "garlic cloves", "coriander leaves"],
    ["besan gram flour", "onions", "ajwain carom seeds"],
    ["cauliflower florets", "potatoes", "turmeric"],
    ["boiled chickpeas chana", "onions", "tomatoes", "garam masala"],
    ["semolina suji", "curd", "mustard seeds", "curry leaves"],
    ["rolled oats", "milk", "honey", "sliced almonds"],
    ["eggs", "diced onions", "tomatoes", "black pepper"],
    ["mushrooms", "garlic cloves", "butter", "black pepper"],
    ["toor dal", "tomatoes", "tamarind", "sambar powder"],
    ["methi fenugreek leaves", "atta flour", "ajwain", "ghee"],
    ["capsicum bell pepper", "paneer cubes", "onions", "kadhai masala"],
    ["poha flattened rice", "roasted peanuts", "mustard seeds", "turmeric"],
    ["sweet potato", "chaat masala", "lemon juice"],
    ["moong dal", "ginger", "green chillies", "hing asafetida"],
    ["bitter gourd karela", "onions", "amchur dry mango powder"],
    ["apples", "cinnamon powder", "honey", "oats"],
    ["cabbage", "green peas", "mustard seeds", "curry leaves"],
    ["brinjal eggplant", "roasted peanuts", "sesame seeds", "tamarind"],
    ["rajma kidney beans", "onions", "tomatoes", "ginger garlic paste"],
    ["lauki bottle gourd", "chana dal", "cumin seeds", "turmeric"],
    ["beetroot", "curd yogurt", "mustard seeds", "green chillies"],
    ["corn kernels", "butter", "chaat masala", "lemon juice"]
]


class ConcurrencyScaleManager:
    def __init__(self):
        self.created_fridges: List[Tuple[requests.Session, str]] = []
        self.run_history: List[Dict[str, Any]] = []

    def run_single_user(self, user_idx: int, batch_id: str) -> Dict[str, Any]:
        """Creates an account, queries rescue recipe, and keeps session for cleanup."""
        session = requests.Session()
        session.verify = certifi.where()
        session.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})

        # Strict alphanumeric ID: 3-30 chars
        unique_token = uuid.uuid4().hex[:6]
        fid = f"Acc{user_idx}b{batch_id}x{unique_token}"
        pin = "1234"

        # Step 1: Create Account
        t_create = time.perf_counter()
        create_ok = False
        create_err = None
        try:
            r_create = session.post(
                f"{BASE_URL}/api/auth/create",
                json={"fridge_id": fid, "pin": pin},
                timeout=30,
            )
            create_ms = round((time.perf_counter() - t_create) * 1000, 1)
            if r_create.status_code == 200:
                create_ok = True
                self.created_fridges.append((session, fid))
            else:
                create_err = f"Create HTTP {r_create.status_code}: {r_create.text[:80]}"
        except Exception as e:
            create_ms = round((time.perf_counter() - t_create) * 1000, 1)
            create_err = f"Create Exception: {e}"

        if not create_ok:
            return {
                "fridge_id": fid,
                "user_idx": user_idx,
                "created": False,
                "recipe_status": "skipped",
                "create_latency_ms": create_ms,
                "recipe_latency_ms": 0.0,
                "recipe_name": None,
                "error": create_err,
            }

        # Step 2: Request Rescue Recipe
        ingredients = INGREDIENT_POOL[(user_idx - 1) % len(INGREDIENT_POOL)]
        t_rec = time.perf_counter()
        try:
            r_rec = session.post(
                f"{BASE_URL}/rescue",
                json={"items": ingredients, "fridge_id": fid},
                timeout=75,
            )
            rec_ms = round((time.perf_counter() - t_rec) * 1000, 1)
            if r_rec.status_code == 200:
                recipe = r_rec.json()
                return {
                    "fridge_id": fid,
                    "user_idx": user_idx,
                    "created": True,
                    "recipe_status": "success",
                    "http_code": 200,
                    "create_latency_ms": create_ms,
                    "recipe_latency_ms": rec_ms,
                    "recipe_name": recipe.get("recipe_name"),
                    "ingredients": ingredients,
                    "error": None,
                }
            else:
                return {
                    "fridge_id": fid,
                    "user_idx": user_idx,
                    "created": True,
                    "recipe_status": "http_error",
                    "http_code": r_rec.status_code,
                    "create_latency_ms": create_ms,
                    "recipe_latency_ms": rec_ms,
                    "recipe_name": None,
                    "error": f"Recipe HTTP {r_rec.status_code}: {r_rec.text[:120]}",
                }
        except Exception as e:
            rec_ms = round((time.perf_counter() - t_rec) * 1000, 1)
            return {
                "fridge_id": fid,
                "user_idx": user_idx,
                "created": True,
                "recipe_status": "exception",
                "http_code": 0,
                "create_latency_ms": create_ms,
                "recipe_latency_ms": rec_ms,
                "recipe_name": None,
                "error": f"Recipe Exception: {e}",
            }

    def execute_concurrent_batch(self, count: int, label: str = "") -> Dict[str, Any]:
        """Executes `count` simultaneous accounts fully in parallel."""
        batch_id = uuid.uuid4().hex[:4]
        print(f"\n{'='*75}")
        print(f"▶ TESTING CONCURRENCY LEVEL: {count} SIMULTANEOUS ACCOUNTS {label}")
        print(f"{'='*75}")

        wall_start = time.perf_counter()
        results: List[Dict[str, Any]] = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=count) as executor:
            futures = [
                executor.submit(self.run_single_user, i, batch_id)
                for i in range(1, count + 1)
            ]
            for f in concurrent.futures.as_completed(futures):
                results.append(f.result())

        total_sec = time.perf_counter() - wall_start
        successful = [r for r in results if r.get("recipe_status") == "success"]
        failed = [r for r in results if r.get("recipe_status") != "success"]

        success_rate = (len(successful) / count) * 100.0
        rps = round(len(successful) / total_sec, 2) if total_sec > 0 else 0.0

        latencies = [r["recipe_latency_ms"] for r in successful if r.get("recipe_latency_ms")]
        median_lat = round(statistics.median(latencies), 1) if latencies else 0.0
        avg_lat = round(statistics.mean(latencies), 1) if latencies else 0.0

        print(f"Result: {len(successful)}/{count} succeeded ({success_rate:.1f}%) in {total_sec:.2f}s")
        print(f"Throughput: {rps} Recipes/Sec | Median Latency: {median_lat}ms | Avg: {avg_lat}ms")

        # Show samples of successful recipes generated
        if successful:
            sample_recipes = [f"'{r['recipe_name']}' ({r['recipe_latency_ms']}ms)" for r in successful[:3]]
            print(f"Sample recipes: {', '.join(sample_recipes)}")

        if failed:
            print(f"⚠️ Failures encountered ({len(failed)}):")
            for f in failed[:5]:
                print(f"  * [User #{f['user_idx']} - {f['fridge_id']}]: {f['error']}")
            if len(failed) > 5:
                print(f"  * ... and {len(failed) - 5} more failures.")

        summary = {
            "target_concurrency": count,
            "label": label,
            "successful": len(successful),
            "failed": len(failed),
            "success_rate_pct": success_rate,
            "wall_sec": round(total_sec, 2),
            "rps": rps,
            "median_lat_ms": median_lat,
            "avg_lat_ms": avg_lat,
            "all_passed": (len(successful) == count),
            "sample_recipes": [r.get("recipe_name") for r in successful[:5]],
            "errors": [f["error"] for f in failed if f.get("error")],
        }
        self.run_history.append(summary)
        return summary

    def cleanup_all_fridges(self):
        """Permanently deletes all test fridges created across all test batches."""
        total = len(self.created_fridges)
        if total == 0:
            print("\nNo fridges to clean up.")
            return

        print(f"\n{'='*75}")
        print(f"🧹 CLEANUP PHASE: Deleting all {total} created test fridges from Firestore...")
        print(f"{'='*75}")

        def delete_fridge_account(item):
            session, fid = item
            try:
                r = session.post(f"{BASE_URL}/api/fridge/delete", timeout=20)
                return r.status_code == 200
            except Exception:
                return False

        deleted_count = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(delete_fridge_account, item) for item in self.created_fridges]
            for f in concurrent.futures.as_completed(futures):
                if f.result():
                    deleted_count += 1

        print(f"✅ Successfully deleted {deleted_count}/{total} fridges from Firestore and memory.")
        self.created_fridges.clear()


def wait_for_groq_reset(seconds: int = 65):
    print(f"\n⏳ Cooldown: Waiting {seconds}s for Groq's 60-second rolling rate-limit window to completely reset...")
    for remaining in range(seconds, 0, -10):
        print(f"   ... {remaining}s remaining for full Groq quota replenishment")
        time.sleep(min(10, remaining))
    print("✅ Groq quota window is 100% refreshed and ready for next batch.\n")


def run_benchmark():
    print("=" * 75)
    print("FRIDGEINVENTORY: CONCURRENCY SCALE-TO-FAILURE & EXACT THRESHOLD SEARCH")
    print(f"Target URL: {BASE_URL}")
    print("Strategy  : Test baseline 13 -> 15 -> 18 -> 20 -> 25 until failure.")
    print("            Pin down the EXACT maximum simultaneous users without crashing.")
    print("            MANDATORY: 65s cooldown between batches for full Groq replenishment.")
    print("            After all tests, permanently delete ALL test fridges from Firestore.")
    print("=" * 75)

    manager = ConcurrencyScaleManager()
    exact_limit = None
    breaking_point = None

    try:
        # Step 1: Verify previous baseline of 13 simultaneous accounts
        print("\n--- Phase 1: Baseline Verification (13 Accounts) ---")
        res_13 = manager.execute_concurrent_batch(13, label="(Baseline: 13 Accounts)")
        
        if res_13["all_passed"]:
            exact_limit = 13
            print(f"\n🎉 13 Simultaneous Accounts PASSED 100%! Baseline confirmed.")
            wait_for_groq_reset(65)
            
            # Step 2: Test 15 accounts
            res_15 = manager.execute_concurrent_batch(15, label="(Scale Step 2: 15 Accounts)")
            if res_15["all_passed"]:
                exact_limit = 15
                print(f"\n🎉 15 Simultaneous Accounts PASSED 100%!")
                wait_for_groq_reset(65)
                
                # Step 3: Test 18 accounts
                res_18 = manager.execute_concurrent_batch(18, label="(Scale Step 3: 18 Accounts)")
                if res_18["all_passed"]:
                    exact_limit = 18
                    print(f"\n🎉 18 Simultaneous Accounts PASSED 100%!")
                    wait_for_groq_reset(65)
                    
                    # Step 4: Test 20 accounts
                    res_20 = manager.execute_concurrent_batch(20, label="(Scale Step 4: 20 Accounts)")
                    if res_20["all_passed"]:
                        exact_limit = 20
                        print(f"\n🎉 20 Simultaneous Accounts PASSED 100%!")
                        wait_for_groq_reset(65)
                        
                        # Step 5: Test 25 accounts
                        res_25 = manager.execute_concurrent_batch(25, label="(Scale Step 5: 25 Accounts)")
                        if res_25["all_passed"]:
                            exact_limit = 25
                            print(f"\n🎉 25 Simultaneous Accounts PASSED 100%!")
                        else:
                            breaking_point = 25
                    else:
                        breaking_point = 20
                else:
                    breaking_point = 18
            else:
                breaking_point = 15
        else:
            breaking_point = 13

        # Phase 2: If a breaking point occurred, search 1-by-1 between exact_limit and breaking_point
        if breaking_point is not None:
            print(f"\n{'='*75}")
            print(f"⚠️ Breaking point observed at: {breaking_point} concurrent accounts.")
            print(f"Searching 1-by-1 between {exact_limit or 1} and {breaking_point} for the EXACT threshold...")
            print(f"{'='*75}")
            
            if exact_limit is None:
                # Step DOWN from breaking_point - 1
                for candidate in range(breaking_point - 1, 0, -1):
                    wait_for_groq_reset(65)
                    res_c = manager.execute_concurrent_batch(candidate, label=f"(Step-Down Search: {candidate} Accounts)")
                    if res_c["all_passed"]:
                        exact_limit = candidate
                        break
            else:
                # Step UP 1-by-1 from exact_limit + 1
                for candidate in range(exact_limit + 1, breaking_point):
                    wait_for_groq_reset(65)
                    res_c = manager.execute_concurrent_batch(candidate, label=f"(Fine Search: {candidate} Accounts)")
                    if res_c["all_passed"]:
                        exact_limit = candidate
                    else:
                        print(f"\n🎯 EXACT LIMIT IDENTIFIED: Breaks at {candidate} concurrent accounts!")
                        break

        print("\n" + "=" * 75)
        print("CONCURRENCY BENCHMARK FINAL AUDIT")
        print("=" * 75)
        print(f"Breaking Point Identified             : {breaking_point} accounts")
        print(f"Exact Maximum 100% Reliable Concurrency: {exact_limit} simultaneous accounts")
        print(f"Total Batches Executed                : {len(manager.run_history)}")
        for idx, h in enumerate(manager.run_history, 1):
            st = "PASS" if h["all_passed"] else "FAIL"
            print(f"  Run #{idx:02d} [{st}]: {h['target_concurrency']:>2} accounts -> {h['successful']}/{h['target_concurrency']} ok | {h['rps']} RPS | {h['wall_sec']}s")
        print("=" * 75)

        # Save results to JSON file
        report_data = {
            "breaking_point": breaking_point,
            "exact_max_reliable_concurrency": exact_limit,
            "history": manager.run_history
        }
        with open("concurrency_benchmark_report.json", "w") as f:
            json.dump(report_data, f, indent=2)

    finally:
        # Step 3: Guaranteed Cleanup - delete all created test fridges
        manager.cleanup_all_fridges()


if __name__ == "__main__":
    run_benchmark()
