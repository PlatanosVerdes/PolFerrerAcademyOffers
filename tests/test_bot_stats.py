import json
import os
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bot_stats import Recorder

START = 1_792_330_830  # 2026-10-18 12:00:30 UTC


class Clock:
    def __init__(self):
        self.t = START

    def __call__(self):
        return self.t


class RecorderTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.clock = Clock()
        self.rec = Recorder(os.path.join(self.dir, "stats.json"), now=self.clock)

    def test_counts_people_and_traffic(self):
        self.rec.message(1, "Ana", "ana")
        self.rec.message(1)
        self.rec.message(2, "Bob")
        self.rec.reject()
        self.clock.t += 180
        self.rec.message(2, "Bobby", "bobby")
        s = self.rec.snapshot("telegram", "PolBot")
        self.assertEqual(s["users"], {"total": 2, "active_24h": 2, "active_7d": 2, "new_24h": 2})
        self.assertEqual((s["traffic"]["messages_24h"], s["traffic"]["rejected_24h"]), (4, 1))
        self.assertEqual(s["traffic"]["per_minute"][-1], 1)
        self.assertEqual(s["traffic"]["per_minute"][-4], 3)
        self.assertEqual((s["people"][0]["name"], s["people"][0]["username"]), ("Bobby", "bobby"))
        self.assertEqual(s["people"][1]["name"], "Ana")

    def test_old_traffic_ages_out(self):
        self.rec.message(1, "Ana")
        self.clock.t += 25 * 3600
        s = self.rec.snapshot("telegram", "PolBot")
        self.assertEqual(s["traffic"]["messages_24h"], 0)
        self.assertEqual((s["users"]["active_24h"], s["users"]["active_7d"]), (0, 1))

    def test_people_survive_a_restart(self):
        self.rec.message(7, "Eve", "eve")
        self.rec.save()
        again = Recorder(self.rec.path, now=self.clock)
        s = again.snapshot("telegram", "PolBot")
        self.assertEqual((s["users"]["total"], s["people"][0]["name"]), (1, "Eve"))

    def test_serves_the_document(self):
        self.rec.message(1, "Ana")
        server = self.rec.serve("127.0.0.1:0", lambda: ("telegram", "PolBot", "Pol", [{"label": "Subscribers", "value": "3"}]))
        port = server.server_address[1]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/bot-stats") as r:
            doc = json.load(r)
        server.shutdown()
        server.server_close()
        self.assertEqual((doc["bot"], doc["users"]["total"], doc["extra"][0]["value"]), ("PolBot", 1, "3"))


if __name__ == "__main__":
    unittest.main()
