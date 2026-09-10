# Note tecniche & storia del progetto

Sintesi di come funziona l'integrazione con le API di `leghe.fantacalcio.it`, così da
non perdere le informazioni utili scoperte durante lo sviluppo. Tutti gli identificativi
qui sono **placeholder**: metti i tuoi in `config.py`.

## Come sono stati scoperti gli endpoint

Aprendo la pagina della formazione con i **DevTools del browser → tab Network** e salvando
un HAR (o "Copy as cURL"), si osservano le chiamate reali dell'API. Da lì si ricavano
endpoint, header e forma dei payload. ⚠️ Un HAR contiene password e token in chiaro:
analizzalo solo in locale e cancellalo dopo.

## Autenticazione

- **Login**: `POST https://apileague.fantacalcio.it/onboarding/v1/login`
  - header: `app_key` (chiave pubblica del frontend, uguale per tutti), `content-type: application/json`,
    `origin`/`referer` di `https://leghe.fantacalcio.it`
  - body: `{"username": "...", "password": "..."}`
  - risposta: token di sessione, dati utente e la lista `leghe` (ognuna con un **`jwt`** dedicato)
- Le chiamate di gioco richiedono l'header **`Authorization: Bearer <jwt della lega>`**
  (il `jwt` della lega bersaglio nella risposta di login), oltre all'`app_key`.
- Nessun CAPTCHA / CSRF / challenge: basta HTTP puro (niente browser headless).

## Lettura stato di giornata e formazione salvata

- `GET https://apileague.fantacalcio.it/gaming/v1/teamLineup/visualizza/<divisione>/<idcomp>`
  (Bearer jwt lega) → `teamLineupDto` (formazione salvata + `mday`/`cmday` **autorevoli** +
  modulo) e `lineUpInfo` (rosa completa con: partita di giornata, casa/trasferta, **% titolarità**,
  status infortunio/squalifica, medie voto).
- `mday`/`cmday` **non** vanno indovinati: `cmday` è la giornata di campionato, `mday` è il turno
  interno della lega (che può essere sfasato). Vanno **letti da questo endpoint** prima di inviare.

## Salvataggio formazione

- `POST https://apileague.fantacalcio.it/gaming/v1/teamLineup/<divisione>` (Bearer jwt lega)
- body:
  ```json
  {"starts": [11 id titolari, ordine P,D,C,A], "bench": [id panchina ordinata],
   "capt": [], "mdl": "343", "idcomp": <idcomp>, "mday": <mday>, "cmday": <cmday>,
   "tid": <id_squadra>, "allComp": false, "visb": true,
   "swtcA": 0, "swtcB": 0, "swtc": 0, "swtcMdl": ""}
  ```
- Gli **ID giocatore** coincidono con la colonna `Id` del listone quotazioni ufficiale.
- **Panchina fissa** (`fbench`): se attiva, la panchina deve avere **esattamente** `tbench`
  giocatori (di solito 12), altrimenti errore `LUP012`. Gli indisponibili possono riempirla in fondo.

## Robustezza

- `FantaSession` fa **ri-login automatico** se una chiamata torna `401/403` (token scaduto):
  ri-logga una volta e riprova; un secondo errore viene propagato. Utile quando il token resta
  in cache (es. servizio sempre attivo).

## Architettura del codice

- `fanta_api.py` — client HTTP (login, get_lineup, save_lineup, `FantaSession`)
- `roster_map.py` — nome giocatore ↔ ID (dal listone) + verifica "è nella tua rosa"
- `build_payload.py` — costruisce e **valida** il payload (11 titolari, ruoli coerenti col modulo,
  panchina della dimensione giusta, solo giocatori posseduti)
- `stato_giornata.py` — stampa leggibile dello stato di giornata (base per il consiglio)
- `invia_formazione.py` — flusso completo: legge la giornata dal sito, anteprima, conferma, invio
- `skill/` — le istruzioni (prompt) per generare il consiglio di formazione e produrre lo `spec` JSON

## Idee / prossimi passi

- Interfaccia di automazione (es. bot di messaggistica) che propone la formazione e, alla conferma,
  la invia (`invia_formazione.py --yes`).
- Impostazione del capitano (formato del campo `capt` da ricavare da una cattura, se la lega lo usa).
