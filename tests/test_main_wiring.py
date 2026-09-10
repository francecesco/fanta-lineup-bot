import os, tempfile, unittest
from bot import main
from bot.settings import Settings
from bot.engine import Engine
from bot.state import Store

def _settings(db):
    return Settings("u", "p", "gk", "tok", "999",
                    lega={"idcomp": 700047, "id_squadra": 1, "divisione": "A"}, db_path=db)

class TestWiring(unittest.TestCase):
    def test_costruisci_senza_rete(self):
        db = tempfile.mktemp(suffix=".db"); self.addCleanup(lambda: os.path.exists(db) and os.remove(db))
        # rm iniettato (dummy): così il wiring test NON carica xlsx/openpyxl (resta ermetico).
        engine, store, provider_factory = main.costruisci(_settings(db), rm=object())
        self.assertIsInstance(engine, Engine)
        self.assertIsInstance(store, Store)
        self.assertTrue(callable(provider_factory))
        store.chiudi()

if __name__ == "__main__":
    unittest.main()
