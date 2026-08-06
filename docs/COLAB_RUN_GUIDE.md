# Google Colab run guide

1. Upload the repository to `https://github.com/romenmeitei/AISKG_Framework`.
2. Open:
   `https://colab.research.google.com/github/romenmeitei/AISKG_Framework/blob/main/notebooks/AISKG_Framework_v3_Complete_Pipeline.ipynb`
3. Select **Runtime → Run all**.
4. Keep `CONFIG_PATH = "configs/manuscript_frozen.yaml"` for publication reproduction.
5. Wait for `SUCCESS`, `285/285 checks passed`, and the ablation table.
6. Download `AISKG_Framework_v3.0.0_Release.zip` when prompted.

The notebook does not use `argparse` inside a notebook cell. It invokes the tested repository command through `subprocess`, preventing the earlier `--input-dir/--output-dir` Colab error.

## Validation performed before release

The notebook was executed end-to-end with `nbclient` using the same cells, Python package, configuration, and frozen inputs. Hosted Google Colab execution must still be initiated by the repository owner because this environment cannot sign in to the owner's Google account.
