"""Test autonomo di build_payload — nessun dato personale, nessuna rete.

Usa una rosa finta (RosterMap simulato) per verificare la costruzione e le
validazioni del payload. Eseguibile con: python3 tests/test_build_payload.py
"""

import os
import shutil
import sys

# Rendi importabili i moduli dalla root del progetto.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Se manca config.py, crealo dal template (placeholder) così il test gira sempre.
if not os.path.exists(os.path.join(ROOT, "config.py")):
    shutil.copy(os.path.join(ROOT, "config.example.py"), os.path.join(ROOT, "config.py"))

import build_payload as bp


class FakeRoster:
    """RosterMap simulato: 3 P, 8 D, 8 C, 6 A con id fittizi."""

    def __init__(self):
        self.players = {}
        pid = 1
        for role, n in (("P", 3), ("D", 8), ("C", 8), ("A", 6)):
            for i in range(1, n + 1):
                self.players[f"{role}{i}"] = (pid, role)
                pid += 1

    def resolve(self, name, require_owned=True):
        if name not in self.players:
            raise ValueError(f"'{name}' non è nella tua rosa")
        return self.players[name]


rm = FakeRoster()

# 3-4-3 valido: 1 P, 3 D, 4 C, 3 A + 12 in panchina.
SPEC_OK = {
    "modulo": "3-4-3",
    "titolari": ["P1", "D1", "D2", "D3", "C1", "C2", "C3", "C4", "A1", "A2", "A3"],
    "panchina": ["P2", "P3", "D4", "D5", "D6", "D7", "C5", "C6", "C7", "A4", "A5", "D8"],
    "capitano": [],
}


def ok(m):
    print(f"  ✓ {m}")


def deve_fallire(descr, mutazione):
    s = {k: (list(v) if isinstance(v, list) else v) for k, v in SPEC_OK.items()}
    mutazione(s)
    try:
        bp.build_payload(s, rm=rm)
    except bp.ValidationError:
        ok(f"rifiutato correttamente: {descr}")
    else:
        raise AssertionError(f"NON rifiutato: {descr}")


def main():
    p = bp.build_payload(SPEC_OK, rm=rm)
    assert p["mdl"] == "343", p["mdl"]
    ok("modulo 4-3-3/3-4-3 normalizzato a 343")
    # ordine atteso P, D, C, A
    assert p["starts"] == [1, 4, 5, 6, 12, 13, 14, 15, 20, 21, 22], p["starts"]
    ok(f"11 titolari ordinati P,D,C,A → {p['starts']}")
    assert len(p["bench"]) == 12
    ok("panchina di esattamente 12")

    deve_fallire("modulo non ammesso", lambda s: s.update(modulo="424"))
    deve_fallire("solo 10 titolari", lambda s: s.update(titolari=SPEC_OK["titolari"][:10]))
    deve_fallire("reparti incoerenti col modulo", lambda s: s.update(modulo="433"))
    deve_fallire("giocatore non in rosa",
                 lambda s: s.update(titolari=["X1"] + SPEC_OK["titolari"][1:]))
    deve_fallire("panchina non esattamente 12 (fissa)",
                 lambda s: s.update(panchina=SPEC_OK["panchina"][:9]))

    print("\n>>> TUTTI I TEST PASSATI.")


if __name__ == "__main__":
    main()
