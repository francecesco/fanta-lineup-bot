import unittest
from datetime import datetime, timezone
from bot.state import Store, PROPOSTA, BLOCCATA, INVIATA, ERRORE
from bot.notifier import Evento
from bot.engine import Engine
from bot.brain import BrainError
from bot.invio import InvioError

SPEC = {"modulo": "343", "titolari": ["t"] * 11, "panchina": ["p"] * 12, "capitano": []}
ORA = datetime(2026, 9, 12, 14, 30, tzinfo=timezone.utc)

class FakeBrain:
    def __init__(self, spec=SPEC, errore=False): self.spec, self.errore = spec, errore
    def proponi(self, tabella, cmday):
        if self.errore: raise BrainError("boom")
        return self.spec
    def modifica(self, spec, richiesta, tabella, cmday): return dict(self.spec, modulo="352")

class FakeNotifier:
    def __init__(self): self.mandati, self.aggiornati, self.attese, self.messaggi = [], [], [], []
    def manda_proposta(self, g, spec, testo): self.mandati.append((g, spec)); return "msg1"
    def aggiorna_messaggio(self, msg_id, testo): self.aggiornati.append((msg_id, testo))
    def manda_messaggio(self, testo): self.messaggi.append(testo); return "msgX"
    def chiedi_testo_modifica(self, g): self.attese.append(g)
    def poll_eventi(self): return []

class FakeSettings:
    lega = {"idcomp": 700047, "divisione": "A"}

def prov_ok():
    return ({"teamLineupDto": {"cmday": 4}, "lineUpInfo": []}, object(), ORA)

class TestEngine(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:"); self.addCleanup(self.store.chiudi)
        self.notif = FakeNotifier()

    def _engine(self, brain=None, invia_fn=None):
        return Engine(self.store, brain or FakeBrain(), self.notif,
                      invia_fn or (lambda spec, cmday, session, rm: {"mdl": "343", "verificato": True}),
                      rm=None, settings=FakeSettings())

    def test_prepara_propone_e_notifica(self):
        e = self._engine()
        self.store.crea_se_assente(700047, 4, ORA)
        e.prepara(700047, 4, {"lineUpInfo": []}, ORA)
        self.assertEqual(self.store.get(700047, 4).stato, PROPOSTA)
        self.assertEqual(len(self.notif.mandati), 1)

    def test_prepara_brain_errore_va_in_errore_e_avvisa(self):
        e = self._engine(brain=FakeBrain(errore=True))
        self.store.crea_se_assente(700047, 4, ORA)
        e.prepara(700047, 4, {"lineUpInfo": []}, ORA)
        self.assertEqual(self.store.get(700047, 4).stato, ERRORE)
        self.assertEqual(len(self.notif.messaggi), 1)  # l'utente è stato avvisato pur senza msg_id

    def test_blocca_non_invia(self):
        e = self._engine()
        self.store.crea_se_assente(700047, 4, ORA)
        e.prepara(700047, 4, {"lineUpInfo": []}, ORA)
        e.on_evento(Evento("blocca", 700047, 4), prov_ok)
        self.assertEqual(self.store.get(700047, 4).stato, BLOCCATA)
        e.scaduto(700047, 4)  # timer scatta dopo: NON deve inviare
        self.assertEqual(self.store.get(700047, 4).stato, BLOCCATA)

    def test_scaduto_invia_una_volta_sola(self):
        chiamate = []
        e = self._engine(invia_fn=lambda *a: chiamate.append(1) or {"mdl": "343", "verificato": True})
        self.store.crea_se_assente(700047, 4, ORA)
        e.prepara(700047, 4, {"lineUpInfo": []}, ORA)
        e._provider = prov_ok
        e.scaduto(700047, 4)
        e.scaduto(700047, 4)  # secondo giro: lock già preso
        self.assertEqual(len(chiamate), 1)
        self.assertEqual(self.store.get(700047, 4).stato, INVIATA)

    def test_conferma_subito_invia(self):
        e = self._engine()
        self.store.crea_se_assente(700047, 4, ORA)
        e.prepara(700047, 4, {"lineUpInfo": []}, ORA)
        e.on_evento(Evento("conferma", 700047, 4), prov_ok)
        self.assertEqual(self.store.get(700047, 4).stato, INVIATA)

    def test_invio_error_va_in_errore(self):
        def boom(*a): raise InvioError("LUP012")
        e = self._engine(invia_fn=boom)
        self.store.crea_se_assente(700047, 4, ORA)
        e.prepara(700047, 4, {"lineUpInfo": []}, ORA)
        e.on_evento(Evento("conferma", 700047, 4), prov_ok)
        self.assertEqual(self.store.get(700047, 4).stato, ERRORE)

    def test_modifica_testo_ripropone(self):
        e = self._engine()
        self.store.crea_se_assente(700047, 4, ORA)
        e.prepara(700047, 4, {"lineUpInfo": []}, ORA)
        e.on_evento(Evento("modifica", 700047, 4), prov_ok)     # tap ✏️
        self.assertEqual(len(self.notif.attese), 1)
        e.on_evento(Evento("modifica_testo", 700047, 4, "gioca il 352"), prov_ok)
        g = self.store.get(700047, 4)
        self.assertEqual(g.stato, PROPOSTA)
        self.assertEqual(g.spec["modulo"], "352")

    def test_invia_ora_lock_una_volta_sola(self):
        chiamate = []
        e = self._engine(invia_fn=lambda *a: chiamate.append(1) or {"mdl": "343", "verificato": True})
        self.store.crea_se_assente(700047, 4, ORA)
        e.prepara(700047, 4, {"lineUpInfo": []}, ORA)
        e._provider = prov_ok
        e.invia_ora(700047, 4)
        e.invia_ora(700047, 4)   # lock già preso: NON invia di nuovo
        self.assertEqual(len(chiamate), 1)

    def test_modifica_brainerror_mantiene_proposta(self):
        class BrainModErr(FakeBrain):
            def modifica(self, spec, richiesta, tabella, cmday):
                raise BrainError("boom")
        e = self._engine(brain=BrainModErr())
        self.store.crea_se_assente(700047, 4, ORA)
        e.prepara(700047, 4, {"lineUpInfo": []}, ORA)
        spec_prima = self.store.get(700047, 4).spec
        e.on_evento(Evento("modifica", 700047, 4), prov_ok)
        e.on_evento(Evento("modifica_testo", 700047, 4, "cambia tutto"), prov_ok)
        g = self.store.get(700047, 4)
        self.assertEqual(g.stato, PROPOSTA)      # torna a PROPOSTA con la vecchia proposta
        self.assertEqual(g.spec, spec_prima)     # spec invariato

if __name__ == "__main__":
    unittest.main()
