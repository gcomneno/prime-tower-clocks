# PTC benchmark results

- Dataset: `gen:500x50d preset=fit seed=12345`
- Files: 500 JSONL signature file(s)
- Python: `3.12.3`
- Platform: `Linux 6.8.0-90-generic`
- Runs per operation: 3 (reported min+avg)

## Sizes

| Artifact | Bytes | Bytes/sig | Notes |
|---|---:|---:|---|
| JSONL files (sum) | 244370 | 488.7 | sum of per-signature files |
| JSONL concat | 244870 | 489.7 | single stream (best-case) |
| gzip(JSONL concat) | 22734 | 45.5 | gzip -9; sha256=210b8f683991… |
| zstd(JSONL concat) | 19385 | 38.8 | zstd -9; sha256=1e263207dfa4… |
| PTC-bin | 15535 | 31.1 | sha256=cf2806d8ed75… |

## Timings

| Operation | min (s) | avg (s) | ms/sig (avg) | Notes |
|---|---:|---:|---:|---|
| gzip encode | 0.0148 | 0.0151 | 0.030 | dataset.concat.jsonl -> .gz |
| zstd encode | 0.0049 | 0.0094 | 0.019 | dataset.concat.jsonl -> .zst |
| pack | 0.0440 | 0.0455 | 0.091 | JSONL files -> dataset.ptcbin |
| unpack | 0.0747 | 0.0958 | 0.192 | dataset.ptcbin -> JSONL files |

## Notes

- gzip/zstd numbers are for a *single concatenated stream* (best-case for text redundancy).
- PTC-bin includes tower dictionary frames + CRC32; unpack writes one JSONL per signature.
- If you benchmark a directory, file ordering is lexicographic by path (stable).

On this dataset (500×50-digit, preset=fit), PTC-bin achieved 31.1 B/sig, beating zstd -9 (38.8 B/sig) and gzip -9 (45.5 B/sig).