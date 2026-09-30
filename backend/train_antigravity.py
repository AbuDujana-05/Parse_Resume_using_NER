"""Train a custom spaCy v3 statistical NER model from the project DocBin datasets."""
from __future__ import annotations

import json, os, random, sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import spacy
from spacy.training import Example
from spacy.util import minibatch, compounding
from spacy.scorer import Scorer

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
OUT=ROOT/'output'
MODEL=ROOT/'models'/'ner_model'
TRAIN_BIN=DATA/'train.spacy'
DEV_BIN=DATA/'dev.spacy'
LABELS=["PERSON","EMAIL","PHONE","DESIGNATION","YEARS_EXPERIENCE","SKILL","DEGREE","INSTITUTION","LOCATION","CERTIFICATION","DOMAIN","PROJECT_TITLE"]

BANNER=r"""
╔══════════════════════════════════════════════════════════════════════╗
║                     PARSE RESUME USING NER                           ║
║              CUSTOM spaCy v3 STATISTICAL NER                        ║
║        DATA → DOCBIN → MINI-BATCH TRAINING → EVALUATION              ║
╚══════════════════════════════════════════════════════════════════════╝
"""


def load_examples(nlp, path:Path):
    from spacy.tokens import DocBin
    docs=list(DocBin().from_disk(path).get_docs(nlp.vocab))
    examples=[]
    for doc in docs:
        examples.append(Example.from_dict(doc,{"entities":[(e.start_char,e.end_char,e.label_) for e in doc.ents]}))
    return examples


def save_loss_chart(losses):
    OUT.mkdir(exist_ok=True)
    fig,ax=plt.subplots(figsize=(10,5.6))
    fig.patch.set_facecolor('#0A0817'); ax.set_facecolor('#0A0817')
    ax.plot(range(1,len(losses)+1),losses,linewidth=2.4,marker='o',markersize=3)
    ax.set_title('spaCy NER Training Loss',color='white',fontweight='bold')
    ax.set_xlabel('Epoch',color='#E8E6F0'); ax.set_ylabel('NER Loss',color='#E8E6F0')
    ax.tick_params(colors='#E8E6F0'); ax.grid(True,alpha=.18)
    for s in ax.spines.values(): s.set_alpha(.25)
    fig.tight_layout(); fig.savefig(OUT/'loss_chart.png',dpi=150,bbox_inches='tight'); plt.close(fig)


def save_confusion(metrics, dev_examples, nlp):
    # Entity overlap confusion matrix: rows=gold labels, cols=predicted labels.
    mat=np.zeros((len(LABELS),len(LABELS)),dtype=int); idx={l:i for i,l in enumerate(LABELS)}
    for ex in dev_examples:
        doc=nlp(ex.reference.text)
        gold=list(ex.reference.ents)
        pred=list(doc.ents)
        for g in gold:
            overlaps=[p for p in pred if max(g.start_char,p.start_char)<min(g.end_char,p.end_char)]
            if overlaps and g.label_ in idx:
                label=overlaps[0].label_
                if label in idx: mat[idx[g.label_],idx[label]]+=1
    fig,ax=plt.subplots(figsize=(12,9)); fig.patch.set_facecolor('#0A0817'); ax.set_facecolor('#0A0817')
    im=ax.imshow(mat,aspect='auto')
    ax.set_xticks(range(len(LABELS)),LABELS,rotation=45,ha='right',color='#E8E6F0',fontsize=8)
    ax.set_yticks(range(len(LABELS)),LABELS,color='#E8E6F0',fontsize=8)
    ax.set_xlabel('Predicted label',color='#E8E6F0'); ax.set_ylabel('Gold label',color='#E8E6F0')
    ax.set_title('Entity Overlap Confusion Matrix',color='white',fontweight='bold')
    for r in range(mat.shape[0]):
        for c in range(mat.shape[1]):
            ax.text(c,r,str(mat[r,c]),ha='center',va='center',color='white',fontsize=8)
    fig.tight_layout(); fig.savefig(OUT/'confusion_matrix.png',dpi=150,bbox_inches='tight'); plt.close(fig)


def main():
    print(BANNER)
    if not TRAIN_BIN.exists() or not DEV_BIN.exists():
        print('[INFO] DocBins missing; running prepare_data.py first...')
        import prepare_data; prepare_data.main()

    OUT.mkdir(exist_ok=True); MODEL.parent.mkdir(exist_ok=True)
    nlp=spacy.blank('en')
    ner=nlp.add_pipe('ner')
    for label in LABELS: ner.add_label(label)
    train_examples=load_examples(nlp,TRAIN_BIN); dev_examples=load_examples(nlp,DEV_BIN)
    print(f'[DATA] Train={len(train_examples)}  Dev={len(dev_examples)}  Labels={len(LABELS)}')

    optimizer=nlp.initialize(get_examples=lambda:train_examples)
    rng=random.Random(42)
    losses=[]
    epochs=int(os.getenv("NER_EPOCHS","15"))
    for epoch in range(1,epochs+1):
        rng.shuffle(train_examples)
        epoch_losses={}
        batches=minibatch(train_examples,size=compounding(4.0,32.0,1.25))
        batch_count=0
        for batch in batches:
            nlp.update(batch,drop=0.25,sgd=optimizer,losses=epoch_losses)
            batch_count+=1
        loss=float(epoch_losses.get('ner',0.0)); losses.append(loss)
        print(f'EPOCH {epoch:02d}/{epochs} | batches={batch_count:03d} | ner_loss={loss:10.4f} | dropout=0.25')

    scorer=Scorer()
    scored=scorer.score([Example(nlp(ex.reference.text), ex.reference) for ex in dev_examples])
    per_entity={label:{"precision":0.0,"recall":0.0,"f1":0.0} for label in LABELS}
    for label,vals in scored.get('ents_per_type',{}).items():
        if label in per_entity:
            per_entity[label]={"precision":round(vals.get('p',0.0),4),"recall":round(vals.get('r',0.0),4),"f1":round(vals.get('f',0.0),4)}
    metrics={
        "engine":"spaCy v3 custom NER",
        "precision":round(float(scored.get('ents_p',0.0)),4),
        "recall":round(float(scored.get('ents_r',0.0)),4),
        "f1":round(float(scored.get('ents_f',0.0)),4),
        "epochs":epochs,
        "dropout":0.25,
        "final_loss":round(losses[-1],4) if losses else 0.0,
        "train_examples":len(train_examples),
        "dev_examples":len(dev_examples),
        "per_entity":per_entity,
    }
    MODEL.mkdir(parents=True,exist_ok=True); nlp.to_disk(MODEL)
    (MODEL/'training_config.json').write_text(json.dumps({"epochs":epochs,"dropout":0.25,"labels":LABELS},indent=2),encoding='utf-8')
    (OUT/'training_metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    save_loss_chart(losses); save_confusion(metrics,dev_examples,nlp)
    print(f"[EVAL] Precision={metrics['precision']:.4f} Recall={metrics['recall']:.4f} F1={metrics['f1']:.4f}")
    print(f'[ARTIFACT] {MODEL}')
    print(f'[ARTIFACT] {OUT/"loss_chart.png"}')
    print(f'[ARTIFACT] {OUT/"confusion_matrix.png"}')
    print(f'[ARTIFACT] {OUT/"training_metrics.json"}')

if __name__=='__main__': main()
