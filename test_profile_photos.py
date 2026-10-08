import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image, PngImagePlugin

import database as db
import profile_photos
from app import app
from director import access_version, init_director


class ProfilePhotoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.db_patch = patch.object(db, "DB_PATH", Path(cls.temp.name) / "photos.db")
        cls.db_patch.start()
        db.init_db()
        init_director()

    @classmethod
    def tearDownClass(cls):
        cls.db_patch.stop()
        cls.temp.cleanup()

    def setUp(self):
        with db.connection() as conn:
            conn.execute("DELETE FROM profile_photos")
        self.client = self.login("thiago.zotti", "aluno", "23081")
        self.client.get("/painel")
        with self.client.session_transaction() as session:
            self.token = session["profile_token"]

    def login(self, username, role, student_id=None):
        client = app.test_client()
        with client.session_transaction() as session:
            session.update(username=username, role=role, display_name="Conta de teste",
                           auth_version=access_version(username))
            if student_id:
                session["aluno_id"] = student_id
        return client

    def source(self):
        output = BytesIO()
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("Comment", "private-source-metadata")
        Image.new("RGB", (600, 400), (25, 90, 160)).save(output, format="PNG", pnginfo=metadata)
        output.seek(0)
        return output

    def upload(self, **extra):
        return self.client.post("/perfil/foto", data={
            "token": self.token, "photo": (self.source(), "foto.png"), **extra,
        }, content_type="multipart/form-data")

    def test_photo_is_small_jpeg_without_source_metadata(self):
        response = self.upload()
        self.assertEqual(response.status_code, 200)
        result = self.client.get(response.json["url"])
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.mimetype, "image/jpeg")
        self.assertIn("private", result.headers["Cache-Control"])
        self.assertIn("Cookie", result.headers["Vary"])
        self.assertLessEqual(len(result.data), profile_photos.MAX_PHOTO_BYTES)
        with Image.open(BytesIO(result.data)) as image:
            self.assertEqual(image.size, (320, 320))
            self.assertNotIn("Comment", image.info)
            self.assertEqual(len(image.getexif()), 0)

    def test_photo_persists_across_new_sessions(self):
        revision = self.upload().json["revision"]
        another_session = self.login("thiago.zotti", "aluno", "23081")
        response = another_session.get("/painel")
        self.assertIn(revision.encode(), response.data)
        self.assertEqual(another_session.get("/perfil/foto").status_code, 200)

    def test_cross_account_reads_and_writes_use_session_owner(self):
        self.assertEqual(self.upload(username="gilberto").status_code, 200)
        self.assertTrue(profile_photos.photo_revision("thiago.zotti"))
        self.assertEqual(profile_photos.photo_revision("gilberto"), "")
        director = self.login("gilberto", "admin")
        self.assertEqual(director.get("/perfil/foto?username=thiago.zotti").status_code, 404)
        anonymous = app.test_client()
        denied = anonymous.get("/perfil/foto")
        self.assertEqual(denied.status_code, 302)
        self.assertEqual(denied.headers["Cache-Control"], "no-store")

    def test_invalid_token_never_changes_photo(self):
        self.upload()
        before = profile_photos.photo_revision("thiago.zotti")
        self.assertEqual(self.upload(token="invalid").status_code, 400)
        self.assertEqual(profile_photos.photo_revision("thiago.zotti"), before)

    def test_invalid_content_and_oversize_keep_previous_photo(self):
        self.upload()
        revision = profile_photos.photo_revision("thiago.zotti")
        for content in (b"<svg><script>invalid</script></svg>", b"x" * (5 * 1024 * 1024 + 1)):
            response = self.client.post("/perfil/foto", data={
                "token": self.token, "photo": (BytesIO(content), "fake.png"),
            }, content_type="multipart/form-data")
            self.assertEqual(response.status_code, 422)
            response.close()
            response.request.close()
            response.request.environ["wsgi.input"].close()
        self.assertEqual(profile_photos.photo_revision("thiago.zotti"), revision)

    def test_remove_is_scoped_and_restores_initials(self):
        self.upload()
        response = self.client.post("/perfil/foto", data={"token": self.token, "action": "remove"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["url"], "")
        self.assertEqual(self.client.get("/perfil/foto").status_code, 404)

    def test_navigation_reuses_photo_metadata_from_signed_session(self):
        with patch("app.profile_photos.photo_revision") as lookup:
            self.client.get("/painel")
            self.client.get("/boletim")
            lookup.assert_not_called()


if __name__ == "__main__":
    unittest.main()
