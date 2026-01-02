"""PTC-bin (binary) backend with Tower Dictionary + CRC32.

Header:
  - magic: b"PTC" (3 bytes)
  - vb: 1 byte (version<<4 | base)
  - flags: 1 byte

Frames:
  - type: 1 byte
  - len: uLEB128 varint (payload length)
  - payload: bytes
  - crc32: 4 bytes big-endian over (type||len_bytes||payload) if HAS_CRC32

Frame types:
  0x01 = TOWER_DICT
  0x02 = SIGNATURE
  0x7F = END (optional)

TOWER_DICT payload:
  dict_id varint
  k varint
  primes encoded as [p0, d1, d2, ...] varints (deltas) if DELTA_P flag

SIGNATURE payload:
  dict_id varint
  z_bitmap ceil(k/8) bytes, bit i=1 => z=true for primes[i]
  e_bitstream packed LSB-first, concatenated e for clocks with z=false,
  where w(p)=bit_length(p-2) bits per exponent.

This module does NOT deal with JSONL I/O.
"""

from __future__ import annotations

import io
import zlib
from dataclasses import dataclass

from ptc_model import ClockRec, PTCSig, e_bit_width_for_prime
from tower_dict import TowerDict, delta_decode_primes, delta_encode_primes

MAGIC = b"PTC"
VERSION = 1

FRAME_TOWER_DICT = 0x01
FRAME_SIGNATURE = 0x02
FRAME_END = 0x7F

# flags bitfield
FLAG_HAS_CRC32 = 1 << 0
FLAG_HAS_LENGTH = 1 << 1
FLAG_BITPACK_E = 1 << 2
FLAG_DELTA_P = 1 << 3


class PTCBinError(ValueError):
    pass


def pack_vb(version: int, base: int) -> int:
    if not (0 <= version <= 15):
        raise PTCBinError("version must be in [0..15]")
    if not (0 <= base <= 15):
        raise PTCBinError("base must be in [0..15]")
    return ((version & 0x0F) << 4) | (base & 0x0F)


def unpack_vb(vb: int) -> tuple[int, int]:
    return ((vb >> 4) & 0x0F, vb & 0x0F)


def uleb128_encode(n: int) -> bytes:
    if n < 0:
        raise PTCBinError("uleb128 only supports non-negative integers")
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def uleb128_decode_from(data: bytes, offset: int = 0) -> tuple[int, int]:
    n = 0
    shift = 0
    i = offset
    while i < len(data):
        b = data[i]
        i += 1
        n |= (b & 0x7F) << shift
        if (b & 0x80) == 0:
            return n, i
        shift += 7
        if shift > 70:
            raise PTCBinError("uleb128 too large")
    raise PTCBinError("unexpected EOF while reading uleb128")


def crc32_be(data: bytes) -> bytes:
    c = zlib.crc32(data) & 0xFFFFFFFF
    return c.to_bytes(4, "big")


def _read_exact(fp: io.BufferedReader, n: int) -> bytes:
    b = fp.read(n)
    if b is None or len(b) != n:
        raise PTCBinError("unexpected EOF")
    return b


