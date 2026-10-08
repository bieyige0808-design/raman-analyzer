# Synthetic example data

The spectra in `synthetic_data/` are artificially generated for software
demonstration and testing. They are not experimental measurements and must not
be interpreted as research results.

Each file contains Lorentzian D, G, and 2D bands, a slowly varying background,
and Gaussian noise. The five spectra use progressively larger nominal D-band
heights to provide visibly different `I_D/I_G` values.

## Try the application

Run the desktop interface:

```bash
python raman_gui.py
```

Choose `examples/synthetic_data` as the data folder, select a save folder, keep
ALS baseline subtraction enabled, and click **Run analysis**.

## Regenerate the data

```bash
python examples/generate_synthetic_data.py
```

Generation uses a fixed random seed, so the example files are reproducible.
