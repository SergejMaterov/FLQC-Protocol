# FLQC Experimental Protocol

Numerical simulation of the **Fundamental Limit of Quantum Computation (FLQC)**
phase-resolution test protocol.

## What this is

This repository implements the gate sequence proposed in the FLQC preprint
[Fundamental Limit of Quantum Computation (FLQC)](https://doi.org/10.5281/zenodo.21253441)
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

---

## Status / Known Limitations

The protocol implemented here is methodologically correct but **not currently
capable of confirming or refuting FLQC on real hardware**. This is a
quantitative, not qualitative, limitation, and it is worth stating plainly.

**The gap.** FLQC predicts $Δθ_{min}$ ~ 10⁻³⁰ rad. Best demonstrated
superconducting-qubit coherence times are ~1 ms; best achievable
measurement-cycle repetition rates are ~10⁶ Hz. Resolving a phase at the
10⁻³⁰ rad level, even under an idealized Heisenberg-limited scheme with
N ~ 10³ entangled qubits, requires on the order of 10⁵⁴ independent
measurements — about 10⁴⁸ seconds of continuous operation. Ordinary
decoherence-induced phase noise at currently achievable coherence times
already exceeds the predicted floor by a comparable margin.

**What this means for a real QPU run.** A non-zero residual on current
hardware is expected regardless of whether FLQC is correct — it is what
technical noise looks like. Do not interpret `residual / Δθ_{min} ≈ 1` as
evidence. Given the ~30-order-of-magnitude gap between the predicted floor
and any achievable noise floor, a fit result landing near 1 is far more
likely to indicate a fitting artifact (overfitting the two-stage model at
small n, numerical precision effects in the noise-extrapolation step) than
a genuine detection. Treat such a result as a flag to audit the fit, not as
a signal.

**What this repository is for, currently.** It is a reference
implementation of the measurement protocol and the noise-subtraction
methodology described in the [FLQC manuscript (§4.1)](https://doi.org/10.5281/zenodo.21253441), useful for:
- verifying the simulator reproduces the expected null result (no floor,
  as it should, since the simulator has no FLQC term);
- providing a ready-to-run template for if/when qubit coherence, repetition
  rate, or statistical methodology improve enough to close a meaningful
  fraction of the gap above;
- giving reviewers and readers a concrete, falsifiable object to inspect,
  rather than an abstract claim.

It is not, at present, a live experimental proposal expected to produce a positive or negative result on existing hardware. See the [manuscript,
§4.3](https://doi.org/10.5281/zenodo.21253441), for the full derivation of the gap above, and the note on why chaotic (OTOC) amplification does not close it either.

## Usage

flqc_protocol.py - Main protocol. Sweeps from n = 1 to max_n; uses mpmath for precise angles (independent of float64); issues a warning when n > 52; plots the results with an FLQC floor overlay. On the simulator, a floor of 0 represents the baseline. On a real QPU, a non-zero residual is expected.
The graph shows that the simulator behaves correctly: (1−F) drops to zero for n > 29 due to float64 truncation—a phenomenon clearly identified as an IEEE 754 limitation rather than a physical effect.

analyse_results.py - Post-processing for data from a real QPU. A two-stage fit: first, it fits the hardware-noise component at shallow depths (n ≤ 20), then subtracts it and compares the residual with the FLQC prediction. It outputs the ratio of the residual/FLQC_predicted —if the value is ≈ 1, it indicates a signal.

    python flqc_protocol.py            # full sweep n = 1..60
    python flqc_protocol.py --shots 50000 --max_n 40
    Notebook                           # notebook demo in QPU with qiskit

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