def _pack_z_bitmap(primes: tuple[int, ...], clocks: list[ClockRec]) -> bytes:
    idx = {p: i for i, p in enumerate(primes)}
    k = len(primes)
    bitmap = bytearray((k + 7) // 8)
    for c in clocks:
        i = idx.get(c.p)
        if i is None:
            raise PTCBinError(f"clock p={c.p} not present in tower dict")
        if c.z:
            bitmap[i // 8] |= 1 << (i % 8)
    return bytes(bitmap)


def _unpack_z_bitmap(primes: tuple[int, ...], bitmap: bytes) -> list[bool]:
    k = len(primes)
    need = (k + 7) // 8
    if len(bitmap) != need:
        raise PTCBinError("invalid z_bitmap length")
    out: list[bool] = []
    for i in range(k):
        out.append(bool((bitmap[i // 8] >> (i % 8)) & 1))
    return out


def _bitpack_es(primes: tuple[int, ...], clocks: list[ClockRec]) -> bytes:
    by_p = {c.p: c for c in clocks}
    buf = 0
    nbits = 0
    out = bytearray()

    for p in primes:
        c = by_p.get(p)
        if c is None:
            raise PTCBinError(f"missing clock for p={p}")
        if c.z:
            continue
        if c.e is None:
            raise PTCBinError(f"clock p={p}: z=false but e is None")
        w = e_bit_width_for_prime(p)
        mask = (1 << w) - 1
        v = int(c.e) & mask
        buf |= v << nbits
        nbits += w
        while nbits >= 8:
            out.append(buf & 0xFF)
            buf >>= 8
            nbits -= 8

    if nbits:
        out.append(buf & 0xFF)
    return bytes(out)


def _bitunpack_es(primes: tuple[int, ...], z_flags: list[bool], bitstream: bytes) -> list[int]:
    buf = 0
    nbits = 0
    i = 0
    es: list[int] = []

    for p, z in zip(primes, z_flags):
        if z:
            continue
        w = e_bit_width_for_prime(p)
        while nbits < w:
            if i >= len(bitstream):
                raise PTCBinError("not enough bits for exponent stream")
            buf |= bitstream[i] << nbits
            nbits += 8
            i += 1
        mask = (1 << w) - 1
        v = buf & mask
        buf >>= w
        nbits -= w
        es.append(int(v))

    return es


@dataclass(frozen=True)
class PTCBinHeader:
    version: int
    base: int
    flags: int


@dataclass(frozen=True)
class DecodedSignature:
    dict_id: int
    sig: PTCSig


@dataclass(frozen=True)
class PTCBinFile:
    header: PTCBinHeader
    dicts: dict[int, TowerDict]
    signatures: list[DecodedSignature]


def write_ptcbin(path: str, *, base: int, dicts: list[TowerDict], signatures: list[DecodedSignature]) -> None:
    flags = FLAG_HAS_CRC32 | FLAG_HAS_LENGTH | FLAG_BITPACK_E | FLAG_DELTA_P
    header = MAGIC + bytes([pack_vb(VERSION, base), flags])

    dict_map = {d.dict_id: d for d in dicts}
    for ds in signatures:
        if ds.dict_id not in dict_map:
            raise PTCBinError(f"signature references unknown dict_id={ds.dict_id}")
        if ds.sig.base != base:
            raise PTCBinError("all signatures must match file base")

    with open(path, "wb") as f:
        f.write(header)

        for d in dicts:
            payload = bytearray()
            payload += uleb128_encode(d.dict_id)
            payload += uleb128_encode(len(d.primes))
            for x in delta_encode_primes(d.primes):
                payload += uleb128_encode(int(x))
            _write_frame(f, FRAME_TOWER_DICT, bytes(payload), flags)

        for ds in signatures:
            td = dict_map[ds.dict_id]
            clocks = sorted(ds.sig.clocks, key=lambda c: c.p)
            z_bitmap = _pack_z_bitmap(td.primes, clocks)
            e_stream = _bitpack_es(td.primes, clocks)

            payload = bytearray()
            payload += uleb128_encode(ds.dict_id)
            payload += z_bitmap
            payload += e_stream
            _write_frame(f, FRAME_SIGNATURE, bytes(payload), flags)

        _write_frame(f, FRAME_END, b"", flags)


def _write_frame(f: io.BufferedWriter, frame_type: int, payload: bytes, flags: int) -> None:
    t = bytes([frame_type])
    len_bytes = uleb128_encode(len(payload))
    blob = t + len_bytes + payload
    f.write(t)
    f.write(len_bytes)
    f.write(payload)
    if flags & FLAG_HAS_CRC32:
        f.write(crc32_be(blob))


def read_ptcbin(path: str) -> PTCBinFile:
    with open(path, "rb") as f:
        magic = _read_exact(f, 3)
        if magic != MAGIC:
            raise PTCBinError("bad magic")

        vb = _read_exact(f, 1)[0]
        flags = _read_exact(f, 1)[0]
        version, base = unpack_vb(vb)
        if version != VERSION:
            raise PTCBinError(f"unsupported version: {version}")
        if not (flags & FLAG_HAS_LENGTH):
            raise PTCBinError("files without length are not supported")
        if not (flags & FLAG_HAS_CRC32):
            raise PTCBinError("files without CRC32 are not supported")
        if not (flags & FLAG_BITPACK_E):
            raise PTCBinError("files without BITPACK_E are not supported")

        header = PTCBinHeader(version=version, base=base, flags=flags)
        dicts: dict[int, TowerDict] = {}
        signatures: list[DecodedSignature] = []

        while True:
            b = f.read(1)
            if not b:
                break
            frame_type = b[0]

            len_raw = bytearray()
            while True:
                c = _read_exact(f, 1)[0]
                len_raw.append(c)
                if (c & 0x80) == 0:
                    break

            payload_len, _ = uleb128_decode_from(bytes(len_raw), 0)
            payload = _read_exact(f, payload_len)

            crc = _read_exact(f, 4)
            blob = bytes([frame_type]) + bytes(len_raw) + payload
            if crc32_be(blob) != crc:
                raise PTCBinError("CRC32 mismatch")

            if frame_type == FRAME_END:
                break
            if frame_type == FRAME_TOWER_DICT:
                td = _decode_tower_dict_payload(payload)
                dicts[td.dict_id] = td
                continue
            if frame_type == FRAME_SIGNATURE:
                ds = _decode_signature_payload(payload, header, dicts)
                signatures.append(ds)
                continue

            raise PTCBinError(f"unknown frame type: {frame_type}")

        return PTCBinFile(header=header, dicts=dicts, signatures=signatures)


def _decode_tower_dict_payload(payload: bytes) -> TowerDict:
    off = 0
    dict_id, off = uleb128_decode_from(payload, off)
    k, off = uleb128_decode_from(payload, off)
    if k <= 0:
        raise PTCBinError("invalid k in tower dict")

    deltas: list[int] = []
    for _ in range(int(k)):
        v, off = uleb128_decode_from(payload, off)
        deltas.append(int(v))

    primes = delta_decode_primes(deltas)
    if len(primes) != int(k):
        raise PTCBinError("decoded primes length mismatch")
    return TowerDict(dict_id=int(dict_id), primes=tuple(int(x) for x in primes))


def _decode_signature_payload(payload: bytes, header: PTCBinHeader, dicts: dict[int, TowerDict]) -> DecodedSignature:
    off = 0
    dict_id, off = uleb128_decode_from(payload, off)
    td = dicts.get(int(dict_id))
    if td is None:
        raise PTCBinError(f"signature references unknown dict_id={dict_id}")

    k = len(td.primes)
    bitmap_len = (k + 7) // 8
    if off + bitmap_len > len(payload):
        raise PTCBinError("signature payload too short for z_bitmap")
    z_bitmap = payload[off : off + bitmap_len]
    off += bitmap_len
    e_stream = payload[off:]

    z_flags = _unpack_z_bitmap(td.primes, z_bitmap)
    es = _bitunpack_es(td.primes, z_flags, e_stream)

    clocks: list[ClockRec] = []
    e_i = 0
    for p, z in zip(td.primes, z_flags):
        if z:
            clocks.append(ClockRec(p=int(p), z=True, e=None))
        else:
            clocks.append(ClockRec(p=int(p), z=False, e=int(es[e_i])))
            e_i += 1

    return DecodedSignature(dict_id=int(dict_id), sig=PTCSig(base=header.base, clocks=clocks))


__all__ = [
    "PTCBinError",
    "PTCBinHeader",
    "PTCBinFile",
    "DecodedSignature",
    "read_ptcbin",
    "write_ptcbin",
    "uleb128_encode",
    "uleb128_decode_from",
    "pack_vb",
    "unpack_vb",
]
