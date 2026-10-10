from __future__ import annotations
import json, os, re, tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from starlette.datastructures import UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import spacy
from spacy import displacy
from spacy.tokens import Doc

from cv_engine import extract_text_from_file
from ner_model import ResumeNER, LABELS
from sample_texts import SAMPLE_TEXTS

ROOT=Path(__file__).resolve().parent
OUTPUT=ROOT/'output'; MODEL=ROOT/'models'/'ner_model'
OUTPUT.mkdir(exist_ok=True)
MAX_UPLOAD_BYTES=4*1024*1024

BANNER=r"""
╔══════════════════════════════════════════════════════════════════════╗
║                      PARSE RESUME USING NER                         ║
║                   FastAPI + spaCy + OpenCV                         ║
╚══════════════════════════════════════════════════════════════════════╝
"""
print('Parse Resume using NER | FastAPI + spaCy + OpenCV')

app=FastAPI(title='Parse Resume using NER API',version='3.0.0')
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
app.mount('/static',StaticFiles(directory=OUTPUT),name='static')

ner_model: Optional[ResumeNER]=None
if MODEL.exists() and (MODEL/'config.cfg').exists():
    try:
        ner_model=ResumeNER(MODEL); print(f'[INFO] Loaded spaCy model: {MODEL}')
    except Exception as exc:
        print(f'[WARNING] spaCy model load failed: {exc}')

class ParseResponse(BaseModel):
    entities: dict[str,list[str]]
    raw_text: str
    displacy_html: str
    ats_score: int

COLORS={
    'PERSON':'#FF6B6B','EMAIL':'#4ECDC4','PHONE':'#45B7D1','LINKEDIN':'#0A66C2','GITHUB':'#B8C0CC','DESIGNATION':'#96CEB4','YEARS_EXPERIENCE':'#FFEAA7',
    'TECHNICAL_SKILL':'#DDA0DD','SOFT_SKILL':'#C39BD3','LANGUAGE':'#5DADE2','DEGREE':'#98D8C8','INSTITUTION':'#F7DC6F','LOCATION':'#82E0AA','CERTIFICATION':'#F0B27A',
    'CERTIFICATION_PROVIDER':'#F5B7B1','HACKATHON':'#FF9F43','ACHIEVEMENT':'#F8C471',
    'DOMAIN':'#AED6F1','PROJECT_TITLE':'#D7BDE2'
}

def safe_displacy(doc):
    # spaCy's renderer escapes resume text while producing the entity markup.
    return displacy.render(doc,style='ent',page=False,options={'colors':COLORS})


