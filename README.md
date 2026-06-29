# FLQC Experimental Protocol

Numerical simulation of the **Fundamental Limit of Quantum Computation (FLQC)**
phase-resolution test protocol.

## What this is

This repository implements the gate sequence proposed in the FLQC preprint
([Fundamental Limit of Quantum Computation (FLQC)](https://doi.org/10.5281/zenodo.20934667))
for searching an anomalous systematic phase offset
in quantum Fourier transform circuits that cannot be attributed to known
noise mechanisms.

The simulation runs on classical hardware (Qiskit Aer) and serves two purposes:

1. **Baseline**: verify that an ideal simulator shows no floor (as expected),
   confirming the protocol isolates the effect correctly.
2. **Template**: provide a drop-in protocol for real QPU runs, where a
   persistent non-zero floor would be evidence for FLQC.

## Theoretical background

For a QFT register of depth *n*, the FLQC hypothesis predicts:

    σ² ≈ n · (Δθ_FLQC / 2)²     where Δθ_FLQC ≈ 10⁻³⁰ rad
    F  ≈ exp(−σ²)

At n = 100, θ_ideal = 2π / 2¹⁰⁰ ≈ 5 × 10⁻³⁰ rad — at the predicted limit.
IEEE 754 float64 saturates at n ≈ 52; this code uses `mpmath` for exact
angle representation and passes it to Qiskit via controlled approximation.

## Requirements

    pip install qiskit qiskit-aer mpmath numpy matplotlib

## Usage

    python flqc_protocol.py            # full sweep n = 1..60
    python flqc_protocol.py --shots 50000 --max_n 40

## Output

- Console: angle, ideal counts, fidelity estimate per step
- `flqc_results.png`: fidelity vs circuit depth, with FLQC floor overlay
"# FLQC-Protocol"

### License
[![License: CC BY-NC-SA 4.0](https://licensebuttons.net/l/by-nc-sa/4.0/88x31.png)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

**CC BY-NC 4.0** — Creative Commons Attribution-NonCommercial 4.0 International.

You are free to use, share, and adapt this code for **non-commercial purposes**
provided you give appropriate credit. Commercial use requires written permission
from the author.

© 2026 Sergej Materov <sergejmaterov2@gmail.com> ORCID: 0009-0001-3398-9906
