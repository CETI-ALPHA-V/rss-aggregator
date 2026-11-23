"""Live LLM benchmark data from LiveBench (https://livebench.ai).

LiveBench publishes each release as static files under /data/<YYYYMMDD>/ and
lists its releases (plus model display names and organisations) inside the
site's JavaScript bundle. We read the newest release from there, compute the
overall score and cost-per-successful-task the same way the site does, and
cache the result in data/livebench.json.

If LiveBench is unreachable or its format changes, the last good cache is
served; with no cache at all, the hand-maintained LLM_INVENTORY snapshot in
config.py is used instead.
"""
import csv
import io
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import requests

from config import LLM_INVENTORY, LLM_INVENTORY_SOURCE

BASE = "https://livebench.ai"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; mAIntain/1.0; +https://livebench.ai)"}
HF_API = "https://huggingface.co/api/models/{repo}"
HF_EXPAND = ["downloads", "likes", "cardData", "safetensors", "lastModified", "evalResults", "trendingScore"]
MAX_AGE_SECONDS = 24 * 3600
CHECK_EVERY_SECONDS = 3 * 3600
# Bump when the cached data's shape changes, so an old cache is refetched rather than served.
SCHEMA_VERSION = 2

# Model metadata entries in the minified bundle look like
#   "gpt-6-astra":{displayName:"GPT-6 Astra",organization:"OpenAI",…}
# and keys that are valid JS identifiers lose their quotes: inkling:{displayName:…}
_META_RE = re.compile(
    r'(?:"([A-Za-z0-9._\-]+)"|\b([A-Za-z_$][\w$]*)):\{displayName:"((?:[^"\\]|\\.)*)",organization:"((?:[^"\\]|\\.)*)"'
)


