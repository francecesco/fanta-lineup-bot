import unittest
from datetime import datetime, timedelta, timezone
from bot import state
from bot.state import Store, DA_PREPARARE, PROPOSTA, BLOCCATA, INVIATA

SPEC = {"modulo": "343", "titolari": ["A"] * 11, "panchina": ["B"] * 12, "capitano": []}

def _ora():
    return datetime(2026, 9, 12, 12, 0, tzinfo=timezone.utc)

class TestStore(unittest.TestCase):
    def setUp(self):
        self.s = Store(":memory:")
        self.addCleanup(self.s.chiudi)

    def test_crea_idempotente(self):
        g1, creata1 = self.s.crea_se_assente(700047, 4, _ora())
        g2, creata2 = self.s.crea_se_assente(700047, 4, _ora())
        self.assertTrue(creata1)
        self.assertFalse(creata2)                 # secondo tick NON ricrea
        self.assertEqual(g1.stato, DA_PREPARARE)
        self.assertEqual(g2.stato, DA_PREPARARE)

    def test_proposta_persiste_spec_e_msgid(self):
        self.s.crea_se_assente(700047, 4, _ora())
        self.s.set_proposta(700047, 4, SPEC, "msg-1", _ora())
        g = self.s.get(700047, 4)
        self.assertEqual(g.stato, PROPOSTA)
        self.assertEqual(g.spec["modulo"], "343")
        self.assertEqual(g.msg_id, "msg-1")

    def test_lock_invio_una_volta_sola(self):
        self.s.crea_se_assente(700047, 4, _ora())
        self.s.set_proposta(700047, 4, SPEC, "m", _ora())
        self.assertTrue(self.s.prova_lock_invio(700047, 4))    # primo prende il lock
        self.assertFalse(self.s.prova_lock_invio(700047, 4))   # secondo NO (già in invio)

    def test_blocca_impedisce_lock(self):
        self.s.crea_se_assente(700047, 4, _ora())
        self.s.set_proposta(700047, 4, SPEC, "m", _ora())
        self.assertTrue(self.s.blocca(700047, 4))
        self.assertFalse(self.s.prova_lock_invio(700047, 4))   # da BLOCCATA non si invia
        self.assertEqual(self.s.get(700047, 4).stato, BLOCCATA)

    def test_non_terminali_esclude_inviata_e_bloccata(self):
        self.s.crea_se_assente(700047, 4, _ora())
        self.s.set_proposta(700047, 4, SPEC, "m", _ora())
        self.s.prova_lock_invio(700047, 4)
        self.s.segna_inviata(700047, 4)
        self.s.crea_se_assente(700047, 5, _ora())              # una aperta
        aperte = self.s.non_terminali()
        cmdays = {g.cmday for g in aperte}
        self.assertIn(5, cmdays)
        self.assertNotIn(4, cmdays)

if __name__ == "__main__":
    unittest.main()
