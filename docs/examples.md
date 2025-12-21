# Prime Tower Clocks (PTC) — Examples
Questo file è pensato come “manuale da campo”: comandi pronti + spiegazione passo‑passo di cosa succede. (Sì: anche se oggi il mostro è un criceto 🐹🕰️)

---

## Esempio 1 — N piccolo (default = preset `fit`) + JSONL + ricostruzione

Comando:

```bash
python3 prime_tower_clocks.py 276 --dump-jsonl sig.jsonl --reconstruct
```

oppure

```bash
make demo
```

Output (esempio reale):

```bash
[ptc] preset=fit  min_p=3  max_p=2000000  pool_limit=50000  prefer_large=False
[ptc] k=2  M_bits=11  N_bits=9  lossless_by_bits=True
[ptc] overshoot_bits=2  overshoot_dec=0
[io] wrote sig.jsonl
[crt] N_mod_M=276
[crt] M=1159
[crt] reconstructed N=276  (lossless: M>N)
```

File `sig.jsonl` generato:

```jsonl
{"type":"ptc","version":1,"base":2,"created_utc":"2025-12-21T06:52:38Z","note":"Prime Tower Clocks signature"}
{"p":19,"z":false,"e":17}
{"p":61,"z":false,"e":5}
{"type":"summary","k":2,"M_bits":11,"N_bits":9,"lossless_claim":true}
```

### Cosa significa ogni riga del JSONL

1) **Header** (`type=ptc`): metadati minimi (versione, base, timestamp).
2) Ogni riga con `p` è un **orologio** (un primo “nice”):
   - `p`: modulo
   - `z`: se `true` significa **p divide N** (quindi il residuo è 0 e l’esponente non esiste)
   - `e`: esponente tale che `2^e ≡ r (mod p)` (solo se `z=false`)
3) **Summary**:
   - `k`: numero totale di orologi
   - `M_bits`: bit-length di `M = Π p`
   - `N_bits`: bit-length di `N`
   - `lossless_claim`: `true` se `M_bits > N_bits` (condizione sufficiente per `M > N`)

Nota importante: i clock nel JSONL sono **ordinati per p crescente** (stabilità/leggibilità),
quindi l’anchor `61` può apparire dopo un altro clock più piccolo (qui `19`).

### Passo per passo: come PTC arriva a quell’output

#### Step A — Calcolo del “target” (quanto deve vedere la torre)
- `N = 276` ha `D = 3` cifre decimali.
- Il target usato dal selettore è `10^D = 1000`.
- Obiettivo: scegliere orologi tali che `M = Π p > 1000`.
  Questo garantisce che la firma sia **lossless per qualsiasi numero a 3 cifre**.

#### Step B — Scelta degli orologi (preset `fit`)
- L’anchor è fisso: `p1 = 61`.
  Dopo l’anchor: `M = 61`.
- In modalità `fit` si cerca un ultimo orologio “su misura”, cioè il **p più piccolo**
  che faccia superare il target:

  Serve:
  ```text
  p2 > target / M  = 1000 / 61 ≈ 16.39
  ```
  
  Il più piccolo “nice prime” ≥ 17 trovato nel range è `p2 = 19`.

- Ora:
  ```text
  M = 61 * 19 = 1159  > 1000

  ```
  Quindi il selettore si ferma: `k = 2`.

#### Step C — Calcolo dei residui r = N mod p
- Per `p=61`:
  - `r = 276 mod 61 = 32`

- Per `p=19`:
  - `r = 276 mod 19 = 10`

#### Step D — Trasformazione del residuo in esponente (discrete log in base 2)
Per ogni `p`, la firma salva `e` tale che:

```text
2^e ≡ r (mod p)
```

- Per `p=61`: `e=5` perché `2^5 = 32` e quindi `2^5 mod 61 = 32`.
- Per `p=19`: `e=17` perché `2^17 mod 19 = 10` (torna il residuo calcolato sopra).

Se invece `r=0` (cioè `p | N`) allora:
- `z=true`
- `e` non esiste (0 non è nel gruppo moltiplicativo), quindi viene omesso.

#### Step E — Perché `M_bits=11` e `N_bits=9`
`X_bits` significa: quanti bit servono a rappresentare `X` in binario.

- `N=276` sta tra `256 (=2^8)` e `512 (=2^9)` ⇒ `N_bits=9`
- `M=1159` sta tra `1024 (=2^10)` e `2048 (=2^11)` ⇒ `M_bits=11`

`lossless_by_bits=True` perché `M_bits > N_bits` ⇒ sicuramente `M > N`.

#### Step F — Ricostruzione via CRT (Chinese Remainder Theorem)
Dalla firma si ricavano le congruenze:
- `N ≡ 32 (mod 61)`
- `N ≡ 10 (mod 19)`

Il CRT ricostruisce l’unico valore `N_mod_M` in `[0, M-1]` che soddisfa entrambe.
Qui:
- `N_mod_M = 276`
- `M = 1159`

Siccome `M > N`, quel valore è proprio l’originale: `reconstructed N = 276`.

---

## Esempio 2 — N enorme (60 cifre) e confronto preset

Con N molto grande, i preset iniziano a differire davvero: cambiano `k` (numero di orologi) e “overshoot” di M.

Esempio comando (N di 60 cifre):

```bash
N=$(python3 - <<'PY'
print(int("314159265358979323846264338327950288419716939937510582097494"))
PY
)

python3 prime_tower_clocks.py "$N" --preset minimal --reconstruct
python3 prime_tower_clocks.py "$N" --preset fast    --reconstruct
python3 prime_tower_clocks.py "$N" --preset safe    --reconstruct
python3 prime_tower_clocks.py "$N" --preset fit     --reconstruct
```

Come leggere i risultati:
- `overshoot_bits = M_bits - N_bits` ⇒ quanta “prigione” in più stai costruendo.
- `overshoot_dec` ⇒ quante cifre extra ha M rispetto al target `10^D` (0 = su misura).
- `k` più basso ⇒ meno righe JSONL / meno congruenze CRT.
- `M_bits - N_bits` piccolo ⇒ M “su misura” (meno titanio).
- `minimal` tende a minimizzare `k` usando primi grandi.
- `fit` tende a minimizzare l’overshoot dell’ultimo step quando possibile.

Suggerimento pratico:
- per CI/demo/iterazione rapida: `fit` o `fast`
- per numeri enormi con obiettivo “k piccolo”: `minimal`
- se temi “pool insufficiente”: `safe`

---

## FAQ lampo

**Perché nel JSONL l’anchor (61) non è per forza la prima riga?**  
Perché nella serializzazione i clock vengono ordinati per `p` crescente per stabilità.

**Cosa succede se `M ≤ N`?**  
La firma è *lossy*: ricostruisci `N mod M`. Il JSONL è comunque coerente, ma non identifica univocamente N.

**Perché serve che i primi siano “nice”?**  
Perché così ogni residuo non nullo è una potenza di 2 (esiste e) e il discrete log è veloce (p−1 smooth).
