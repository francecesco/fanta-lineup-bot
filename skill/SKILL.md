---
name: consiglia-formazione
description: Legge la rosa da rosa.xlsx, cerca online probabili formazioni, infortuni, squalifiche, avversari e stato di forma della prossima giornata di Serie A, e restituisce modulo, undici titolari e panchina ordinata. Usa questa skill quando l'utente chiede chi schierare, la formazione della prossima giornata, "consigliami la rosa", "chi metto in campo", "formazione fantacalcio", o quando parla della giornata di campionato in arrivo e vuole indicazioni sulla sua rosa, anche se non pronuncia la parola "formazione".
---

# Consiglia Formazione

Trasforma la rosa in `rosa.xlsx` nella formazione da schierare nella prossima giornata di Serie A, motivata da dati cercati online al momento della richiesta.

## Quando attivarti

- "Chi schiero questa giornata?" / "Chi metto in campo?"
- "Consigliami la formazione" / "Consigliami la rosa per la prossima giornata"
- "Dammi l'undici titolare" / "Che modulo faccio?"
- "Sta giocando bene X? Lo schiero?" (dubbio su singoli giocatori della rosa)
- L'utente parla della giornata in arrivo e chiede indicazioni sulla sua rosa

## Regole della lega (fisse)

| Parametro | Valore |
|---|---|
| Formato | classic, 8 squadre, 500 crediti |
| Slot rosa | 25 giocatori: 3 portieri, 8 difensori, 8 centrocampisti, 6 attaccanti |
| Moduli | liberi: 3-4-3, 3-5-2, 4-3-3, 4-4-2, 4-5-1, 5-3-2, 5-4-1 |
| Modificatore difesa | ATTIVO |
| Panchina | lunga, con ordine di ingresso per le sostituzioni automatiche |

## Preferenze (personalizza qui)

Vincoli e gusti personali che guidano ogni scelta, **oltre** alle regole generali sotto.
Adatta questa sezione alla tua rosa e al tuo stile — i valori qui sotto sono un esempio:

- **Approccio** (es. aggressivo): massimizza i bonus attesi. Privilegia attacco, rigoristi e
  giocatori offensivi contro difese deboli, accettando qualche rischio in più.
- **Modulo giornata per giornata**: scegli il modulo sugli accoppiamenti della settimana
  (più attacco contro difese deboli, più copertura contro le big), non a priori.
- **Scheletro fisso della squadra** — i tuoi top acquisti sono **sempre titolari se disponibili**
  (in campo e non infortunati/squalificati); l'undici si costruisce attorno a loro. Elencali qui
  per reparto, ad esempio:
  - Difesa: **&lt;tuo difensore top&gt;**
  - Centrocampo: **&lt;tuo centrocampista top&gt;**
  - Attacco: **&lt;tuo attaccante top 1&gt;** e **&lt;tuo attaccante top 2&gt;**

  Se uno di loro è infortunato, squalificato o chiaramente fuori dai titolari, salta la regola
  solo per lui e sostituiscilo con la migliore alternativa di reparto.
- **Mai schierare infortunati**: un infortunato non va in campo per nessun motivo, nemmeno se
  è nello scheletro fisso. Nel dubbio tra infortunio e recupero non confermato, tienilo fuori.
- **Sempre valutare l'avversario di ogni titolare**: per ciascun giocatore schierato pesa
  l'avversario (difesa/attacco avversario, casa/trasferta) per massimizzare la probabilità di
  gol e di voto alto. A parità di titolarità, gioca chi ha l'accoppiamento migliore.

## Workflow obbligatorio

### Step 1 — Leggi la rosa

```bash
skill/rosa.sh
```

Lo script cerca `rosa.xlsx` nella cartella corrente e in quelle superiori, e stampa la rosa divisa per reparto con le squadre di Serie A coinvolte.

- Se il file non esiste, crea il template e fermati chiedendo all'utente di compilarlo: `rosa.sh --template ./rosa.xlsx`
- Se lo script segnala reparti incompleti o la colonna Squadra vuota, dillo all'utente e procedi comunque con quello che c'è.
- Non leggere `rosa.xlsx` con altri strumenti: lo script gestisce già alias delle colonne, ruoli, quotazioni dal listone e messaggi di errore.

### Step 2 — Leggi lo stato di giornata dal sito (base autorevole)

```bash
python3 stato_giornata.py
```

Lo script fa login e stampa, per ogni giocatore della rosa: la **partita di questa giornata**,
**casa/trasferta**, la **% di titolarità** (la probabile del sito stesso), la **disponibilità**
(OK / INDISPONIBILE = infortunato o squalificato), **media voto** e **fantamedia**. In cima dà la
giornata (Serie A e turno lega) e il modulo attualmente salvato. Prendi da qui, come base
autorevole, ciò che prima cercavi a mano:

