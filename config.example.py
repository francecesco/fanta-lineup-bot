"""Configurazione della lega bersaglio.

Copia questo file in `config.py` e inserisci i valori della TUA lega.
`config.py` è ignorato da git (contiene i tuoi identificativi): non committarlo.

Come ricavare gli ID (da loggato sul sito, nell'URL della tua lega):
- `id_squadra`: numero in `.../view/rosters/<id_squadra>`
- `idcomp`:     numero in `.../view/competition/<idcomp>/lineup`
- `divisione`:  di solito "A" (ultimo segmento dell'endpoint di salvataggio)
"""

LEGA = {
    "nome": "La tua lega",
    "alias": "la-tua-lega",
    "id_squadra": 0,     # <-- inserisci il tuo id_squadra
    "idcomp": 0,         # <-- inserisci il tuo idcomp
    "divisione": "A",
}

# Moduli ammessi → (difensori, centrocampisti, attaccanti). Il portiere è sempre 1.
MODULI = {
    "343": (3, 4, 3),
    "352": (3, 5, 2),
    "433": (4, 3, 3),
    "442": (4, 4, 2),
    "451": (4, 5, 1),
    "532": (5, 3, 2),
    "541": (5, 4, 1),
}

MAX_PANCHINA = 12       # campo tbench dalle impostazioni lega
PANCHINA_FISSA = True   # fbench: con panchina fissa servono ESATTAMENTE MAX_PANCHINA giocatori

# File dati (relativi alla cartella del progetto)
FILE_QUOTAZIONI = "Quotazioni.xlsx"
FILE_ROSA = "rosa.xlsx"

# --- Bot autonomo (Zimaboard) ---
ORA_HEARTBEAT = "08:00"          # ogni mattina il bot controlla se oggi si gioca
BUFFER_INVIO_MIN = 30            # invia N minuti prima del primo kickoff dei tuoi
MAX_TENTATIVI_GEMINI = 3         # tentativi di ottenere uno spec valido da Gemini
GEMINI_MODEL = "gemini-3.6-flash"
TZ_BOT = "Europe/Rome"
DB_PATH = "bot.db"
# Cutoff di sicurezza per giorno (0=lun..6=dom): ora oltre cui non si invia,
# usato se il calendario reale non è disponibile.
CUTOFF_FALLBACK = {0: "18:15", 1: "18:15", 2: "18:15", 3: "18:15",
                   4: "18:15", 5: "12:15", 6: "12:15"}
