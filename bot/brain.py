"""Client Gemini (gemini-3.6-flash + google_search) con anello di validazione build_payload."""
import json
import urllib.request
from roster_map import RosterMap
import build_payload as bp

class BrainError(Exception):
    pass

_SYSTEM = """Sei un esperto di fantacalcio Serie A. Scegli la formazione ottimale dalla rosa data.
REGOLE TASSATIVE:
- Modulo tra: 343, 352, 433, 442, 451, 532, 541, scelto sugli accoppiamenti.
- 11 titolari: 1 portiere + D/C/A coerenti col modulo. Panchina: ESATTAMENTE 12 (indisponibili in fondo). 2 restano fuori.
- MAI schierare titolari INDISPONIBILE. Usa ESATTAMENTE i nomi forniti (stessa grafia).
- A parità di ruolo vince chi ha % titolarità e accoppiamento migliori: non lasciare in panchina un titolare al ~90%% per uno al ~60%%.
PREFERENZE: approccio AGGRESSIVO (max bonus); scheletro fisso di top acquisti sempre titolari se OK.
Usa la ricerca Google per aggiornare rigoristi, infortuni e ballottaggi dell'ultima ora.
Termina SEMPRE la risposta con SOLO il blocco JSON:
{"modulo":"343","titolari":[...11 nomi...],"panchina":[...12 nomi...],"capitano":[]}"""

def _http_post_reale(url, headers, body):
    req = urllib.request.Request(url, data=body, headers=headers)
    return json.load(urllib.request.urlopen(req, timeout=180))

class Brain:
    def __init__(self, api_key, model, max_tentativi=3, rm=None, http_post=None):
        self.api_key = api_key
        self.model = model
        self.max_tentativi = max_tentativi
        self.rm = rm if rm is not None else RosterMap()
        self.http_post = http_post or _http_post_reale

    def _url(self):
        return f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    def _genera(self, system, user, con_ricerca=True):
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0.3},
        }
        if con_ricerca:
            payload["tools"] = [{"google_search": {}}]
        headers = {"Content-Type": "application/json",
                   "User-Agent": "fanta-lineup-bot/1.0",
                   "x-goog-api-key": self.api_key}
        resp = self.http_post(self._url(), headers, json.dumps(payload).encode())
        cand = resp["candidates"][0]
        return "".join(pt.get("text", "") for pt in cand["content"]["parts"])

    @staticmethod
    def _estrai_spec(testo):
        i, j = testo.find("{"), testo.rfind("}")
        if i < 0 or j < 0:
            raise ValueError("nessun blocco JSON nella risposta")
        return json.loads(testo[i:j + 1])

    def _valida(self, spec, cmday):
        """Ritorna lo spec validato, oppure solleva ValueError con il motivo."""
        payload = bp.build_payload(dict(spec, cmday=cmday), rm=self.rm)  # solleva ValidationError
        return spec

    def _cicla(self, system, primo_user, cmday):
        user = primo_user
        ultimo_errore = ""
        for _ in range(self.max_tentativi):
            try:
                testo = self._genera(system, user)
                spec = self._estrai_spec(testo)
                self._valida(spec, cmday)
                return spec
            except (bp.ValidationError, ValueError, KeyError) as e:
                ultimo_errore = str(e)
                user = (primo_user + "\n\nLa tua risposta precedente NON era valida: "
                        + ultimo_errore + "\nCorreggi e restituisci SOLO il JSON valido.")
        raise BrainError(f"Nessuno spec valido dopo {self.max_tentativi} tentativi: {ultimo_errore}")

    def proponi(self, tabella_rosa, cmday):
        user = (f"Prossimo turno = giornata {cmday} di Serie A.\n"
                f"Rosa e dati del sito (verifica/aggiorna col web):\n\n{tabella_rosa}\n\n"
                f"Cerca le ultime su rigoristi, infortuni e ballottaggi, poi scegli. "
                f"Chiudi con il solo JSON.")
        return self._cicla(_SYSTEM, user, cmday)

    def modifica(self, spec_prec, richiesta, tabella_rosa, cmday):
        user = (f"Giornata {cmday}. Rosa e dati del sito:\n\n{tabella_rosa}\n\n"
                f"Formazione attuale (JSON):\n{json.dumps(spec_prec)}\n\n"
                f"Modifica richiesta dall'utente: {richiesta}\n"
                f"Applica la modifica mantenendo la formazione valida. Chiudi con il solo JSON.")
        return self._cicla(_SYSTEM, user, cmday)
