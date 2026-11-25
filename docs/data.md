# Data provenance

## Public pen strokes

UJI Pen Characters (V1) by D. Llorens, F. Prat, A. Marzal and J. M. Vilar (Universitat Jaume I, 2007), distributed through the UCI Machine Learning Repository under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The [dataset record](https://archive.ics.uci.edu/dataset/160/uji%2Bpen%2Bcharacters) describes the original online stylus samples.

`inventory/uji_training.json` derives only digit coordinates from writers w01–w05. Processing removes letters and metadata, groups the remaining points into glyphs and rasterises them with deterministic thickness and rotation augmentations. This derived data remains under CC BY 4.0. No raw archive or test-writer strokes are committed.

The writer benchmark composites original digit strokes onto programmatically generated tables. It uses w01–w05 and layout 0 for development, and w06–w11 and layouts 1 and 2 for evaluation. The test measures transfer to new writers **in generated layouts**. It supplies no evidence about naturally captured full sheets, real stockrooms or arbitrary handwriting.

## Other material

The digit classifier also uses the small optical digits dataset bundled in scikit-learn. The [scikit-learn dataset documentation](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_digits.html) describes the feature representation. Procedural sheet examples and the sample catalogue contain invented inventory records. A separate benchmark measures procedural strokes and keeps style and layout groups disjoint between development and test.

## Additional digit benchmarks

- [MNIST](https://keras.io/api/datasets/mnist/), by Yann LeCun, Corinna Cortes and collaborators, uses the documented 60,000 training images and 10,000 test images. Keras identifies the dataset licence as CC BY-SA 3.0.
- [Pen-Based Recognition of Handwritten Digits](https://doi.org/10.24432/C5MG62), by Fevzi Alimoglu and Ethem Alpaydin, is distributed by UCI under CC BY 4.0. The official files provide 7,494 training trajectories and 3,498 test trajectories from separate groups of writers. Sequences of eight points are drawn into raster masks before classification.

The archives are downloaded from their sources and verified against pinned SHA-256 hashes. They are not included in this repository. The training command writes a local numeric checkpoint. The reported MLP uses only the training partitions for fitting and internal validation. The UJI evaluation then tests transfer to a third dataset in composite stocktake sheets.
