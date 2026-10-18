"""Who uses the bot, how much, and what it turned away, served as the /bot-stats document muninn
reads (https://github.com/PlatanosVerdes/gonana#botstats-the-bot-stats-contract).

The people are kept on disk, written once a minute at most; the minute counts start over on
restart. Serve it on a port that is never published: the people list holds names.
"""
import json
import os
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DAY = 24 * 60  # minutes


def _iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat().replace("+00:00", "Z")


class Recorder:
    def __init__(self, path, now=time.time):
        self.path = path
        self.now = now
        self.lock = threading.Lock()
        self.people = {}
        self.messages = [0] * DAY
        self.rejected = [0] * DAY
        self.minute = int(now() // 60)
        self.dirty = False
        if os.path.exists(path):
            with open(path) as f:
                for p in json.load(f):
                    self.people[p["id"]] = p

    def message(self, user_id, name=None, username=None):
        """Count one update from a person, and refresh their name."""
        with self.lock:
            now = self.now()
            self._advance(now)
            self.messages[self.minute % DAY] += 1
            key = str(user_id)
            p = self.people.setdefault(key, {"id": key, "first_seen": now, "messages": 0})
            if name:
                p["name"] = name
            if username:
                p["username"] = username
            p["last_seen"] = now
            p["messages"] += 1
            self.dirty = True

    def reject(self):
        """Count one request turned away, by a rate limit or as abuse."""
        with self.lock:
            self._advance(self.now())
            self.rejected[self.minute % DAY] += 1

    def _advance(self, now):
        cur = int(now // 60)
        if cur <= self.minute:
            return
        for m in range(self.minute + 1, min(cur, self.minute + DAY) + 1):
            self.messages[m % DAY] = self.rejected[m % DAY] = 0
        self.minute = cur

    def snapshot(self, platform, bot, name="", extra=None):
        with self.lock:
            now = self.now()
            self._advance(now)
            people = sorted(self.people.values(), key=lambda p: p["last_seen"], reverse=True)
            day, week = 24 * 3600, 7 * 24 * 3600
            return {
                "platform": platform,
                "bot": bot,
                "name": name,
                "users": {
                    "total": len(people),
                    "active_24h": sum(1 for p in people if now - p["last_seen"] < day),
                    "active_7d": sum(1 for p in people if now - p["last_seen"] < week),
                    "new_24h": sum(1 for p in people if now - p["first_seen"] < day),
                },
                "people": [
                    {
                        "id": p["id"],
                        "name": p.get("name", ""),
                        "username": p.get("username", ""),
                        "first_seen": _iso(p["first_seen"]),
                        "last_seen": _iso(p["last_seen"]),
                        "messages": p["messages"],
                    }
                    for p in people
                ],
                "traffic": {
                    "per_minute": [self.messages[(self.minute - 59 + i) % DAY] for i in range(60)],
                    "messages_24h": sum(self.messages),
                    "rejected_24h": sum(self.rejected),
                },
                "extra": extra or [],
            }

    def save(self):
        with self.lock:
            if not self.dirty:
                return
            data = list(self.people.values())
            self.dirty = False
        tmp = os.path.join(os.path.dirname(self.path) or ".", "." + os.path.basename(self.path) + ".tmp")
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, self.path)

    def serve(self, addr, about):
        """Serve the document on addr (":9180") in a thread, and save the people once a minute.
        about() returns (platform, bot, name, extra) when asked."""
        host, _, port = addr.rpartition(":")
        recorder = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                body = json.dumps(recorder.snapshot(*about())).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer((host, int(port)), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()

        def keep_saving():
            while True:
                time.sleep(60)
                try:
                    recorder.save()
                except OSError:
                    pass

        threading.Thread(target=keep_saving, daemon=True).start()
        return server
