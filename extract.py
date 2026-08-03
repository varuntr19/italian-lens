import re

import argostranslate.package
import argostranslate.translate
import pytesseract
import spacy
from PIL import Image

_nlp = spacy.load("it_core_news_sm")

_VOCAB_POS = {"NOUN": "noun", "VERB": "verb", "ADJ": "adjective", "ADV": "adverb"}
_PRICE_RE = re.compile(r"\d.*(€|euro)|(€|\$).*\d", re.IGNORECASE)
_INSTRUCTION_RE = re.compile(r"^(vietato|non |chiuso|aperto|attenzione)", re.IGNORECASE)

_MAX_VOCAB = 10


class ExtractionError(RuntimeError):
    pass


def _ensure_it_en_package():
    """Install the offline Italian->English Argos Translate model on first use."""
    installed = argostranslate.translate.get_installed_languages()
    if any(l.code == "it" for l in installed):
        return
    argostranslate.package.update_package_index()
    available = argostranslate.package.get_available_packages()
    pkg = next((p for p in available if p.from_code == "it" and p.to_code == "en"), None)
    if not pkg:
        raise ExtractionError("Could not find the Italian->English Argos Translate package.")
    argostranslate.package.install_from_path(pkg.download())


def _translate(text):
    return argostranslate.translate.translate(text, "it", "en")


def _categorize(line):
    if _PRICE_RE.search(line):
        return "price"
    if _INSTRUCTION_RE.match(line.strip()):
        return "instruction"
    return "other"


def analyze_image(image_path, media_type="image/jpeg"):
    _ensure_it_en_package()

    try:
        raw_text = pytesseract.image_to_string(Image.open(image_path), lang="ita")
    except Exception as e:
        raise ExtractionError(f"OCR failed: {e}")

    lines = [
        line.strip()
        for line in raw_text.splitlines()
        if line.strip() and re.search(r"[A-Za-zÀ-ù]", line)
    ]

    if not lines:
        return {
            "scene_description": "No readable Italian text found in this photo.",
            "phrases": [],
            "vocabulary": [],
        }

    phrases = []
    line_translations = {}
    for line in lines:
        english = _translate(line)
        line_translations[line] = english
        phrases.append({"italian": line, "english": english, "category": _categorize(line)})

    full_text = "\n".join(lines)
    doc = _nlp(full_text)

    seen_lemmas = set()
    vocabulary = []
    for tok in doc:
        if len(vocabulary) >= _MAX_VOCAB:
            break
        if tok.pos_ not in _VOCAB_POS or tok.is_stop or not tok.is_alpha or len(tok.text) < 3:
            continue
        lemma = tok.lemma_.lower()
        if lemma in seen_lemmas:
            continue
        seen_lemmas.add(lemma)

        source_line = next((l for l in lines if tok.text in l), lines[0])
        vocabulary.append(
            {
                "italian": lemma,
                "english": _translate(lemma),
                "part_of_speech": _VOCAB_POS[tok.pos_],
                "example_it": source_line,
                "example_en": line_translations[source_line],
            }
        )

    return {
        "scene_description": f"Text capture — {len(phrases)} line(s) of Italian text found.",
        "phrases": phrases,
        "vocabulary": vocabulary,
    }
