import unittest
from bot.invio import invia, InvioError

class FakeRoster:
    RUOLI = {**{f"P{i}": "P" for i in range(3)}, **{f"D{i}": "D" for i in range(8)},
             **{f"C{i}": "C" for i in range(8)}, **{f"A{i}": "A" for i in range(6)}}
    def resolve(self, nome, require_owned=True):
        if nome not in self.RUOLI:
            raise ValueError(f"'{nome}' non in rosa")
        return (abs(hash(nome)) % 100000, self.RUOLI[nome])   # (id, ruolo), come il RosterMap reale

def _spec():
    tit = ["P0"] + [f"D{i}" for i in range(3)] + [f"C{i}" for i in range(4)] + [f"A{i}" for i in range(3)]
    panca = ["P1", "P2"] + [f"D{i}" for i in range(3, 8)] + [f"C{i}" for i in range(4, 8)] + ["A3"]
    return {"modulo": "343", "titolari": tit, "panchina": panca, "capitano": []}

class FakeSession:
    def __init__(self, salva_ok=True, mdl_riletto="343"):
        self.salva_ok = salva_ok
        self.mdl_riletto = mdl_riletto
        self.inviato = None
    def save_lineup(self, payload):
        if not self.salva_ok:
            raise RuntimeError("LUP012 fixed bench")
        self.inviato = payload
        return {"mdl": payload["mdl"]}
    def get_lineup(self):
        return {"teamLineupDto": {"mdl": self.mdl_riletto}}

class TestInvio(unittest.TestCase):
    def test_invio_ok_e_verifica(self):
        sess = FakeSession()
        res = invia(_spec(), 4, sess, FakeRoster())
        self.assertEqual(res["mdl"], "343")
        self.assertTrue(res["verificato"])
        self.assertEqual(len(sess.inviato["starts"]), 11)

    def test_rifiuto_sito_solleva_invioerror(self):
        with self.assertRaises(InvioError):
            invia(_spec(), 4, FakeSession(salva_ok=False), FakeRoster())

    def test_mismatch_modulo_non_verificato(self):
        res = invia(_spec(), 4, FakeSession(mdl_riletto="352"), FakeRoster())
        self.assertFalse(res["verificato"])

    def test_spec_invalido_solleva_invioerror(self):
        # build_payload rifiuta il modulo -> ValidationError deve diventare InvioError
        with self.assertRaises(InvioError):
            invia(dict(_spec(), modulo="999"), 4, FakeSession(), FakeRoster())

if __name__ == "__main__":
    unittest.main()
