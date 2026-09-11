"""Interfaccia Notifier + implementazione Telegram (urllib, pura HTTPS)."""
import json
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class Evento:
    tipo: str
    idcomp: int
    cmday: int
    testo: str | None = None

# Comandi che l'utente può mandare al bot (nome, descrizione per il menu Telegram).
COMANDI = [
    ("formazione", "Calcola e proponi la formazione adesso"),
    ("stato", "Stato della giornata e ora limite d'invio"),
    ("vedi", "Mostra la formazione salvata sul sito"),
    ("invia", "Invia subito la proposta corrente"),
    ("blocca", "Blocca l'auto-invio di questa giornata"),
    ("modifica", "Modifica a parole (es. /modifica gioca il 352)"),
    ("aiuto", "Elenco dei comandi"),
]

class Notifier(ABC):
    @abstractmethod
    def manda_proposta(self, giornata, spec, testo): ...
    @abstractmethod
    def aggiorna_messaggio(self, msg_id, testo): ...
    @abstractmethod
    def manda_messaggio(self, testo): ...
    @abstractmethod
    def chiedi_testo_modifica(self, giornata): ...
    @abstractmethod
    def poll_eventi(self): ...
    def registra_comandi(self):
        """Registra il menu comandi sul canale (no-op se il canale non lo supporta)."""
        return None

def _get_reale(url):
    return json.load(urllib.request.urlopen(url, timeout=60))

def _post_reale_factory(token):
    def post(metodo, params):
        url = f"https://api.telegram.org/bot{token}/{metodo}"
        body = urllib.parse.urlencode(
            {k: (v if isinstance(v, str) else json.dumps(v)) for k, v in params.items()}).encode()
        req = urllib.request.Request(url, data=body,
                                     headers={"User-Agent": "fanta-lineup-bot/1.0"})
        return json.load(urllib.request.urlopen(req, timeout=60))
    return post

class TelegramNotifier(Notifier):
    def __init__(self, token, chat_id, http_get=None, http_post=None):
        self.token = token
        self.chat_id = str(chat_id)
        self._offset = 0
        self._attesa_modifica = None
        self._get = http_get or _get_reale
        self._post = http_post or _post_reale_factory(token)

    def _keyboard(self, idcomp, cmday):
        suf = f"{idcomp}:{cmday}"
        return {"inline_keyboard": [[
            {"text": "❌ Blocca", "callback_data": f"blocca:{suf}"},
            {"text": "✏️ Modifica", "callback_data": f"modifica:{suf}"},
            {"text": "✅ Conferma", "callback_data": f"conferma:{suf}"},
        ]]}

    def manda_proposta(self, giornata, spec, testo):
        res = self._post("sendMessage", {
            "chat_id": self.chat_id, "text": testo, "parse_mode": "HTML",
            "reply_markup": self._keyboard(giornata["idcomp"], giornata["cmday"])})
        return str(res["result"]["message_id"])

    def aggiorna_messaggio(self, msg_id, testo):
        self._post("editMessageText", {
            "chat_id": self.chat_id, "message_id": msg_id, "text": testo, "parse_mode": "HTML"})

    def manda_messaggio(self, testo):
        res = self._post("sendMessage", {
            "chat_id": self.chat_id, "text": testo, "parse_mode": "HTML"})
        return str(res["result"]["message_id"])

    def chiedi_testo_modifica(self, giornata):
        self._attesa_modifica = (giornata["idcomp"], giornata["cmday"])
        self._post("sendMessage", {
            "chat_id": self.chat_id,
            "text": "Cosa cambio? Scrivimelo a parole (es. \"gioca il 352, A3 titolare\")."})

    def registra_comandi(self):
        self._post("setMyCommands", {
            "commands": [{"command": c, "description": d} for c, d in COMANDI]})

    def _parse_updates(self, updates, chat_id):
        eventi = []
        for u in updates:
            if "callback_query" in u:
                cq = u["callback_query"]
                if str(cq.get("message", {}).get("chat", {}).get("id")) != str(chat_id):
                    continue
                parti = cq.get("data", "").split(":")
                if len(parti) != 3:
                    continue  # callback malformato: non far crashare il polling loop
                tipo, idcomp, cmday = parti
                try:
                    eventi.append(Evento(tipo, int(idcomp), int(cmday)))
                except ValueError:
                    continue
            elif "message" in u and "text" in u["message"]:
                m = u["message"]
                if str(m.get("chat", {}).get("id")) != str(chat_id):
                    continue
                testo = m["text"]
                if testo.lstrip().startswith("/"):
                    # Un comando interrompe l'eventuale attesa di modifica.
                    self._attesa_modifica = None
                    eventi.append(Evento("comando", 0, 0, testo.strip()))
                elif self._attesa_modifica:
                    idcomp, cmday = self._attesa_modifica
                    eventi.append(Evento("modifica_testo", idcomp, cmday, testo))
        return eventi

    def poll_eventi(self):
        url = (f"https://api.telegram.org/bot{self.token}/getUpdates"
               f"?timeout=30&offset={self._offset}")
        resp = self._get(url)
        updates = resp.get("result", [])
        if updates:
            self._offset = updates[-1]["update_id"] + 1
        return self._parse_updates(updates, self.chat_id)
