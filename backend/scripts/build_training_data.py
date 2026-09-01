"""Generate the synthetic *labelled* datasets used to train LectureLens models.

Lecture prose is highly templated (definitions, worked examples, theorems, step
lists, comparisons, code, background). We exploit that structure to build a
balanced training set from sentence templates + a domain term bank, then inject
realistic difficulty:

* shared "filler" clauses that appear across every class,
* blended sentences that carry cues for two classes at once,
* a small amount of label noise toward an adjacent class.

The result is separable but not trivially so, which makes the
sklearn-vs-PyTorch comparison in ``evaluate_models.py`` meaningful. This is
training data, not test data - evaluation uses a disjoint split.

Run::  python scripts/build_training_data.py
"""
from __future__ import annotations

import json
import random
from pathlib import Path

SEED = 20240501
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "training"

TERMS = [
    "binary search", "hash table", "quicksort", "the call stack", "a linked list",
    "dynamic programming", "the page table", "a semaphore", "gradient descent",
    "the bias-variance tradeoff", "a B-tree", "Dijkstra's algorithm", "TCP congestion control",
    "a virtual address", "the CAP theorem", "backpropagation", "a bloom filter",
    "amortised analysis", "a red-black tree", "the producer-consumer problem",
    "L2 regularisation", "a context switch", "the master theorem", "a priority queue",
    "a merge step", "reference counting", "a spin lock", "a suffix array",
]
EASY_TERMS = ["a variable", "a for loop", "an array", "an if statement", "a function call",
              "a string", "a boolean", "the print statement", "a comment", "an integer",
              "a list index", "the return keyword", "a whitespace character"]
HARD_TERMS = ["the amortised analysis of a Fibonacci heap", "lock-free concurrent hashing",
              "the KKT optimality conditions", "cache-oblivious matrix transposition",
              "Paxos leader election", "the expectation-maximisation derivation",
              "wait-free consensus hierarchies", "the polynomial hierarchy",
              "persistent data structure fat-node encoding", "the PCP theorem"]

FILLER = [
    "This idea comes up repeatedly later in the course.",
    "Keep the running time in mind as we go.",
    "We return to this point in the next lecture.",
    "It is worth pausing to make sure this is clear.",
    "The notation follows the textbook.",
]

TEMPLATES: dict[str, list[str]] = {
    "definition": [
        "{T} is defined as a technique that {X}.",
        "Formally, {T} refers to {X}.",
        "We say that {T} is a construct that {X}.",
        "{T}: a structure that {X}.",
        "The term {T} denotes the mechanism by which a program {X}.",
        "By definition, {T} is any method that {X}.",
    ],
    "example": [
        "For example, applying {T} to the list [5, 2, 9, 1] walks through three iterations.",
        "Consider {T}: suppose we start with n = 8 and trace what happens at each step.",
        "For instance, {T} is what your text editor's find command relies on.",
        "As a concrete example, {T} on the input 42 returns the value at position three.",
        "Take {T} and run it on a dictionary of ten thousand words to see the effect.",
        "Worked example: with {T} and array [3, 1, 2] the result after one pass is [1, 2, 3].",
    ],
    "theorem_or_rule": [
        "Theorem: {T} runs in O(log n) time in the worst case.",
        "Lemma: if the input to {T} is sorted, correctness follows by induction on the range.",
        "The invariant maintained by {T} is that the left portion is always fully processed.",
        "Property: {T} always terminates because a non-negative quantity strictly decreases.",
        "By the master theorem, {T} satisfies the stated asymptotic bound.",
        "Rule: {T} is correct only if the precondition on ordering holds.",
    ],
    "process": [
        "Step 1: initialise the bounds. Step 2: compute the midpoint. Step 3: recurse on one side.",
        "First, we sort the array. Then we repeatedly halve the interval until it is empty.",
        "The procedure for {T} is: pick a pivot, partition around it, then recurse on each part.",
        "Repeat the following until the queue is empty: pop the front node and relax its edges.",
        "Next, update the pointers; after that, free the removed node; finally, return.",
        "The algorithm proceeds in rounds: scan, update the best candidate, then advance.",
    ],
    "comparison": [
        "Unlike linear search, {T} needs sorted input but is far faster on large arrays.",
        "{T} versus a hash table: one keeps ordering, the other gives average constant lookup.",
        "Compared to quicksort, {T} has a better worst case but larger constant factors.",
        "In contrast to breadth-first search, {T} uses far less memory but can go deep.",
        "The tradeoff is clear: {T} is slower to build yet cheaper to query afterwards.",
        "Whereas the naive method rescans everything, {T} reuses previously computed work.",
    ],
    "implementation_detail": [
        "def search(a, x):\n    lo, hi = 0, len(a) - 1\n    while lo <= hi:\n        mid = (lo + hi) // 2",
        "The implementation stores child pointers in a fixed-size array of length two per node.",
        "In C, {T} is a struct holding a key plus two node pointers and a colour bit.",
        "Watch for integer overflow when computing mid = (lo + hi) // 2 inside {T}.",
        "The function returns -1 when the key is absent, so callers must check before indexing.",
        "Allocate the temporary buffer once outside the loop to avoid repeated heap traffic.",
    ],
    "background_information": [
        "This lecture introduces {T} and explains why it matters in real systems.",
        "Historically, {T} was first described decades ago and refined many times since.",
        "Over the next three weeks we will build the tools needed to analyse {T}.",
        "Before we begin, recall the prerequisites you need to follow the treatment of {T}.",
        "The motivation for {T} is the need to scale gracefully to very large inputs.",
        "Roadmap: today we motivate {T}; next time we prove the bound; then we benchmark it.",
    ],
}
FILLER_X = [
    "locates a target value by repeatedly dividing the search interval in half",
    "maps keys to array indices using a hash function and resolves collisions",
    "stores elements so the smallest can be retrieved in logarithmic time",
    "trades additional memory for asymptotically faster lookups",
    "maintains balance through rotations after every insertion and deletion",
    "reuses the solutions to overlapping subproblems instead of recomputing them",
]

