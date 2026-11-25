# Additional handwriting datasets

The candidate is a two-hidden-layer MLP trained on **67,494** examples from the official MNIST and PenDigits training partitions. Training reserved 10% of that pool for internal validation. The run reached its 40-epoch limit. The official test partitions were scored separately.

| Official test partition | Test examples | Original k-NN accuracy | New MLP accuracy | New MLP macro-F1 |
| --- | ---: | ---: | ---: | ---: |
| MNIST | 10,000 | 71.60% | 97.46% | 0.9744 |
| PenDigits | 3,498 | 68.07% | 93.40% | 0.9343 |

On the same 72 clean UJI writer-held-out stocktake rows, cell-first exact row accuracy improved from **52.8% to 86.1%** and exact quantity accuracy improved from **83.3% to 94.4%**. At a nominal 0.80 threshold, the MLP would route 32 of 72 rows to review and accept 40. Two accepted rows had wrong quantities. These confidence scores are uncalibrated and the application still requires explicit approval. The dataset measurements cover individual digit crops and composited sheets. Naturally photographed full sheets remain unevaluated.

[Official split metrics and confusion matrices](additional-handwriting-metrics.json) · [Writer-held-out transfer and stress metrics](additional-model-writer-metrics.json) · [Dataset attribution](data.md)

## Reproduce and run locally

```sh
mkdir -p runtime
curl -fL 'https://storage.googleapis.com/tensorflow/tf-keras-datasets/mnist.npz' -o runtime/mnist.npz
curl -fL 'https://archive.ics.uci.edu/static/public/81/pen+based+recognition+of+handwritten+digits.zip' -o runtime/pendigits.zip
curl -fL 'https://archive.ics.uci.edu/static/public/160/uji+pen+characters.zip' -o runtime/uji-pen.zip
python -m inventory.extra_training --mnist runtime/mnist.npz --pendigits runtime/pendigits.zip \
  --output runtime/additional-handwriting-metrics.json --weights runtime/handwriting-mlp.npz
python -m inventory.writer_benchmark runtime/uji-pen.zip --model runtime/handwriting-mlp.npz \
  --output runtime/additional-model-writer-metrics.json
inventory-digitiser --port 8011 --model runtime/handwriting-mlp.npz
```

The original recogniser remains the default. Select the locally generated weights with `--model` to try the MLP. Reading numeric weights does not load executable Python objects.
