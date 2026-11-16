import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from lean_memory.store import Store


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name))

    def test_create_search_read_and_update(self):
        task = self.store.save("Tela de cadastro", "Validar endereço e testar amanhã")
        results = self.store.search("endereco")
        self.assertEqual(results[0]["id"], task["id"])
        self.assertNotIn("summary", results[0])
        self.assertEqual(self.store.read(task["id"])["summary"], "Validar endereço e testar amanhã")
        updated = self.store.save("Cadastro pronto", "Testes passaram", task["id"], "completed", 1)
        self.assertEqual(updated["revision"], 2)
        self.assertEqual(self.store.search("endereco"), [])
        self.assertEqual(self.store.search("passaram")[0]["status"], "completed")

    def test_update_rejects_stale_or_missing_revision(self):
        task = self.store.save("Atualização", "Primeiro estado")
        with self.assertRaisesRegex(ValueError, "expected_revision"):
            self.store.save("Atualização", "Nova versão", task["id"])
        self.store.save("Atualização", "Segunda versão", task["id"], expected_revision=1)
        with self.assertRaisesRegex(ValueError, "Revision conflict"):
            self.store.save("Atualização", "Estado antigo", task["id"], expected_revision=1)
        self.assertEqual(self.store.read(task["id"])["summary"], "Segunda versão")

    def test_two_updates_from_same_revision_only_one_succeeds(self):
        task_id = self.store.save("Concorrência", "Estado inicial")["id"]
        def update(value):
            try:
                self.store.save("Concorrência", value, task_id, expected_revision=1)
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(update, ["A", "B"]))
        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(self.store.read(task_id)["revision"], 2)

    def test_search_escapes_query_and_limits_results(self):
        for i in range(7):
            self.store.save(f"Projeto {i}", "Uma pendência")
        self.assertEqual(len(self.store.search('projeto " OR *', 3)), 3)
        with self.assertRaises(ValueError):
            self.store.search("***")
        with self.assertRaises(ValueError):
            self.store.search("projeto", 11)

    def test_validation_and_database_isolation(self):
        with self.assertRaises(ValueError):
            self.store.save("", "resumo")
        with self.assertRaises(ValueError):
            self.store.save("Título", "x" * 12001)
        with self.assertRaises(ValueError):
            self.store.save("Título", "resumo", "000000000000", expected_revision=1)
        with self.assertRaises(ValueError):
            self.store.read("../../x")
        self.store.save("Segredo de teste", "Exemplo local")
        other = Store(Path(self.tmp.name) / "other")
        self.assertEqual(other.search("segredo"), [])


if __name__ == "__main__":
    unittest.main()