# pairs (label, confusable_label): a blended sentence gets cues for both
CONFUSABLE = {
    "definition": "example",
    "example": "process",
    "theorem_or_rule": "comparison",
    "process": "implementation_detail",
    "implementation_detail": "process",
    "comparison": "theorem_or_rule",
    "background_information": "definition",
}
ADJACENT_NOISE = {
    "definition": "background_information",
    "example": "process",
    "theorem_or_rule": "comparison",
    "process": "example",
    "comparison": "theorem_or_rule",
    "implementation_detail": "process",
    "background_information": "definition",
}


def _fill(rng: random.Random, template: str) -> str:
    return template.format(T=rng.choice(TERMS), X=rng.choice(FILLER_X))


def _concept_rows(rng: random.Random, per_class: int) -> list[dict]:
    rows: list[dict] = []
    for label, templates in TEMPLATES.items():
        for _ in range(per_class):
            text = _fill(rng, rng.choice(templates))
            roll = rng.random()
            if roll < 0.14:  # blend a confusable class's cue in
                other = CONFUSABLE[label]
                text = f"{text} {_fill(rng, rng.choice(TEMPLATES[other]))}"
            elif roll < 0.30:
                text = f"{text} {rng.choice(FILLER)}"
            final_label = label
            if rng.random() < 0.06:  # adjacent-class label noise
                final_label = ADJACENT_NOISE[label]
            rows.append({"text": text, "label": final_label})
    rng.shuffle(rows)
    return rows


def _difficulty_rows(rng: random.Random, per_class: int) -> list[dict]:
    rows: list[dict] = []
    variants = {
        "easy": [
            "{T} is straightforward: it simply holds or names a single value you can read.",
            "You met {T} in week one; there is nothing subtle about it.",
            "{T} needs no maths — just remember the syntax and what it stands for.",
        ],
        "medium": [
            "{T} builds on earlier ideas; you must trace a few steps and hold one invariant in mind.",
            "Understanding {T} takes a diagram and a careful read, but no heavy proof.",
            "{T} has a couple of edge cases that trip people up on the first attempt.",
        ],
        "hard": [
            "{T} combines several non-obvious results; the proof uses amortisation and probabilistic bounds.",
            "{T} requires case analysis, a potential function, and comfort with asymptotic reasoning.",
            "Most students find {T} demanding: the derivation is long and every step matters.",
        ],
    }
    pools = {"easy": EASY_TERMS, "medium": TERMS, "hard": HARD_TERMS + TERMS[:8]}
    for label, templates in variants.items():
        for _ in range(per_class):
            term = rng.choice(pools[label])
            name = term.replace("a ", "").replace("an ", "").replace("the ", "").strip().title()
            text = rng.choice(templates).format(T=term)
            if rng.random() < 0.2:
                text = f"{text} {rng.choice(FILLER)}"
            final = label
            if rng.random() < 0.08:  # noise toward neighbouring difficulty
                final = {"easy": "medium", "medium": rng.choice(["easy", "hard"]), "hard": "medium"}[label]
            rows.append({"name": name, "text": text, "label": final})
    rng.shuffle(rows)
    return rows


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    concept_rows = _concept_rows(rng, per_class=110)
    difficulty_rows = _difficulty_rows(rng, per_class=200)
    (OUT_DIR / "concept_examples.jsonl").write_text(
        "\n".join(json.dumps(r) for r in concept_rows) + "\n"
    )
    (OUT_DIR / "difficulty_examples.jsonl").write_text(
        "\n".join(json.dumps(r) for r in difficulty_rows) + "\n"
    )
    print(
        f"Wrote {len(concept_rows)} concept rows and {len(difficulty_rows)} difficulty rows "
        f"to {OUT_DIR}"
    )


if __name__ == "__main__":
    main()