# Resumes often title their education section "Studies", "Qualifications", or
# "Academic Background" rather than "Education".  The trained model sees these
# headings as ordinary text, so inspect only the short section following one of
# these headings and add an INSTITUTION span when an institution is clear.
EDUCATION_HEADING = re.compile(
    r'^\s*(?:education(?:al\s+(?:background|history|details))?|'
    r'academic(?:\s+(?:background|qualifications?|profile))?|'
    r'stud(?:y|ies)|qualifications?)\s*:?\s*(.*)$',
    re.IGNORECASE,
)
NEXT_SECTION_HEADING = re.compile(
    r'^\s*(?:experience|work\s+experience|employment|skills?|technical\s+skills|'
    r'projects?|certifications?|certificates?|achievements?|summary|profile|'
    r'contact|languages?|interests?|references?)\s*:?\s*$',
    re.IGNORECASE,
)
INSTITUTION_NAME = re.compile(
    r'\b(?:(?:[A-Z][A-Za-z&.\'-]*|[A-Z]{2,})\s+){0,6}'
    r'(?:University|College|Institute|School|Academy|Polytechnic|Conservatory|Faculty|'
    r'UNIVERSITY|COLLEGE|INSTITUTE|SCHOOL|ACADEMY|POLYTECHNIC|CONSERVATORY|FACULTY)'
    r'(?:\s+(?:of|for|at|and|the|[A-Z][A-Za-z&.\'-]*|[A-Z]{2,})){0,6}\b'
)
DEGREE = re.compile(
    r'\b(?:b\.?\s*tech|b\.?\s*e\.?|bachelor(?:\'s)?(?:\s+of\s+[a-z ]+)?|'
    r'm\.?\s*tech|m\.?\s*e\.?|m\.?\s*s\.?|master(?:\'s)?(?:\s+of\s+[a-z ]+)?|'
    r'mba|ph\.?\s*d\.?|doctorate|diploma)\b',
    re.IGNORECASE,
)
INSTITUTION_ABBREVIATION = re.compile(r'\b[A-Z]{2,8}\b')
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
PHONE_PATTERN = re.compile(r'(?<!\w)(?:\+?\d[\d .()\-]{7,}\d)(?!\w)')
LINKEDIN_PATTERN = re.compile(r'\b(?:https?://)?(?:(?:www\.)?linkedin\.com|lnkd\.in|tinyurl\.com)/[^\s|,;]+', re.IGNORECASE)
GITHUB_PATTERN = re.compile(r'\b(?:https?://)?(?:www\.)?github\.com/[^\s|,;]+', re.IGNORECASE)
ROLE_PATTERN = re.compile(
    r'\b(?:[A-Za-z]{2,}\s*(?:[&/]\s*)?){0,5}'
    r'(?:Engineer|Developer|Scientist|Analyst|Designer|Manager|Architect|Consultant|Intern)\b',
    re.IGNORECASE,
)
SECTION_BOUNDARY = re.compile(
    r'^\s*(?:about\s+me|summary|profile|technical\s+skills|skills|'
    r'certifications?(?:\s*&\s*internships?)?|projects?|hackathons?(?:\s*&\s*achievements?)?|'
    r'education|educational\s+background|academic\s+background|studies|qualifications?|languages?)\s*$',
    re.IGNORECASE,
)


def text_lines(text: str) -> list[tuple[str, int]]:
    """Return each resume line with its character offset in the original text."""
    output: list[tuple[str, int]] = []
    offset = 0
    for line_with_end in text.splitlines(keepends=True):
        output.append((line_with_end.rstrip('\r\n'), offset))
        offset += len(line_with_end)
    return output


def section_content(text: str, heading: re.Pattern[str]) -> list[tuple[str, int]]:
    """Read non-empty lines after a known resume section heading."""
    lines = text_lines(text)
    values: list[tuple[str, int]] = []
    for index, (line, _) in enumerate(lines):
        if not heading.match(line):
            continue
        for following, start in lines[index + 1:]:
            if SECTION_BOUNDARY.match(following):
                break
            if following.strip():
                leading = len(following) - len(following.lstrip())
                values.append((following.strip(), start + leading))
        break
    return values


def all_section_content(text: str, heading: re.Pattern[str]) -> list[tuple[str, int]]:
    """Read every section matching a heading (for example, Technical Skills and Skills)."""
    lines = text_lines(text)
    values: list[tuple[str, int]] = []
    for index, (line, _) in enumerate(lines):
        if not heading.match(line):
            continue
        for following, start in lines[index + 1:]:
            if SECTION_BOUNDARY.match(following):
                break
            if following.strip():
                leading = len(following) - len(following.lstrip())
                values.append((following.strip(), start + leading))
    return values


def named_skill_sections(text: str) -> list[tuple[str, str, int]]:
    """Keep Technical Skills and the separate Skills section as distinct entities."""
    heading = re.compile(r'^\s*(?:technical\s+)?skills\s*$', re.IGNORECASE)
    values: list[tuple[str, str, int]] = []
    lines = text_lines(text)
    for index, (line, _) in enumerate(lines):
        if not heading.match(line):
            continue
        label = 'TECHNICAL_SKILL' if re.search(r'technical', line, re.IGNORECASE) else 'SOFT_SKILL'
        for following, start in lines[index + 1:]:
            if SECTION_BOUNDARY.match(following):
                break
            if following.strip():
                leading = len(following) - len(following.lstrip())
                values.append((label, following.strip(), start + leading))
    return values


