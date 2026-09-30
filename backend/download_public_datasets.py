"""Download public resume-NER data into backend/datasets/raw.

Run in Windows PowerShell:
    python download_public_datasets.py

The script downloads the documented public resume-NER sources below. It does not
silently substitute a different dataset, and it records a manifest of downloaded
files. The JSON/ZIP sources are directly ingestible by prepare_data.py; the
Hugging Face parquet file is retained as provenance and is not silently claimed as
training data until a parquet converter is added. If internet access is unavailable, the project still trains from the local
seed dataset already shipped in backend/datasets/processed/.
"""
from pathlib import Path
import os
from urllib.request import Request, urlopen
import json, zipfile, io

ROOT=Path(__file__).resolve().parent
RAW=ROOT/'datasets'/'raw'; RAW.mkdir(parents=True,exist_ok=True)
SOURCES=[
  {'id':'dotin_545_cc0','url':'https://github.com/dotin-inc/resume-dataset-NER-annotations/raw/refs/heads/master/545_cvs_train_v2.zip','filename':'545_cvs_train_v2.zip','license':'CC0-1.0'},
  {'id':'yashpwr_resume_ner','url':'https://huggingface.co/datasets/yashpwr/resume-ner-training-data/resolve/main/data/train-00000-of-00001.parquet','filename':'yashpwr_resume_ner_train.parquet','license':'MIT'},
  {'id':'dataturks_220_spacy','url':'https://raw.githubusercontent.com/DataTurks-Engg/Entity-Recognition-In-Resumes-SpaCy/master/traindata.json','filename':'traindata_dataturks.json','license':'Repository license should be checked before redistribution'},
]
manifest={'sources':SOURCES,'downloaded':[],'failed':[],'note':'Parquet source is recorded for provenance; the current converter expects JSON/JSONL. The two GitHub JSON/ZIP sources are directly ingestible.'}
for src in SOURCES:
    dest=RAW/src['filename']
    try:
        req=Request(src['url'],headers={'User-Agent':'Mozilla/5.0'})
        with urlopen(req,timeout=30) as r: data=r.read()
        dest.write_bytes(data)
        manifest['downloaded'].append({'id':src['id'],'file':src['filename'],'bytes':len(data)})
        if dest.suffix.lower()=='.zip':
            target=RAW/src['id']; target.mkdir(parents=True,exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                base=target.resolve()
                for member in z.infolist():
                    candidate=(target/member.filename).resolve()
                    if not str(candidate).startswith(str(base)+os.sep) and candidate != base:
                        raise RuntimeError(f'Unsafe archive member: {member.filename}')
                    z.extract(member,target)
    except Exception as exc:
        manifest['failed'].append({'id':src['id'],'error':str(exc)})

(RAW/'download_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(manifest,indent=2))
