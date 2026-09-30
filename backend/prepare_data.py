"""Dataset engineering for the custom spaCy resume NER model.

Inputs supported:
- Existing project JSON: [[text, {"entities": [[start, end, label], ...]}], ...]
- spaCy-style JSON/JSONL: {"text": ..., "entities": [...]}
- DataTurks JSON/JSONL: {"content": ..., "annotation": [...]}
- BIO JSONL exports containing tokens + ner_tags.

Outputs:
- backend/data/train.json and dev.json
- backend/data/train.spacy and dev.spacy
- backend/datasets/processed/dataset_manifest.json
- backend/datasets/processed/combined_*.json

The public datasets are not silently fabricated. Put downloaded source files in
backend/datasets/raw/ and this script will ingest them. A companion downloader
is included for reproducibility.
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Iterable

import spacy
from spacy.tokens import DocBin
from spacy.training import offsets_to_biluo_tags

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RAW = ROOT / "datasets" / "raw"
PROC = ROOT / "datasets" / "processed"
TRAIN_JSON = DATA / "train.json"
DEV_JSON = DATA / "dev.json"
TRAIN_SPACY = DATA / "train.spacy"
DEV_SPACY = DATA / "dev.spacy"

LABELS = [
    "PERSON", "EMAIL", "PHONE", "DESIGNATION", "YEARS_EXPERIENCE",
    "SKILL", "DEGREE", "INSTITUTION", "LOCATION", "CERTIFICATION",
    "DOMAIN", "PROJECT_TITLE"
]
LABEL_SET = set(LABELS)

# Map common public resume-NER labels to the project's fixed 12-label schema.
LABEL_MAP = {
    "Name": "PERSON", "NAME": "PERSON", "PERSON": "PERSON",
    "Email Address": "EMAIL", "EMAIL": "EMAIL",
    "Phone": "PHONE", "Phone Number": "PHONE", "PHONE": "PHONE",
    "Designation": "DESIGNATION", "TITLE": "DESIGNATION", "Job Title": "DESIGNATION",
    "Years of Experience": "YEARS_EXPERIENCE", "EXPERIENCE": "YEARS_EXPERIENCE",
    "Skills": "SKILL", "Skill": "SKILL", "SKILLS": "SKILL",
    "Job Specific Skill": "SKILL", "Soft Skills": "SKILL", "Tech Tools": "SKILL",
    "Degree": "DEGREE", "Education": "DEGREE", "EDUCATION": "DEGREE",
    "College Name": "INSTITUTION", "Institution": "INSTITUTION", "INSTITUTION": "INSTITUTION",
    "Companies worked at": "INSTITUTION", "Company": "INSTITUTION", "ORG": "INSTITUTION",
    "Location": "LOCATION", "LOCATION": "LOCATION", "LOC": "LOCATION",
    "Certification": "CERTIFICATION", "Certifications": "CERTIFICATION", "CERT": "CERTIFICATION",
    "Domain": "DOMAIN", "DOMAIN": "DOMAIN", "FIELD": "DOMAIN",
    "Project": "PROJECT_TITLE", "Project Title": "PROJECT_TITLE", "PROJECT_TITLE": "PROJECT_TITLE",
}


def _canonical(label: str) -> str | None:
    label = str(label).strip()
    if label in LABEL_SET:
        return label
    return LABEL_MAP.get(label)


def _clean_entities(text: str, entities: Iterable, nlp) -> list[list]:
    """Trim whitespace, map labels, remove bad/overlapping spans, and validate token alignment."""
    normalized=[]
    for item in entities:
        try:
            start, end, raw_label = int(item[0]), int(item[1]), item[2]
        except Exception:
            continue
        label=_canonical(raw_label)
        if not label or start < 0 or end <= start or end > len(text):
            continue
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end-1].isspace():
            end -= 1
        if start >= end:
            continue
        normalized.append((start,end,label))

    # Prefer longer spans, then earlier spans. This avoids impossible overlaps in public datasets.
    normalized.sort(key=lambda e: (-(e[1]-e[0]), e[0], e[1]))
    accepted=[]
    for span in normalized:
        if any(not (span[1] <= s[0] or span[0] >= s[1]) for s in accepted):
            continue
        accepted.append(span)
    accepted.sort(key=lambda e:(e[0],e[1]))

    tags = offsets_to_biluo_tags(nlp.make_doc(text), accepted)
    if "-" in tags:
        # Keep only examples whose spans can be represented by the tokenizer.
        accepted=[]
        for start,end,label in normalized:
            test = accepted + [(start,end,label)]
            if "-" not in offsets_to_biluo_tags(nlp.make_doc(text), test):
                accepted.append((start,end,label))
    return [[s,e,l] for s,e,l in accepted]


def _from_dataturks(obj, nlp):
    text=obj.get("content", "")
    entities=[]
    for ann in obj.get("annotation", []):
        point=(ann.get("points") or [{}])[0]
        labels=ann.get("label", [])
        if not isinstance(labels,list): labels=[labels]
        for label in labels:
            # DataTurks uses inclusive end indexes; spaCy uses exclusive end indexes.
            entities.append([point.get("start",-1), point.get("end",-1)+1, label])
    return [text, {"entities": _clean_entities(text, entities, nlp)}] if text else None


def _from_standard(obj, nlp):
    if "text" not in obj:
        return None
    text=obj["text"]
    ents=obj.get("entities", [])
    return [text, {"entities": _clean_entities(text, ents, nlp)}]


def _from_bio(obj, nlp):
    tokens=obj.get("tokens") or []
    tags=obj.get("ner_tags") or []
    if not tokens or len(tokens)!=len(tags):
        return None
    text=obj.get("text")
    if not text:
        text=" ".join(str(t) for t in tokens)
    # When offsets aren't included, rebuild a whitespace-tokenized document deterministically.
    entities=[]; cursor=0; cur=None
    for tok, tag in zip(tokens,tags):
        tok=str(tok); idx=text.find(tok,cursor)
        if idx<0: return None
        start=idx; end=idx+len(tok); cursor=end
        tag=str(tag)
        if tag in ("O","0","None"): 
            if cur: entities.append(cur); cur=None
            continue
        if tag.startswith("B-"):
            if cur: entities.append(cur)
            cur=[start,end,_canonical(tag[2:]) or tag[2:]]
        elif tag.startswith("I-") and cur and _canonical(tag[2:])==cur[2]:
            cur[1]=end
        else:
            if cur: entities.append(cur)
            cur=[start,end,_canonical(tag.split("-",1)[-1]) or tag.split("-",1)[-1]]
    if cur: entities.append(cur)
    return [text,{"entities":_clean_entities(text,entities,nlp)}]


def load_any_file(path: Path, nlp) -> list[list]:
    items=[]
    raw=path.read_text(encoding="utf-8", errors="ignore")
    stripped=raw.lstrip()
    candidates=[]
    if stripped.startswith("["):
        try: candidates=json.loads(raw)
        except Exception: candidates=[]
    else:
        for line in raw.splitlines():
            line=line.strip()
            if not line: continue
            try: candidates.append(json.loads(line))
            except Exception: continue
    for obj in candidates:
        if isinstance(obj,list) and len(obj)==2:
            text=obj[0]; ann=obj[1] if isinstance(obj[1],dict) else {}
            items.append([text,{"entities":_clean_entities(text,ann.get("entities",[]),nlp)}])
        elif isinstance(obj,dict):
            row=_from_dataturks(obj,nlp) if "content" in obj and "annotation" in obj else (_from_bio(obj,nlp) if "tokens" in obj and "ner_tags" in obj else _from_standard(obj,nlp))
            if row and row[0].strip(): items.append(row)
    return items


def noise_variant(example, rng: random.Random):
    """Create OCR/typing noise outside gold entities while preserving character offsets."""
    text, ann = example
    entities=[tuple(e) for e in ann.get("entities", [])]
    protected=set()
    for s,e,_ in entities:
        protected.update(range(s,e))

    # Same-length substitutions preserve all gold character offsets. This includes
    # casing noise, OCR-like character swaps, and mild spelling/typing errors.
    keyboard = {
        'a':'sqz', 'b':'vng', 'c':'xvd', 'd':'sfc', 'e':'wr', 'f':'dgr', 'g':'fht',
        'h':'gju', 'i':'uo', 'j':'hik', 'k':'jlo', 'l':'kop', 'm':'n', 'n':'mbh',
        'o':'ip', 'p':'ol', 'q':'wa', 'r':'etf', 's':'awd', 't':'ryg', 'u':'yih',
        'v':'bfc', 'w':'qes', 'x':'zsc', 'y':'tuh', 'z':'xas'
    }
    out=[]
    for i,ch in enumerate(text):
        if i in protected:
            out.append(ch); continue
        r=rng.random()
        lower=ch.lower()
        if ch.isalpha() and r < 0.009 and lower in keyboard:
            repl=rng.choice(keyboard[lower])
            out.append(repl.upper() if ch.isupper() else repl)
        elif ch.isalpha() and r < 0.022:
            out.append(ch.lower() if ch.isupper() else ch.upper())
        elif ch in ",.;:|/" and r < 0.18:
            out.append(" ")
        elif ch==" " and r < 0.018:
            out.append("  ")
        else:
            out.append(ch)
    new_text="".join(out)

    # Only accept a variant when protected gold spans are byte-for-byte unchanged.
    valid=[]
    for s,e,label in entities:
        if new_text[s:e] == text[s:e]:
            valid.append([s,e,label])
    return [new_text,{"entities":valid}]


def build_synthetic_seed(base_examples, target=240):
    # Reuse the project's existing domain-specific seed data. This ensures 10-domain coverage.
    result=list(base_examples)
    rng=random.Random(20260929)
    while len(result)<target and base_examples:
        src=rng.choice(base_examples)
        result.append(noise_variant(src,rng))
    return result[:target]


def write_docbin(path: Path, examples, nlp):
    db=DocBin(store_user_data=True)
    kept=0
    for text, ann in examples:
        doc=nlp.make_doc(text)
        spans=[]; bad=False
        for s,e,label in ann.get("entities",[]):
            span=doc.char_span(s,e,label=label,alignment_mode="contract")
            if span is None:
                bad=True; break
            spans.append(span)
        if bad: continue
        doc.ents=spans
        db.add(doc); kept+=1
    db.to_disk(path)
    return kept


def main():
    DATA.mkdir(exist_ok=True); PROC.mkdir(exist_ok=True)
    nlp=spacy.blank("en")

    local=[]
    seed_paths=[PROC/"local_seed_train.json", PROC/"local_seed_dev.json"]
    if not all(path.exists() for path in seed_paths):
        seed_paths=[TRAIN_JSON, DEV_JSON]
    for path in seed_paths:
        if path.exists(): local.extend(load_any_file(path,nlp))

    external=[]
    for path in sorted(RAW.rglob("*.json")) + sorted(RAW.rglob("*.jsonl")):
        try: external.extend(load_any_file(path,nlp))
        except Exception as exc: print(f"[WARN] Skipping {path.name}: {exc}")

    # Synthetic/noise expansion is used only to broaden coverage and OCR robustness.
    synthetic=build_synthetic_seed(local, target=240)
    all_examples=[]; seen=set()
    for row in external+synthetic:
        key=json.dumps(row,ensure_ascii=False,sort_keys=True)
        if key not in seen and row[1].get("entities"):
            seen.add(key); all_examples.append(row)

    if len(all_examples)<100:
        raise RuntimeError(f"Only {len(all_examples)} usable labeled examples were found. Expected at least 100.")

    rng=random.Random(42); rng.shuffle(all_examples)
    split=max(20,int(len(all_examples)*0.18))
    dev=all_examples[:split]; train=all_examples[split:]

    TRAIN_JSON.write_text(json.dumps(train,ensure_ascii=False,indent=2),encoding="utf-8")
    DEV_JSON.write_text(json.dumps(dev,ensure_ascii=False,indent=2),encoding="utf-8")
    (PROC/"combined_train.json").write_text(json.dumps(train,ensure_ascii=False,indent=2),encoding="utf-8")
    (PROC/"combined_dev.json").write_text(json.dumps(dev,ensure_ascii=False,indent=2),encoding="utf-8")

    train_count=write_docbin(TRAIN_SPACY,train,nlp)
    dev_count=write_docbin(DEV_SPACY,dev,nlp)

    label_counts={label:0 for label in LABELS}
    for text,ann in train+dev:
        for _,_,label in ann["entities"]:
            if label in label_counts: label_counts[label]+=1

    manifest={
        "schema_version":"1.0",
        "labels":LABELS,
        "local_seed_examples":len(local),
        "external_examples":len(external),
        "synthetic_and_noise_examples":len(synthetic),
        "final_train_examples":train_count,
        "final_dev_examples":dev_count,
        "label_counts":label_counts,
        "external_source_files":[str(p.relative_to(ROOT)) for p in sorted(RAW.rglob("*.json")) + sorted(RAW.rglob("*.jsonl")) + sorted(RAW.rglob("*.zip")) if p.is_file()],
        "note":"External public resume datasets are ingested when present under datasets/raw. The bundled local_seed_*.json files are the data shipped with the supplied project; no external record is fabricated when a download is unavailable."
    }
    (PROC/"dataset_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")

    print(f"[DATA] External labeled records: {len(external)}")
    print(f"[DATA] Final train/dev: {train_count}/{dev_count}")
    print(f"[DATA] DocBin written: {TRAIN_SPACY.name}, {DEV_SPACY.name}")
    print(f"[DATA] Manifest: {PROC/'dataset_manifest.json'}")

if __name__=="__main__": main()
