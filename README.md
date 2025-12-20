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
