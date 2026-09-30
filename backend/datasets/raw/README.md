# External resume datasets

Put downloaded public resume-NER source files in this directory and rerun:

```powershell
python ..\download_public_datasets.py
python ..\prepare_data.py
python ..\train_antigravity.py
```

The project intentionally keeps external acquisition explicit so the provenance is inspectable. The `prepare_data.py` loader supports DataTurks JSON/JSONL, spaCy-style JSON, and BIO JSONL records.
