import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from bot import orari

TZ = "Europe/Rome"
def R(y, m, d, hh, mm): return datetime(y, m, d, hh, mm, tzinfo=ZoneInfo(TZ))
CUTOFF = {5: "12:15", 6: "12:15", 0: "18:15", 1: "18:15", 2: "18:15", 3: "18:15", 4: "18:15"}

class TestOrari(unittest.TestCase):
    def test_primo_kickoff_meno_buffer(self):
        cal = [{"squadra": "Inter", "kickoff": "2026-09-12T20:45"},
               {"squadra": "Juventus", "kickoff": "2026-09-12T15:00"}]
        adesso = R(2026, 9, 12, 8, 0)
        limite = orari.ora_limite(cal, 30, adesso, CUTOFF, TZ)
        self.assertEqual(limite, R(2026, 9, 12, 14, 30))   # 15:00 − 30min

    def test_calendario_vuoto_usa_cutoff_del_giorno(self):
        adesso = R(2026, 9, 12, 8, 0)   # 2026-09-12 è sabato → weekday 5 → 12:15
        limite = orari.ora_limite([], 30, adesso, CUTOFF, TZ)
        self.assertEqual(limite, R(2026, 9, 12, 12, 15))

    def test_kickoff_nel_passato_o_troppo_lontano_scartato(self):
        self.assertFalse(orari.calendario_valido(
            [{"squadra": "X", "kickoff": "2026-09-10T15:00"}], R(2026, 9, 12, 8, 0)))
        self.assertFalse(orari.calendario_valido(
            [{"squadra": "X", "kickoff": "2026-10-30T15:00"}], R(2026, 9, 12, 8, 0)))
        self.assertTrue(orari.calendario_valido(
            [{"squadra": "X", "kickoff": "2026-09-12T15:00"}], R(2026, 9, 12, 8, 0)))

if __name__ == "__main__":
    unittest.main()
