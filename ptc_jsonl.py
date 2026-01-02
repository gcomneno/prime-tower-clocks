"""JSONL backend for Prime Tower Clocks (PTC).

File format (v1):
  - First line: header {"type":"ptc","version":1,"base":2,...}
  - Next lines: clock records {"p":..., "z":true} or {"p":..., "z":false, "e":...}
  - Optional last line: summary {"type":"summary","k":...,"M_bits":...,"N_bits":...,"lossless_claim":...}

This module is intentionally independent from the PTC-bin backend.
"""

from __future__ import annotations

import json

from ptc_model import ClockRec, PTCSig


def dump_signature_jsonl(sig: PTCSig, path: str, include_summary: bool = True) -> None:
    """Write signature to JSONL in canonical-ish key order."""
    header: dict[str, object] = {"type": "ptc", "version": 1, "base": sig.base}
    if sig.created_utc:
        header["created_utc"] = sig.created_utc
    if sig.note:
        header["note"] = sig.note

    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(header, separators=(",", ":"), ensure_ascii=False) + "\n")

        for c in sorted(sig.clocks, key=lambda x: x.p):
            if c.z:
                rec = {"p": c.p, "z": True}
            else:
                rec = {"p": c.p, "z": False, "e": int(c.e)}
            f.write(json.dumps(rec, separators=(",", ":"), ensure_ascii=False) + "\n")

        if include_summary:
            summary: dict[str, object] = {"type": "summary", "k": len(sig.clocks)}
            if sig.M_bits is not None:
                summary["M_bits"] = int(sig.M_bits)
            if sig.N_bits is not None:
                summary["N_bits"] = int(sig.N_bits)
            if sig.lossless_claim is not None:
                summary["lossless_claim"] = bool(sig.lossless_claim)
            f.write(json.dumps(summary, separators=(",", ":"), ensure_ascii=False) + "\n")


def _validate_header(obj: dict) -> PTCSig:
    allowed = {"type", "version", "base", "created_utc", "note"}
    extra = set(obj.keys()) - allowed
    if extra:
        raise ValueError(f"Header: chiavi non ammesse: {sorted(extra)}")

    if obj.get("type") != "ptc":
        raise ValueError("Header: type deve essere 'ptc'")
    if obj.get("version") != 1:
        raise ValueError("Header: version deve essere 1")
    base = obj.get("base")
    if not isinstance(base, int) or base < 2:
        raise ValueError("Header: base deve essere un int >= 2")

    return PTCSig(
        base=base,
        clocks=[],
        created_utc=obj.get("created_utc"),
        note=obj.get("note"),
    )


def _validate_clock(obj: dict) -> ClockRec:
    allowed = {"p", "z", "e"}
    extra = set(obj.keys()) - allowed
    if extra:
        raise ValueError(f"Clock: chiavi non ammesse: {sorted(extra)}")

    if "p" not in obj or "z" not in obj:
        raise ValueError("Clock: campi richiesti: p, z")

    p = obj["p"]
    z = obj["z"]
    if not isinstance(p, int) or p < 3:
        raise ValueError("Clock: p deve essere int >= 3")
    if not isinstance(z, bool):
        raise ValueError("Clock: z deve essere boolean")

    if z:
        if "e" in obj:
            raise ValueError(f"Clock p={p}: z=true => e NON deve esserci")
        return ClockRec(p=p, z=True, e=None)

    if "e" not in obj:
        raise ValueError(f"Clock p={p}: z=false => e deve esserci")
    e = obj["e"]
    if not isinstance(e, int) or e < 0:
        raise ValueError(f"Clock p={p}: e deve essere int >= 0")
    return ClockRec(p=p, z=False, e=e)


def _validate_summary(obj: dict) -> dict:
    allowed = {"type", "k", "M_bits", "N_bits", "lossless_claim"}
    extra = set(obj.keys()) - allowed
    if extra:
        raise ValueError(f"Summary: chiavi non ammesse: {sorted(extra)}")
    if obj.get("type") != "summary":
        raise ValueError("Summary: type deve essere 'summary'")
    return obj


def load_signature_jsonl(path: str) -> PTCSig:
    header: PTCSig | None = None
    clocks: list[ClockRec] = []
    seen_p: set[int] = set()
    summary: dict | None = None

    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"JSON invalido alla riga {lineno}: {e}") from e
            if not isinstance(obj, dict):
                raise ValueError(f"Riga {lineno}: atteso oggetto JSON")

            if header is None:
                header = _validate_header(obj)
                continue

            if obj.get("type") == "summary":
                summary = _validate_summary(obj)
                continue

            c = _validate_clock(obj)
            if c.p in seen_p:
                raise ValueError(f"Clock: p duplicato: {c.p}")
            seen_p.add(c.p)
            clocks.append(c)

    if header is None:
        raise ValueError("File vuoto o senza header ptc")
    if not clocks:
        raise ValueError("Nessun clock record trovato (firma inutile)")

    M_bits = summary.get("M_bits") if summary else None
    N_bits = summary.get("N_bits") if summary else None
    lossless_claim = summary.get("lossless_claim") if summary else None

    return PTCSig(
        base=header.base,
        clocks=sorted(clocks, key=lambda x: x.p),
        created_utc=header.created_utc,
        note=header.note,
        M_bits=M_bits,
        N_bits=N_bits,
        lossless_claim=lossless_claim,
    )


__all__ = ["ClockRec", "PTCSig", "dump_signature_jsonl", "load_signature_jsonl"]
