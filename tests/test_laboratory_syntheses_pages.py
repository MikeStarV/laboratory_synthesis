import hashlib
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from laboratory_syntheses.laboratory_syntheses_app import app
from laboratory_syntheses.laboratory_syntheses_data import LABORATORY_SYNTHESES
from laboratory_syntheses.laboratory_syntheses_models import LaboratorySynthesisStatus


class LaboratorySynthesesCollectionTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.media = patch("laboratory_syntheses.laboratory_syntheses_media.laboratory_synthesis_media_available", return_value=True)
        self.media.start()
        self.addCleanup(self.media.stop)
        self.addCleanup(self.client.close)

    def test_filter_boundaries_and_statuses(self):
        full = self.client.get("/laboratory_syntheses?laboratory_synthesis_max_duration=90")
        self.assertEqual(full.status_code, 200)
        self.assertEqual(full.text.count('class="catalog-card"'), 4)
        empty = self.client.get("/laboratory_syntheses?laboratory_synthesis_max_duration=0")
        self.assertEqual(empty.status_code, 200)
        self.assertNotIn('class="catalog-card"', empty.text)
        self.assertIn('value="0"', empty.text)
        self.assertEqual(self.client.get("/laboratory_syntheses/feed/5").status_code, 404)
        self.assertEqual(self.client.get("/laboratory_syntheses/feed/6").status_code, 404)

    def test_feed_next_likes_and_readonly_draft(self):
        response = self.client.get("/laboratory_syntheses/feed/1?next=true")
        self.assertIn("Получение йодоформа", response.text)
        self.assertIn('data-laboratory-likes-count>2<', response.text)
        for path in ("/laboratory_syntheses", "/laboratory_syntheses/feed", "/laboratory_syntheses/draft"):
            html = self.client.get(path).text
            self.assertNotIn("<script", html)
            self.assertNotIn("<style", html)
            self.assertNotIn("style=", html)
            self.assertEqual(html.count('class="nav-item'), 3)
        draft = self.client.get("/laboratory_syntheses/draft").text
        self.assertIn("Получение этилена", draft)
        self.assertNotIn('type="submit"', draft)
        self.assertEqual(self.client.post("/laboratory_syntheses/draft").status_code, 405)

    def test_published_media_are_distinct_and_descriptions_have_full_text(self):
        published = [item for item in LABORATORY_SYNTHESES if item.laboratory_synthesis_status == LaboratorySynthesisStatus.PUBLISHED]
        media = Path(__file__).resolve().parents[1] / "laboratory_syntheses/static/media"
        hashes = {hashlib.sha256((media / item.laboratory_synthesis_image_key).read_bytes()).hexdigest() for item in published}
        self.assertEqual(len(hashes), len(published))
        for item in published:
            self.assertGreater(len(item.laboratory_synthesis_description), 400)
            self.assertTrue((media/item.laboratory_synthesis_video_key).is_file())
            html = self.client.get(f"/laboratory_syntheses/feed/{item.laboratory_synthesis_id}").text
            self.assertIn(item.laboratory_synthesis_description, html)
