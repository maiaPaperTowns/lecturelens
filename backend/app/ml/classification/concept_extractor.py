"""Unsupervised concept detection.

Pipeline: noun-phrase candidate generation (lightweight POS heuristics, no spaCy
dependency) -> TF-IDF ranking across the lecture (recurrence-weighted) ->
de-duplication -> snippet selection. No LLM involved.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from app.ml.preprocessing.chunk import Chunk
from app.ml.preprocessing.clean import sentence_split

# --- function words: determiners, prepositions, conjunctions, pronouns, aux ---
_FUNCTION_WORDS = set(
    """a an the this that these those it its it's each any some all no not only just very
    of to in on at by for from with without within into onto over under across through
    and or but nor so as if then than because while when where which who whom whose since
    before after though although unless until whether once whereas however therefore thus
    hence upon per via about above below here there we you they he she i our your their his
    her them us me my mine ours yours theirs also both either neither more most such many few
    is are was were be been being am do does did have has had can could will would shall
    should may might must let""".split()
)

# words that are almost always the wrong *tail* for a concept name
_BAD_TAIL = _FUNCTION_WORDS | {
    "run", "runs", "use", "uses", "used", "make", "makes", "made", "give", "gives",
    "given", "take", "takes", "taken", "get", "gets", "got", "need", "needs", "means",
    "yields", "returns", "requires", "provides", "shows", "works", "goes", "comes",
    "first", "second", "third", "next", "last", "same", "different", "such", "many",
    "small", "large", "big", "good", "bad", "proportional", "correct", "absent",
    "several", "various", "certain", "possible", "similar", "equal", "along",
}
_VERBS_EXTRA = {"costs", "stops", "observe", "observes", "along", "generalises", "predates"}
_VERB_LEAD = {
    "recurse", "return", "repeat", "compute", "consider", "suppose", "recall", "assume",
    "imagine", "note", "see", "let", "predates", "decrements", "performs", "denotes",
    "maintains", "guarantees", "explains", "introduces", "requires", "combines",
}
_CODE_TOKENS = {"lo", "hi", "mid", "lhs", "rhs", "idx", "tmp", "ptr", "arr", "elif", "else", "def"}

# Any of these tokens anywhere in a span means it is a clause, not a concept name.
_VERBS = set(
    """is are was were be been being have has had do does did will would can could should
    contain contains hold holds store stores map maps split splits merge merges sort sorts
    return returns compute computes compare compares halve halves divide divides denote denotes
    refer refers mean means make makes avoid avoids appear appears give gives update updates
    adjust adjusts choose chooses predict predicts predicted initialise initialises oscillate
    diverge run runs use uses used require requires provide provides show shows work works
    proceed proceeds select selects preempt preempts move moves raise raises prevent prevents
    guarantee guarantees maintain maintains explain explains introduce introduces build builds
    scale scales decompose decomposes add adds shrink shrinks yield yields conclude concludes
    check checks trace traces pick picks partition update keep keeps become becomes remain
    remains follow follows relax free freed set sets take takes get gets need needs
    lies lie lay walk walks halve estimate estimates minimise minimises""".split()
)
_NP_CONNECTORS = {"of"}

# suffixes that mark a plausible head noun
_NOUN_SUFFIX = re.compile(
    r"(tion|sion|ment|ity|ness|ism|ance|ence|ology|graph|logy|acy|ure|dom|ship|"
    r"sort|tree|list|queue|stack|table|array|heap|graph|node|edge|search|rate|"
    r"time|space|order|model|method|rule|law|theorem|lemma|factor|score|value|"
    r"function|variable|pointer|process|thread|cache|memory|algorithm|complexity)$"
)
_TECH_HINT = re.compile(
    r"(algorithm|complexity|invariant|theorem|lemma|recursion|gradient|regularis|"
    r"schedul|cluster|embedding|entropy|variance|probabil|asymptot|heuristic)"
)

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9'\-]*")
_DEF_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9\- ]{2,50}?)\s+(?:is|are)\s+(?:defined as|a |an |the |called|known as)",
)


@dataclass
class ConceptCandidate:
    name: str
    snippet: str
    chunk_index: int
    source_page: int | None
    source_section: str | None
    relevance_score: float


def _is_headish(tok: str) -> bool:
    low = tok.lower()
    if low in _FUNCTION_WORDS:
        return False
    if low.endswith("ly"):
        return False
    if low.endswith(("ing", "ed")) and not low.endswith(("ring", "thing", "ing")):
        # keep 'string', 'meaning'-like via suffix check below; otherwise treat as verby
        return bool(_NOUN_SUFFIX.search(low))
    return True


def _clean_phrase_tokens(tokens: list[str]) -> list[str] | None:
    """Trim leading/trailing function words; reject clause fragments."""
    lowered = [t.lower() for t in tokens]
    while lowered and lowered[0] in _FUNCTION_WORDS:
        tokens, lowered = tokens[1:], lowered[1:]
    while lowered and lowered[-1] in _BAD_TAIL:
        tokens, lowered = tokens[:-1], lowered[:-1]
    if not (1 <= len(tokens) <= 4):
        return None
    if any(t in _VERBS or t in _VERBS_EXTRA for t in lowered):  # span has a verb -> a clause
        return None
    # interior function words are only allowed if they are NP connectors ("order of growth")
    if any(t in _FUNCTION_WORDS and t not in _NP_CONNECTORS for t in lowered):
        return None
    if lowered[0] in _NP_CONNECTORS or lowered[-1] in _NP_CONNECTORS:
        return None
    if lowered[0] in _VERB_LEAD or _CODE_TOKENS.intersection(lowered):
        return None
    if lowered[0].endswith(("ing", "ed")) and not _NOUN_SUFFIX.search(lowered[0]):
        return None
    head = lowered[-1]
    if head in _BAD_TAIL or head.endswith("ly"):
        return None
    is_head_noun = (
        tokens[-1][:1].isupper()
        or bool(_NOUN_SUFFIX.search(head))
        or bool(_TECH_HINT.search(head))
        or (len(head) > 4 and head not in _FUNCTION_WORDS and not head.endswith(("ing", "ed")))
    )
    if not is_head_noun:
        return None
    if len(tokens) == 1:
        only = lowered[0]
        strong = (
            tokens[0][:1].isupper()
            or bool(_NOUN_SUFFIX.search(only))
            or bool(_TECH_HINT.search(only))
        )
        if not strong or len(only) < 4:
            return None
    return tokens


def _noun_phrases(text: str) -> list[str]:
    """Yield candidate noun-phrase strings from a chunk of text."""
    phrases: list[str] = []
    # definitional subjects: "Binary search is defined as ..."
    for m in _DEF_RE.finditer(text):
        phrases.append(m.group(1).strip())

    # sliding windows over token runs, cut at punctuation
    for run in re.split(r"[.;:,()\[\]{}!?]", text):
        toks = _TOKEN_RE.findall(run)
        n = len(toks)
        for i in range(n):
            for size in (4, 3, 2, 1):
                if i + size > n:
                    continue
                window = toks[i : i + size]
                cleaned = _clean_phrase_tokens(window)
                if cleaned:
                    phrases.append(" ".join(cleaned))
    return phrases


class ConceptExtractor:
    def __init__(self, max_concepts: int = 40, min_chunks: int = 1):
        self.max_concepts = max_concepts
        self.min_chunks = min_chunks

    def extract(self, chunks: list[Chunk]) -> list[ConceptCandidate]:
        if len(chunks) < self.min_chunks:
            return []
        texts = [c.text for c in chunks]
        headings = " ".join((c.section_title or "") for c in chunks).lower()

        vocab_df: dict[str, int] = {}
        for t in texts:
            for phrase in {p.lower() for p in _noun_phrases(t)}:
                vocab_df[phrase] = vocab_df.get(phrase, 0) + 1
        if not vocab_df:
            return []

        many_chunks = len(chunks) >= 8
        vocabulary = [
            p
            for p, df in vocab_df.items()
            if df >= 2
            or " " in p
            or not many_chunks
            or any(w in headings for w in p.split())
        ]
        vocabulary = vocabulary[:4000] or list(vocab_df)[:4000]

        vectorizer = TfidfVectorizer(
            vocabulary=vocabulary, ngram_range=(1, 4), lowercase=True, sublinear_tf=True
        )
        try:
            tfidf = vectorizer.fit_transform(texts)
        except ValueError:
            return []
        terms = np.array(vectorizer.get_feature_names_out())
        col_max = np.asarray(tfidf.max(axis=0).todense()).ravel()
        col_df = np.asarray((tfidf > 0).sum(axis=0)).ravel()
        n_words = np.array([t.count(" ") + 1 for t in terms])
        heading_bonus = np.array(
            [1.4 if any(w in headings for w in t.split()) else 1.0 for t in terms]
        )
        # single bare words are rarely good concept names unless technical/proper
        single_penalty = np.array(
            [
                0.45
                if (n == 1 and not _TECH_HINT.search(t) and not _proper_in(t, texts))
                else 1.0
                for t, n in zip(terms, n_words, strict=True)
            ]
        )
        # recurrence-weighted salience with a clear preference for real phrases
        scores = (
            col_max
            * np.power(np.clip(col_df, 1, None), 0.7)
            * np.clip(1 + 0.5 * (n_words - 1), 1, 2.0)
            * heading_bonus
            * single_penalty
        )

        ranked = np.argsort(scores)[::-1]
        chosen: list[ConceptCandidate] = []
        chosen_tokens: list[set[str]] = []

        for idx in ranked:
            if scores[idx] <= 0:
                break
            term = terms[idx]
            token_set = set(term.split())
            subset_of_existing = False
            for j, prev in enumerate(chosen_tokens):
                if token_set == prev:
                    subset_of_existing = True
                    break
                if token_set < prev:  # a longer phrase already covers this one
                    subset_of_existing = True
                    break
                if prev < token_set:  # this phrase is richer: replace the shorter one
                    chosen.pop(j)
                    chosen_tokens.pop(j)
                    break
            if subset_of_existing:
                continue
            best_chunk = int(np.asarray(tfidf[:, idx].todense()).ravel().argmax())
            chunk = chunks[best_chunk]
            chosen.append(
                ConceptCandidate(
                    name=_display_name(term, chunk.text),
                    snippet=_best_sentence(chunk.text, term),
                    chunk_index=best_chunk,
                    source_page=chunk.page_number or chunk.slide_number,
                    source_section=chunk.section_title,
                    relevance_score=float(round(scores[idx] / (scores[ranked[0]] or 1.0), 4)),
                )
            )
            chosen_tokens.append(token_set)
            if len(chosen) >= self.max_concepts:
                break
        return chosen


def _proper_in(term: str, texts: list[str]) -> bool:
    """True if the term appears capitalised mid-sentence somewhere (proper/technical noun)."""
    pattern = re.compile(r"(?<=[a-z0-9] )" + re.escape(term.title()))
    return any(pattern.search(t) for t in texts)


def _best_sentence(text: str, term: str) -> str:
    sentences = sentence_split(text) or [text]
    term_low = term.lower()
    for sentence in sentences:
        if term_low in sentence.lower():
            return sentence[:400]
    return sentences[0][:400]


def _display_name(term: str, context: str) -> str:
    """Reuse the surface form as it appears in the text (preserves acronyms/casing)."""
    match = re.search(re.escape(term), context, re.IGNORECASE)
    surface = match.group(0).strip() if match else term
    if surface.islower():
        # Title-case but keep short function words lower ("order of growth")
        words = surface.split()
        return " ".join(
            w if (w in _FUNCTION_WORDS and i > 0) else w.capitalize()
            for i, w in enumerate(words)
        )
    return surface