def rule_entity_ranges(text: str) -> list[tuple[str, int, int]]:
    """Extract high-confidence entities from standard resume structure and OCR text."""
    candidates: list[tuple[str, int, int]] = []

    def add(label: str, start: int, end: int) -> None:
        value = text[start:end].strip()
        if value and not any(label == item[0] and start == item[1] and end == item[2] for item in candidates):
            candidates.append((label, start, end))

    for match in EMAIL_PATTERN.finditer(text):
        add('EMAIL', match.start(), match.end())
    for match in PHONE_PATTERN.finditer(text):
        if sum(char.isdigit() for char in match.group()) >= 9:
            add('PHONE', match.start(), match.end())
    for match in LINKEDIN_PATTERN.finditer(text):
        add('LINKEDIN', match.start(), match.end())
    for match in GITHUB_PATTERN.finditer(text):
        add('GITHUB', match.start(), match.end())

    # Names are normally the first short, all-caps line in image/PDF OCR output.
    for line, start in text_lines(text)[:5]:
        words = line.strip().split()
        if 2 <= len(words) <= 4 and line.strip() == line.strip().upper() and all(word.replace('-', '').isalpha() for word in words):
            add('PERSON', start + len(line) - len(line.lstrip()), start + len(line.rstrip()))
            break

    # A role sits immediately below the name in most modern one-page resumes.
    for line, start in text_lines(text)[:6]:
        role = ROLE_PATTERN.search(line)
        if role:
            add('DESIGNATION', start + role.start(), start + role.end())
            break

    education_lines = section_content(text, EDUCATION_HEADING)
    for line, start in education_lines:
        degree = DEGREE.search(line)
        if degree:
            end = re.search(r'\s+(?:[-–—])\s+|\b20\d{2}\b', line[degree.start():])
            degree_end = degree.start() + end.start() if end else len(line.rstrip())
            add('DEGREE', start + degree.start(), start + degree_end)
    for start, end in education_institution_ranges(text):
        add('INSTITUTION', start, end)

    for label, line, start in named_skill_sections(text):
        cleaned = re.sub(r'^[\s•*#©]+', '', line)
        cleaned_start = start + len(line) - len(cleaned)
        if label == 'TECHNICAL_SKILL' and ':' in cleaned:
            category = cleaned.split(':', 1)[0].strip()
            if 2 <= len(category) <= 50:
                category_start = cleaned_start + cleaned.find(category)
                add(label, category_start, category_start + len(category))
        value_start = cleaned.find(':') + 1 if ':' in cleaned else 0
        for item in re.finditer(r'[^,|]+', cleaned[value_start:]):
            value = item.group().strip(' -–—.\t')
            if 2 <= len(value) <= 60 and any(char.isalpha() for char in value):
                item_start = cleaned_start + value_start + item.start() + len(item.group()) - len(item.group().lstrip())
                add(label, item_start, item_start + len(value))

    language_heading = re.compile(r'^\s*languages?\s*$', re.IGNORECASE)
    for line, start in section_content(text, language_heading):
        for item in re.finditer(r'[^,|]+', line):
            value = item.group().strip(' -–—.\t')
            if 2 <= len(value) <= 40 and any(char.isalpha() for char in value):
                item_start = start + item.start() + len(item.group()) - len(item.group().lstrip())
                add('LANGUAGE', item_start, item_start + len(value))

    certification_heading = re.compile(r'^\s*certifications?(?:\s*&\s*internships?)?\s*$', re.IGNORECASE)
    for line, start in section_content(text, certification_heading):
        cleaned = re.sub(r'^[\s•*#©+]+', '', line)
        header = re.split(r'\s+[\u2013\u2014-]\s+', cleaned, maxsplit=1)[0]
        title = header.split(',', 1)[0].strip()
        if 3 <= len(title) <= 80:
            title_start = start + len(line) - len(cleaned) + cleaned.find(title)
            add('CERTIFICATION', title_start, title_start + len(title))
        if ',' in header:
            provider_text = header.split(',', 1)[1]
            provider_offset = start + len(line) - len(cleaned) + cleaned.find(provider_text)
            for provider in re.finditer(r'[^,&]+', provider_text):
                value = provider.group().strip()
                if 2 <= len(value) <= 60:
                    provider_start = provider_offset + provider.start() + len(provider.group()) - len(provider.group().lstrip())
                    add('CERTIFICATION_PROVIDER', provider_start, provider_start + len(value))

    project_heading = re.compile(r'^\s*projects?\s*$', re.IGNORECASE)
    for line, start in section_content(text, project_heading):
        project = re.match(r'^\s*\d+[.),]\s*(.+?)\s*$', line)
        if project:
            value = project.group(1)
            add('PROJECT_TITLE', start + project.start(1), start + project.start(1) + len(value))

    achievement_heading = re.compile(r'^\s*(?:hackathons?|achievements?)(?:\s*&\s*(?:hackathons?|achievements?))?\s*$', re.IGNORECASE)
    last_achievement_index = None
    for line, start in section_content(text, achievement_heading):
        cleaned = re.sub(r'^[\s•*#©]+', '', line)
        cleaned_start = start + len(line) - len(cleaned)
        separator = re.search(r'\s+[\u2013\u2014-]\s+', cleaned)
        title = cleaned[:separator.start()].strip() if separator else cleaned.strip()
        if title and re.search(r'hackathon', title, re.IGNORECASE):
            title_start = cleaned_start + cleaned.find(title)
            add('HACKATHON', title_start, title_start + len(title))
        if separator:
            description = cleaned[separator.end():].strip()
            if len(description) >= 8:
                description_start = cleaned_start + separator.end() + len(cleaned[separator.end():]) - len(cleaned[separator.end():].lstrip())
                add('ACHIEVEMENT', description_start, description_start + len(description))
                last_achievement_index = len(candidates) - 1
        elif title and not re.search(r'hackathon', title, re.IGNORECASE):
            if last_achievement_index is not None:
                label, achievement_start, _ = candidates[last_achievement_index]
                candidates[last_achievement_index] = (label, achievement_start, start + len(line.rstrip()))
            else:
                title_start = cleaned_start + cleaned.find(title)
                add('ACHIEVEMENT', title_start, title_start + len(title))
                last_achievement_index = len(candidates) - 1

    return candidates


