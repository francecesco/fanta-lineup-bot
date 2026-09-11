import json, unittest
from bot.notifier import TelegramNotifier, Evento

class TestParse(unittest.TestCase):
    def _n(self):
        return TelegramNotifier("tok", "999", http_get=lambda *a, **k: {}, http_post=lambda *a, **k: {})

    def test_callback_blocca(self):
        n = self._n()
        upd = [{"update_id": 1, "callback_query": {
            "message": {"chat": {"id": 999}}, "data": "blocca:700047:4"}}]
        ev = n._parse_updates(upd, "999")
        self.assertEqual(ev, [Evento("blocca", 700047, 4)])

    def test_ignora_chat_non_autorizzata(self):
        n = self._n()
        upd = [{"update_id": 1, "callback_query": {
            "message": {"chat": {"id": 111}}, "data": "conferma:700047:4"}}]
        self.assertEqual(n._parse_updates(upd, "999"), [])

    def test_messaggio_testo_diventa_modifica_testo_se_in_attesa(self):
        n = self._n()
        n._attesa_modifica = (700047, 4)
        upd = [{"update_id": 2, "message": {"chat": {"id": 999}, "text": "gioca il 352"}}]
        ev = n._parse_updates(upd, "999")
        self.assertEqual(ev, [Evento("modifica_testo", 700047, 4, "gioca il 352")])

    def test_messaggio_testo_ignorato_se_nessuna_attesa(self):
        n = self._n()
        n._attesa_modifica = None
        upd = [{"update_id": 2, "message": {"chat": {"id": 999}, "text": "ciao"}}]
        self.assertEqual(n._parse_updates(upd, "999"), [])

    def test_manda_proposta_invia_keyboard_e_ritorna_msgid(self):
        inviati = []
        def fake_post(metodo, params):
            inviati.append((metodo, params))
            return {"result": {"message_id": 555}}
        n = TelegramNotifier("tok", "999", http_get=lambda *a, **k: {}, http_post=fake_post)
        msg_id = n.manda_proposta({"idcomp": 700047, "cmday": 4}, {"modulo": "343"}, "testo")
        self.assertEqual(msg_id, "555")
        metodo, params = inviati[0]
        self.assertEqual(metodo, "sendMessage")
        self.assertIn("reply_markup", params)
        self.assertIn("blocca:700047:4", json.dumps(params["reply_markup"]))

    def test_messaggio_da_chat_non_autorizzata_ignorato_anche_in_attesa(self):
        n = self._n()
        n._attesa_modifica = (700047, 4)
        upd = [{"update_id": 3, "message": {"chat": {"id": 111}, "text": "hack"}}]
        self.assertEqual(n._parse_updates(upd, "999"), [])

    def test_comando_slash_diventa_evento_comando(self):
        n = self._n()
        upd = [{"update_id": 4, "message": {"chat": {"id": 999}, "text": "/stato"}}]
        self.assertEqual(n._parse_updates(upd, "999"), [Evento("comando", 0, 0, "/stato")])

    def test_comando_con_argomenti(self):
        n = self._n()
        upd = [{"update_id": 5, "message": {"chat": {"id": 999}, "text": "/modifica gioca il 352"}}]
        self.assertEqual(n._parse_updates(upd, "999"),
                         [Evento("comando", 0, 0, "/modifica gioca il 352")])

    def test_comando_prevale_su_attesa_modifica_e_la_azzera(self):
        n = self._n()
        n._attesa_modifica = (700047, 4)
        upd = [{"update_id": 6, "message": {"chat": {"id": 999}, "text": "/stato"}}]
        self.assertEqual(n._parse_updates(upd, "999"), [Evento("comando", 0, 0, "/stato")])
        self.assertIsNone(n._attesa_modifica)

    def test_comando_da_chat_non_autorizzata_ignorato(self):
        n = self._n()
        upd = [{"update_id": 7, "message": {"chat": {"id": 111}, "text": "/invia"}}]
        self.assertEqual(n._parse_updates(upd, "999"), [])

    def test_registra_comandi_chiama_setmycommands(self):
        inviati = []
        def fake_post(metodo, params):
            inviati.append((metodo, params)); return {"ok": True}
        n = TelegramNotifier("tok", "999", http_get=lambda *a, **k: {}, http_post=fake_post)
        n.registra_comandi()
        self.assertEqual(inviati[0][0], "setMyCommands")
        self.assertIn("formazione", json.dumps(inviati[0][1]))

if __name__ == "__main__":
    unittest.main()
