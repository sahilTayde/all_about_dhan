"""In-process X25519 + ChaCha20-Poly1305 (age primitives). No CLI, no new lock pin.

Envelope ``aad-age/v1`` uses the same primitives as age (X25519, HKDF-SHA256,
ChaCha20-Poly1305). It is not the age-CLI file format. Fake test keys use the
``AGE-TEST-KEY-1`` / ``age1test`` prefixes so nothing in-tree looks like a live
age identity. Upgrade path: wrap ``sops`` / ``age`` CLI or ``cryptography``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from base64 import b64decode, b64encode
from dataclasses import dataclass
from pathlib import Path

from secretstore.errors import SecretClosed

P = 2**255 - 19
A24 = 121665
_BASE = (9).to_bytes(32, "little")
_INFO = b"aad-age/v1"
ID_PREFIX = "AGE-TEST-KEY-1"
RECIP_PREFIX = "age1test"
ENVELOPE_V = "aad-age/v1"


def _rotl32(x: int, n: int) -> int:
    x &= 0xFFFFFFFF
    return ((x << n) | (x >> (32 - n))) & 0xFFFFFFFF


def _qr(s: list[int], a: int, b: int, c: int, d: int) -> None:
    s[a] = (s[a] + s[b]) & 0xFFFFFFFF
    s[d] = _rotl32(s[d] ^ s[a], 16)
    s[c] = (s[c] + s[d]) & 0xFFFFFFFF
    s[b] = _rotl32(s[b] ^ s[c], 12)
    s[a] = (s[a] + s[b]) & 0xFFFFFFFF
    s[d] = _rotl32(s[d] ^ s[a], 8)
    s[c] = (s[c] + s[d]) & 0xFFFFFFFF
    s[b] = _rotl32(s[b] ^ s[c], 7)


def chacha20_block(key: bytes, nonce: bytes, counter: int) -> bytes:
    if len(key) != 32 or len(nonce) != 12:
        raise SecretClosed("invalid_envelope", "chacha20 key/nonce size")
    const = b"expand 32-byte k"
    st = [
        *[int.from_bytes(const[i : i + 4], "little") for i in range(0, 16, 4)],
        *[int.from_bytes(key[i : i + 4], "little") for i in range(0, 32, 4)],
        counter & 0xFFFFFFFF,
        *[int.from_bytes(nonce[i : i + 4], "little") for i in range(0, 12, 4)],
    ]
    w = list(st)
    for _ in range(10):
        _qr(w, 0, 4, 8, 12)
        _qr(w, 1, 5, 9, 13)
        _qr(w, 2, 6, 10, 14)
        _qr(w, 3, 7, 11, 15)
        _qr(w, 0, 5, 10, 15)
        _qr(w, 1, 6, 11, 12)
        _qr(w, 2, 7, 8, 13)
        _qr(w, 3, 4, 9, 14)
    out = bytearray()
    for i, orig in enumerate(st):
        out.extend(((w[i] + orig) & 0xFFFFFFFF).to_bytes(4, "little"))
    return bytes(out)


def chacha20_xor(key: bytes, nonce: bytes, data: bytes, *, counter: int = 1) -> bytes:
    out = bytearray()
    n = 0
    while n < len(data):
        block = chacha20_block(key, nonce, counter + n // 64)
        chunk = data[n : n + 64]
        out.extend(a ^ b for a, b in zip(chunk, block, strict=False))
        n += 64
    return bytes(out)


def poly1305(key: bytes, msg: bytes) -> bytes:
    if len(key) != 32:
        raise SecretClosed("invalid_envelope", "poly1305 key size")
    r = int.from_bytes(key[:16], "little") & 0x0FFFFFFC0FFFFFFC0FFFFFFC0FFFFFFF
    s = int.from_bytes(key[16:], "little")
    prime = (1 << 130) - 5
    acc = 0
    for i in range(0, len(msg), 16):
        block = msg[i : i + 16]
        n = int.from_bytes(block + b"\x01", "little")
        acc = ((acc + n) * r) % prime
    return ((acc + s) % (1 << 128)).to_bytes(16, "little")


def _pad16(data: bytes) -> bytes:
    rem = len(data) % 16
    return data if rem == 0 else data + b"\x00" * (16 - rem)


def aead_seal(key: bytes, nonce: bytes, plaintext: bytes, aad: bytes) -> bytes:
    otk = chacha20_block(key, nonce, 0)[:32]
    ct = chacha20_xor(key, nonce, plaintext, counter=1)
    mac_data = _pad16(aad) + _pad16(ct) + len(aad).to_bytes(8, "little") + len(ct).to_bytes(8, "little")
    return ct + poly1305(otk, mac_data)


def aead_open(key: bytes, nonce: bytes, blob: bytes, aad: bytes) -> bytes:
    if len(blob) < 16:
        raise SecretClosed("invalid_envelope", "ciphertext too short")
    ct, tag = blob[:-16], blob[-16:]
    otk = chacha20_block(key, nonce, 0)[:32]
    mac_data = _pad16(aad) + _pad16(ct) + len(aad).to_bytes(8, "little") + len(ct).to_bytes(8, "little")
    expect = poly1305(otk, mac_data)
    if not hmac.compare_digest(expect, tag):
        raise SecretClosed("wrong_identity")
    return chacha20_xor(key, nonce, ct, counter=1)


def _cswap(swap: int, x: int, y: int) -> tuple[int, int]:
    dummy = (-swap) & (x ^ y)
    return x ^ dummy, y ^ dummy


def x25519(scalar: bytes, u: bytes) -> bytes:
    if len(scalar) != 32 or len(u) != 32:
        raise SecretClosed("invalid_envelope", "x25519 size")
    k = bytearray(scalar)
    k[0] &= 248
    k[31] &= 127
    k[31] |= 64
    n = int.from_bytes(k, "little")
    u_int = int.from_bytes(u, "little") % (1 << 255)
    x1 = u_int
    x2, z2 = 1, 0
    x3, z3 = u_int, 1
    swap = 0
    for t in range(254, -1, -1):
        kt = (n >> t) & 1
        swap ^= kt
        x2, x3 = _cswap(swap, x2, x3)
        z2, z3 = _cswap(swap, z2, z3)
        swap = kt
        a = (x2 + z2) % P
        aa = (a * a) % P
        b = (x2 - z2) % P
        bb = (b * b) % P
        e = (aa - bb) % P
        c = (x3 + z3) % P
        d = (x3 - z3) % P
        da = (d * a) % P
        cb = (c * b) % P
        x3 = (da + cb) ** 2 % P
        z3 = (x1 * (da - cb) ** 2) % P
        x2 = (aa * bb) % P
        z2 = (e * (aa + A24 * e)) % P
    x2, x3 = _cswap(swap, x2, x3)
    z2, z3 = _cswap(swap, z2, z3)
    return ((x2 * pow(z2, P - 2, P)) % P).to_bytes(32, "little")


def hkdf_sha256(ikm: bytes, salt: bytes, info: bytes, length: int) -> bytes:
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    okm = b""
    prev = b""
    counter = 1
    while len(okm) < length:
        prev = hmac.new(prk, prev + info + bytes([counter]), hashlib.sha256).digest()
        okm += prev
        counter += 1
    return okm[:length]


def _b64(data: bytes) -> str:
    return b64encode(data).decode("ascii")


def _unb64(text: str, *, what: str) -> bytes:
    try:
        return b64decode(text, validate=True)
    except Exception as exc:
        raise SecretClosed("invalid_envelope", f"bad {what}") from exc


@dataclass(frozen=True)
class AgeIdentity:
    """32-byte X25519 scalar. Repr never prints the scalar."""

    secret: bytes

    def __post_init__(self) -> None:
        if len(self.secret) != 32:
            raise SecretClosed("missing_identity", "identity must be 32 bytes")

    @property
    def public(self) -> bytes:
        return x25519(self.secret, _BASE)

    def encode(self) -> str:
        return ID_PREFIX + self.secret.hex()

    def recipient(self) -> AgeRecipient:
        return AgeRecipient(self.public)

    def __repr__(self) -> str:
        return "AgeIdentity(redacted)"


@dataclass(frozen=True)
class AgeRecipient:
    public: bytes

    def __post_init__(self) -> None:
        if len(self.public) != 32:
            raise SecretClosed("invalid_envelope", "recipient must be 32 bytes")

    def encode(self) -> str:
        return RECIP_PREFIX + self.public.hex()


def generate_identity() -> AgeIdentity:
    return AgeIdentity(secrets.token_bytes(32))


def parse_identity(text: str) -> AgeIdentity:
    raw = text.strip().splitlines()
    lines = [ln.strip() for ln in raw if ln.strip() and not ln.strip().startswith("#")]
    if not lines:
        raise SecretClosed("missing_identity")
    token = lines[0]
    if not token.startswith(ID_PREFIX):
        raise SecretClosed("missing_identity", "not an AAD test/ops identity")
    try:
        secret = bytes.fromhex(token[len(ID_PREFIX) :])
    except ValueError as exc:
        raise SecretClosed("missing_identity", "identity is not hex") from exc
    if len(secret) != 32:
        raise SecretClosed("missing_identity", "identity length")
    return AgeIdentity(secret)


def parse_recipient(text: str) -> AgeRecipient:
    token = text.strip()
    if not token.startswith(RECIP_PREFIX):
        raise SecretClosed("invalid_envelope", "not an AAD recipient")
    try:
        public = bytes.fromhex(token[len(RECIP_PREFIX) :])
    except ValueError as exc:
        raise SecretClosed("invalid_envelope", "recipient is not hex") from exc
    if len(public) != 32:
        raise SecretClosed("invalid_envelope", "recipient length")
    return AgeRecipient(public)


def load_identity_file(path: str | os.PathLike[str] | None) -> AgeIdentity:
    if path is None:
        raise SecretClosed("missing_identity")
    try:
        data = Path(os.fsdecode(path)).read_text(encoding="utf-8")
    except OSError as exc:
        raise SecretClosed("missing_identity") from exc
    return parse_identity(data)


def _shared(secret: bytes, peer_pub: bytes) -> bytes:
    shared = x25519(secret, peer_pub)
    if shared == b"\x00" * 32:
        raise SecretClosed("wrong_identity")
    return shared


def seal(recipient: AgeRecipient, plaintext: bytes, *, account_id: str) -> bytes:
    eph = generate_identity()
    shared = _shared(eph.secret, recipient.public)
    salt = eph.public + recipient.public
    key = hkdf_sha256(shared, salt, _INFO, 32)
    nonce = secrets.token_bytes(12)
    aad = f"{ENVELOPE_V}|{account_id}|{recipient.encode()}".encode()
    blob = aead_seal(key, nonce, plaintext, aad)
    body = {
        "v": ENVELOPE_V,
        "kind": "aad-sops-age",
        "account_id": account_id,
        "recipient": recipient.encode(),
        "eph_pub": _b64(eph.public),
        "nonce": _b64(nonce),
        "ct": _b64(blob),
    }
    return json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")


def open_envelope(identity: AgeIdentity | None, blob: bytes, *, account_id: str) -> bytes:
    if identity is None:
        raise SecretClosed("missing_identity")
    try:
        body = json.loads(blob.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SecretClosed("invalid_envelope") from exc
    if not isinstance(body, dict):
        raise SecretClosed("invalid_envelope")
    if body.get("v") != ENVELOPE_V or body.get("kind") != "aad-sops-age":
        raise SecretClosed("invalid_envelope", "unknown envelope")
    if body.get("account_id") != account_id:
        raise SecretClosed("invalid_envelope", "account mismatch")
    recip_s = body.get("recipient")
    if not isinstance(recip_s, str):
        raise SecretClosed("invalid_envelope")
    recipient = parse_recipient(recip_s)
    if recipient.public != identity.public:
        raise SecretClosed("wrong_identity")
    eph_pub = _unb64(str(body.get("eph_pub", "")), what="eph_pub")
    nonce = _unb64(str(body.get("nonce", "")), what="nonce")
    ct = _unb64(str(body.get("ct", "")), what="ct")
    if len(eph_pub) != 32 or len(nonce) != 12:
        raise SecretClosed("invalid_envelope")
    shared = _shared(identity.secret, eph_pub)
    salt = eph_pub + identity.public
    key = hkdf_sha256(shared, salt, _INFO, 32)
    aad = f"{ENVELOPE_V}|{account_id}|{recipient.encode()}".encode()
    return aead_open(key, nonce, ct, aad)
