"""Cifra i file con una chiave pubblica prima del caricamento.

Uso: python seal.py <file_chiave_pubblica> <file> [<file> ...]

Ogni file diventa <file>.enc e l'originale viene cancellato. Si usa la "sealed box"
di libsodium (X25519 + XSalsa20-Poly1305): chi ha solo la chiave pubblica, come
questo repo e GitHub, può cifrare ma non decifrare. La chiave privata non sta qui.
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

from nacl.public import PublicKey, SealedBox


def load_public_key(path: Path) -> PublicKey:
    return PublicKey(base64.b64decode(Path(path).read_text().strip()))


def seal_file(path: Path, key: PublicKey) -> Path:
    out = path.with_name(path.name + ".enc")
    out.write_bytes(SealedBox(key).encrypt(path.read_bytes()))
    path.unlink()
    return out


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    key = load_public_key(Path(argv[0]))
    for name in argv[1:]:
        seal_file(Path(name), key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
