# Public Resume Dataset Sources

These are the public resume-NER sources supported by the project downloader. The pipeline records a source as *used* only when its downloaded file is present under this folder and parsed successfully.

## 1. Dotin 545 CVs (CC0)
- Repository: https://github.com/dotin-inc/resume-dataset-NER-annotations
- File: `545_cvs_train_v2.zip`
- Size claimed by source: 545 annotated resumes, 12 entity categories
- License shown by repository: CC0-1.0

## 2. DataTurks resume NER
- Repository: https://github.com/DataTurks-Engg/Entity-Recognition-In-Resumes-SpaCy
- File: `traindata.json`
- Format: annotated resume JSON used by their spaCy NER project

## 3. Hugging Face resume NER
- Dataset: https://huggingface.co/datasets/yashpwr/resume-ner-training-data
- Size claimed by dataset card: 22,855 BIO-tagged resume records
- License shown by dataset card: MIT

## Runtime rule
Run `python download_public_datasets.py` from `backend` before `python prepare_data.py`.
The generated `dataset_manifest.json` is the audit record of which external files physically existed and contributed training examples.

The verified model bundled with this project was trained from the bundled/local annotated seed plus noisy augmentation because the current build environment could not fetch the public binary archives. It does **not** claim external examples that were not physically ingested.
