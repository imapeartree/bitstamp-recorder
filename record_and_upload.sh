#!/usr/bin/env bash
# Registra a blocchi e carica ogni blocco nella release del giorno (data-AAAAMMGG).
# Se il giro viene interrotto si perde al massimo un blocco.
set -u

CHUNKS="${CHUNKS:-6}"
SECONDS_PER_CHUNK="${SECONDS_PER_CHUNK:-3420}"
RUN="${GITHUB_RUN_ID:-locale}"

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
    # Due giri sovrapposti possono creare la stessa release insieme: l'errore del secondo si ignora.
    gh release view "$tag" >/dev/null 2>&1 ||
      gh release create "$tag" --title "Dati $day" --notes "Book, scambi e funding registrati il $day (UTC)." ||
      true
    gh release upload "$tag" upload/* --clobber || echo "caricamento fallito per $tag"
    rm -f upload/*
  done
done
