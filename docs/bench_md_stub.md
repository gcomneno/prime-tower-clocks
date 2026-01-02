# Benchmarks

Questo documento viene generato automaticamente da `tools/bench_pack.py`.

Esegui ad esempio:

```bash
# benchmark su dataset esistente (directory di *.jsonl)
python3 tools/bench_pack.py --jsonl-dir out/ --outdir bench_out --write-docs

# oppure: genera dataset (lento, 1 firma per processo)
python3 tools/bench_pack.py --generate 1000 --digits 50 --preset fit --outdir bench_out --write-docs
```

Il report verrà scritto in `docs/bench.md`.
