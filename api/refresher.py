import threading
import time

import duckdb

from config import CACHE_TTL_SECONDS, FEEDS, SCRAPERS
from feeds.cache import is_feed_stale
from feeds.fetcher import fetch_all
from feeds.scraper import scrape_all


class Refresher:
    """Fetches feeds on a background thread so requests never wait on the network.

    Runs once at startup, then every CACHE_TTL_SECONDS (re-fetching only stale
    feeds). `trigger()` forces a full re-fetch unless one is already running.
    """

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._force = False
        self._lock = threading.Lock()
        self.state = {
            "running": False,
            "done": 0,
            "total": 0,
            "current": "",
            "errors": [],
            "last_finished": None,
        }

    def start(self) -> None:
        threading.Thread(target=self._loop, name="feed-refresher", daemon=True).start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()

    def trigger(self) -> bool:
        with self._lock:
            if self.state["running"]:
                return False
            self._force = True
        self._wake.set()
        return True

    def _loop(self) -> None:
        cur = self._conn.cursor()  # DuckDB connections aren't shared across threads; cursors are
        while not self._stop.is_set():
            with self._lock:
                force, self._force = self._force, False
            self._run(cur, force)
            self._wake.wait(timeout=CACHE_TTL_SECONDS)
            self._wake.clear()

    def _run(self, cur, force: bool) -> None:
        sources = FEEDS + SCRAPERS
        total = sum(1 for f in sources if force or is_feed_stale(cur, f["id"], CACHE_TTL_SECONDS))
        if not total:
            return
        self.state.update(running=True, done=0, total=total, current="", errors=[])

        def on_feed(name, _new_count, error=False):
            self.state["done"] += 1
            self.state["current"] = name
            if error:
                self.state["errors"].append(name)

        try:
            fetch_all(FEEDS, cur, force=force, on_feed=on_feed)
            scrape_all(SCRAPERS, cur, force=force, on_feed=on_feed)
        finally:
            self.state.update(running=False, current="", last_finished=time.time())
