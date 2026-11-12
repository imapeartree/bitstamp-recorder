# bitstamp-recorder

Registra i dati pubblici in tempo reale di Bitstamp con GitHub Actions. Non usa
chiavi API e non invia ordini: si collega solo ai canali pubblici del WebSocket.

## Cosa registra

Per XRP/EUR, XRP/USD, BTC/EUR e BTC/USD:

- book: primi 10 livelli di denaro e lettera, una riga al secondo;
- scambi: ogni scambio, con il lato di chi ha preso liquidità;
- funding dei perpetui XRP/USD e BTC/USD, una riga al minuto.

## Dove finiscono i dati

Nelle **release** di questo repo, una per giorno UTC (`data-AAAAMMGG`), come file
`.jsonl.gz`. Non entrano nella cronologia git e non toccano GitHub Pages.

## Come gira

Il workflow `.github/workflows/record.yml` parte cinque volte al giorno e registra
per circa 5 ore e 40 minuti a blocchi di 57 minuti, caricando ogni blocco. I giri
si sovrappongono: i dati doppi vengono scartati in lettura.

- Avvio manuale: scheda **Actions** → *Registra dati Bitstamp* → **Run workflow**.
- Stop: scheda **Actions** → *Registra dati Bitstamp* → menu **…** → **Disable workflow**.

## Note

- In un repo pubblico i minuti di GitHub Actions sono gratuiti. In un repo privato
  il piano gratuito ne dà 2000 al mese, cioè circa un giorno di registrazione.
- GitHub sospende i workflow pianificati dopo 60 giorni senza attività nel repo.
- Questo repo non ha GitHub Pages attivo: il sito `<utente>.github.io` resta com'è.

## Prova in locale

```bash
pip install "websockets>=12,<16"
python record.py --seconds 60 --root ticks
```
