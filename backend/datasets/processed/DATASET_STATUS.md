# Dataset status for the verified build

## Physically included and used in the verified model

- `local_seed_train.json` — 139 bundled annotated examples
- `local_seed_dev.json` — 35 bundled annotated examples
- Generated same-length noisy/spelling-error variants — up to 240 augmentation candidates
- `combined_train.json` / `combined_dev.json` — exact JSON records converted to `train.spacy` / `dev.spacy`

## Public sources wired for reproducible ingestion

- Dotin 545-resume NER dataset (CC0-1.0), with 12 annotation categories.
- DataTurks annotated resume NER dataset.
- Hugging Face `yashpwr/resume-ner-training-data`, 22,855 BIO-tagged resume records, MIT.

## Important audit statement

The verified model in this delivered build reports `external_examples: 0`. The sandbox environment could search the public sources, but could not retrieve their binary archives into the container. Therefore the delivered metrics do not falsely claim that external records were trained on.

When this project is run on a normal Windows machine with internet access:

```powershell
cd backend
python download_public_datasets.py
python prepare_data.py
python train_antigravity.py
```

The `dataset_manifest.json` file will report the actual external records successfully ingested, and those downloaded source files can be retained under `backend/datasets/raw/` as dataset evidence.
