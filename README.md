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

## Come funziona (pipeline)

```
rosa.xlsx + listone quotazioni
        │
        ▼
 stato_giornata.py ──► dati di giornata dal sito (avversari, %titolarità, infortuni)
        │
        ▼
 scelta undici/modulo  ──►  formazione.json  (spec: modulo, titolari, panchina)
        │
        ▼
 invia_formazione.py ──► login ─► legge mday/cmday dal sito ─► anteprima ─► conferma ─► invio
```

## Requisiti

- Python 3.9+
- `openpyxl` (solo per leggere gli `.xlsx`): `pip install -r requirements.txt`
  - `fanta_api.py` e `build_payload.py` usano solo la libreria standard.

## Setup

> Per una guida completa passo-passo — utile anche per replicare il progetto su **un'altra lega
> o un altro account** — vedi **[docs/REPLICARE.md](docs/REPLICARE.md)**. Note tecniche (endpoint,
> payload, autenticazione) in **[docs/ROADMAP.md](docs/ROADMAP.md)**.

```bash
git clone https://github.com/<utente>/fanta-lineup-bot.git
cd fanta-lineup-bot
pip install -r requirements.txt

# 1) credenziali del sito (mai committare .env)
cp .env.example .env        # poi inserisci FANTA_USER e FANTA_PWD

# 2) identificativi della tua lega (mai committare config.py)
cp config.example.py config.py   # poi inserisci id_squadra e idcomp
```

Come ricavare `id_squadra` e `idcomp`: da loggato sul sito, guarda l'URL della tua lega —
`.../view/rosters/<id_squadra>` e `.../view/competition/<idcomp>/lineup`.

**File dati** (non inclusi, mettili nella cartella del progetto):
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

## Sicurezza

- `.env` (credenziali), `config.py` (i tuoi ID), i file `.xlsx` e gli `.har` sono in `.gitignore`:
  non vengono committati.
- Un file `.har` catturato dal browser contiene password e token in chiaro: analizzalo solo in
  locale e cancellalo.

## Struttura

```
fanta_api.py            client HTTP + FantaSession (ri-login automatico)
roster_map.py           nome giocatore ↔ ID + verifica rosa
build_payload.py        costruzione e validazione del payload
stato_giornata.py       stato di giornata leggibile dal sito
invia_formazione.py     flusso completo di invio
config.example.py       template di configurazione della lega
formazione.example.json esempio di spec formazione
skill/                  prompt (SKILL.md) + lettura rosa (rosa.sh, leggi_rosa.py)
tests/                  test autonomi
docs/                   note tecniche (endpoint, payload, auth)
```
