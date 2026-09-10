# Replicare il progetto in una nuova istanza

Guida passo-passo per far girare `fanta-lineup-bot` con **un altro account / un'altra lega**.
Tutto ciò che è specifico della lega sta in `config.py` e `.env`: nella maggior parte dei casi
**non serve toccare il codice**. Se la tua lega ha regole diverse (panchina non fissa, capitano
attivo, divisione diversa), vedi la sezione [Adattare a leghe diverse](#adattare-a-leghe-diverse).

---

## 0. Prerequisiti

- Python 3.9+ e `pip`
- Un account su `leghe.fantacalcio.it` con almeno **una lega attiva** in cui sei allenatore
- Il **listone quotazioni** ufficiale della stagione (file `.xlsx`, si scarica da fantacalcio.it)
- Un browser con i **DevTools** (Chrome/Firefox) per la cattura iniziale
- (Facoltativo) la CLI `gh` se vuoi versionare la tua copia su GitHub

---

## 1. Clona e installa

```bash
git clone https://github.com/<utente>/fanta-lineup-bot.git
cd fanta-lineup-bot
pip install -r requirements.txt
```

---

## 2. Ricava gli identificativi della tua lega

Da **loggato** sul sito, apri la tua lega e guarda l'URL della pagina rose/formazione:

- `.../view/rosters/<id_squadra>`  → **`id_squadra`** (il tuo `tid`)
- `.../view/competition/<idcomp>/lineup` → **`idcomp`** (la competizione)

La **`divisione`** è quasi sempre `"A"`. Se non lo è, la trovi al passo 3 (nella risposta di login,
campo `divisione` della tua lega) o nell'URL dell'endpoint di salvataggio.

---

## 3. (Consigliato) Cattura le chiamate reali con i DevTools

Serve a **verificare** che endpoint e formati coincidano per la tua lega, e a leggere le regole
(moduli, panchina, capitano). Apri **DevTools → tab Network**, spunta **Preserve log**, poi:

1. **Fai il login** (partendo da sloggato) → chiamata `POST /onboarding/v1/login`.
   Nella risposta trovi la lista `leghe`, ognuna con il suo **`jwt`** e la **`divisione`**.
2. **Apri la pagina formazione** → chiamata
   `GET /gaming/v1/teamLineup/visualizza/<divisione>/<idcomp>`.
   Ti dà `mday`/`cmday` correnti, la formazione salvata e `lineUpInfo` (rosa con % titolarità).
3. **Salva una formazione a mano** → chiamata `POST /gaming/v1/teamLineup/<divisione>`.
   Conferma la forma del payload (`starts`, `bench`, `mdl`, `idcomp`, `tid`, ...).
4. Le **regole della lega** stanno in `GET /onboarding/v1/league/settings/lineup`:
   - `mods` → moduli ammessi (es. `["343","352","433",...]`)
   - `tbench` → numero di posti in panchina (es. `12`)
   - `fbench` → `true` se la **panchina è fissa** (allora servono ESATTAMENTE `tbench` giocatori)
   - `lcap` → numero di capitani ammessi (0 = capitano non usato)

> ⚠️ Un file `.har`/una richiesta catturata contiene **password e token in chiaro**: analizzalo
> solo in locale e cancellalo subito dopo. Non committarlo mai (`*.har` è già in `.gitignore`).

---

## 4. Configura `config.py`

```bash
cp config.example.py config.py
```

Inserisci i valori del passo 2-3:

```python
LEGA = {
    "nome": "La mia lega",
    "alias": "la-mia-lega",
    "id_squadra": 12345678,   # dal passo 2
    "idcomp": 700000,         # dal passo 2
    "divisione": "A",         # dal passo 3 se diversa
}

MODULI = { ... }              # allinea ai `mods` della tua lega (passo 3)
MAX_PANCHINA = 12             # = `tbench`
PANCHINA_FISSA = True         # = `fbench`
FILE_QUOTAZIONI = "Quotazioni.xlsx"
FILE_ROSA = "rosa.xlsx"
```

`config.py` è in `.gitignore`: i tuoi ID **non** verranno committati.

---

## 5. Credenziali

```bash
cp .env.example .env
```

Inserisci `FANTA_USER` e `FANTA_PWD`. Anche `.env` è in `.gitignore`.

---

## 6. File dati

Metti nella cartella del progetto:

- **Listone quotazioni** ufficiale, col nome indicato in `FILE_QUOTAZIONI`. Deve avere le colonne
  `Id`, `R` (ruolo), `Nome`, `Squadra`. La colonna **`Id` è l'ID usato dall'API**: è la chiave di
  tutto (il codice traduce i nomi in questi ID).
- **`rosa.xlsx`** con la tua rosa. Genera un template e poi compilalo:
  ```bash
  skill/rosa.sh --template ./rosa.xlsx
  ```
  Colonne: `Ruolo` (P/D/C/A), `Giocatore`, `Squadra` (facoltative: `Quotazione`, `Pagato`, `Note`).
  **I nomi in `rosa.xlsx` devono combaciare esattamente con la colonna `Nome` del listone.**

Verifica che tutto si leghi:
```bash
python3 stato_giornata.py     # deve stampare la tua rosa con partite, %titolarità, stato
```

---

## 7. Personalizza la skill (facoltativo ma consigliato)

Apri `skill/SKILL.md` e adatta la sezione **Preferenze**: approccio (aggressivo/prudente),
giocatori "scheletro fisso" (i tuoi intoccabili), regole di casa. Il resto della skill è generico.

---

## 8. Primo giro completo

```bash
# 1) guarda lo stato di giornata
python3 stato_giornata.py

# 2) prepara la formazione (parti dall'esempio; nomi = colonna Giocatore di rosa.xlsx)
cp formazione.example.json formazione.json   # poi compilalo

# 3) invia (chiede conferma; mostra l'anteprima e legge mday/cmday dal sito)
python3 invia_formazione.py formazione.json
```

Per un'automazione non interattiva, `--yes` salta la conferma.

Controllo veloce che l'ambiente sia a posto (senza rete né dati):
```bash
python3 tests/test_build_payload.py
```

---

## 9. (Opzionale) Bot autonomo su un server sempre acceso

Oltre al flusso manuale, il progetto include un bot always-on (cartella `bot/`) che ogni giorno
prepara la formazione, la propone su Telegram e la **invia da solo** prima del deadline se non
intervieni (**auto-invio con veto**). Pensato per un piccolo server sempre acceso (Zimaboard,
Raspberry, ...) via Docker.

### 9.1 Chiave Gemini (il ragionamento del bot)

Il bot sceglie la formazione con **Gemini** + ricerca Google (il flusso manuale usa invece la skill).
Crea una API key gratuita su [Google AI Studio](https://aistudio.google.com/apikey) e mettila in
`GEMINI_API_KEY` nel `.env` (mai committarla). Modello di default: `gemini-3.6-flash`
(configurabile con `GEMINI_MODEL`).

### 9.2 Bot Telegram (canale di proposta e veto)

1. Parla con [@BotFather](https://t.me/BotFather), comando `/newbot`: ottieni un **token** →
   `TELEGRAM_BOT_TOKEN` nel `.env`.
2. Scrivi un messaggio al tuo bot, poi apri `https://api.telegram.org/bot<TOKEN>/getUpdates` e
   leggi `message.chat.id` → `TELEGRAM_CHAT_ID` nel `.env`. Il bot risponde **solo** a questo chat.

### 9.3 Parametri del bot (in `config.py`)

`config.example.py` include i default; copiali in `config.py` se non ci sono:

```python
ORA_HEARTBEAT = "08:00"      # ogni mattina controlla se oggi giochi
BUFFER_INVIO_MIN = 30        # invia N minuti prima del primo kickoff dei tuoi
MAX_TENTATIVI_GEMINI = 3
GEMINI_MODEL = "gemini-3.6-flash"
TZ_BOT = "Europe/Rome"
CUTOFF_FALLBACK = {0: "18:15", 1: "18:15", 2: "18:15", 3: "18:15",
                   4: "18:15", 5: "12:15", 6: "12:15"}
```

### 9.4 Personalizza le preferenze del bot

Il cervello Gemini segue le stesse preferenze della skill (approccio, scheletro fisso di titolari,
mai infortunati, valuta l'avversario). Adattale al tuo stile nel *system prompt* di `bot/brain.py`
(la costante `_SYSTEM`).

### 9.5 Avvio con Docker

Con `.env`, `config.py` e i due `.xlsx` (rosa e listone) pronti nella cartella del progetto:

```bash
touch bot.db                 # crea il file del DB prima del primo avvio: il volume monta un file, non una cartella
docker compose up -d --build
docker compose logs -f       # segui i log
```

Il container si riavvia da solo (`restart: always`) e alla partenza **riconcilia** lo stato salvato
in `bot.db` (montato come volume, così sopravvive ai riavvii): è sicuro riavviarlo in qualsiasi
momento. Senza Docker: `pip install -r requirements.txt` (serve **Python 3.12+**) e `python3 -m bot.main`.

### 9.6 Come si comporta

- **Ogni mattina** (`ORA_HEARTBEAT`) controlla se oggi giocano le tue squadre.
- Se sì, prepara la formazione con Gemini e manda la proposta su Telegram con tre azioni:
  **❌ Blocca** · **✏️ Modifica** (scrivi a parole cosa cambiare, il bot ripropone) ·
  **✅ Conferma** (invia subito).
- Se non intervieni, **invia in automatico** all'`ora_limite` (primo kickoff − `BUFFER_INVIO_MIN`).
- **Idempotente**: ogni giornata è preparata e inviata una sola volta, anche con riavvii o crash.

> ⚠️ **Prima volta**: fai un giro controllato e **non affidarti all'auto-invio** finché non hai visto
> almeno una proposta corretta e testato i tre pulsanti.

> ℹ️ **Limite noto**: l'orario del match non è esposto dal sito, quindi il bot lo ricava dal calendario
> via Gemini. Prepara solo se il calendario è affidabile e il tuo primo kickoff è **oggi**; se in un
> giorno-match Gemini non desse un calendario valido, quel giorno non prepara in automatico (puoi
> sempre usare il flusso manuale). Miglioria possibile: una fonte match-day dedicata (es. l'endpoint
> calendario di fantacalcio).

---

## Adattare a leghe diverse

- **Panchina non fissa** (`fbench: false`): imposta `PANCHINA_FISSA = False` in `config.py`.
  Così la panchina può avere **fino a** `MAX_PANCHINA` giocatori invece di esattamente `tbench`.
- **Numero posti panchina diverso**: allinea `MAX_PANCHINA` a `tbench`.
- **Moduli diversi**: aggiorna il dizionario `MODULI` con i `mods` della tua lega
  (chiave = stringa modulo senza trattini, valore = `(difensori, centrocampisti, attaccanti)`).
- **Divisione diversa da "A"**: impostala in `LEGA["divisione"]` (finisce nell'URL degli endpoint).
- **Capitano attivo** (`lcap > 0`): al momento `build_payload` invia `capt: []`. Per impostarlo
  serve ricavare il **formato del campo `capt`** da una cattura (passo 3) di un salvataggio con il
  capitano scelto a mano, poi estendere `build_payload`. (Nota: inviare `[<id>]` **non** basta.)

---

## Troubleshooting

| Sintomo | Causa probabile | Soluzione |
|---|---|---|
| `HTTP 400 ... ATH018` al login | credenziali errate | controlla `FANTA_USER`/`FANTA_PWD` in `.env` |
| `HTTP 401 ... Bearer token missing` | token scaduto/mancante | gestito da `FantaSession` (ri-login automatico); se persiste, rifai login |
| `LUP012 ... fixed bench` | panchina con numero sbagliato di giocatori | con panchina fissa servono ESATTAMENTE `tbench` (riempi anche con indisponibili in fondo) |
| `'<nome>' non è nella tua rosa` | nome in `formazione.json` diverso da `rosa.xlsx` | usa la grafia esatta della colonna Giocatore |
| `'<nome>' non trovato nel listone` | nome in `rosa.xlsx` diverso dal listone | allinea alla colonna `Nome` del listone quotazioni |
| `Reparti non coerenti col modulo` | conteggio D/C/A ≠ modulo | correggi titolari o modulo |
| ID/giornata sbagliati | `id_squadra`/`idcomp` errati | ricontrolla dall'URL (passo 2) |
