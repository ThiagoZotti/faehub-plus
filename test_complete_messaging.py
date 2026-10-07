import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database


class CompleteMessagingTests(unittest.TestCase):
    def test_direct_message_lifecycle_and_receipts(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(database, "DB_PATH", Path(folder) / "messages.db"):
            database.init_db()
            message_id = database.send_message("thiago.zotti", "aline", "Mensagem direta", "Primeira versão")
            visible = database.message_visible_to(message_id, "aline")
            self.assertEqual(visible["body"], "Primeira versão")
            self.assertIsNone(database.message_visible_to(message_id, "pablo.sousa"))

            self.assertTrue(database.edit_message(message_id, "thiago.zotti", "Versão editada"))
            self.assertFalse(database.edit_message(message_id, "aline", "Tentativa"))
            self.assertTrue(database.toggle_message_reaction(message_id, "aline", "👍"))
            self.assertFalse(database.toggle_message_reaction(message_id, "aline", "👍"))

            database.mark_messages_delivered("aline")
            database.mark_thread_read("aline", "thiago.zotti")
            message = next(row for row in database.get_messages("thiago.zotti") if row["id"] == message_id)
            self.assertEqual(message["body"], "Versão editada")
            self.assertEqual(message["receipt_count"], 1)
            self.assertEqual(message["read_count"], 1)

    def test_group_membership_and_group_messages(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(database, "DB_PATH", Path(folder) / "groups.db"):
            database.init_db()
            group_id = database.create_message_group(
                "Projeto Integrador", "3110", "aline", ["thiago.zotti", "jonathan.samuel"]
            )
            self.assertIn(group_id, {row["id"] for row in database.list_message_groups("thiago.zotti")})
            self.assertNotIn(group_id, {row["id"] for row in database.list_message_groups("pablo.sousa")})

            message_id = database.send_message(
                "thiago.zotti", "thiago.zotti", "Mensagem direta", "Atualização do grupo", group_id=group_id
            )
            self.assertEqual(database.get_group_messages(group_id, "jonathan.samuel")[-1]["id"], message_id)
            self.assertEqual(database.get_group_messages(group_id, "pablo.sousa"), [])
            database.mark_group_read("jonathan.samuel", group_id)
            message = database.get_group_messages(group_id, "thiago.zotti")[-1]
            self.assertEqual(message["receipt_count"], 2)
            self.assertEqual(message["read_count"], 1)


if __name__ == "__main__":
    unittest.main()
