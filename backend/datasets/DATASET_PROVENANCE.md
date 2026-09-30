# Dataset provenance

## Bundled training evidence
The supplied project seed annotations are preserved verbatim as:
- `backend/datasets/processed/local_seed_train.json`
- `backend/datasets/processed/local_seed_dev.json`

The generated noise-expanded and combined datasets are written to `backend/datasets/processed/combined_train.json` and `combined_dev.json`.

## Public resume datasets supported by the pipeline
The downloader can place public source datasets under `backend/datasets/raw/` and records what was actually downloaded in `backend/datasets/raw/download_manifest.json`.

1. dotin-inc/resume-dataset-NER-annotations — 545 resumes, 12 annotation categories, repository marked CC0-1.0: https://github.com/dotin-inc/resume-dataset-NER-annotations
2. DataTurks-Engg/Entity-Recognition-In-Resumes-SpaCy — public annotated resume NER project with `traindata.json`: https://github.com/DataTurks-Engg/Entity-Recognition-In-Resumes-SpaCy
3. yashpwr/resume-ner-training-data — 22,855 BIO-tagged resume records, MIT license: https://huggingface.co/datasets/yashpwr/resume-ner-training-data

## Truthful usage rule
`backend/datasets/processed/dataset_manifest.json` records `external_examples`. A non-zero value is only written when external source files are physically present under `backend/datasets/raw/` and were successfully parsed. The current execution environment could search the public sources but could not fetch their binary archives into the container, so the current verified model run uses the bundled project seed data plus generated OCR-noise augmentation; it does not falsely claim the public records were trained on.
