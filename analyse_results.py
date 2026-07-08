"""
FLQC Result Analyser
====================

Post-processing tool for separating hardware-noise component from
the FLQC residual in real QPU data.

Usage (after running flqc_protocol.py on a real QPU and saving counts to JSON):

    python analyse_results.py --data qpu_results.json

------------------------------------------------------------------------------
KNOWN LIMITATION (read before interpreting output)
------------------------------------------------------------------------------
FLQC predicts Delta_theta_min ~ 1e-30 rad. Best demonstrated superconducting-
qubit coherence times are ~1 ms; best achievable measurement-cycle repetition
rates are ~1e6 Hz. Resolving a phase at the 1e-30 rad level, even under an
idealized Heisenberg-limited scheme with N ~ 1e3 entangled qubits, requires on
the order of 1e54 independent measurements (~1e48 seconds of continuous
operation). Ordinary decoherence-induced phase noise at currently achievable
coherence times already exceeds the predicted floor by a comparable margin.

Consequence: a non-zero residual on current hardware is expected regardless
of whether FLQC is correct -- it is what technical noise looks like. Given the
~30-order-of-magnitude gap between the predicted floor and any achievable
noise floor, a fit result with ratio ~= 1 is far more likely to indicate a
fitting artifact (overfitting the two-stage model at small n, numerical
precision effects in the noise-extrapolation step) than a genuine detection.
Treat such a result as a flag to audit the fit, not as a signal. See the FLQC
manuscript, Section 4.3, for the full derivation of this gap, and the note on
why chaotic (OTOC) amplification does not close it either.

This script remains useful as a reference implementation of the measurement
and noise-subtraction methodology, and as a ready-to-run template for if/when
qubit coherence, repetition rate, or statistical methodology improve enough
to close a meaningful fraction of the gap above.
------------------------------------------------------------------------------
"""

import json
import argparse
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

DELTA_THETA_FLQC = 1e-30  # rad

# Ratio range treated as "near 1" for the purpose of the audit warning below.
RATIO_AUDIT_TOLERANCE = 0.5


# ── Noise models ───────────────────────────────────────────────────────────

def hardware_noise_model(n, a, b):
    """
    Empirical hardware noise: linear in depth (standard gate error accumulation).
    (1 − F)_hw = a * n + b
    """
    return a * np.array(n, dtype=float) + b


def flqc_floor(n, delta_theta=DELTA_THETA_FLQC):
    n = np.array(n, dtype=float)
    sigma2 = n * (delta_theta / 2) ** 2
    return 1.0 - np.exp(-sigma2)


def total_model(n, a, b, delta_theta):
    """Combined model: hardware noise + FLQC floor."""
    return hardware_noise_model(n, a, b) + flqc_floor(n, delta_theta)


# ── Fit ────────────────────────────────────────────────────────────────────

def fit_decomposition(n_values, infidelity):
    """
    Two-stage fit:
      Stage 1: fit hardware-noise component on shallow depths (n <= 20)
               where FLQC floor is negligible.
      Stage 2: subtract hardware fit, check residual against FLQC floor.
    """
    n = np.array(n_values, dtype=float)
    inf = np.array(infidelity, dtype=float)

    # Stage 1: hardware fit on shallow circuit
    shallow_mask = n <= 20
    popt_hw, _ = curve_fit(hardware_noise_model, n[shallow_mask], inf[shallow_mask],
                            p0=[1e-4, 1e-5], maxfev=10000)
    a_fit, b_fit = popt_hw
    hw_component = hardware_noise_model(n, a_fit, b_fit)
    residual = inf - hw_component

    print(f"Hardware noise fit: a = {a_fit:.3e} / gate, b = {b_fit:.3e}")
    print(f"Residual range: [{residual.min():.3e}, {residual.max():.3e}]")

    flqc_predicted = flqc_floor(n)
    ratio = residual / np.where(flqc_predicted > 0, flqc_predicted, np.nan)
    mean_ratio = np.nanmean(ratio[n > 40])

    print(f"Residual / FLQC_predicted (mean over deep n>40): {mean_ratio:.2f}")

    # ── Interpretation guard ────────────────────────────────────────────────
    # See the KNOWN LIMITATION note at the top of this file. A ratio near 1
    # is NOT, on its own, evidence for FLQC: at current qubit coherence and
    # repetition rates, a genuine detection is not statistically achievable
    # (see manuscript Section 4.3). Report it, but flag it correctly.
    if abs(mean_ratio - 1.0) < RATIO_AUDIT_TOLERANCE:
        print(
            "NOTE: ratio is near 1. Before treating this as signal, audit for "
            "fitting artifacts (overfitting at small n, float precision in the "
            "noise-extrapolation step). At current qubit coherence and "
            "repetition rates, a genuine FLQC detection is not statistically "
            "achievable (see manuscript Section 4.3); this result is far more "
            "likely to reflect a methodological artifact than a real effect."
        )
    else:
        print(
            "NOTE: ratio is far from 1 -- consistent with expectation: the "
            "residual is dominated by technical noise, not FLQC."
        )

    return {
        "n": n.tolist(),
        "infidelity": inf.tolist(),
        "hw_component": hw_component.tolist(),
        "residual": residual.tolist(),
        "flqc_predicted": flqc_predicted.tolist(),
        "hw_fit_params": {"a": float(a_fit), "b": float(b_fit)},
    }


# ── Plot ───────────────────────────────────────────────────────────────────

def plot_decomposition(fit_data: dict, output: str = "flqc_decomposition.png"):
    n = np.array(fit_data["n"])
    inf = np.array(fit_data["infidelity"])
    hw = np.array(fit_data["hw_component"])
    res = np.array(fit_data["residual"])
    flqc = np.array(fit_data["flqc_predicted"])

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("FLQC Result Decomposition", fontsize=13, fontweight="bold")

    ax = axes[0]
    ax.semilogy(n, np.clip(inf, 1e-12, None), "o-", label="Total (1−F)", color="#1f77b4")
    ax.semilogy(n, np.clip(hw, 1e-12, None), "--", label="Hardware noise fit", color="#ff7f0e")
    ax.semilogy(n, flqc, ":", label=f"FLQC floor (Δθ={DELTA_THETA_FLQC:.0e})", color="#d62728", linewidth=2)
    ax.set_xlabel("n")
    ax.set_ylabel("Infidelity (1−F)")
    ax.set_title("Total infidelity decomposition")
    ax.legend(fontsize=9)
    ax.grid(True, which="both", alpha=0.3)

    ax2 = axes[1]
    ax2.plot(n, res, "s-", color="#9467bd", label="Residual (total − hw fit)", markersize=4)
    ax2.plot(n, flqc, ":", color="#d62728", label="FLQC prediction", linewidth=2)
    ax2.axhline(0, color="gray", linewidth=0.8)
    ax2.set_xlabel("n")
    ax2.set_ylabel("Infidelity")
    ax2.set_title("Residual vs. FLQC prediction")
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output, dpi=150)
    print(f"Decomposition plot saved to {output}")


# ── CLI ────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="FLQC result analyser")
    p.add_argument("--data", required=True, help="JSON file with QPU results")
    p.add_argument("--output", default="flqc_decomposition.png")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    with open(args.data) as f:
        data = json.load(f)

    fit_data = fit_decomposition(data["n_values"], data["infidelity"])
    plot_decomposition(fit_data, output=args.output)