def valid_model_entity(entity) -> bool:
    """Reject model predictions that cannot be the label they claim to be."""
    value = entity.text.strip()
    if not value or '\n' in value or len(value) > 100:
        return False
    if entity.label_ == 'EMAIL':
        return bool(EMAIL_PATTERN.fullmatch(value))
    if entity.label_ == 'PHONE':
        return bool(PHONE_PATTERN.fullmatch(value)) and sum(char.isdigit() for char in value) >= 9
    if entity.label_ == 'LINKEDIN':
        return bool(LINKEDIN_PATTERN.fullmatch(value))
    if entity.label_ == 'GITHUB':
        return bool(GITHUB_PATTERN.fullmatch(value))
    if entity.label_ == 'DEGREE':
        return bool(DEGREE.search(value))
    if entity.label_ == 'INSTITUTION':
        return bool(INSTITUTION_NAME.search(value))
    if entity.label_ == 'YEARS_EXPERIENCE':
        return bool(re.search(r'\b\d+\+?\s+years?\b', value, re.IGNORECASE))
    if entity.label_ == 'DESIGNATION':
        return bool(ROLE_PATTERN.search(value))
    return entity.label_ in {'LANGUAGE', 'CERTIFICATION', 'CERTIFICATION_PROVIDER', 'HACKATHON', 'ACHIEVEMENT', 'PROJECT_TITLE', 'LOCATION', 'PERSON'}


