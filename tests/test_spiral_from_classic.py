from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import ptc_jsonl
from ptc_spiral.from_classic import classic_to_spiral


def test_classic_to_spiral_from_generated_jsonl(tmp_path: Path):
    """
    Generate a classic JSONL signature via prime_tower_clocks.py, then convert to SpiralSig.
    This avoids relying on repo-local "out/" artifacts and avoids guessing ptc_model constructors.
    """
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "prime_tower_clocks.py"
    assert script.exists()

    N = 12345
    out_jsonl = tmp_path / "sig.jsonl"

    # Generate classic signature JSONL
    cmd = [
        sys.executable,
        str(script),
        str(N),
        "--dump-jsonl",
        str(out_jsonl),
        # no need to reconstruct; keep it fast
    ]
    subprocess.run(cmd, cwd=repo_root, check=True, capture_output=True, text=True)
    assert out_jsonl.exists()

    classic = ptc_jsonl.load_signature_jsonl(str(out_jsonl))
    spiral = classic_to_spiral(classic)

    # Basic shape
    assert spiral.k == len(classic.clocks)
    assert spiral.k == len(spiral.primes) == len(spiral.xs)

    # Spiral coherence must always hold
    Ms = spiral.Ms()
    for i in range(1, spiral.k):
        assert spiral.xs[i] % Ms[i - 1] == spiral.xs[i - 1]

    # If conversion declares lossless, last x must equal N (because M_last > N)
    if spiral.mode == "lossless":
        assert spiral.xs[-1] == N
