#!/usr/bin/env bash
# Registra a blocchi, cifra e carica ogni blocco nella release del giorno (data-AAAAMMGG).
# Se il giro viene interrotto si perde al massimo un blocco.
# Nessun file viene caricato in chiaro: se la cifratura fallisce, il blocco si scarta.
set -u

CHUNKS="${CHUNKS:-6}"
SECONDS_PER_CHUNK="${SECONDS_PER_CHUNK:-3420}"
RUN="${GITHUB_RUN_ID:-locale}"
KEY="data_public_key.txt"

if [ ! -s "$KEY" ]; then
  echo "Manca $KEY: senza chiave pubblica non si registra, per non caricare dati in chiaro."
  exit 1
fi

for i in $(seq 1 "$CHUNKS"); do
  rm -rf ticks upload
  mkdir -p upload
  python record.py --seconds "$SECONDS_PER_CHUNK" --root ticks || echo "registratore terminato con errore"

  for day_dir in ticks/*/; do
    [ -d "$day_dir" ] || continue
    day="$(basename "$day_dir")"
    tag="data-$day"
    for f in "$day_dir"*.jsonl.gz; do
      [ -f "$f" ] || continue
      cp "$f" "upload/$(basename "$f" .jsonl.gz).$RUN-$i.jsonl.gz"
    done
    ls upload/* >/dev/null 2>&1 || continue
    if ! python seal.py "$KEY" upload/*; then
      echo "cifratura fallita: blocco scartato"
      rm -f upload/*
      continue
    fi
    rm -f upload/*.jsonl.gz   # per sicurezza: restano solo i file .enc
    # Due giri sovrapposti possono creare la stessa release insieme: l'errore del secondo si ignora.
    gh release view "$tag" >/dev/null 2>&1 ||
      gh release create "$tag" --title "$tag" --notes "" ||
      true
    gh release upload "$tag" upload/*.enc --clobber || echo "caricamento fallito per $tag"
    rm -f upload/*
  done
done