- **Avversario e casa/trasferta**: usa questi, non la colonna Squadra di `rosa.xlsx` (che può
  essere sfasata dal mercato — il sito ha la squadra reale aggiornata).
- **Titolarità** (`%tit`): ≥75% titolare quasi certo · 50-74% probabile ma con ballottaggio ·
  <50% a rischio panchina · 0% + INDISPONIBILE = fuori.
- **Indisponibili**: chi è INDISPONIBILE non si schiera mai e non va nemmeno in panchina
  (coerente con la preferenza «mai infortunati»).
- **Medie** (`Media`/`FMedia`): per scegliere tra alternative con % simile. `0.0` = ancora senza
  voti (inizio stagione o chi non ha ancora giocato), **non** è un brutto voto.

**Conta i giorni al primo match** per calibrare quanto le % sono stabili: a 4-5 giorni ballano
ancora (trattale come indicative), a 1-2 giorni sono attendibili. Se mancano 5+ giorni, dichiaralo
in cima e consiglia di richiamare la skill due giorni prima del match.

### Step 3 — Ricerca web mirata (solo per rifinire e sciogliere i dubbi)

I dati del sito (Step 2) coprono già avversario, titolarità e disponibilità. Il web serve **solo**
per ciò che la % non dice o potrebbe non essere aggiornata. Cerca, in parallelo dove possibile,
usando WebSearch e poi WebFetch sulle pagine più promettenti:

1. **Rigoristi e tiratori di piazzati** attuali delle squadre dei tuoi giocatori (bonus attesi).
2. **Forma recente** dei tuoi dubbi (ultimi 2-3 turni: minuti, gol, assist) per scegliere fra
   alternative con % simile.
3. **Difese e attacchi** delle squadre avversarie (gol fatti/subiti), per il modificatore difesa.
4. **Ballottaggi e notizie last-minute** (conferenze, rifiniture) che possono spostare una % al
   fischio d'inizio, soprattutto per i giocatori 50-74%.
5. **Conflitti col sito**: se una fonte affidabile contraddice il dato API (un giocatore dato OK
   dal sito ma segnalato infortunato altrove, o viceversa), verifica su una seconda fonte e
   **segnalalo nei dubbi**. Nel dubbio su un infortunio, tienilo fuori.

Se una ricerca non aggiunge nulla di affidabile, va bene fermarsi ai dati del sito.

#### Attendibilità delle fonti

Le pagine di pronostici e i siti di scommesse producono formazioni inventate. Applica questi filtri:

- **Due fonti indipendenti** per ogni notizia che sposta una scelta: infortunio, esclusione dall'undici, cambio di rigorista. Con una sola fonte, il giocatore va nei dubbi, non fuori dall'undici.
- **Controlla la data di ogni pagina.** Le ricerche restituiscono spesso la stessa partita giocata in una stagione precedente. Verifica che la pagina parli della giornata e della stagione giuste prima di usarne il contenuto, e scartala se la data non torna.
- **Scarta la fonte che contraddice fatti di base**: se assegna un giocatore a una squadra sbagliata, cita allenatori inesistenti o si contraddice al suo interno, non usarla per nulla, nemmeno per il resto della pagina.
- **Gerarchia delle fonti**: siti specializzati di fantacalcio e testate sportive nazionali prima; siti di pronostici, aggregatori e blog solo come conferma di qualcosa già letto altrove.
- **Se due fonti affidabili si contraddicono**, riporta il contrasto nei dubbi e scegli in base al minutaggio recente, non alla fonte letta per ultima.

Se una ricerca non produce risultati affidabili, dichiaralo nell'output invece di colmare il buco a memoria.

#### Squadra dei giocatori: fidati del sito, non di `rosa.xlsx`

La colonna Squadra di `rosa.xlsx` è statica e può essere sfasata dal mercato. Lo Step 2 dà la
**squadra reale aggiornata** e la partita di giornata: usa quella. Se differisce da `rosa.xlsx`,
**segnala all'utente la riga da correggere** nel file, ma ragiona sulla squadra del sito. Se un
giocatore non gioca più in Serie A, trattalo come non schierabile e dillo. Se le cessioni svuotano
un reparto e restano pochi schierabili, dillo apertamente: serve intervenire in rosa, non solo in
formazione.

### Step 4 — Scegli modulo e undici

Criteri, in ordine di priorità:

