# Touching digits, severe blur and real-photo validation

## What changed

The conservative cell-first reader now examines alternative cuts when a four-digit SKU has merged components. It scores each cut with the existing classifier and considers catalogue entries only where the segments supply evidence for their digits. Two thresholded views of the crop must agree on the proposed SKU. The normal OCR reading and crop remain visible. The proposal does not prefill the approval form. This recovery applies to catalogue SKUs, whose length is known. Variable-length quantities remain on the existing recognition and review path.

## Crowded writing

On 72 crowded rows made from six held-out UCI writers and two layouts, the ordinary readings achieved 18/72 exact rows (**25.0%**). The recovery proposed a SKU on 42 rows, and 38 proposals matched the reference. If every proposal were substituted into the raw output, 48/72 rows would match (**66.7%**). That number estimates reviewer assistance from the proposals. It is not automatic export accuracy, and four proposals were wrong. No crowded rows passed the conservative screening policy. [Raw paired measurements](touching-sku-results.json)

## Severe blur

I trained a separate sheet-adapted MLP on 99,511 examples, including labelled crops from degraded synthetic sheets with UCI development-writer strokes. The existing augmented MLP outperformed it on the same severely blurred composites, **55.6% versus 38.9% exact rows**. A second preprocessing experiment required agreement between two contrast-enhanced cuts for uncertain quantities. It made no qualifying proposals on this stress set and was not included in the app.

For an external check, both checkpoint candidates were evaluated on 1,000 manually drawn, isolated digits from [HwD-1000 by Niklas Henning](https://github.com/niklashenning/hwd-1000-dataset/tree/93b3ba9e45624ee557360229a42298eaa6b3a106). The dataset is MIT-licensed. No HwD-1000 image was used to fit either checkpoint. Gaussian blur was applied to a copy of each released image.

| External digit condition | Existing augmented MLP | Sheet-adapted MLP |
| --- | ---: | ---: |
| As released | 99.9% | 99.3% |
| Gaussian blur, radius 1.6 px | 92.9% | 91.4% |
| Gaussian blur, radius 2.8 px | 59.8% | 50.7% |

The existing augmented model remains the primary reader. The app continues to flag severely blurred sheets. These are isolated digit results and controlled sheet composites. [External predictions](external-digit-results.json) · [Candidate training and test results](sheet-adapted-digit-results.json) · [Candidate sheet stress results](sheet-adapted-stress-results.json)

## Evaluate actual stocktake photos privately

I did not find a verified, reusable collection of naturally photographed, labelled stocktake sheets in this app's format. Published resources like [UFPR Touching Digits](https://web.inf.ufpr.br/vri/databases/touching-digits/) and [DIDA](https://didadataset.github.io/DIDA/) address important parts of the problem, including connected numeral strings and degraded historical recording. End-to-end stocktake-photo performance remains unverified.

Keep permission-cleared unedited images and their labels in a local folder outside version control. Record writer, device and lighting when collecting the evaluation set. Use distinct sheets and writers from any tuning set. Supply the rows in visual order. Use strings for SKUs and quantities, and `null` for a genuinely blank quantity. Optional `corners` accepts four source coordinates clockwise from the top left when testing operator-assisted perspective correction.

```json
{
  "photos": [
    {
      "image": "sheet-001.jpg",
      "condition": "phone-photo-dim-light",
      "rows": [
        {"sku": "0012", "quantity": "0"},
        {"sku": "0074", "quantity": null}
      ]
    }
  ]
}
```

```sh
python -m inventory.photo_benchmark --photos runtime/private-photos \
  --manifest runtime/private-photos/labels.json \
  --model runtime/models/handwriting-robust.npz \
  --comparison-model runtime/models/handwriting-mlp.npz \
  --output runtime/private-photo-metrics.json
```

The report contains per-condition counts and checkpoint identifiers. Grid failures and sheets with the wrong number of detected rows count against the result. The tool measures exact matches in row order on the remaining sheets. It does not score source-box localisation. Only aggregate numbers are written to the report.
