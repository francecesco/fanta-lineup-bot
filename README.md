# fanta-lineup-bot

Automazione della **formazione del fantacalcio** su `leghe.fantacalcio.it`: legge lo stato di
giornata dal sito (avversari, probabili titolarità, infortuni), aiuta a scegliere l'undici e la
panchina, e **carica la formazione** sul sito via API — senza browser.

> **Non ufficiale.** Progetto personale, non affiliato a fantacalcio.it. Usalo solo con il **tuo**
> account e la **tua** lega. Le API non sono pubbliche e possono cambiare senza preavviso.

## Cosa fa

- **Login via API** (HTTP puro, niente browser headless)
- **Legge lo stato di giornata**: per ogni giocatore della tua rosa mostra partita, casa/trasferta,
  % di titolarità (probabile del sito), disponibilità (infortunato/squalificato) e medie voto
- **Costruisce e valida** il payload della formazione (11 titolari coerenti col modulo, panchina
  della dimensione richiesta, solo giocatori che possiedi)
- **Invia la formazione** e la riverifica leggendola dal sito
- **Robusto ai token scaduti**: ri-login automatico su `401`
- Include una **skill** (prompt) che, a partire dalla rosa e dai dati del sito, propone modulo,
  undici e panchina e produce lo `spec` JSON pronto da inviare
- **Modalità bot autonomo** (`bot/`): un servizio always-on (es. su una Zimaboard) che ogni giorno
  prepara la formazione con Gemini, te la propone su Telegram e la **invia da solo** prima del
  deadline se non intervieni (auto-invio con veto). Vedi [Bot autonomo](#bot-autonomo-zimaboard).

## Come funziona (pipeline)

```
 sito fantacalcio.it (login via API)
        │
        ▼
 stato_giornata.py ──► dati di giornata dal sito (rosa, avversari, %titolarità, infortuni)
        │
        ▼
 scelta undici/modulo  ──►  formazione.json  (spec: modulo, titolari, panchina)
        │
        ▼
 invia_formazione.py ──► login ─► rosa e mday/cmday dal sito ─► anteprima ─► conferma ─► invio
```

La rosa (nome giocatore → ID) si ricava dai dati del sito: **nessun file Excel è
necessario** per leggere lo stato di giornata, inviare la formazione o far girare il bot.

## Requisiti

- **Python 3.12+** (il bot autonomo usa `zoneinfo` e type hints moderni; il flusso manuale gira
  anche su 3.9+).
- `pip install -r requirements.txt` — installa `tzdata` (fusi orari, unica dipendenza del bot) e
  `openpyxl`, quest'ultimo **opzionale**, usato solo dal flusso manuale basato su Excel (skill
  `consiglia-formazione`). Il bot e l'invio ricavano la rosa dai dati del sito: sono stdlib puro.