def normalize_resume_entities(doc: Doc) -> Doc:
    """Prefer structured, validated entities over impossible statistical predictions."""
    ranges = rule_entity_ranges(doc.text)
    rule_labels = {label for label, _, _ in ranges}
    selected = []
    for label, start, end in ranges:
        span = doc.char_span(start, end, label=label, alignment_mode='contract')
        if span is not None and not any(span.start < other.end and span.end > other.start for other in selected):
            selected.append(span)
    for entity in doc.ents:
        if entity.label_ in rule_labels or entity.label_ == 'SKILL' or not valid_model_entity(entity):
            continue
        if not any(entity.start < other.end and entity.end > other.start for other in selected):
            selected.append(entity)
    doc.ents = tuple(sorted(selected, key=lambda entity: (entity.start, entity.end)))
    return doc


def education_institution_ranges(text: str) -> list[tuple[int, int]]:
    """Return reliable institution text ranges under an education-style heading."""
    lines = text.splitlines(keepends=True)
    ranges: list[tuple[int, int]] = []
    offset = 0

    for index, line_with_end in enumerate(lines):
        line = line_with_end.rstrip('\r\n')
        heading = EDUCATION_HEADING.match(line)
        if not heading:
            offset += len(line_with_end)
            continue

        section_lines: list[tuple[str, int]] = []
        inline_value = heading.group(1).strip()
        if inline_value:
            section_lines.append((inline_value, offset + heading.start(1) + (len(heading.group(1)) - len(heading.group(1).lstrip()))))

        next_offset = offset + len(line_with_end)
        for following in lines[index + 1:index + 7]:
            candidate = following.rstrip('\r\n')
            if NEXT_SECTION_HEADING.match(candidate):
                break
            if candidate.strip():
                leading_space = len(candidate) - len(candidate.lstrip())
                section_lines.append((candidate.strip(), next_offset + leading_space))
            next_offset += len(following)

        for candidate, start in section_lines:
            matches = list(INSTITUTION_NAME.finditer(candidate))
            if not matches:
                # Support compact institution names (for example, "MIT") only
                # when they are clearly on a degree line in an education section.
                if DEGREE.search(candidate):
                    degree_spans = [(degree.start(), degree.end()) for degree in DEGREE.finditer(candidate)]
                    matches = [
                        match for match in INSTITUTION_ABBREVIATION.finditer(candidate)
                        if not any(match.start() < end and match.end() > start for start, end in degree_spans)
                    ]
            for match in matches:
                ranges.append((start + match.start(), start + match.end()))

        offset += len(line_with_end)

    return ranges


def enrich_education_institutions(doc: Doc) -> Doc:
    """Add non-overlapping INSTITUTION spans inferred from education sections."""
    entities = list(doc.ents)
    for start, end in education_institution_ranges(doc.text):
        candidate = doc.char_span(start, end, label='INSTITUTION', alignment_mode='contract')
        if candidate is None or any(candidate.start < ent.end and candidate.end > ent.start for ent in entities):
            continue
        entities.append(candidate)
    doc.ents = tuple(sorted(entities, key=lambda ent: (ent.start, ent.end)))
    return doc


def calculate_ats_score(entities: dict[str, list[str]], text: str) -> int:
    """Score ATS-readiness completeness; job-specific matching needs a job description."""
    has = lambda label: bool(entities.get(label))
    score = 0
    score += 5 if has('EMAIL') or EMAIL_PATTERN.search(text) else 0
    score += 5 if has('PHONE') else 0
    score += 2 if has('LINKEDIN') or has('GITHUB') else 0
    score += 4 if has('PERSON') else 0
    score += 4 if has('DESIGNATION') else 0
    score += 5 if re.search(r'\b(?:about me|professional summary|summary|profile)\b', text, re.IGNORECASE) else 0
    skill_count = len(entities.get('TECHNICAL_SKILL', [])) + len(entities.get('SOFT_SKILL', []))
    score += min(skill_count, 8) * 18 // 8
    score += 6 if has('DEGREE') or DEGREE.search(text) else 0
    score += 6 if has('INSTITUTION') else 0
    score += min(len(entities.get('PROJECT_TITLE', [])), 3) * 5
    score += min(len(entities.get('CERTIFICATION', [])), 2) * 4
    score += 10 if has('YEARS_EXPERIENCE') or re.search(r'\b\d+\+?\s+years?\b', text, re.IGNORECASE) else 5 if re.search(r'\b(?:intern|internship)\b', text, re.IGNORECASE) else 0
    score += 5 if has('HACKATHON') or has('ACHIEVEMENT') else 0
    score += 5 if len(text.split()) >= 75 else 0
    return min(score, 100)