1. **Titolarità**: guidata dalla `%tit` e dallo stato dello Step 2. Chi è INDISPONIBILE non si schiera; sotto il ~50% senza motivi forti va in panchina, non in campo; un panchinaro probabile vale meno di un titolare mediocre. Eccezione: lo **scheletro fisso** (i tuoi top acquisti definiti nelle Preferenze) gioca sempre se disponibile.
2. **Modificatore difesa**: essendo attivo, conta la media voto di portiere più i difensori schierati, quindi servono difensori che giochino e prendano voto, non difensori spettacolari. Con più difensori della stessa squadra, punta su quelli che affrontano un attacco poco prolifico: il clean sheet è correlato. Se invece i difensori sono sparsi in squadre diverse, come capita spesso, scegli partita per partita chi affronta l'attacco più debole e chi ha la media voto più alta, ed evita il difensore a rischio panchina anche se più talentuoso. Una difesa a quattro o cinque che regge spesso rende più di un attaccante in più.
3. **Portiere**: si schiera quello che gioca. A parità di titolarità certa, vince chi ha più probabilità di clean sheet, cioè la squadra con la difesa migliore contro l'attacco più debole, non il portiere più quotato. Il portiere entra anche nella media del modificatore difesa, quindi conta la squadra, non il nome.
4. **Bonus attesi**: rigoristi, tiratori di piazzati, giocatori offensivi contro difese deboli.
5. **Avversario e campo**: partita in casa contro fondo classifica batte trasferta a Milano o Napoli.
6. **Rischio**: diffidati, rientri da infortunio, giocatori con minutaggio in gestione, turni infrasettimanali o coppe europee ravvicinate.

Il modulo si sceglie in base ai giocatori disponibili, non viceversa.

### Step 5 — Ordina la panchina

Le sostituzioni automatiche pescano **per ruolo**: se un titolare non prende voto, entra la prima riserva disponibile di quel ruolo. Quindi la panchina va raggruppata per ruolo, nell'ordine P, D, C, A, e numerata dall'inizio alla fine, con l'ordine interno a ciascun ruolo che è quello che conta davvero.

Ordina in base alla probabilità di scendere in campo e prendere un voto, non al talento assoluto. Un titolare di provincia entra prima di un panchinaro di una big.

Fra due riserve dello stesso ruolo con incertezza comparabile, l'ordine è: chi è fisicamente disponibile, poi chi ha giocato più minuti nelle ultime giornate, poi chi affronta l'avversario più morbido. Chi rientra da un infortunio va sempre dietro a chi è già in gruppo.

## Output esatto

````markdown
# Giornata <N> Serie A — <data della giornata>

<AVVISO OBBLIGATORIO qui in cima ogni volta che manca almeno una probabile
formazione fra le partite che ti interessano, a qualunque distanza dal match:
di' quanti giorni mancano, per quali partite non ci sono ancora le probabili,
su cosa si basano quindi quelle scelte, e invita a richiamare la skill a due
giorni dal fischio d'inizio. Ometti questo blocco solo quando hai le probabili
di tutte le partite dei tuoi giocatori.>

**Modulo consigliato: <modulo>**

## Titolari

| Ruolo | Giocatore | Avversario | Motivo |
|---|---|---|---|
| P | ... | Squadra (casa/trasferta) | max una riga |
| D | ... | ... | ... |
...

## Panchina (ordine di ingresso, raggruppata per ruolo)

| # | Ruolo | Giocatore | Nota |
|---|---|---|---|
| 1 | P | ... | perché in questa posizione |
| 2 | D | ... | ... |
...

## Fuori dai giochi

| Giocatore | Motivo |
|---|---|
| ... | infortunio / squalifica / panchina certa / non piu' in Serie A |

## Dubbi da ricontrollare prima del fischio d'inizio

- <giocatore>: <cosa verificare e quando esce la notizia>

## Fonti

- <titolo pagina> — <url> (consultata il <data>)
````

## Formazione da inviare (blocco JSON)