- Solo per il **bot autonomo**: una **API key Gemini** (Google AI Studio, gratuita) in
  `GEMINI_API_KEY` e un **bot Telegram** (token + chat id) — vedi
  [Bot autonomo](#bot-autonomo-zimaboard).

## Setup

> Per una guida completa passo-passo — utile anche per replicare il progetto su **un'altra lega
> o un altro account** — vedi **[docs/REPLICARE.md](docs/REPLICARE.md)**. Note tecniche (endpoint,
> payload, autenticazione) in **[docs/ROADMAP.md](docs/ROADMAP.md)**.

```bash
git clone https://github.com/<utente>/fanta-lineup-bot.git
cd fanta-lineup-bot
pip install -r requirements.txt

# 1) credenziali del sito (mai committare .env)
cp .env.example .env        # FANTA_USER e FANTA_PWD (+ GEMINI_API_KEY e TELEGRAM_* se usi il bot)

# 2) identificativi della tua lega (mai committare config.py)
cp config.example.py config.py   # poi inserisci id_squadra e idcomp
```

Come ricavare `id_squadra` e `idcomp`: da loggato sul sito, guarda l'URL della tua lega —
`.../view/rosters/<id_squadra>` e `.../view/competition/<idcomp>/lineup`.

**File dati** — **opzionali**: il bot e `invia_formazione.py` leggono la rosa dal sito e non ne
hanno bisogno. Servono solo se usi la skill manuale `consiglia-formazione` (che legge la rosa da
Excel per ragionare sull'undici):
- `Quotazioni.xlsx` — il listone ufficiale (colonne `Id`, `R`, `Nome`, `Squadra`); il nome file
  atteso è configurabile in `config.py` (`FILE_QUOTAZIONI`)
- `rosa.xlsx` — la tua rosa (colonne `Ruolo`, `Giocatore`, ...). Puoi generare un template con
  `skill/rosa.sh --template ./rosa.xlsx`

## Uso

Stato di giornata (base per la scelta):
```bash
python3 stato_giornata.py
```

Prepara `formazione.json` (parti da `formazione.example.json`; i nomi devono combaciare con
`rosa.xlsx`) e invia:
```bash
python3 invia_formazione.py formazione.json          # chiede conferma
python3 invia_formazione.py formazione.json --yes     # invia senza chiedere (per automazioni)
```

## Test

```bash
python3 tests/test_build_payload.py   # autonomo, senza rete né dati personali
```

## La skill

`skill/SKILL.md` è il prompt che trasforma rosa + dati di giornata in un consiglio (modulo,
undici, panchina) e nel blocco JSON pronto per `invia_formazione.py`. La sezione
**Preferenze** è pensata per essere personalizzata (approccio, giocatori intoccabili, ecc.).

## Bot autonomo (Zimaboard)

Oltre al flusso manuale (`stato_giornata.py` + `invia_formazione.py`), il progetto include un
bot always-on pensato per girare su un piccolo server sempre acceso (es. una Zimaboard) dentro
`bot/`. Il bot:

- ogni giorno, a un orario configurabile (`ora_heartbeat`), controlla se oggi giocano le tue
  squadre; se sì, calcola l'`ora_limite` di invio dal calendario reale (con un cutoff di
  sicurezza se il sito non espone l'orario) e prepara una **proposta di formazione**
  (modulo, undici, panchina) usando la skill/il cervello Gemini
- manda la proposta sul canale configurato (vedi sotto) con tre azioni: **❌ blocca** (non
  invia, la sistemi a mano sul sito), **✏️ modifica** (scrivi in una frase cosa cambiare, il
  bot ripropone), **✅ conferma** (invia subito)
- se non intervieni, **invia automaticamente** la formazione proposta all'`ora_limite`
  (auto-invio con veto: puoi sempre fermarlo o correggerlo prima che scada il tempo)
- riconcilia lo stato a ogni riavvio (giornate lasciate a metà, invii da verificare) così è
  sicuro riavviare il container in qualsiasi momento
- è idempotente: ogni giornata viene preparata e inviata una sola volta, anche in caso di
  riavvii o crash a metà

Il canale di notifica è astratto (`bot/notifier.py`, classe base `Notifier`): oggi è
implementato solo **Telegram** (`TelegramNotifier`); un canale WhatsApp/`open-wa` è sulla
roadmap e si aggiungerebbe come nuova implementazione della stessa interfaccia, senza toccare
il resto del bot.

### Setup Telegram

1. Crea un bot parlando con **[@BotFather](https://t.me/BotFather)** su Telegram: comando
   `/newbot`, scegli nome e username; BotFather ti restituisce un **token** (va in
   `TELEGRAM_BOT_TOKEN` nel tuo `.env`, non committarlo mai).
2. Scrivi un messaggio qualsiasi al tuo bot (deve essere lui a scriverti, quindi inizia tu la
   conversazione), poi apri nel browser:
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
   e leggi `message.chat.id` dalla risposta JSON: è il tuo `chat_id` (va in
   `TELEGRAM_CHAT_ID` nel tuo `.env`). Il bot risponde solo a messaggi da questo `chat_id`.

### Avvio con Docker

Al bot bastano `.env` (credenziali del sito + Gemini + Telegram) e `config.py` (id lega) già
pronti nella cartella del progetto (vedi sezione [Setup](#setup) sopra). **Nessun file Excel**:
la rosa la legge dal sito.

```bash
touch bot.db   # crea il file del DB prima del primo avvio, così il volume monta un file e non una cartella
docker compose up -d --build
docker compose logs -f
```

Il container si riavvia da solo (`restart: always`) e alla partenza riconcilia lo stato
salvato in `bot.db` (montato come volume, così sopravvive ai riavvii del container).

Per fermarlo:
```bash
docker compose down
```

## Sicurezza

- `.env` (credenziali), `config.py` (i tuoi ID), i file `.xlsx` e gli `.har` sono in `.gitignore`:
  non vengono committati.
- Un file `.har` catturato dal browser contiene password e token in chiaro: analizzalo solo in
  locale e cancellalo.

## Struttura

```
fanta_api.py            client HTTP + FantaSession (ri-login automatico)
roster_map.py           nome giocatore ↔ ID: RosterSito (dai dati del sito) e RosterMap (da Excel)
build_payload.py        costruzione e validazione del payload
stato_giornata.py       stato di giornata leggibile dal sito
invia_formazione.py     flusso completo di invio
config.example.py       template di configurazione della lega
formazione.example.json esempio di spec formazione
skill/                  prompt (SKILL.md) + lettura rosa (rosa.sh, leggi_rosa.py)
bot/                    bot autonomo always-on: settings, state (SQLite), giornata, brain (Gemini),
                        orari, invio, notifier (Telegram), engine, scheduler, main
Dockerfile              immagine del bot
docker-compose.yml      deploy del bot (restart: always, volumi, timezone)
tests/                  test autonomi
docs/                   note tecniche (endpoint, payload, auth) + guida di replica
```
