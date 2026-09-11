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

class FakeRoster:
    """Rosa dal sito simulata: registra le risposte con cui è stata aggiornata."""
    def __init__(self): self.aggiornata_con = []
    def aggiorna(self, res): self.aggiornata_con.append(res)
    def resolve(self, name, require_owned=True): return (1, "P")

class FakeSettings:
    lega = {"idcomp": 700047, "divisione": "A"}
    tz = "Europe/Rome"
    buffer_invio_min = 30
    cutoff_fallback = {0: "18:15", 1: "18:15", 2: "18:15", 3: "18:15",
                       4: "18:15", 5: "12:15", 6: "12:15"}

def prov_ok():
    return ({"teamLineupDto": {"cmday": 4}, "lineUpInfo": []}, object(), ORA)

class TestEngine(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:"); self.addCleanup(self.store.chiudi)
        self.notif = FakeNotifier()

    def _engine(self, brain=None, invia_fn=None, rm=None):
        return Engine(self.store, brain or FakeBrain(), self.notif,
                      invia_fn or (lambda spec, cmday, session, rm: {"mdl": "343", "verificato": True}),
                      rm=rm, settings=FakeSettings())

    def test_prepara_aggiorna_rosa_dal_sito(self):
        rm = FakeRoster()
        e = self._engine(rm=rm)
        self.store.crea_se_assente(700047, 4, ORA)
        res = {"lineUpInfo": [{"pid": 1, "plyr": "V", "role": [1], "tname": "Juventus",
                               "teamH": "SAS", "teamA": "JUV", "hoaw": 1,
                               "percent": 90, "status": 1, "agrd": 6, "fagrd": 6}]}
        e.prepara(700047, 4, res, ORA)
        self.assertEqual(rm.aggiornata_con, [res])   # rosa rinfrescata prima di proporre

    def test_invia_ora_aggiorna_rosa_dal_sito(self):
        rm = FakeRoster()
        e = self._engine(rm=rm)
        self.store.crea_se_assente(700047, 4, ORA)
        e.prepara(700047, 4, {"lineUpInfo": []}, ORA)
        e._provider = prov_ok
        e.invia_ora(700047, 4)
        # l'ultima aggiornata è la risposta del provider usata per l'invio
        self.assertEqual(rm.aggiornata_con[-1], prov_ok()[0])

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

    def test_heartbeat_prepara_se_giorno_di_match(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        oggi = datetime.now(ZoneInfo("Europe/Rome")).date().isoformat()
        class BrainCal(FakeBrain):
            def calendario(self, cmday):
                return [{"partita": "Juventus-X", "kickoff": f"{oggi}T15:00"}]
        e = self._engine(brain=BrainCal())
        def provider():
            return ({"teamLineupDto": {"cmday": 4},
                     "lineUpInfo": [{"role": [1], "plyr": "V", "tname": "Juventus",
                                     "teamH": "SAS", "teamA": "JUV", "hoaw": 1,
                                     "percent": 90, "status": 1, "agrd": 6, "fagrd": 6}]},
                    object(), None)
        e.heartbeat(provider, oggi_iso=oggi)
        g = self.store.get(700047, 4)
        self.assertIsNotNone(g)
        self.assertEqual(g.stato, PROPOSTA)

    def test_heartbeat_deadline_sul_primo_match_del_turno(self):
        # Anticipo del turno OGGI (squadra senza miei giocatori); i miei giocano tra 3 giorni.
        # Deve preparare oggi: il blocco è al primo fischio del turno, non dei miei.
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        oggi = datetime.now(ZoneInfo("Europe/Rome")).date()
        fra_tre = (oggi + timedelta(days=3)).isoformat()
        class BrainCal(FakeBrain):
            def calendario(self, cmday):
                return [{"partita": "Venezia-Fiorentina", "kickoff": f"{oggi.isoformat()}T20:45"},
                        {"partita": "Sassuolo-Juventus", "kickoff": f"{fra_tre}T20:45"}]
        e = self._engine(brain=BrainCal())
        def provider():  # i miei sono della Juventus, che gioca fra 3 giorni
            return ({"teamLineupDto": {"cmday": 4},
                     "lineUpInfo": [{"role": [1], "plyr": "V", "tname": "Juventus",
                                     "teamH": "SAS", "teamA": "JUV", "hoaw": 1,
                                     "percent": 90, "status": 1, "agrd": 6, "fagrd": 6}]},
                    object(), None)
        e.heartbeat(provider, oggi_iso=oggi.isoformat())
        g = self.store.get(700047, 4)
        self.assertIsNotNone(g)          # preparata oggi
        self.assertEqual(g.stato, PROPOSTA)

    def test_heartbeat_non_prepara_se_match_non_oggi(self):
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        oggi = datetime.now(ZoneInfo("Europe/Rome")).date()
        fra_tre = (oggi + timedelta(days=3)).isoformat()
        class BrainCal(FakeBrain):
            def calendario(self, cmday):
                return [{"partita": "Juventus-X", "kickoff": f"{fra_tre}T15:00"}]
        e = self._engine(brain=BrainCal())
        def provider():
            return ({"teamLineupDto": {"cmday": 4},
                     "lineUpInfo": [{"role": [1], "plyr": "V", "tname": "Juventus",
                                     "teamH": "SAS", "teamA": "JUV", "hoaw": 1,
                                     "percent": 90, "status": 1, "agrd": 6, "fagrd": 6}]},
                    object(), None)
        e.heartbeat(provider, oggi_iso=oggi.isoformat())
        self.assertIsNone(self.store.get(700047, 4))

    def test_heartbeat_non_prepara_se_calendario_invalido(self):
        class BrainNoCal(FakeBrain):
            def calendario(self, cmday):
                return []
        e = self._engine(brain=BrainNoCal())
        def provider():
            return ({"teamLineupDto": {"cmday": 4},
                     "lineUpInfo": [{"role": [1], "plyr": "V", "tname": "Juventus",
                                     "teamH": "SAS", "teamA": "JUV", "hoaw": 1,
                                     "percent": 90, "status": 1, "agrd": 6, "fagrd": 6}]},
                    object(), None)
        e.heartbeat(provider)
        self.assertIsNone(self.store.get(700047, 4))

    def test_riconcilia_verifica_invio_ok(self):
        e = self._engine()
        self.store.crea_se_assente(700047, 4, ORA)
        self.store.set_proposta(700047, 4, SPEC, "m", ORA)
        self.store.prova_lock_invio(700047, 4)   # -> INVIO_IN_CORSO
        g = self.store.get(700047, 4)
        def provider(): return ({"teamLineupDto": {"mdl": "343"}}, object(), None)
        e.on_evento_riconcilia("verifica_invio", g, provider)
        self.assertEqual(self.store.get(700047, 4).stato, INVIATA)

    def test_riconcilia_verifica_invio_mismatch_va_in_errore(self):
        e = self._engine()
        self.store.crea_se_assente(700047, 4, ORA)
        self.store.set_proposta(700047, 4, SPEC, "m", ORA)
        self.store.prova_lock_invio(700047, 4)
        g = self.store.get(700047, 4)
        def provider(): return ({"teamLineupDto": {"mdl": "352"}}, object(), None)
        e.on_evento_riconcilia("verifica_invio", g, provider)
        self.assertEqual(self.store.get(700047, 4).stato, ERRORE)

    def test_scaduto_invia_anche_da_in_modifica(self):
        chiamate = []
        e = self._engine(invia_fn=lambda *a: chiamate.append(1) or {"mdl": "343", "verificato": True})
        self.store.crea_se_assente(700047, 4, ORA)
        e.prepara(700047, 4, {"lineUpInfo": []}, ORA)
        e._provider = prov_ok
        e.on_evento(Evento("modifica", 700047, 4), prov_ok)   # -> IN_MODIFICA
        e.scaduto(700047, 4)
        self.assertEqual(len(chiamate), 1)
        self.assertEqual(self.store.get(700047, 4).stato, INVIATA)

    def test_invia_ora_mismatch_va_in_errore(self):
        e = self._engine(invia_fn=lambda *a: {"mdl": "343", "verificato": False})
        self.store.crea_se_assente(700047, 4, ORA)
        e.prepara(700047, 4, {"lineUpInfo": []}, ORA)
        e._provider = prov_ok
        e.invia_ora(700047, 4)
        self.assertEqual(self.store.get(700047, 4).stato, ERRORE)

    def test_riconcilia_invia(self):
        chiamate = []
        e = self._engine(invia_fn=lambda *a: chiamate.append(1) or {"mdl": "343", "verificato": True})
        self.store.crea_se_assente(700047, 4, ORA)
        self.store.set_proposta(700047, 4, SPEC, "m", ORA)   # PROPOSTA
        g = self.store.get(700047, 4)
        e.on_evento_riconcilia("invia", g, prov_ok)
        self.assertEqual(len(chiamate), 1)
        self.assertEqual(self.store.get(700047, 4).stato, INVIATA)


class TestComandi(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:"); self.addCleanup(self.store.chiudi)
        self.notif = FakeNotifier()

    def _engine(self, brain=None, invia_fn=None):
        return Engine(self.store, brain or FakeBrain(), self.notif,
                      invia_fn or (lambda spec, cmday, session, rm: {"mdl": "343", "verificato": True}),
                      rm=None, settings=FakeSettings())

    def _cmd(self, e, testo, provider=prov_ok):
        e.on_evento(Evento("comando", 0, 0, testo), provider)

    def test_aiuto_elenca_comandi(self):
        e = self._engine()
        self._cmd(e, "/aiuto")
        self.assertTrue(any("/formazione" in m for m in self.notif.messaggi))

    def test_formazione_prepara_e_propone(self):
        e = self._engine()
        self._cmd(e, "/formazione")
        g = self.store.get(700047, 4)
        self.assertIsNotNone(g)
        self.assertEqual(g.stato, PROPOSTA)
        self.assertEqual(len(self.notif.mandati), 1)

    def test_stato_non_preparata(self):
        e = self._engine()
        self._cmd(e, "/stato")
        self.assertTrue(any("non ancora preparata" in m for m in self.notif.messaggi))

    def test_stato_dopo_proposta(self):
        e = self._engine()
        self.store.crea_se_assente(700047, 4, ORA)
        e.prepara(700047, 4, {"lineUpInfo": []}, ORA)
        self._cmd(e, "/stato")
        self.assertTrue(any("PROPOSTA" in m for m in self.notif.messaggi))

    def test_vedi_mostra_formazione_dal_sito(self):
        e = self._engine()
        def prov():
            return ({"teamLineupDto": {"cmday": 4, "mdl": "352", "starts": [10], "bench": [20]},
                     "lineUpInfo": [{"pid": 10, "plyr": "Vicario", "role": [1]},
                                    {"pid": 20, "plyr": "Corvi", "role": [1]}]},
                    object(), None)
        self._cmd(e, "/vedi", prov)
        blob = " ".join(self.notif.messaggi)
        self.assertIn("Vicario", blob)
        self.assertIn("3-5-2", blob)

    def test_invia_senza_proposta_avvisa(self):
        e = self._engine()
        self._cmd(e, "/invia")
        self.assertTrue(any("Nessuna proposta" in m for m in self.notif.messaggi))
        self.assertIsNone(self.store.get(700047, 4))

    def test_invia_con_proposta_invia(self):
        e = self._engine()
        self.store.crea_se_assente(700047, 4, ORA)
        e.prepara(700047, 4, {"lineUpInfo": []}, ORA)
        self._cmd(e, "/invia")
        self.assertEqual(self.store.get(700047, 4).stato, INVIATA)

    def test_blocca_blocca(self):
        e = self._engine()
        self.store.crea_se_assente(700047, 4, ORA)
        e.prepara(700047, 4, {"lineUpInfo": []}, ORA)
        self._cmd(e, "/blocca")
        self.assertEqual(self.store.get(700047, 4).stato, BLOCCATA)

    def test_modifica_con_argomento_ripropone(self):
        e = self._engine()
        self.store.crea_se_assente(700047, 4, ORA)
        e.prepara(700047, 4, {"lineUpInfo": []}, ORA)
        self._cmd(e, "/modifica gioca il 352")
        g = self.store.get(700047, 4)
        self.assertEqual(g.stato, PROPOSTA)
        self.assertEqual(g.spec["modulo"], "352")

    def test_comando_sconosciuto_avvisa(self):
        e = self._engine()
        self._cmd(e, "/pippo")
        self.assertTrue(any("sconosciuto" in m.lower() for m in self.notif.messaggi))


if __name__ == "__main__":
    unittest.main()
