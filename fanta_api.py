"""Client HTTP per le API di fantacalcio.it (leghe).

Dependency-free (solo stdlib): funziona identico su macOS e su Raspberry Pi.

Espone:
- login(username, password) -> dict con i token di sessione e le leghe
- save_lineup(payload, auth_headers=None, division="A") -> dict risposta

La password NON va messa nel codice: usare variabili d'ambiente / file .env
(vedi load_env()).
"""

import json
import urllib.request
import urllib.error

BASE = "https://apileague.fantacalcio.it"
# Chiave pubblica del frontend di leghe.fantacalcio.it (uguale per tutti, non è un segreto).
APP_KEY = "ICiELOObd5DF5uJEATi77CRvHiiRuMU0"

COMMON_HEADERS = {
    "app_key": APP_KEY,
    "content-type": "application/json",
    "accept": "application/json, text/plain, */*",
    "origin": "https://leghe.fantacalcio.it",
    "referer": "https://leghe.fantacalcio.it/",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
    ),
}


class FantaError(Exception):
    """Errore di comunicazione o risposta non valida dall'API.

    `status` è il codice HTTP quando disponibile (es. 401 = token scaduto/mancante).
    """

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def _is_auth_error(err):
    """True se l'errore è di autenticazione (token scaduto/mancante): HTTP 401/403."""
    return isinstance(err, FantaError) and err.status in (401, 403)


def _post(path, body, extra_headers=None):
    url = BASE + path
    data = json.dumps(body).encode("utf-8")
    headers = dict(COMMON_HEADERS)
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            status = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        raise FantaError(f"HTTP {e.code} su {path}: {raw[:500]}", status=e.code) from e
    except urllib.error.URLError as e:
        raise FantaError(f"Rete non raggiungibile su {path}: {e.reason}") from e
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise FantaError(f"Risposta non-JSON da {path}: {raw[:300]}") from e
    return status, parsed


def login(username, password):
    """Autentica e restituisce il blocco `data` della risposta.

    Contiene: token_auth, jwt, utente, e la lista `leghe` (ognuna con jwt/token).
    """
    status, resp = _post("/onboarding/v1/login", {"username": username, "password": password})
    if not resp.get("success"):
        raise FantaError(f"Login fallito: {resp.get('error_msgs')}")
    return resp["data"]


def _get(path, bearer_token=None):
    url = BASE + path
    headers = dict(COMMON_HEADERS)
    if bearer_token:
        headers["authorization"] = f"Bearer {bearer_token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            status = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        raise FantaError(f"HTTP {e.code} su {path}: {raw[:500]}", status=e.code) from e
    except urllib.error.URLError as e:
        raise FantaError(f"Rete non raggiungibile su {path}: {e.reason}") from e
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError as e:
        raise FantaError(f"Risposta non-JSON da {path}: {raw[:300]}") from e


def get_lineup(bearer_token, idcomp, division="A"):
    """Legge la formazione attualmente salvata e lo stato di giornata.

    Restituisce il dict completo: `teamLineupDto` (con `mday`/`cmday` autorevoli,
    modulo e undici salvati) e `lineUpInfo` (rosa con avversario, % titolarità, medie).
    """
    _status, resp = _get(f"/gaming/v1/teamLineup/visualizza/{division}/{idcomp}", bearer_token)
    return resp


def find_league(data, id_squadra):
    """Trova la lega dell'utente per id_squadra nel blocco `data` del login."""
    for lg in data.get("leghe", []):
        if lg.get("id_squadra") == id_squadra:
            return lg
    raise FantaError(f"Lega con id_squadra {id_squadra} non trovata per questo utente")


def save_lineup(payload, bearer_token, division="A"):
    """Invia la formazione. `payload` = body JSON completo (vedi build_payload).

    Autenticazione richiesta: `bearer_token` è il JWT della lega
    (data.leghe[].jwt), inviato come header `Authorization: Bearer ...`.
    Restituisce (status, risposta).
    """
    headers = {"authorization": f"Bearer {bearer_token}"}
    return _post(f"/gaming/v1/teamLineup/{division}", payload, extra_headers=headers)


def submit_lineup(username, password, id_squadra, payload):
    """Convenience: login + selezione lega + invio in un colpo solo.

    Usa il jwt della lega come Bearer e la sua `divisione` per l'endpoint.
    Restituisce la risposta del salvataggio.
    """
    data = login(username, password)
    lega = find_league(data, id_squadra)
    _status, resp = save_lineup(
        payload, bearer_token=lega["jwt"], division=lega.get("divisione", "A")
    )
    return resp


class FantaSession:
    """Sessione con ri-login automatico quando il token scade (HTTP 401/403).

    Fa login una volta e riusa il jwt della lega; se una chiamata autenticata
    fallisce per token scaduto/mancante, ri-effettua il login UNA sola volta e
    riprova. Un secondo 401 (o un errore diverso) viene propagato.
    """

    def __init__(self, username, password, id_squadra, idcomp, division=None):
        self.username = username
        self.password = password
        self.id_squadra = id_squadra
        self.idcomp = idcomp
        self._division = division
        self._data = None
        self._lega = None
        self.relogin_count = 0   # per diagnostica/test

    def login(self):
        self._data = login(self.username, self.password)
        self._lega = find_league(self._data, self.id_squadra)
        return self._lega

    @property
    def lega(self):
        if self._lega is None:
            self.login()
        return self._lega

    @property
    def division(self):
        return self._division or self.lega.get("divisione", "A")

    def _with_auth_retry(self, call):
        """Esegue `call(jwt)`; su errore di auth ri-logga una volta e riprova."""
        if self._lega is None:
            self.login()
        try:
            return call(self._lega["jwt"])
        except FantaError as e:
            if not _is_auth_error(e):
                raise
            # Token scaduto/mancante: ri-login e un solo nuovo tentativo.
            self.relogin_count += 1
            self.login()
            return call(self._lega["jwt"])

    def get_lineup(self):
        return self._with_auth_retry(
            lambda jwt: get_lineup(jwt, self.idcomp, self.division)
        )

    def save_lineup(self, payload):
        return self._with_auth_retry(
            lambda jwt: save_lineup(payload, bearer_token=jwt, division=self.division)
        )


def load_env(path=".env"):
    """Legge un file .env semplice (KEY=VALUE per riga) e ritorna un dict."""
    import os

    env = {}
    if not os.path.exists(path):
        return env
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env