Subito dopo le tabelle, aggiungi **sempre** un blocco ```json con la formazione scelta,
nello schema qui sotto. È la parte che alimenta il caricamento automatico sul sito
(`invia_formazione.py`): deve combaciare esattamente con le tabelle e superare le
validazioni, altrimenti l'invio viene rifiutato.

Regole tassative del blocco:

- **Nomi identici a `rosa.xlsx`**: usa la stringa esatta della colonna *Giocatore*, con
  stessi accenti e abbreviazioni (es. `Miranda J.`, `Kessiè`, `Zapata D.`). Ogni nome deve
  esistere in `rosa.xlsx`: niente giocatori inventati o fuori rosa.
- **`modulo`**: uno tra `343 352 433 442 451 532 541` (senza trattini), lo stesso delle tabelle.
- **`titolari`**: esattamente 11 nomi — un solo portiere e un numero di D/C/A coerente col modulo.
- **`panchina`**: **esattamente 12** giocatori (la lega ha la panchina fissa), nell'**ordine di
  ingresso** dello Step 5. Metti davanti gli schierabili nell'ordine giusto; se per arrivare a 12
  servono anche degli indisponibili, mettili **in fondo** (non verranno usati per le sostituzioni).
  I 2 giocatori esclusi dai 23 (11 titolari + 12 panchina) siano i meno utili (es. infortuni lunghi).
- **`capitano`**: lascia sempre `[]` (nella lega il capitano non è tra i bonus; se cambierà, l'utente avviserà).
- Se la formazione è **provvisoria** (probabili non ancora uscite), emetti comunque il blocco,
  ma dillo nell'avviso in cima: va riconfermata richiamando la skill prima del fischio d'inizio.
- **Non indicare la giornata (`mday`/`cmday`) nel JSON**: la legge da sé lo strumento di invio
  direttamente dal sito. A te basta identificare la giornata per ragionare su avversari e forma.

```json
{
  "modulo": "352",
  "titolari": ["<P>", "<D>", "<D>", "<D>", "<C>", "<C>", "<C>", "<C>", "<C>", "<A>", "<A>"],
  "panchina": ["<riserva 1>", "<riserva 2>", "<riserva 3>", "..."],
  "capitano": []
}
```

## Regole

1. **Cerca sempre online prima di consigliare.** Infortuni, formazioni e forma cambiano ogni settimana: nessun consiglio si basa sulla memoria del modello.
2. **Schiera solo giocatori presenti in `rosa.xlsx`.** Mai suggerire acquisti o giocatori non in rosa, a meno che l'utente lo chieda esplicitamente.
3. **Rispetta gli slot**: undici titolari con un solo portiere, e un numero di difensori, centrocampisti e attaccanti coerente con il modulo dichiarato. Ricontrolla il conteggio prima di rispondere.
4. **Se un'informazione non è verificabile, dichiaralo.** Scrivi "titolarità non confermata dalle fonti" invece di indovinare. Mai inventare infortuni, voti, statistiche o probabili formazioni.
5. **Cita le fonti** con url e data di consultazione. Ogni affermazione su infortuni o formazioni deve poter essere ricondotta a una fonte.
6. **Una fonte sola non basta** per escludere un giocatore dall'undici: serve una seconda conferma indipendente, altrimenti finisce tra i dubbi. Scarta del tutto le fonti che contengono errori palesi.
7. **Non spacciare per certo un consiglio dato troppo presto.** Se le probabili formazioni non sono ancora pubblicate, l'avviso in cima alla risposta non è opzionale.
8. **Una riga di motivazione per giocatore.** Il valore sta nella scelta, non nella prosa.
9. **Segnala i dubbi aperti** invece di nasconderli: le probabili formazioni pubblicate a metà settimana cambiano fino a poche ore dal fischio d'inizio.
10. **Se la rosa è incompleta o le squadre mancano**, avvisa e procedi con i dati disponibili, indicando cosa manca nel file.
11. **Se un giocatore risulta trasferito**, segnala la riga da correggere in `rosa.xlsx` invece di correggerla tu.
12. **Non toccare `rosa.xlsx`**: la skill legge, non scrive. Il file lo aggiorna l'utente.
13. **Emetti sempre il blocco JSON «Formazione da inviare»** e rendilo coerente con le tabelle: nomi identici a `rosa.xlsx`, modulo ammesso, 11 titolari coerenti col modulo, panchina ordinata (≤12), `capitano` `[]`. È ciò che permette il caricamento automatico; se non lo produci o è incoerente, l'invio si blocca.

## Esempio

Input:
> chi schiero questa giornata?

Output (estratto):
> # Giornata 4 Serie A — 20-21 settembre 2026
>
> **Modulo consigliato: 3-5-2**
>
> ## Titolari
>
> | Ruolo | Giocatore | Avversario | Motivo |
> |---|---|---|---|
> | P | Svilar | Verona (casa) | Roma favorita, clean sheet probabile |
> | D | Dimarco | Sassuolo (casa) | rientrato in gruppo, spinta e assist |
> | C | Calhanoglu | Sassuolo (casa) | rigorista, difesa avversaria tra le più battute |
>
> ## Dubbi da ricontrollare
>
> - Dimarco: rientro dal problema muscolare, conferma attesa nella rifinitura del sabato

Secondo esempio, richiesta arrivata a inizio settimana:

Input:
> chi schiero questa giornata?

Output (estratto):
> # Giornata 4 Serie A — 20-21 settembre 2026
>
> Mancano sei giorni al primo match e nessuna probabile formazione è ancora
> pubblicata. Quello che segue si basa su gerarchie di ruolo e minutaggio
> delle ultime giornate. Richiamami il venerdì per la conferma.
>
> **Modulo consigliato: 3-5-2**
>
> ## Dubbi da ricontrollare
>
> - Kean: una sola fonte lo dà fuori dall'undici, nessuna conferma altrove. Resta titolare fino a prova contraria.
> - Krstovic: una fonte lo colloca all'Atalanta invece che al Lecce, trasferimento non confermato. Se è cambiato, correggi la riga in `rosa.xlsx`.
