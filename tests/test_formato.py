import unittest
from datetime import datetime, timezone
from bot import formato

RUOLI = {"Vicario": "P", "Wesley": "D", "Spinazzola": "D", "Chalobah T.": "D",
         "Miranda J.": "D", "Calhanoglu": "C", "Bernardeschi": "C", "Kessiè": "C",
         "De Ketelaere": "A", "Kean": "A", "Douvikas": "A",
         "Corvi": "P", "Grabara": "P"}
SPEC = {"modulo": "433",
        "titolari": ["Vicario", "Wesley", "Spinazzola", "Chalobah T.", "Miranda J.",
                     "Calhanoglu", "Bernardeschi", "Kessiè", "De Ketelaere", "Kean", "Douvikas"],
        "panchina": ["Corvi", "Grabara"]}
ORA = datetime(2026, 9, 11, 20, 15, tzinfo=timezone.utc)


class TestFormato(unittest.TestCase):
    def test_fmt_modulo(self):
        self.assertEqual(formato.fmt_modulo("433"), "4-3-3")
        self.assertEqual(formato.fmt_modulo("3-4-3"), "3-4-3")

    def test_campo_raggruppa_per_reparto(self):
        c = formato.campo(SPEC["titolari"], RUOLI)
        righe = c.split("\n")
        self.assertEqual(len(righe), 4)  # P, D, C, A
        self.assertIn("🧤", righe[0]); self.assertIn("Vicario", righe[0])
        self.assertIn("🛡", righe[1]); self.assertIn("Wesley · Spinazzola · Chalobah T. · Miranda J.", righe[1])
        self.assertIn("🎯", righe[2])
        self.assertIn("🔥", righe[3]); self.assertIn("Douvikas", righe[3])

    def test_campo_nomi_senza_ruolo_non_persi(self):
        c = formato.campo(["Vicario", "Ignoto"], {"Vicario": "P"})
        self.assertIn("Ignoto", c)
        self.assertIn("▪️", c)

    def test_panchina_numerata_con_cerchi(self):
        p = formato.panchina(["Corvi", "Grabara"])
        self.assertTrue(p.startswith("① Corvi"))
        self.assertIn("② Grabara", p)

    def test_messaggio_proposta_completo(self):
        m = formato.messaggio_proposta(SPEC, RUOLI, "Fandagalgio il ritorno", 4, ORA)
        self.assertIn("Fandagalgio il ritorno", m)
        self.assertIn("Giornata 4", m)
        self.assertIn("4-3-3", m)
        self.assertIn("20:15", m)
        for n in SPEC["titolari"]:
            self.assertIn(n, m)          # tutti gli 11 presenti
        self.assertIn("Panchina", m)

    def test_messaggio_proposta_senza_lega(self):
        m = formato.messaggio_proposta(SPEC, RUOLI, "", 4, None)
        self.assertIn("Giornata 4", m)
        self.assertIn("?", m)            # ora limite mancante

    def test_messaggio_sito(self):
        m = formato.messaggio_sito(["Vicario"], ["Corvi"], {"Vicario": "P", "Corvi": "P"}, "352")
        self.assertIn("Sul sito ora", m)
        self.assertIn("3-5-2", m)
        self.assertIn("Vicario", m)
        self.assertIn("Corvi", m)

    def test_escape_html(self):
        m = formato.campo(["A<b>&"], {"A<b>&": "P"})
        self.assertIn("&lt;", m); self.assertIn("&amp;", m)


if __name__ == "__main__":
    unittest.main()
