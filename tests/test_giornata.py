import unittest
from bot import giornata

RES = {
    "teamLineupDto": {"cmday": 4, "mday": 1},
    "lineUpInfo": [
        {"role": [1], "plyr": "Vicario", "tname": "Juventus", "teamH": "SAS",
         "teamA": "JUV", "hoaw": 1, "percent": 90, "status": 1, "agrd": 6.1, "fagrd": 5.8},
        {"role": [4], "plyr": "Kean", "tname": "Fiorentina", "teamH": "FIO",
         "teamA": "COM", "hoaw": 0, "percent": 95, "status": 1, "agrd": 7.0, "fagrd": 8.2},
        {"role": [3], "plyr": "Calhanoglu", "tname": "Inter", "teamH": "INT",
         "teamA": "TOR", "hoaw": 0, "percent": 88, "status": 2, "agrd": 6.5, "fagrd": 6.0},
    ],
}

class TestGiornata(unittest.TestCase):
    def test_cmday(self):
        self.assertEqual(giornata.cmday(RES), 4)

    def test_tabella_contiene_ruoli_nomi_stato(self):
        t = giornata.tabella_rosa(RES)
        self.assertIn("Vicario", t)
        self.assertIn("Kean", t)
        self.assertIn("INDISPONIBILE", t)          # Calhanoglu status 2
        self.assertIn("90%", t)                     # percentuale titolarità
        # ordine per reparto: il portiere compare prima dell'attaccante
        self.assertLess(t.index("Vicario"), t.index("Kean"))

    def test_squadre_utente_deduplicate_reali(self):
        sq = giornata.squadre_utente(RES)
        self.assertEqual(set(sq), {"Juventus", "Fiorentina", "Inter"})

if __name__ == "__main__":
    unittest.main()
