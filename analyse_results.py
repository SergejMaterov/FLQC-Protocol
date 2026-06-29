"""
FLQC Result Analyser
====================
Post-processing tool for separating hardware-noise component from
the FLQC residual in real QPU data.

Usage (after running flqc_protocol.py on a real QPU and saving counts to JSON):
    python analyse_results.py --data qpu_results.json
"""

import json
import argparse
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

DELTA_THETA_FLQC = 1e-30  # rad


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
      Stage 1: fit hardware-noise component on shallow depths (n ≤ 20)
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

    print(f"Hardware noise fit:  a = {a_fit:.3e} / gate,  b = {b_fit:.3e}")
    print(f"Residual range: [{residual.min():.3e}, {residual.max():.3e}]")

    flqc_predicted = flqc_floor(n)
    ratio = residual / np.where(flqc_predicted > 0, flqc_predicted, np.nan)
    print(f"Residual / FLQC_predicted (mean over deep n>40): "
          f"{np.nanmean(ratio[n > 40]):.2f}  "
          f"(1.0 would be perfect match, ~0 means no signal)")

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
    p.add_argument("--data",   required=True, help="JSON file with QPU results")
    p.add_argument("--output", default="flqc_decomposition.png")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    with open(args.data) as f:
        data = json.load(f)

    fit_data = fit_decomposition(data["n_values"], data["infidelity"])
    plot_decomposition(fit_data, output=args.output)