def _round1(x: float) -> float:
    """Round half up to 1 dp, like JavaScript's toFixed (Python's round() is half-to-even)."""
    return float(Decimal(repr(x)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def _get(url: str) -> requests.Response:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp


def _bundle() -> str:
    html = _get(f"{BASE}/").text
    m = re.search(r'/static/js/main\.[0-9a-f]+\.js', html)
    if not m:
        raise ValueError("LiveBench: main bundle not found in index.html")
    return _get(BASE + m.group(0)).text


def _release_dates(bundle: str) -> list[str]:
    today = date.today()
    dates = set()
    for d in re.findall(r'"(20\d{6})"', bundle):
        try:
            parsed = datetime.strptime(d, "%Y%m%d").date()
        except ValueError:
            continue
        if parsed <= today:
            dates.add(d)
    return sorted(dates, reverse=True)


def _model_metadata(bundle: str) -> dict[str, dict]:
    matches = list(_META_RE.finditer(bundle))
    meta = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else m.end() + 400
        segment = bundle[m.end():end]
        entry = segment.split("},", 1)[0]
        meta[m.group(1) or m.group(2)] = {
            "name": json.loads(f'"{m.group(3)}"'),
            "organization": json.loads(f'"{m.group(4)}"'),
            "open_weight": "openweight:!0" in entry,
            "url": (re.search(r'\burl:"([^"]+)"', entry) or [None, None])[1],
            "huggingface": (re.search(r'huggingface:"([^"]+)"', entry) or [None, None])[1],
        }
    return meta


def _hf_repo(url: str | None) -> str | None:
    m = re.match(r"https?://huggingface\.co/([^/?#]+/[^/?#]+)", url or "")
    return m.group(1) if m else None


def _hf_stats(repo: str) -> dict:
    """Adoption and licensing info for one Hugging Face repo. Never raises: on
    failure the model keeps its repo link and simply has no stats."""
    base = {"repo": repo, "url": f"https://huggingface.co/{repo}"}
    try:
        resp = requests.get(
            HF_API.format(repo=repo), params=[("expand[]", e) for e in HF_EXPAND], headers=HEADERS, timeout=20
        )
        resp.raise_for_status()
        d = resp.json()
    except Exception:
        return base

    card = d.get("cardData") or {}
    license_ = card.get("license")
    if license_ == "other":
        license_ = card.get("license_name") or "other"

    evals = []
    for r in d.get("evalResults") or []:
        data = r.get("data") or {}
        dataset = data.get("dataset") or {}
        if data.get("value") is None:
            continue
        evals.append({
            "benchmark": (dataset.get("id") or "").split("/")[-1] or r.get("filename"),
            "task": dataset.get("task_id"),
            "value": data.get("value"),
            "verified": bool(r.get("verified")),
            "source": (data.get("source") or {}).get("url"),
        })

    return {
        **base,
        "downloads": d.get("downloads"),  # Hugging Face reports the last 30 days
        "likes": d.get("likes"),
        "trending": d.get("trendingScore"),
        "license": license_,
        "params": (d.get("safetensors") or {}).get("total"),
        "updated": d.get("lastModified"),
        "evals": evals[:12],
    }


def _guess_org(model_id: str) -> str:
    prefixes = {
        "claude": "Anthropic", "gpt": "OpenAI", "o3": "OpenAI", "o4": "OpenAI", "gemini": "Google",
        "gemma": "Google", "grok": "xAI", "deepseek": "DeepSeek", "qwen": "Alibaba", "kimi": "Moonshot AI",
        "glm": "Z.AI", "mistral": "Mistral AI", "nemotron": "NVIDIA", "minimax": "MiniMax", "llama": "Meta",
        "muse": "Meta", "inkling": "Thinking Machines",
    }
    return next((org for p, org in prefixes.items() if model_id.startswith(p)), "Other")


def _num(value: str | None) -> float | None:
    try:
        return float(value) if value not in (None, "", "-") else None
    except ValueError:
        return None


def fetch_latest() -> dict:
    """Download and assemble the newest LiveBench release. Raises on any failure."""
    bundle = _bundle()
    meta = _model_metadata(bundle)

    release = table = None
    for d in _release_dates(bundle)[:5]:
        resp = requests.get(f"{BASE}/data/{d}/table.csv", headers=HEADERS, timeout=20)
        if resp.ok and resp.text.startswith("model,"):
            release, table = d, resp.text
            break
    if not release:
        raise ValueError("LiveBench: no release with a table.csv found")

    categories_raw = _get(f"{BASE}/data/{release}/categories.json").json()
    weights = categories_raw.pop("_overall_weights", {}) or {}
    categories = [
        {"key": re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_"), "label": name,
         "columns": cols, "weight": float(weights.get(name, 1.0))}
        for name, cols in categories_raw.items() if isinstance(cols, list)
    ]

    costs: dict[str, dict] = {}
    try:
        cost_text = _get(f"{BASE}/data/{release}/cost.csv").text
        costs = {row["model"]: row for row in csv.DictReader(io.StringIO(cost_text))}
    except Exception:
        pass  # cost is optional; scores still render without it

    items = []
    for row in csv.DictReader(io.StringIO(table)):
        model_id = row["model"]
        scores = {}
        for c in categories:
            vals = [v for v in (_num(row.get(col)) for col in c["columns"]) if v is not None]
            scores[c["key"]] = _round1(sum(vals) / len(vals)) if vals else None

        weighted = [(scores[c["key"]], c["weight"]) for c in categories if scores[c["key"]] is not None]
        total_w = sum(w for _, w in weighted)
        overall = _round1(sum(s * w for s, w in weighted) / total_w) if total_w else None

        # Matches the site: (Σ cost ÷ Σ questions) ÷ overall × 100, over every scored column.
        cost = None
        cost_row = costs.get(model_id)
        if cost_row and overall:
            spent = answered = 0.0
            for c in categories:
                for col in c["columns"]:
                    amount, n = _num(cost_row.get(col)), _num(cost_row.get(f"nq_{col}"))
                    if amount is not None and n:
                        spent += amount
                        answered += n
            if answered:
                unrounded = sum(s * w for s, w in weighted) / total_w
                cost = round(spent / answered / unrounded * 100, 3)

        info = meta.get(model_id, {})
        items.append({
            "id": model_id,
            "model": info.get("name") or model_id,
            "provider": info.get("organization") or _guess_org(model_id),
            "tier": "Open Source" if info.get("open_weight") else "Frontier",
            "url": info.get("url"),
            "overall": overall,
            "scores": scores,
            "cost": cost,
            "hf": None,
            "_hf_repo": _hf_repo(info.get("huggingface")),
        })

    # Cross-reference open-weight models with Hugging Face (closed models have no repo).
    repos = sorted({m["_hf_repo"] for m in items if m["_hf_repo"]})
    with ThreadPoolExecutor(max_workers=8) as pool:
        hf = dict(zip(repos, pool.map(_hf_stats, repos)))
    for m in items:
        repo = m.pop("_hf_repo")
        m["hf"] = hf.get(repo) if repo else None

    items.sort(key=lambda m: m["overall"] or 0, reverse=True)
    pretty = f"{release[:4]}-{release[4:6]}-{release[6:]}"
    return {
        "schema": SCHEMA_VERSION,
        "source": f"LiveBench — {pretty} release",
        "release": pretty,
        "live": True,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "categories": [{k: c[k] for k in ("key", "label", "weight")} for c in categories],
        "items": items,
        "unmatched_metadata": sorted(m["id"] for m in items if m["id"] not in meta),
    }


def _static_fallback() -> dict:
    """The hand-maintained snapshot from config.py, in the same shape as fetch_latest()."""
    cat_keys = ["reasoning", "coding", "agentic_coding", "mathematics", "data_analysis", "language", "instruction_following"]
    labels = {"agentic_coding": "Agentic Coding", "data_analysis": "Data Analysis", "instruction_following": "Instruction Following"}
    return {
        "source": LLM_INVENTORY_SOURCE,
        "release": None,
        "live": False,
        "fetched_at": None,
        "categories": [{"key": k, "label": labels.get(k, k.title()), "weight": 1.0} for k in cat_keys],
        "items": [
            {"id": m["model"], "model": m["model"], "provider": m["provider"], "tier": m["tier"], "url": None,
             "overall": m["overall"], "scores": {k: m[k] for k in cat_keys}, "cost": m["cost"], "hf": None}
            for m in LLM_INVENTORY
        ],
        "unmatched_metadata": [],
    }


class BenchmarkStore:
    """Holds the latest benchmark data and refreshes it in the background."""

    def __init__(self, cache_path: Path):
        self._cache_path = cache_path
        self._lock = threading.Lock()
        self._refreshing = False
        self.last_error: str | None = None
        self._data = self._load_cache() or _static_fallback()

    def _load_cache(self) -> dict | None:
        try:
            return json.loads(self._cache_path.read_text())
        except Exception:
            return None

    def get(self) -> dict:
        return {**self._data, "last_error": self.last_error}

    def _age(self) -> float:
        fetched = self._data.get("fetched_at")
        if not fetched or self._data.get("schema") != SCHEMA_VERSION:
            return float("inf")
        return (datetime.now(timezone.utc) - datetime.fromisoformat(fetched)).total_seconds()

    def refresh(self) -> None:
        with self._lock:
            if self._refreshing:
                return
            self._refreshing = True
        try:
            data = fetch_latest()
            self._data = data
            self.last_error = None
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache_path.write_text(json.dumps(data))
        except Exception as e:
            self.last_error = f"{type(e).__name__}: {e}"[:300]
        finally:
            self._refreshing = False

    def refresh_async(self) -> None:
        threading.Thread(target=self.refresh, name="benchmarks-refresh", daemon=True).start()

    def start(self) -> None:
        def loop():
            while True:
                if self._age() > MAX_AGE_SECONDS:
                    self.refresh()
                time.sleep(CHECK_EVERY_SECONDS)

        threading.Thread(target=loop, name="benchmarks-loop", daemon=True).start()
