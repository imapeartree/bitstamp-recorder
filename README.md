# Registratore

Registra dati pubblici di mercato in tempo reale con GitHub Actions. Non usa
chiavi di accesso a servizi esterni e non invia ordini.

## Riservatezza

- I file registrati vengono **cifrati prima del caricamento** con la chiave
  pubblica in `data_public_key.txt`. La chiave privata non è in questo repo né nei
  segreti di GitHub: sta solo sul computer di chi analizza i dati.
- Se la chiave pubblica manca o la cifratura fallisce, non viene caricato nulla.
- Il repo non contiene password, token o dati in chiaro, e non ha GitHub Pages.

## Dove finiscono i dati

Nelle release, una per giorno UTC (`data-AAAAMMGG`), come file `.enc`.

## Come gira

Il workflow `.github/workflows/record.yml` parte cinque volte al giorno e registra
per circa 5 ore e 40 minuti a blocchi di 57 minuti. I giri si sovrappongono: i dati
doppi si scartano in lettura.

- Avvio manuale: scheda **Actions** → **Run workflow**.
- Stop: scheda **Actions** → menu **…** → **Disable workflow**.

## Note

- In un repo pubblico i minuti di GitHub Actions sono gratuiti; in uno privato il
  piano gratuito ne dà 2000 al mese, circa un giorno di registrazione.
- GitHub sospende i workflow pianificati dopo 60 giorni senza attività nel repo.
