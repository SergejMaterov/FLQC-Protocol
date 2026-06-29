"""
FLQC Phase-Resolution Test Protocol
=====================================
Implements the gate sequence from the FLQC preprint for searching a
systematic phase-noise floor independent of hardware noise.

Protocol (per depth step n):
  1. Prepare |+⟩ on qubit 0 via Hadamard.
  2. Set qubit 1 to |1⟩.
  3. Apply controlled phase rotation CP(θ_n) with θ_n = 2π / 2^n.
  4. Apply Hadamard on qubit 0 (inverse QFT step).
  5. Measure qubit 0. Ideal result: |0⟩ with probability cos²(θ_n/2) ≈ 1.

Fidelity is estimated as F_n = P(|0⟩) / P_ideal(|0⟩).
A persistent floor in (1 − F_n) that does not scale with gate error rate
is the signature of the FLQC effect.

On a classical simulator: floor should be zero (float64 truncation is
handled explicitly — see angle_float_safe()).
On a real QPU: decompose (1 − F_n) into hardware-noise fit + residual.
"""

import argparse
import warnings
import numpy as np
import matplotlib.pyplot as plt
from mpmath import mp, pi as mp_pi, mpf, cos, power

# Qiskit imports
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

# ── Precision ──────────────────────────────────────────────────────────────
mp.dps = 60  # 60 significant decimal digits — well past 10^-30


def exact_angle(n: int) -> mp.mpf:
    """Return θ_n = 2π / 2^n as an mpmath float."""
    return (2 * mp_pi) / power(2, n)


def angle_float_safe(n: int) -> float:
    """
    Convert exact angle to Python float.
    For n > 52, float64 underflows to 0.0 (IEEE 754 limit).
    We detect this and warn rather than silently passing 0.0 to Qiskit.
    """
    theta_exact = exact_angle(n)
    theta_f = float(theta_exact)
    if theta_f == 0.0 and n > 0:
        warnings.warn(
            f"n={n}: angle {theta_exact:.3e} underflows float64 → 0.0. "
            "Simulator result will reflect IEEE 754 truncation, not FLQC. "
            "For n > 52 use a QPU with hardware-level phase control.",
            UserWarning,
            stacklevel=2,
        )
    return theta_f


def ideal_p0(n: int) -> float:
    """Ideal probability of measuring |0⟩: cos²(θ_n / 2)."""
    half = exact_angle(n) / 2
    return float(cos(half) ** 2)


# ── Circuit ────────────────────────────────────────────────────────────────

def build_circuit(theta_float: float) -> QuantumCircuit:
    """
    Single-step FLQC test circuit.
      q0: probe qubit  (H → CP → H → measure)
      q1: control in |1⟩
    """
    qc = QuantumCircuit(2, 1)
    qc.h(0)
    qc.x(1)
    qc.cp(theta_float, 1, 0)   # controlled-phase on probe
    qc.h(0)
    qc.measure(0, 0)
    return qc


# ── Noise model (optional) ─────────────────────────────────────────────────

def build_noise_model(gate_error: float) -> NoiseModel:
    """Simple depolarising noise on 1- and 2-qubit gates."""
    nm = NoiseModel()
    err1 = depolarizing_error(gate_error, 1)
    err2 = depolarizing_error(gate_error * 10, 2)
    nm.add_all_qubit_quantum_error(err1, ["h", "x"])
    nm.add_all_qubit_quantum_error(err2, ["cp"])
    return nm


# ── Main sweep ─────────────────────────────────────────────────────────────

def run_sweep(
    max_n: int = 60,
    shots: int = 10_000,
    gate_error: float = 0.0,
    verbose: bool = True,
) -> dict:
    """
    Sweep n from 1 to max_n. Return results dict.

    Returns
    -------
    dict with keys:
        n_values, angles_exact, angles_float,
        p0_ideal, p0_measured, fidelity, infidelity
    """
    simulator = AerSimulator()
    noise_model = build_noise_model(gate_error) if gate_error > 0 else None

    results = {
        "n_values":      [],
        "angles_exact":  [],
        "angles_float":  [],
        "p0_ideal":      [],
        "p0_measured":   [],
        "fidelity":      [],
        "infidelity":    [],
    }

    for n in range(1, max_n + 1):
        theta_f = angle_float_safe(n)
        theta_exact = exact_angle(n)
        p_ideal = ideal_p0(n)

        qc = build_circuit(theta_f)
        compiled = transpile(qc, simulator)

        run_kwargs = {"shots": shots}
        if noise_model:
            run_kwargs["noise_model"] = noise_model

        job = simulator.run(compiled, **run_kwargs)
        counts = job.result().get_counts()

        p0_meas = counts.get("0", 0) / shots
        fidelity = p0_meas / p_ideal if p_ideal > 0 else float("nan")
        infidelity = 1.0 - fidelity

        results["n_values"].append(n)
        results["angles_exact"].append(float(theta_exact))
        results["angles_float"].append(theta_f)
        results["p0_ideal"].append(p_ideal)
        results["p0_measured"].append(p0_meas)
        results["fidelity"].append(fidelity)
        results["infidelity"].append(infidelity)

        if verbose:
            flag = "⚠ float64=0" if theta_f == 0.0 else ""
            print(
                f"n={n:3d}  θ={float(theta_exact):.3e} rad  "
                f"P(0) ideal={p_ideal:.6f}  meas={p0_meas:.6f}  "
                f"F={fidelity:.6f}  (1-F)={infidelity:.2e}  {flag}"
            )

    return results


