"""Generate synthetic Raman spectra for demonstration and testing.

The generated files are artificial signals, not experimental measurements.
Each spectrum contains Lorentzian D, G, and 2D bands, a curved background,
and reproducible Gaussian noise.
"""

from pathlib import Path

import numpy as np


OUTPUT_DIR = Path(__file__).resolve().parent / "synthetic_data"
RNG_SEED = 20261008


def lorentzian(x, center, fwhm, height):
    """Return a Lorentzian peak parameterized by maximum height and FWHM."""
    half_width = fwhm / 2.0
    return height * half_width**2 / ((x - center) ** 2 + half_width**2)


def make_spectrum(x, sample, rng):
    """Build one synthetic spectrum from peak, baseline, and noise settings."""
    baseline = (
        sample["baseline"]
        + sample["slope"] * (x - x.min())
        + sample["curvature"] * (x - 1900.0) ** 2
    )

    signal = baseline.copy()
    signal += lorentzian(x, sample["d_center"], sample["d_fwhm"], sample["d_height"])
    signal += lorentzian(x, sample["g_center"], sample["g_fwhm"], sample["g_height"])
    signal += lorentzian(
        x,
        sample["two_d_center"],
        sample["two_d_fwhm"],
        sample["two_d_height"],
    )
    signal += rng.normal(0.0, sample["noise"], size=x.size)
    return signal


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(RNG_SEED)
    x = np.arange(800.0, 3200.1, 2.0)

    samples = [
        dict(name="synthetic_01", d_height=260, g_height=1000, two_d_height=410,
             d_center=1347, g_center=1579, two_d_center=2692,
             d_fwhm=72, g_fwhm=48, two_d_fwhm=90,
             baseline=135, slope=0.018, curvature=0.000010, noise=12),
        dict(name="synthetic_02", d_height=420, g_height=1000, two_d_height=360,
             d_center=1350, g_center=1581, two_d_center=2698,
             d_fwhm=78, g_fwhm=50, two_d_fwhm=96,
             baseline=170, slope=0.025, curvature=0.000014, noise=14),
        dict(name="synthetic_03", d_height=610, g_height=1000, two_d_height=300,
             d_center=1353, g_center=1580, two_d_center=2703,
             d_fwhm=84, g_fwhm=52, two_d_fwhm=102,
             baseline=205, slope=0.030, curvature=0.000018, noise=16),
        dict(name="synthetic_04", d_height=790, g_height=1000, two_d_height=245,
             d_center=1356, g_center=1583, two_d_center=2708,
             d_fwhm=92, g_fwhm=56, two_d_fwhm=108,
             baseline=235, slope=0.035, curvature=0.000022, noise=18),
        dict(name="synthetic_05", d_height=960, g_height=1000, two_d_height=190,
             d_center=1359, g_center=1585, two_d_center=2714,
             d_fwhm=100, g_fwhm=60, two_d_fwhm=116,
             baseline=270, slope=0.042, curvature=0.000026, noise=20),
    ]

    for sample in samples:
        intensity = make_spectrum(x, sample, rng)
        output_path = OUTPUT_DIR / f"{sample['name']}.txt"
        with output_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write("Raman shift (cm^-1)\tIntensity (a.u.)\n")
            for shift, value in zip(x, intensity):
                handle.write(f"{shift:.1f}\t{value:.6f}\n")
        print(f"Created: {output_path.name}")


if __name__ == "__main__":
    main()
