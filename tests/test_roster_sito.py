"""Test di RosterSito: la rosa costruita dai dati del sito (get_lineup), senza Excel.

Verifica che nome→(pid, ruolo) e l'insieme dei posseduti si ricavino da
`lineUpInfo`, così il bot è autonomo con le sole credenziali del sito.
Eseguibile con: python3 tests/test_roster_sito.py
"""
import os
import shutil
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
if not os.path.exists(os.path.join(ROOT, "config.py")):
    shutil.copy(os.path.join(ROOT, "config.example.py"), os.path.join(ROOT, "config.py"))

import build_payload as bp
from roster_map import RosterSito


def _giocatore(pid, plyr, role, tname="X"):
    return {"pid": pid, "plyr": plyr, "role": [role], "tname": tname,
            "percent": 90, "status": 1}


def _res(giocatori):
    return {"teamLineupDto": {"cmday": 4}, "lineUpInfo": giocatori}


# Rosa finta completa: 3 P, 8 D, 8 C, 6 A con pid progressivi.
def _rosa_completa():
    gioc, pid = [], 1000
    for role, n in ((1, 3), (2, 8), (3, 8), (4, 6)):
        for i in range(1, n + 1):
            lettera = {1: "P", 2: "D", 3: "C", 4: "A"}[role]
            gioc.append(_giocatore(pid, f"{lettera}{i}", role))
            pid += 1
    return gioc


class TestRosterSito(unittest.TestCase):
    def test_resolve_nome_a_pid_e_ruolo(self):
        rm = RosterSito(_res([_giocatore(4964, "Vicario", 1, "Juventus")]))
        self.assertEqual(rm.resolve("Vicario"), (4964, "P"))

    def test_mappa_ruoli_da_api(self):
        rm = RosterSito(_res([
            _giocatore(1, "Por", 1), _giocatore(2, "Dif", 2),
            _giocatore(3, "Cen", 3), _giocatore(4, "Att", 4)]))
        self.assertEqual(rm.resolve("Por")[1], "P")
        self.assertEqual(rm.resolve("Dif")[1], "D")
        self.assertEqual(rm.resolve("Cen")[1], "C")
        self.assertEqual(rm.resolve("Att")[1], "A")

    def test_role_of(self):
        rm = RosterSito(_res([_giocatore(2194, "Calhanoglu", 3)]))
        self.assertEqual(rm.role_of("Calhanoglu"), "C")

    def test_match_insensibile_a_maiuscole_e_accenti(self):
        rm = RosterSito(_res([_giocatore(1, "Kessié", 3)]))
        self.assertEqual(rm.resolve("kessie")[0], 1)

    def test_non_in_rosa_solleva(self):
        rm = RosterSito(_res([_giocatore(1, "Vicario", 1)]))
        with self.assertRaises(ValueError):
            rm.resolve("Sconosciuto")

    def test_owned_popolato(self):
        rm = RosterSito(_res([_giocatore(1, "A", 1), _giocatore(2, "B", 2)]))
        self.assertEqual(set(rm.owned), {"A", "B"})

    def test_aggiorna_sostituisce_la_rosa(self):
        rm = RosterSito(_res([_giocatore(1, "Vecchio", 1)]))
        rm.aggiorna(_res([_giocatore(2, "Nuovo", 1)]))
        self.assertEqual(rm.resolve("Nuovo"), (2, "P"))
        with self.assertRaises(ValueError):
            rm.resolve("Vecchio")

    def test_ignora_giocatori_senza_pid_o_nome(self):
        rm = RosterSito(_res([
            {"pid": None, "plyr": "SenzaId", "role": [1]},
            {"pid": 5, "plyr": "", "role": [1]},
            _giocatore(7, "Valido", 1)]))
        self.assertEqual(set(rm.owned), {"Valido"})

    def test_costruttore_vuoto_non_esplode(self):
        rm = RosterSito()
        self.assertEqual(rm.owned, {})

    def test_integrazione_build_payload(self):
        """Il payload di invio si costruisce interamente dalla rosa del sito."""
        rm = RosterSito(_res(_rosa_completa()))
        spec = {
            "modulo": "343",
            "titolari": ["P1", "D1", "D2", "D3", "C1", "C2", "C3", "C4", "A1", "A2", "A3"],
            "panchina": ["P2", "P3", "D4", "D5", "D6", "D7", "C5", "C6", "C7", "A4", "A5", "D8"],
            "capitano": [],
            "mday": 4,
        }
        payload = bp.build_payload(spec, rm=rm)
        self.assertEqual(payload["mdl"], "343")
        self.assertEqual(len(payload["starts"]), 11)
        self.assertEqual(len(payload["bench"]), 12)


if __name__ == "__main__":
    unittest.main()
