"""Thin inference wrapper around the serialized spaCy NER model."""
from __future__ import annotations
from pathlib import Path
import spacy

LABELS=["PERSON","EMAIL","PHONE","LINKEDIN","GITHUB","DESIGNATION","YEARS_EXPERIENCE","TECHNICAL_SKILL","SOFT_SKILL","LANGUAGE","DEGREE","INSTITUTION","LOCATION","CERTIFICATION","CERTIFICATION_PROVIDER","HACKATHON","ACHIEVEMENT","DOMAIN","PROJECT_TITLE"]

class ResumeNER:
    def __init__(self, model_dir: str | Path):
        self.model_dir=Path(model_dir)
        self.nlp=spacy.load(self.model_dir)
        # Prevent spaCy E088 on unusually verbose OCR output while retaining the
        # same statistical NER pipeline.
        self.nlp.max_length = max(self.nlp.max_length, 2_000_000)
    def predict_entities(self,text:str):
        doc=self.nlp(text)
        return [{"label":e.label_,"start":e.start_char,"end":e.end_char,"text":e.text} for e in doc.ents]
    def document(self,text:str):
        return self.nlp(text)