# ── FLQC theoretical floor ─────────────────────────────────────────────────

DELTA_THETA_FLQC = 1e-30  # rad — predicted lower bound


def flqc_infidelity_floor(n_values: list, delta_theta: float = DELTA_THETA_FLQC) -> np.ndarray:
    """
    Predicted (1 − F) floor from FLQC:
        σ² = n · (Δθ/2)²
        F  = exp(−σ²)
        1−F ≈ σ²  for small σ²
    """
    n = np.array(n_values, dtype=float)
    sigma2 = n * (delta_theta / 2) ** 2
    return 1.0 - np.exp(-sigma2)


# ── Plot ───────────────────────────────────────────────────────────────────

def plot_results(results: dict, output: str = "flqc_results.png") -> None:
    n = np.array(results["n_values"])
    inf_meas = np.array(results["infidelity"])
    inf_flqc = flqc_infidelity_floor(n)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("FLQC Phase-Resolution Test Protocol", fontsize=13, fontweight="bold")

    # Left: infidelity vs n
    ax = axes[0]
    ax.semilogy(n, np.clip(np.abs(inf_meas), 1e-12, None),
                "o-", color="#1f77b4", label="Measured (1−F)", markersize=4)
    ax.semilogy(n, inf_flqc, "--", color="#d62728",
                label=f"FLQC floor (Δθ={DELTA_THETA_FLQC:.0e} rad)", linewidth=1.5)
    ax.axvline(52, color="gray", linestyle=":", linewidth=1, label="float64 limit (n=52)")
    ax.set_xlabel("Circuit depth  n")
    ax.set_ylabel("Infidelity  (1 − F)")
    ax.set_title("Infidelity vs. circuit depth")
    ax.legend(fontsize=9)
    ax.grid(True, which="both", alpha=0.3)

    # Right: angle vs n
    ax2 = axes[1]
    ax2.semilogy(n, np.array(results["angles_exact"]), "s-",
                 color="#2ca02c", markersize=4, label="θ_n = 2π/2ⁿ (exact, mpmath)")
    ax2.axhline(DELTA_THETA_FLQC, color="#d62728", linestyle="--",
                label=f"Δθ_FLQC ≈ {DELTA_THETA_FLQC:.0e} rad")
    ax2.axvline(52, color="gray", linestyle=":", linewidth=1, label="float64 limit")
    ax2.set_xlabel("n")
    ax2.set_ylabel("Phase angle  θ_n  (rad)")
    ax2.set_title("Phase angle vs. depth")
    ax2.legend(fontsize=9)
    ax2.grid(True, which="both", alpha=0.3)

    plt.tight_layout()
    plt.savefig(output, dpi=150)
    print(f"\nPlot saved to {output}")


# ── CLI ────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="FLQC phase-resolution sweep")
    p.add_argument("--max_n",      type=int,   default=60,    help="Maximum circuit depth (default 60)")
    p.add_argument("--shots",      type=int,   default=10000, help="Shots per experiment (default 10000)")
    p.add_argument("--gate_error", type=float, default=0.0,   help="Depolarising gate error rate (default 0)")
    p.add_argument("--no_plot",    action="store_true",        help="Skip plot generation")
    p.add_argument("--output",     type=str,   default="flqc_results.png")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    print("=" * 70)
    print("FLQC Phase-Resolution Test Protocol")
    print(f"Δθ_FLQC = {DELTA_THETA_FLQC:.0e} rad  |  max_n={args.max_n}  |  shots={args.shots}")
    if args.gate_error > 0:
        print(f"Noise model: depolarising gate error = {args.gate_error}")
    print("=" * 70)

    results = run_sweep(
        max_n=args.max_n,
        shots=args.shots,
        gate_error=args.gate_error,
        verbose=True,
    )

    print("\n── Summary ──────────────────────────────────────────────────────────")
    print(f"  Max measured infidelity : {max(results['infidelity']):.4e}")
    print(f"  Min measured infidelity : {min(results['infidelity']):.4e}")
    print(f"  FLQC floor at n=max_n   : {float(flqc_infidelity_floor([args.max_n])[0]):.4e}")
    print(
        "\n  On an ideal simulator the measured floor should be ~0 (shot noise only).\n"
        "  On a real QPU, fit the hardware-noise component and extract the residual.\n"
        "  A residual consistent with the FLQC floor would be evidence for the limit."
    )

    if not args.no_plot:
        plot_results(results, output=args.output)
