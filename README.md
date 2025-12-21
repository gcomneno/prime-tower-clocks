# Prime Tower Clocks 🕰️

**Prime Tower Clocks** è un laboratorio matematico–computazionale per **“ingabbiare” numeri interi (anche enormi)** dentro una firma modulare, costruita usando **numeri primi come orologi** e il **Teorema Cinese del Resto (CRT)**.

Se hai mai guardato un numero da 100 cifre pensando  
> “ok, tu sei un mostro”  

questo progetto è l'**incantesimo** che lo mette in gabbia 😄

---

## Idea in una frase (versione scimmietta 🐒)

Un numero **N** viene osservato da tanti **orologi a base primo**.  

Ogni orologio dice solo:
> “che ora è, modulo p?”

Mettendo insieme abbastanza orologi, **il numero non può più scappare**.

---

## L’idea chiave
- Scegli una base fissa: **2**
- Scegli una lista di **primi** \( p₁, p₂, … \) → gli *orologi*
- Per ogni primo p:
  - calcoli `r = N mod p`
  - se `r ≠ 0`, trovi un esponente `e` tale che **2ᵉ ≡ r (mod p)**
  - se `r = 0`, annoti semplicemente: **p divide N**

Questa collezione di informazioni è la **firma** di N.

---

## Perché funziona davvero (intuizione)
Ogni orologio vede N in modo parziale.  
Ma **tutti insieme** impongono vincoli così forti che:
- se il prodotto degli orologi **M = p₁·p₂·…** è **più grande di N**  
- allora esiste **un solo numero possibile** compatibile con tutti

👉 quel numero è **N stesso**

Questo è il **Teorema Cinese del Resto (CRT)** in azione.

---

## Quando la firma è *lossless*
La firma è **lossless** (ricostruzione perfetta) se:

```
M > N
```

cioè se il “campo visivo” degli orologi è più grande del numero osservato.

Se invece `M ≤ N`:
- la firma identifica solo **N modulo M**
- più numeri diversi condividono la stessa firma (firma **lossy**, ma comunque utile!)

---

## Cosa viene salvato (firma minimale)
Per ogni orologio (primo `p`) salviamo solo:
- `p` → il primo
- `z` → `true` se `p` divide N
- `e` → l’esponente tale che `2^e ≡ N (mod p)` (solo quando `z=false`)

Niente N.  
Niente residui espliciti.  
Solo ciò che serve per ricostruire.

---

## Formato su file: JSONL
La firma viene salvata in **JSON Lines** (una riga JSON per riga).

Esempio:
```json
{"type":"ptc","version":1,"base":2}
{"p":5,"z":false,"e":0}
{"p":11,"z":false,"e":0}
{"p":13,"z":false,"e":4}
{"p":23,"z":true}
{"type":"summary","k":4,"M_bits":15,"N_bits":9,"lossless_claim":true}
```

Il `summary` non serve per ricostruire, ma dice chiaramente se la firma era **lossless garantita**.

### Campi di summary (k / M_bits / N_bits)

Nel record finale `{"type":"summary",...}`:

- `k` = **numero di orologi** (quante righe `{"p":...}` ci sono)
- `M_bits` = `bit_length(M)` dove `M = Π p` (numero di bit necessari a rappresentare `M`)
- `N_bits` = `bit_length(N)`
- `lossless_claim` = `True` se `M_bits > N_bits` (condizione **sufficiente** per garantire `M > N`)

Nota: `M_bits > N_bits` garantisce lossless, ma non è una condizione necessaria: può capitare `M > N` anche con `M_bits == N_bits`.


---

## Uso rapido

### Costruire una firma + salvarla
```bash
python3 prime_tower_clocks.py 276 --dump-jsonl sig.jsonl
```

### Ricostruire da firma
```bash
python3 prime_tower_clocks.py --load-jsonl sig.jsonl --reconstruct
```

### Demo completa
```bash
make demo
```


## Preset di torri (Step 3 + "fit")

I preset servono a scegliere **range** e **strategia** di selezione degli orologi.

- `minimal` (default): pochi orologi, primi grandi (stile 32-bit) → **k piccolo**, numeri nel JSONL più grossi.
- `fast`: range basso → veloce per CI/demo.
- `safe`: range più ampio + pool più grande → meno probabilità di “pool insufficiente”.
- `fit`: **su misura**: quando è possibile chiudere con un solo orologio in più, sceglie il **p più piccolo** che fa superare il target (`M > 10^D`).

> Nota onesta: “fit” non è magia. È un greedy per minimizzare l’overshoot *nell’ultimo step*.

### Esempio con N a 60 cifre

Usa questo N (60 cifre, deterministico):

```bash
N=123456789012345678901234567890123456789012345678901234567890
```

Confronto rapido:

```bash
python3 prime_tower_clocks.py "$N" --preset minimal   --dump-jsonl minimal.jsonl   --reconstruct
python3 prime_tower_clocks.py "$N" --preset fast      --dump-jsonl fast.jsonl      --reconstruct
python3 prime_tower_clocks.py "$N" --preset safe      --dump-jsonl safe.jsonl      --reconstruct
python3 prime_tower_clocks.py "$N" --preset fit       --dump-jsonl fit.jsonl       --reconstruct
```

Guarda la riga `[ptc] k=... M_bits=...` (e anche la riga `{"type":"summary",...}` dentro il JSONL):

- `k` = numero di orologi
- `M_bits` = “campo visivo” totale degli orologi (bit length di `M = Π p`)
- se `M_bits > N_bits` allora la firma è **lossless garantita** (`M > N`)


---

## A cosa serve davvero questo progetto
- studio di **rappresentazioni modulari compatte**
- firme numeriche **indipendenti dalla dimensione di N**
- esperimenti su **CRT, log discreti, primi “nice”**
- laboratorio per numeri enormi (100+ cifre senza paura)

⚠️ **Non è crittografia**
⚠️ **Non è compressione classica**
È un **laboratorio matematico esplorativo**.

---

## Filosofia del progetto
- chiarezza > magia
- firma minimale > ridondanza
- se una cosa non è dimostrabile, **non viene venduta**
- humor ammesso 😄

---

## Motto ufficiale
> *If the clocks are enough, the monster has nowhere to hide.*
🕰️

## Diagramma ASCII della “Torre degli Orologi”

```
          N  (mostro)
            |
            v
   +-------------------+
   | Prime Tower Clocks |
   +-------------------+
     |      |      |
     v      v      v
  p=61   p=97   p=101     ... (orologi)
  r=N%p  r=N%p  r=N%p
  e:2^e=r   z: p|N   e:2^e=r
     \      |      /
      \     |     /
       v    v    v
        +--------+
        |  CRT   |
        +--------+
            |
            v
        N mod M   (lossless se M>N)
```

## Dev setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

Tests
```bash
pytest -q
```

---

Da root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

ruff check .
ruff format .

pytest -q
make demo
```

![CI](https://img.shields.io/github/actions/workflow/status/gcomneno/prime-tower-clocks/ci.yml?branch=main&label=CI)
![License](https://img.shields.io/github/license/gcomneno/prime-tower-clocks)
