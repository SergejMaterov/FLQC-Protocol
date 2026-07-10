# The Fundamental Limit of Quantum Computation (FLQC) — Try It Yourself

Three notebooks, zero installation, real Qiskit circuits. Click, run, play
with the sliders.


| Phase-floor demo | Why a discretized spacetime would leave a fingerprint in a quantum circuit's error pattern | | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/SergejMaterov/FLQC-Protocol/blob/main/Notebook/flqc_phase_floor_demo.ipynb#scrollTo=b649ba54) |

| [![DEMO](https://github.com/SergejMaterov/FLQC-Protocol/blob/main/Notebook/badge-preview.png)](https://github.com/SergejMaterov/FLQC-Protocol/blob/main/Notebook/badge-preview.png) |

No installation, no account beyond a free Google login. Each notebook takes
under a minute to start and is meant to be readable by a physics undergrad
with no quantum-computing background.

## What this is / isn't

These are **pedagogical illustrations**, not reproductions of the research
results. Real predicted quantities (e.g. Δθ_min ~ 10⁻³⁰ rad) are far too
small to visualize directly — these notebooks use inflated, clearly-labeled
illustrative values so the *mechanism* is visible. For the actual research
package, feasibility analysis, and real measurement protocol, see:
- [FLQC-Protocol](https://github.com/SergejMaterov/FLQC-Protocol) — the real
  (currently infeasible, honestly documented) measurement protocol
- the FLQC manuscript, §4.1–4.3

## Contents:

- Builds a standard QFT circuit two ways: (a) every controlled-phase angle
  rounded to the nearest multiple of Δθ (FLQC-style discrete phase lattice),
  (b) every angle perturbed by independent Gaussian noise of comparable
  magnitude (ordinary engineering noise model).
- Computes state infidelity vs. register size n (2–16 qubits, exact
  statevector simulation, no need for Aer/shots).
- Interactive `ipywidgets` sliders for Δθ and noise σ (log-scale, 10⁻³–10⁻⁰·⁵)
  and number of noise realizations to average.
- Verified numerically: the FLQC-style curve visibly saturates with n
  (bounded, deterministic rounding error — gates whose ideal angle is finer
  than Δθ stop contributing), while the random-noise curve keeps growing
  and is visibly noisier run-to-run — the same qualitative signature
  described in the manuscript, §4.1.
- Explicit disclaimer that Δθ values used are pedagogically inflated, not
  the real ~10⁻³⁰ prediction, with a pointer to §4.3 for why.

## License

CC BY-NC 4.0. see LICENSE for details. Educational
and research use is unrestricted under CC BY-NC 4.0; commercial hardware
implementation is not covered by this license.


