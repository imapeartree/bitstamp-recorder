"""Registratore dei dati in tempo reale di Bitstamp (solo canali pubblici, nessuna chiave).

Book e scambi non hanno storico sulle API: per studiare segnali a minuti vanno
registrati. Per ogni mercato salva, in `data/ticks/AAAAMMGG/`:
- `<mercato>_book.jsonl.gz`: una riga al secondo con i primi N livelli di denaro e lettera;
- `<mercato>_trades.jsonl.gz`: ogni scambio, con il lato di chi ha preso liquidità;
- `funding.jsonl.gz`: tasso di funding, mark e index dei perpetui richiesti.
"""

from __future__ import annotations

import argparse
import asyncio
import gzip
import json
import logging
import time
from pathlib import Path

WS_URL = "wss://ws.bitstamp.net"
log = logging.getLogger("recorder")


class Sink:
    """File gzip giornalieri, aperti in aggiunta. Ogni riapertura crea un nuovo blocco gzip valido."""

    def __init__(self, root: Path):
        self.root, self.files, self.day = Path(root), {}, None

    def write(self, name: str, row: dict, now: float) -> None:
        day = time.strftime("%Y%m%d", time.gmtime(now))
        if day != self.day:
            self.close()
            self.day = day
            (self.root / day).mkdir(parents=True, exist_ok=True)
        if name not in self.files:
            self.files[name] = gzip.open(self.root / day / f"{name}.jsonl.gz", "at")
        self.files[name].write(json.dumps(row, separators=(",", ":")) + "\n")

    def close(self) -> None:
        for fh in self.files.values():
            fh.close()
        self.files = {}


def book_row(data: dict, levels: int, now: float) -> dict:
    return {
        "t": round(now, 3),
        "ts": int(data["microtimestamp"]),
        "b": [[float(p), float(q)] for p, q in data["bids"][:levels]],
        "a": [[float(p), float(q)] for p, q in data["asks"][:levels]],
    }


def trade_row(data: dict, now: float) -> dict:
    # type: 0 = acquisto aggressivo, 1 = vendita aggressiva
    return {"t": round(now, 3), "ts": int(data["microtimestamp"]), "p": float(data["price"]),
            "q": float(data["amount"]), "s": int(data["type"]), "id": data["id"]}


class Recorder:
    def __init__(self, markets, perps, root: Path, levels: int = 10):
        self.markets, self.perps, self.levels = list(markets), list(perps), levels
        self.sink = Sink(root)
        self.latest: dict[str, dict] = {}
        self.counts = {"book": 0, "trades": 0, "funding": 0}
        self.last_funding: dict[str, float] = {}

    def channels(self) -> list[str]:
        out = [f"{kind}_{m}" for m in self.markets for kind in ("live_trades", "order_book")]
        return out + [f"funding_rate_{m}" for m in self.perps]

    def handle(self, msg: dict, now: float) -> None:
        channel, event, data = msg.get("channel", ""), msg.get("event"), msg.get("data")
        if event == "data" and channel.startswith("order_book_"):
            self.latest[channel[len("order_book_"):]] = data      # si scrive al prossimo secondo
        elif event == "trade" and channel.startswith("live_trades_"):
            self.sink.write(f"{channel[len('live_trades_'):]}_trades", trade_row(data, now), now)
            self.counts["trades"] += 1
        elif event == "funding_rate_saved":
            market = data.get("market", channel)
            if now - self.last_funding.get(market, 0.0) >= 60:   # arriva ogni secondo: basta una riga al minuto
                self.last_funding[market] = now
                self.sink.write("funding", {"t": round(now, 3), **data}, now)
                self.counts["funding"] += 1

    def sample(self, now: float) -> None:
        """Una riga di book al secondo per mercato, con l'ultima istantanea ricevuta."""
        for market, data in self.latest.items():
            if data["bids"] and data["asks"]:
                self.sink.write(f"{market}_book", book_row(data, self.levels, now), now)
                self.counts["book"] += 1

    async def _sampler(self) -> None:
        while True:
            await asyncio.sleep(1 - time.time() % 1)
            self.sample(time.time())

    async def _stream(self) -> None:
        import websockets

        async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=20) as ws:
            for ch in self.channels():
                await ws.send(json.dumps({"event": "bts:subscribe", "data": {"channel": ch}}))
            log.info("Connesso: %d canali", len(self.channels()))
            async for raw in ws:
                msg = json.loads(raw)
                if msg.get("event") == "bts:request_reconnect":
                    return
                self.handle(msg, time.time())

    async def run(self, seconds: float | None = None) -> None:
        sampler = asyncio.create_task(self._sampler())
        deadline = None if seconds is None else time.time() + seconds
        backoff = 1.0
        try:
            while deadline is None or time.time() < deadline:
                try:
                    left = None if deadline is None else max(0.1, deadline - time.time())
                    await asyncio.wait_for(self._stream(), left)
                    backoff = 1.0
                except asyncio.TimeoutError:
                    break
                except Exception as exc:  # rete caduta, server chiuso: si riprova
                    log.warning("Connessione persa (%s); riprovo tra %.0f s", exc, backoff)
                    self.latest.clear()   # niente book vecchi mentre si è scollegati
                    await asyncio.sleep(backoff)
                    backoff = min(30.0, backoff * 2)
        finally:
            sampler.cancel()
            self.sink.close()
            log.info("Chiuso. Righe scritte: %s", self.counts)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Registra book, scambi e funding da Bitstamp (dati pubblici).")
    ap.add_argument("--markets", nargs="+", default=["xrpeur", "xrpusd", "btceur", "btcusd"])
    ap.add_argument("--perps", nargs="*", default=["xrpusd-perp", "btcusd-perp"])
    ap.add_argument("--root", type=Path, default=Path("data/ticks"))
    ap.add_argument("--levels", type=int, default=10)
    ap.add_argument("--seconds", type=float, help="durata; senza, registra finché non lo fermi (Ctrl-C)")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    rec = Recorder(args.markets, args.perps, args.root, args.levels)
    try:
        asyncio.run(rec.run(args.seconds))
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
