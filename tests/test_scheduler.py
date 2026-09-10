import unittest
from datetime import datetime, timezone
from bot import scheduler, state
from bot.state import Giornata, PROPOSTA, DA_PREPARARE, INVIO_IN_CORSO

def G(stato, ora_limite):
    return Giornata(700047, 4, stato, {"modulo": "343"}, ora_limite, "m", None, None, "")

class TestScheduler(unittest.TestCase):
    def test_riconciliazione_invia_se_deadline_passata(self):
        adesso = datetime(2026, 9, 12, 15, 0, tzinfo=timezone.utc)
        g = G(PROPOSTA, datetime(2026, 9, 12, 14, 30, tzinfo=timezone.utc))
        azioni = scheduler.azioni_riconciliazione(adesso, [g])
        self.assertEqual(azioni, [("invia", g)])

    def test_riconciliazione_non_invia_se_deadline_futura(self):
        adesso = datetime(2026, 9, 12, 12, 0, tzinfo=timezone.utc)
        g = G(PROPOSTA, datetime(2026, 9, 12, 14, 30, tzinfo=timezone.utc))
        self.assertEqual(scheduler.azioni_riconciliazione(adesso, [g]), [])

    def test_riconciliazione_verifica_invio_in_corso(self):
        adesso = datetime(2026, 9, 12, 15, 0, tzinfo=timezone.utc)
        g = G(INVIO_IN_CORSO, datetime(2026, 9, 12, 14, 30, tzinfo=timezone.utc))
        self.assertEqual(scheduler.azioni_riconciliazione(adesso, [g]), [("verifica_invio", g)])

    def test_prossimo_heartbeat_oggi_o_domani(self):
        from zoneinfo import ZoneInfo
        tz = "Europe/Rome"
        adesso = datetime(2026, 9, 12, 7, 0, tzinfo=ZoneInfo(tz))
        hb = scheduler.prossimo_heartbeat(adesso, "08:00", tz)
        self.assertEqual((hb.hour, hb.minute, hb.day), (8, 0, 12))
        adesso2 = datetime(2026, 9, 12, 9, 0, tzinfo=ZoneInfo(tz))
        hb2 = scheduler.prossimo_heartbeat(adesso2, "08:00", tz)
        self.assertEqual(hb2.day, 13)  # già passato oggi → domani

if __name__ == "__main__":
    unittest.main()
