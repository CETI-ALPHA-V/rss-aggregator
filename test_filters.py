"""
Tests that apply_filters correctly filters articles for every sidebar control.
Each test prints PASS or FAIL with a description of what was checked.
"""
import sys
import pandas as pd
from ui.feed_view import apply_filters

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
failures = []


def check(label, got, expected):
    ok = got == expected
    tag = PASS if ok else FAIL
    print(f"  [{tag}] {label} — got {got}, expected {expected}")
    if not ok:
        failures.append(label)


# ── Base dataset ─────────────────────────────────────────────────────────────
rows = [
    # within 2-month window
    {"feed_id":"a","link":"https://openai.com/1",    "title":"OAI blog",     "summary":"s","published":"2026-04-01T00:00:00Z","platform":"OpenAI",       "category":"AI",         "type":"blog"},
    {"feed_id":"b","link":"https://github.com/1",    "title":"OAI release",  "summary":"s","published":"2026-04-10T00:00:00Z","platform":"OpenAI",       "category":"AI",         "type":"releases"},
    {"feed_id":"c","link":"https://anthropic.com/1", "title":"Claude news",  "summary":"s","published":"2026-05-01T00:00:00Z","platform":"Anthropic",    "category":"AI",         "type":"blog"},
    {"feed_id":"d","link":"https://snowflake.com/1", "title":"SF release",   "summary":"s","published":"2026-04-20T00:00:00Z","platform":"Snowflake",    "category":"Data Tools", "type":"releases"},
    {"feed_id":"e","link":"https://databricks.com/1","title":"DB blog",      "summary":"s","published":"2026-04-25T00:00:00Z","platform":"Databricks",   "category":"Data Tools", "type":"blog"},
    {"feed_id":"f","link":"https://aws.amazon.com/1","title":"AWS release",  "summary":"s","published":"2026-04-28T00:00:00Z","platform":"AWS",          "category":"Cloud",      "type":"releases"},
    {"feed_id":"g","link":"https://airflow.com/1",   "title":"Airflow rel",  "summary":"s","published":"2026-04-15T00:00:00Z","platform":"Apache Airflow","category":"Orchestration","type":"releases"},
    # outside 2-month window — should always be excluded
    {"feed_id":"h","link":"https://old.com/1",       "title":"Old article",  "summary":"s","published":"2025-01-01T00:00:00Z","platform":"OpenAI",       "category":"AI",         "type":"blog"},
    # no date — should be kept
    {"feed_id":"i","link":"https://nodate.com/1",    "title":"No date art",  "summary":"s","published":"",                    "platform":"Anthropic",    "category":"AI",         "type":"blog"},
]
df = pd.DataFrame(rows)

all_cats      = ["AI", "Data Tools", "Cloud", "Orchestration"]
all_platforms = ["OpenAI", "Anthropic", "Snowflake", "Databricks", "AWS", "Apache Airflow"]

base_filters = {
    "categories": all_cats,
    "platforms":  all_platforms,
    "type":       "All",
    "keyword":    "",
}

print("\n=== Date cutoff ===")
result = apply_filters(df, base_filters)
# 'Old article' (2025) excluded; 'No date art' kept; 7 fresh rows remain = 8 total
check("Old article excluded",        "Old article" not in result["title"].tolist(), True)
check("No-date article kept",        "No date art"  in result["title"].tolist(),    True)
check("Total rows (7 fresh + 1 no-date)", len(result), 8)

print("\n=== Category filter ===")
f_ai = {**base_filters, "categories": ["AI"]}
result = apply_filters(df, f_ai)
check("Only AI category rows returned",  set(result["category"].tolist()),  {"AI"})
check("AI count (3 fresh + 1 no-date)", len(result), 4)

f_data = {**base_filters, "categories": ["Data Tools"]}
result = apply_filters(df, f_data)
check("Only Data Tools rows returned", set(result["category"].tolist()), {"Data Tools"})
check("Data Tools count",              len(result), 2)

f_multi = {**base_filters, "categories": ["Cloud", "Orchestration"]}
result = apply_filters(df, f_multi)
check("Cloud + Orchestration only", set(result["category"].tolist()), {"Cloud", "Orchestration"})
check("Cloud + Orchestration count", len(result), 2)

print("\n=== Platform filter ===")
f_plat = {**base_filters, "platforms": ["Anthropic"]}
result = apply_filters(df, f_plat)
check("Only Anthropic platform",         set(result["platform"].tolist()), {"Anthropic"})
check("Anthropic count (1 fresh + 1 no-date)", len(result), 2)

f_plat2 = {**base_filters, "platforms": ["OpenAI", "AWS"]}
result = apply_filters(df, f_plat2)
check("OpenAI + AWS platforms only", set(result["platform"].tolist()), {"OpenAI", "AWS"})
check("OpenAI + AWS count",          len(result), 3)

f_empty_plat = {**base_filters, "platforms": []}
result = apply_filters(df, f_empty_plat)
check("Empty platform list = show all", len(result), 8)

print("\n=== Content type filter ===")
f_blog = {**base_filters, "type": "blog"}
result = apply_filters(df, f_blog)
check("Blog only — no releases", "releases" not in result["type"].tolist(), True)
check("Blog count (3 fresh + 1 no-date)", len(result), 4)

f_rel = {**base_filters, "type": "releases"}
result = apply_filters(df, f_rel)
check("Releases only — no blogs", "blog" not in result["type"].tolist(), True)
check("Releases count",           len(result), 4)

print("\n=== Combined filters ===")
f_combo = {**base_filters, "categories": ["AI"], "platforms": ["OpenAI"], "type": "blog"}
result = apply_filters(df, f_combo)
check("AI + OpenAI + blog", len(result), 1)
check("Correct title", result["title"].iloc[0], "OAI blog")

f_combo2 = {**base_filters, "categories": ["Data Tools"], "type": "releases"}
result = apply_filters(df, f_combo2)
check("Data Tools + releases", len(result), 1)
check("Correct title", result["title"].iloc[0], "SF release")

# ── Summary ──────────────────────────────────────────────────────────────────
print()
if failures:
    print(f"\033[31m{len(failures)} test(s) FAILED:\033[0m", failures)
    sys.exit(1)
else:
    print(f"\033[32mAll tests passed.\033[0m")
