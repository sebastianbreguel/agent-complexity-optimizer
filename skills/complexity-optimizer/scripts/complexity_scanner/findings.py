"""What a finding is, and the catalog of patterns the scanners can report."""

from dataclasses import dataclass

MODULE_SCOPE = "<module>"
SEVERITY_ORDER = {"high": 0, "medium": 1, "info": 2}


@dataclass(frozen=True)
class Kind:
    severity: str
    weight: int  # relative cost of the pattern; ranking multiplies it by loop depth and confidence
    message: str
    suggestion: str


KINDS = {
    "io-or-query-in-loop": Kind(
        "high",
        8,
        "Database/API call inside a loop (possible N+1).",
        "Batch or preload (bulk fetch by IDs, join, dataloader) while preserving auth, filters, ordering, and error handling.",
    ),
    "await-in-loop": Kind(
        "high",
        7,
        "Sequential await inside a for loop: each iteration waits for the previous one.",
        "If iterations are independent, run them together (Promise.all / asyncio.gather) with a concurrency limit; "
        "keep it sequential when order, transactions, or rate limits require it.",
    ),
    "quadratic-accumulation": Kind(
        "high",
        6,
        "Collection copied on every iteration (spread / concat / pd.concat into itself): O(n^2) total.",
        "Mutate one accumulator (push, append, assign a key), or collect the parts and concatenate once after the loop.",
    ),
    "nested-loop": Kind(
        "high",
        5,
        "Loop over an independent collection inside another loop: O(n*m) or worse.",
        "Index the inner collection once (map/set/grouping), or use sort + two pointers / sweep line for pairwise work.",
    ),
    "sort-in-loop": Kind(
        "high",
        5,
        "Sort inside a loop repeats O(n log n) work on every iteration.",
        "Sort once outside the loop, keep a heap, or use binary insertion if intermediate order is needed.",
    ),
    "list-shift-in-loop": Kind(
        "medium",
        4,
        "Front insert/remove on an array list (pop(0), insert(0, ...), shift(), unshift(), remove(0)) inside a loop "
        "shifts every element: O(n^2).",
        "Use a deque (collections.deque, ArrayDeque, VecDeque) or iterate by index.",
    ),
    "dataframe-row-loop": Kind(
        "medium",
        4,
        "Row-by-row pandas iteration (iterrows / itertuples / apply(axis=1)) runs Python code per row.",
        "Vectorize with column operations, merge/groupby, or np.where; itertuples is the least-bad fallback.",
    ),
    "string-concat-in-loop": Kind(
        "medium",
        4,
        "String built with += inside a loop; immutable strings are copied on every append: O(n^2).",
        "Use StringBuilder (Java/Kotlin), StringBuilder/string.Join (C#), strings.Builder (Go), or collect parts and join once.",
    ),
    "deep-copy-in-loop": Kind(
        "medium",
        3,
        "Deep copy (deepcopy / JSON.parse(JSON.stringify(...)) / structuredClone) inside a loop copies the whole object graph per iteration.",
        "Copy once before the loop, copy only the fields that change, or use immutable updates on the touched path.",
    ),
    "regex-compile-in-loop": Kind(
        "medium",
        2,
        "Regular expression compiled inside a loop (new RegExp / Pattern.compile / regexp.MustCompile).",
        "Compile it once outside the loop (module constant or field) and reuse it.",
    ),
    "membership-in-loop": Kind(
        "medium",
        3,
        "Linear search (in / includes / indexOf / find / index / count / remove) inside a loop: O(n*m).",
        "Build a set/dict/Map once before the loop if equality semantics allow it.",
    ),
    "repeated-scan": Kind(
        "medium",
        3,
        "filter()/map() inside a loop re-scans a collection on every iteration.",
        "Precompute an index or grouping, or combine passes.",
    ),
    "render-derived-work": Kind(
        "medium",
        2,
        "Collection transform in a likely UI component render path (runs on every render).",
        "For large collections, memoize the derived value, derive it server-side, or virtualize the list.",
    ),
    "parse-error": Kind(
        "info",
        0,
        "Python file could not be parsed; fell back to textual scanning.",
        "Inspect manually if this file is on a hot path.",
    ),
}


@dataclass
class Finding:
    path: str
    line: int
    function: str
    kind: str
    depth: int  # loops (that grow with input) enclosing the pattern
    confidence: str  # "high" for AST findings, "low" for regex heuristics
    severity: str = ""
    score: float = 0.0
    context: str = "app"  # "one-off" for migrations, seeds, scripts
    status: str = ""  # "new" or "known" when compared with a baseline
    code: str = ""
    message: str = ""
    suggestion: str = ""
