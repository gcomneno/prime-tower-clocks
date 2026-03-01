# PTC Spiral (v2)

Spiral is a progressive modular "microscope" centered on an (implicit) integer `N`.

Given primes `p1..pk`, define:

- `M_k = Π_{i<=k} p_i`
- `x_k = N mod M_k`

A Spiral signature stores:
- `primes = [p1..pk]`
- `xs = [x1..xk]`

## Spiral property

For all `k`:

`x_{k+1} % M_k == x_k`

Meaning: each refinement contains the previous observation.

## Modes

### lossy

`mode="lossy"` stores only modular information:
- the last value identifies `N mod M_last`
- many integers share the same last residue

Useful for progressive comparison / filtering.

### lossless (for a known N during build-time)

When constructing from a known `N`, the spiral is lossless if:

`M_last > N`

In that case the last residue equals the original number in `[0, M_last)`:
`x_last == N`.

By default `SpiralSig(mode="lossless", bound_bits=None)` expresses this.

### lossless (provable a-posteriori with a bound)

If you want lossless to be verifiable without knowing `N`, provide a bound:

- `bound_bits` means `0 <= N < 2**bound_bits`

Then lossless is provable if:

`M_last > 2**bound_bits - 1`

This is enforced in the SpiralSig model whenever `mode="lossless"` and `bound_bits` is provided.

## Classic → Spiral conversion

`ptc_spiral.from_classic.classic_to_spiral()` converts a classic PTC signature (v1 clocks) into a SpiralSig by:
- recovering each residue modulo prime
- lifting progressively via CRT to get `x_k = N mod M_k`
- selecting lossless/lossy based on the available bound and `M_last`