async def get_payload(request:Request):
    ctype=request.headers.get('content-type','')
    if 'multipart/form-data' in ctype:
        form=await request.form(); return form.get('file'), form.get('text')
    if 'application/json' in ctype:
        body=await request.json(); return None, (body.get('text') if isinstance(body,dict) else None)
    return None,None

@app.post('/api/parse',response_model=ParseResponse)
async def parse_resume(request:Request):
    file,text=await get_payload(request); raw_text=''
    if file is not None and hasattr(file, 'read') and hasattr(file, 'filename'):
        ext=Path(file.filename or 'resume.txt').suffix.lower().lstrip('.') or 'txt'
        allowed={'pdf','docx','pptx','png','jpg','jpeg','webp','bmp','tiff','txt','md'}
        if ext not in allowed:
            raise HTTPException(status_code=415, detail=f'Unsupported file type: .{ext}')
        payload=await file.read(MAX_UPLOAD_BYTES+1)
        if len(payload)>MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f'File exceeds the {MAX_UPLOAD_BYTES // (1024*1024)} MB upload limit.')
        with tempfile.NamedTemporaryFile(delete=False,suffix='.'+ext) as tmp:
            tmp.write(payload); temp_path=tmp.name
        try:
            raw_text=extract_text_from_file(temp_path,ext)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f'Could not extract text from the uploaded file: {exc}') from exc
        finally:
            try: os.remove(temp_path)
            except OSError: pass
    elif isinstance(text,str):
        raw_text=text.strip()
        if len(raw_text) > 1_500_000:
            raise HTTPException(status_code=413, detail='Resume text is too long. Please submit a document smaller than 1.5 million characters.')
    if not raw_text.strip(): raw_text='No resume text was provided or could be extracted.'

    entities={label:[] for label in LABELS}
    if ner_model:
        try:
            doc=ner_model.document(raw_text)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f'spaCy inference failed: {exc}') from exc
        doc=normalize_resume_entities(doc)
        entities={label:[] for label in LABELS}
        for ent in doc.ents:
            value=re.sub(r'\s+', ' ', ent.text).strip()
            if ent.label_ in entities and value not in entities[ent.label_]:
                entities[ent.label_].append(value)
        html=safe_displacy(doc)
    else:
        raise HTTPException(status_code=503, detail='The spaCy NER model is not loaded. Start the backend from the project root so backend/models/ner_model can be loaded.')
    entities={k:v for k,v in entities.items() if v}
    return ParseResponse(
        entities=entities,
        raw_text=raw_text,
        displacy_html=html,
        ats_score=calculate_ats_score(entities, raw_text),
    )

@app.get('/api/metrics')
def metrics():
    path=OUTPUT/'training_metrics.json'
    data=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    return {'metrics':data,'loss_chart':'/static/loss_chart.png','confusion_matrix':'/static/confusion_matrix.png'}

@app.get('/api/health')
def health():
    return {'status':'ok','model_loaded':ner_model is not None,'engine':'spaCy v3 custom NER' if ner_model else 'unloaded'}

@app.get('/api/samples/{domain}')
def get_sample(domain:str):
    return {'text':SAMPLE_TEXTS.get(domain.lower(),'Sample not found.')}

if __name__=='__main__':
    import uvicorn
    uvicorn.run('app:app',host='0.0.0.0',port=8000,reload=False)
