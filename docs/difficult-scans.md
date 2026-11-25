# Blurry scans and difficult handwriting

The app now warns about soft edges, low contrast, uneven lighting and small source images. It can recover soft grid lines with a local contrast mask and long-line filtering. If the stronger mask finds no usable glyph, the cell reader checks for faint evidence. A faint recovery receives at most 0.50 confidence and goes to review at the default 0.80 threshold. The source crop remains visible. If the grid cannot be recovered, the app asks for a better image instead of inventing rows.

## Training and measured results

The experimental MLP added 19,000 degraded copies of MNIST and PenDigits training glyphs and 1,500 rasterised glyphs from the five UJI development writers. Degradations included blur, weak ink, noise and small rotations. The run trained on 87,994 examples for a fixed maximum of 40 epochs. It achieved **97.51%** digit accuracy on the official MNIST test split and **94.63%** on the official PenDigits test split.

Both MLPs were compared with the same grid and cell pipeline on the same UJI composites. Six writers and two layouts were excluded from model fitting. Each condition reused the same underlying rows, with 72 rows per condition. Grid recovery was developed while inspecting these stress cases, so the results describe this engineering benchmark rather than a blind estimate of accuracy in a new setting.

| Condition | Standard MLP exact rows | Augmented MLP exact rows |
| --- | ---: | ---: |
| Clean | 86.1% | 88.9% |
| Blur | 75.0% | 86.1% |
| Severe blur | 47.2% | 55.6% |
| Faint writing | 86.1% | 88.9% |
| Low resolution | 63.9% | 68.1% |
| Crowded digits | 25.0% | 25.0% |
| Crossed-out values | 75.0% | 77.8% |
| Uneven lighting | 86.1% | 88.9% |
| Skew | 86.1% | 87.5% |

The augmented model still passed two wrong quantities on clean composites and two under skew at the simulated 0.80 threshold. On severely blurred examples it passed no wrong quantities among the 26 accepted rows, with the other 46 routed for review. Every export still requires approval. The perturbations were applied to composited sheets, so accuracy on naturally blurry stockroom photos remains unknown.

[Training and official test scores](robust-digit-metrics.json) · [Paired standard-model results](stress-standard-model.json) · [Paired augmented-model results](stress-augmented-model.json)

## Reproduce

Download the pinned input archives using the [additional model setup](additional-handwriting.md), then run:

```sh
python -m inventory.extra_training --mnist runtime/mnist.npz --pendigits runtime/pendigits.zip \
  --robust --output runtime/robust-digit-metrics.json --weights runtime/handwriting-robust.npz
python -m inventory.writer_benchmark runtime/uji-pen.zip --model runtime/handwriting-robust.npz \
  --extended-stress --output runtime/stress-augmented-model.json
inventory-digitiser --port 8012 --model runtime/handwriting-robust.npz
```

Run the same stress command with the standard checkpoint to reproduce the paired comparison. The optional model does not change the app's default recogniser.

## Conservative review mode

For difficult scans, use the augmented model as the primary reader and the standard MLP as a cross-check. If the digit readings disagree, the review form shows both readings and leaves the disputed field empty. A scan-quality warning flags every row. Quantities below the cross-check cutoff of 0.99 must be entered from the source crop. The 0.99 value is a screening score, not a calibrated probability.

On the existing 648 cell-first stress observations, this stricter policy left 18 rows unflagged and routed 630 to priority review. No wrong quantities were observed among those 18. All mildly and severely blurred rows were flagged. This is a retrospective check on the same benchmark used to select the policy. Both models can agree on a wrong reading, and human confirmation remains mandatory for every export.

[Cross-checked policy measurements](stress-cross-checked-model.json)

```sh
python -m inventory.writer_benchmark runtime/uji-pen.zip \
  --model runtime/handwriting-robust.npz --comparison-model runtime/handwriting-mlp.npz \
  --extended-stress --gate-scan-quality --output runtime/stress-cross-checked-model.json
inventory-digitiser --port 8013 --workspace runtime/cross-checked \
  --model runtime/handwriting-robust.npz --comparison-model runtime/handwriting-mlp.npz
```
