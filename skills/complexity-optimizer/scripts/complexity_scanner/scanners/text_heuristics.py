"""Line-based regex heuristics for languages without an AST scanner (low confidence).

Scopes are tracked by indentation: a loop or function stays open while the following lines are
indented deeper than its header. String literals and comments are blanked out first so words
inside them ("for" in a test name, a URL) never match.
"""

import re
from dataclasses import dataclass

from ..findings import MODULE_SCOPE, Finding
from .naming import SEQUENTIAL_NAME_RE, is_batch_name, is_constant_name, is_hashed_name, is_retry_name
from .render_path import RENDER_SUFFIXES, RENDER_TRANSFORM_RE, render_path_lines

STRING_RE = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`')
TEMPLATE_STRING_SUFFIXES = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go"}
HASH_COMMENT_SUFFIXES = {".py", ".rb", ".r", ".R", ".jl", ".ex", ".exs"}
COMMENT_PREFIXES = ("//", "#", "*", "/*")
# Lines starting with these continue a multi-line signature or call instead of closing scopes.
CONTINUATION_PREFIXES = (")", "]", "})", "}]", "}:")
IDENT_RE = re.compile(r"[A-Za-z_$][\w$]*")

# -- loops --------------------------------------------------------------------

KEYWORD_LOOP_RE = re.compile(r"^(?:\}\s*)?(?:[A-Za-z_$][\w$]*\s*:\s*)?(?:(for|foreach|while|until)\b(?!\s*[:=.,)])|(loop|do)\s*\{)")
CALL_LOOP_RE = re.compile(
    r"\.(forEach|map|flatMap|filter|reduce|reduceRight|some|every|find|findIndex|findLast|findLastIndex|any|for_each|position"
    r"|Select|SelectMany|Where|Any|All|ForEach|First|FirstOrDefault|Single|SingleOrDefault|Last|LastOrDefault)\s*\(|\bEnum\.(\w+)\s*\("
)
BLOCK_LOOP_RE = re.compile(
    r"\.(each\w*|map|flat_map|flatMap|collect|select|filter|reject|detect|find|forEach|times|any\?|all\?|sum|group_by|sort_by|reduce|fold|inject)"
    r"\s*(?:\([^)]*\)\s*)?(?:\{|do\b)"
)
ACCUMULATOR_METHODS = {"reduce", "reduceRight", "fold", "inject"}
# Kotlin `it` and Swift `$0` name the element of a block without explicit parameters.
IMPLICIT_BLOCK_PARAMS = {"it", "$0"}
CALLBACK_PARAMS_RE = re.compile(r"\s*(?:async\s+)?(?:\(([^)]*)\)|\|([^|]*)\||([A-Za-z_$][\w$]*(?:\s*,\s*[A-Za-z_$][\w$]*)*)\s*(?:=>|->))")
FOR_EACH_RE = re.compile(
    r"\bfor(?:each)?\s*(?:await\s*)?\(?\s*(?:const|let|var|val|mut|auto|final)?\s*([\w$\[\]{},\s:]+?)\s+(?:of|in)\s+&?(?:mut\s+)?([A-Za-z_$][\w$]*)"
)
GO_RANGE_RE = re.compile(r"\bfor\s+([\w\s,]+?)\s*:?=\s*range\s+&?([A-Za-z_]\w*)")
C_STYLE_FOR_RE = re.compile(r"\bfor\s*\(\s*(?:let|var|int|long|auto|size_t|unsigned)?\s*([A-Za-z_$][\w$]*)\s*=")
JAVA_FOREACH_RE = re.compile(r"\bfor\s*\(\s*(?:final\s+)?[\w<>\[\],.?\s]+?\s+([A-Za-z_$][\w$]*)\s*:\s*([A-Za-z_$][\w$]*)")
CHAIN_ROOT_RE = re.compile(r"([A-Za-z_$][\w$]*)(?:\s*\??\.\s*[\w$]+|\[[^\]]*\]|\(\s*\))*\s*\??\s*$")
# The root is found with an end-anchored search, which retries from every column; a bounded tail
# keeps that linear per line (receiver chains are far shorter than this).
CHAIN_ROOT_WINDOW = 160
WRAPPED_ROOT_RE = re.compile(r"\b(?:Object\.(?:entries|values|keys)|Array\.from)\(\s*([A-Za-z_$][\w$]*)[^()]*\)\s*\??\s*$")
# `.find({ where })` or `.filter("x")` take options, not a callback: a query builder call, not a loop.
NON_CALLBACK_ARG_RE = re.compile(r"\s*[{\[)\"\d]")
# `return await x()` in a for body leaves the loop (inside a callback it only ends that call).
EXITS_LOOP_RE = re.compile(r"(?:^|[\s;{)])(?:return|throw)\s")
# while loops are usually pagination or queue consumers: one call per page/message is the design.
PER_ITEM_LOOP_KEYWORDS = {"for", "foreach", ""}

# -- patterns inside loops -----------------------------------------------------

# `.find(` also opens a callback loop; ranking keeps the stronger finding per line.
MEMBERSHIP_RE = re.compile(
    r'\.(?:includes|indexOf|lastIndexOf|find|findIndex|findLast|contains|Contains|include\?)\s*\((?!\s*"")|\bin_array\s*\('
)
# Declarations that tell a name's collection type; the latest one seen wins, so `banned: Set<..>`
# in one method doesn't hide `banned: List<..>` in the next. contains/has on sets and maps is O(1).
HASHED_DECLARATION_RE = re.compile(
    r"\b([A-Za-z_]\w*)\s*:\s*&?(?:mut\s+)?(?:Readonly)?(?:Hash|BTree|Mutable|Linked|Sorted|Tree|ReadonlySet|Readonly)?(?:Set|Map)\s*<"
    r"|\b(?:Hash|Tree|Linked|Sorted|Concurrent)?(?:Set|Map|Dictionary|HashSet)\s*<[^>]*>\s+([A-Za-z_]\w*)"
    r"|\b(?:const|let|var|val)\s+([A-Za-z_]\w*)\s*(?::[^=]+)?=\s*(?:new\s+)?(?:Hash|Mutable|Linked)?(?:Set|Map)\b"
    r"|\b([A-Za-z_]\w*)\s*:?=\s*(?:make\(\s*)?map\["
    r"|\b([A-Za-z_]\w*)\s+map\["
)
COLLECTION_HINT_RE = re.compile(r"Set|Map|map\[|\[\]|List|Array|Vec|Dictionary|listOf|arrayOf|Seq|Iterable|Enumerable|=\s*\[")
LINEAR_DECLARATION_RE = re.compile(
    r"\b([A-Za-z_]\w*)\s*:\s*&?(?:mut\s+)?(?:readonly\s+)?(?:Vec|List|Array|ReadonlyArray|MutableList|Seq|Iterable|IEnumerable|IList)\s*<"
    r"|\b([A-Za-z_]\w*)\s*:\s*(?:readonly\s+)?[\w.]+(?:<[^>]*>)?\[\]"
    r"|\b(?:List|ArrayList|LinkedList|IEnumerable|IList|ICollection|Collection|Iterable|Seq)\s*<[^>]*>\s+([A-Za-z_]\w*)"
    r"|\b(?:const|let|var|val)\s+([A-Za-z_]\w*)\s*(?::[^=]+)?=\s*(?:\[|new\s+Array\b|Array\.|listOf|mutableListOf|arrayOf)"
    r"|\b([A-Za-z_]\w*)\s*:?=\s*(?:make\(\s*)?\[\]"
    r"|\b([A-Za-z_]\w*)\s+\[\]\w"
)
SORT_RE = re.compile(
    r"\.(?:sort|toSorted|sortBy|sort_by)\s*[\({]|\bsorted\s*\(|\bsort\.(?:Slice|SliceStable|Sort|Strings|Ints)\s*\(|\bslices\.Sort(?:Func|StableFunc)?\s*\(|\bsort\s*\("
)
QUERY_IN_LOOP_RE = re.compile(
    r"\bfetch\s*\(|\baxios(?:\.\w+)?\s*\(|\.(?:query|findMany|findFirst|findOne|findOneBy|findUnique|findBy|find_by|findAll|findAndCount|getMany|getOne|getRawMany)\s*\("
    r"|\b(?:db|database|client|session|conn|connection|cursor|api|http|httpService|repo|repository|knex|prisma|supabase|requests|redis"
    r"|queryRunner|manager|em|dataSource|s3|\w*(?:Repository|Repo|Client|Dao))\.\w+\s*\(",
    re.IGNORECASE,
)
QUERY_RECEIVER_RE = re.compile(r"([A-Za-z_$][\w$]*)\.\w+\s*\($")
AWAIT_RE = re.compile(r"\bawait\b")
FOR_AWAIT_RE = re.compile(r"\bfor\s+await\b")
BATCH_AWAIT_RE = re.compile(r"\bPromise\.(?:all|allSettled|any|race)\b|\b(?:sleep|delay|setTimeout|wait|once)\s*\(|\bgather\s*\(")
SELF_REBUILD_RE = re.compile(r"\b([A-Za-z_$][\w$]*)\s*=\s*(?:\[\s*\.\.\.\s*\1\b|\{\s*\.\.\.\s*\1\b|\1\.concat\s*\()")
LIST_SHIFT_RE = re.compile(
    r"\.(?:shift|unshift)\s*\(|\.remove\(\s*0\s*\)|\.RemoveAt\(\s*0\s*\)|\.(?:add|insert|Insert)\(\s*0\s*,|\.splice\(\s*0\s*,"
)
DEEP_COPY_RE = re.compile(r"\bJSON\.parse\(\s*JSON\.stringify\(|\bstructuredClone\s*\(|\bcloneDeep\s*\(|\bdeepcopy\s*\(")
REGEX_COMPILE_RE = re.compile(
    r"\bnew\s+RegExp\s*\(|\bPattern\.compile\s*\(|\bregexp\.(?:Must)?Compile\s*\(|\bRegex::new\s*\(|\bnew\s+Regex\s*\(|\bRegexp\.new\s*\("
)
PER_ITERATION_PATTERNS = [
    ("list-shift-in-loop", LIST_SHIFT_RE),
    ("deep-copy-in-loop", DEEP_COPY_RE),
    ("regex-compile-in-loop", REGEX_COMPILE_RE),
]

# Languages where `s += x` on an immutable string copies the whole string (JS engines and
# CPython optimize this case, Swift/Rust/C++ strings are mutable buffers).
IMMUTABLE_STRING_SUFFIXES = {".java", ".kt", ".kts", ".scala", ".cs", ".go"}
STRING_DECLARATION_RE = re.compile(
    r"\b(?:String|string)\s+([A-Za-z_]\w*)\s*[=;]"
    r"|\b(?:var|val)\s+([A-Za-z_]\w*)\s*(?::\s*String\s*)?=\s*(?:\"\"|String\.Empty|string\.Empty)"
    r"|\bvar\s+([A-Za-z_]\w*)\s+string\b"
    r"|\b([A-Za-z_]\w*)\s*:=\s*\"\""
)

# -- enclosing function names --------------------------------------------------

FUNCTION_MODIFIERS = r"(?:(?:public|private|protected|internal|static|async|override|final|abstract|virtual|readonly|export|default)\s+)"
FUNCTION_RE = re.compile(
    r"\bfunction\s*\*?\s*([A-Za-z_$][\w$]*)\s*[<(]"
    r"|\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*(?::[^=]+)?=\s*(?:async\s+)?(?:function\b|\([^)]*\)[^=]*=>|[A-Za-z_$][\w$]*\s*=>)"
    r"|\b(?:def|fn|func|fun)\s+(?:\([^)]*\)\s*)?([A-Za-z_][\w!?]*)"
    rf"|^{FUNCTION_MODIFIERS}*(?:[\w<>\[\],.?]+\s+)?([A-Za-z_$][\w$]*)\s*\([^;]*\)\s*(?::\s*[^{{;=]+)?(?:throws\s+[\w.,\s]+)?\{{\s*$"
    # `private async load(` / `async run(input?: {`: a modifier before `name(` means a declaration, never a call.
    rf"|^{FUNCTION_MODIFIERS}+(?:[\w<>\[\],.?]+\s+)?([A-Za-z_$][\w$]*)\s*(?:<[^>]*>)?\s*\("
    r"|^(constructor)\s*\("
)
CONTROL_WORDS = {
    "if",
    "for",
    "foreach",
    "while",
    "switch",
    "catch",
    "with",
    "return",
    "function",
    "else",
    "do",
    "try",
    "until",
    "unless",
    "using",
    "lock",
}


@dataclass
class TextLoop:
    indent: int
    keyword: str  # "for", "while", ... for keyword loops; "" for callback loops
    targets: set[str]  # names bound to the current element
    counts: bool  # False when it walks an outer loop's element (`for (const item of order.items)`)
    accumulator: str = ""
    keeps_open: bool = True  # False when a callback closes on its own line
    start: int = 0  # column of the callback method, so a line's own `.find(` isn't "inside" itself
    batched: bool = False


def code_only(line: str, in_template: bool, suffix: str) -> tuple[str, bool]:
    """Blank out string literals and trailing comments; track multi-line template strings."""
    if in_template:
        end = line.find("`")
        if end == -1:
            return "", True
        line, in_template = line[end + 1 :], False
    line = STRING_RE.sub('""', line)
    if suffix in TEMPLATE_STRING_SUFFIXES:
        opening = line.find("`")
        if opening != -1:
            line, in_template = line[:opening], True
    comment = line.find("#" if suffix in HASH_COMMENT_SUFFIXES else "//")
    if comment != -1:
        line = line[:comment]
    return line, in_template


def chain_root(prefix: str) -> str:
    """Root variable of the expression that ends `prefix`: `order.items` -> "order"."""
    tail = prefix[-CHAIN_ROOT_WINDOW:]
    match = WRAPPED_ROOT_RE.search(tail) or CHAIN_ROOT_RE.search(tail)
    return match.group(1) if match else ""


def function_name(code: str) -> str:
    match = FUNCTION_RE.search(code)
    if not match:
        return ""
    name = next(group for group in match.groups() if group)
    return "" if name in CONTROL_WORDS else name


def make_loop(indent: int, keyword: str, targets: set[str], root: str, open_targets: set[str], **extra) -> TextLoop:
    names = {name for name in targets | {root} if name}
    # Walking an outer element, a fixed UPPER_CASE collection, or retry attempts doesn't multiply the cost.
    counts = root not in open_targets and not is_constant_name(root) and not any(is_retry_name(name) for name in names)
    return TextLoop(indent, keyword, targets, counts, batched=any(is_batch_name(name) for name in names), **extra)


def parse_loop(code: str, indent: int, open_targets: set[str], chain_head: str) -> TextLoop | None:
    """The loop opened on this line, if any. `chain_head` is the line a `.method(` continuation belongs to."""
    keyword = KEYWORD_LOOP_RE.match(code)
    if keyword:
        header = FOR_EACH_RE.search(code) or GO_RANGE_RE.search(code) or JAVA_FOREACH_RE.search(code)
        if header:
            targets, root = set(IDENT_RE.findall(header.group(1))), header.group(2)
        else:
            counter = C_STYLE_FOR_RE.search(code)
            targets, root = ({counter.group(1)} if counter else set()), ""
        return make_loop(indent, keyword.group(1) or keyword.group(2), targets, root, open_targets)

    call = CALL_LOOP_RE.search(code) or BLOCK_LOOP_RE.search(code)
    if not call or (call.re is CALL_LOOP_RE and NON_CALLBACK_ARG_RE.match(code, call.end())):
        return None
    params = CALLBACK_PARAMS_RE.match(code, call.end())
    param_names = IDENT_RE.findall(next((group for group in params.groups() if group), "")) if params else []
    targets = set(param_names) or (IMPLICIT_BLOCK_PARAMS if call.re is BLOCK_LOOP_RE else set())
    accumulator = param_names[0] if (call.group(1) or "") in ACCUMULATOR_METHODS and param_names else ""
    rest = code[call.start() :]
    keeps_open = rest.count("(") > rest.count(")") or code.rstrip().endswith(("{", "=>", "->", "do", "|"))
    prefix = code[: call.start()]
    root = chain_root(prefix) if prefix.strip() else chain_root(chain_head)
    return make_loop(indent, "", targets, root, open_targets, accumulator=accumulator, keeps_open=keeps_open, start=call.start())


def loop_depth(loops: list[TextLoop]) -> int:
    return sum(loop.counts for loop in loops)


def loop_targets(loops: list[TextLoop]) -> set[str]:
    return {target for loop in loops for target in loop.targets}


def is_per_item(loops: list[TextLoop]) -> bool:
    """Inside a loop that makes one call per element (not a while/pagination loop, not a batch loop)."""
    innermost = next((loop for loop in reversed(loops) if loop.counts), None)
    return innermost is not None and innermost.keyword in PER_ITEM_LOOP_KEYWORDS and not innermost.batched


def is_single_shot(code: str, enclosing: list[TextLoop]) -> bool:
    """The call on this line leaves the loop, or handles a whole page/chunk (`const page = await ...`,
    `save(chunk)`), so it isn't repeated per element."""
    leaves_loop = bool(enclosing) and bool(enclosing[-1].keyword) and EXITS_LOOP_RE.search(code) is not None
    return leaves_loop or any(is_batch_name(name) for name in IDENT_RE.findall(code))


def is_io_call(code: str, match: re.Match) -> bool:
    """A query match whose receiver isn't a map named after its key (`phaseByClient.get(id)`)."""
    receiver = QUERY_RECEIVER_RE.search(match.group())
    return not (receiver and is_hashed_name(receiver.group(1)))


def is_sequential_await(code: str, enclosing: list[TextLoop], function: str) -> bool:
    """`await` directly in a for-loop body: not inside a callback, a batch, a sleep, or a function meant to be sequential."""
    return (
        bool(enclosing[-1].keyword)
        and AWAIT_RE.search(FOR_AWAIT_RE.sub("", code)) is not None
        and not BATCH_AWAIT_RE.search(code)
        and not SEQUENTIAL_NAME_RE.search(function)
    )


def is_quadratic_accumulation(code: str, active: list[TextLoop]) -> bool:
    if SELF_REBUILD_RE.search(code):
        return True
    for loop in active:
        if loop.accumulator:
            acc = re.escape(loop.accumulator)
            # `...acc` (JS spread), `acc.concat(` / Ruby `acc.merge(` (new copies), `acc + [x]`.
            if re.search(rf"\.\.\.\s*{acc}\b|\b{acc}\.(?:concat|merge)\s*\(|\b{acc}\s*\+\s*\[", code):
                return True
    return False


def is_string_concat(code: str, string_names: set[str]) -> bool:
    match = re.search(r"\b([A-Za-z_]\w*)\s*(?:\+=|=\s*\1\s*\+)", code)
    return bool(match) and match.group(1) in string_names


@dataclass
class FileContext:
    """Facts collected from the whole file before the line-by-line pass."""

    string_names: set[str]  # variables declared as immutable strings
    render_lines: set[int]


def is_linear_receiver(name: str, hashed: dict[str, bool]) -> bool:
    """False when the searched collection is known or named to be a set/map, or is a fixed UPPER_CASE constant."""
    return not hashed.get(name, is_hashed_name(name)) and not is_constant_name(name)


def line_findings(
    code: str, enclosing: list[TextLoop], new_loop: TextLoop | None, context: FileContext, hashed: dict[str, bool], function: str
) -> list[tuple[str, int]]:
    """(kind, loop depth) pairs for one line of code that runs inside at least one loop."""

    def loops_at(position: int) -> list[TextLoop]:
        # Code after a callback opened on this line runs inside it: `users.filter(u => ids.includes(u.id))`.
        # A keyword loop's header (its iterable) is evaluated once, outside the loop.
        if new_loop and not new_loop.keyword and position > new_loop.start:
            return enclosing + [new_loop]
        return enclosing

    found = []
    if new_loop and new_loop.counts and loop_depth(enclosing):
        found.append(("nested-loop", loop_depth(enclosing) + 1))
    membership = MEMBERSHIP_RE.search(code)
    if membership:
        loops = loops_at(membership.start())
        receiver = chain_root(code[: membership.start()])
        if loop_depth(loops) and receiver not in loop_targets(loops) and is_linear_receiver(receiver, hashed):
            found.append(("membership-in-loop", loop_depth(loops)))
    sort = SORT_RE.search(code)
    if sort and loop_depth(loops_at(sort.start())) and chain_root(code[: sort.start()]) not in loop_targets(loops_at(sort.start())):
        found.append(("sort-in-loop", loop_depth(loops_at(sort.start()))))
    query = QUERY_IN_LOOP_RE.search(code)
    single_shot = is_single_shot(code, enclosing)
    if query and is_io_call(code, query) and is_per_item(loops_at(query.start())) and not single_shot:
        found.append(("io-or-query-in-loop", loop_depth(loops_at(query.start()))))
    if loop_depth(enclosing) and is_per_item(enclosing) and not single_shot and is_sequential_await(code, enclosing, function):
        found.append(("await-in-loop", loop_depth(enclosing)))
    for kind, pattern in PER_ITERATION_PATTERNS:
        match = pattern.search(code)
        if match and loop_depth(loops_at(match.start())):
            found.append((kind, loop_depth(loops_at(match.start()))))
    if loop_depth(enclosing) and is_string_concat(code, context.string_names):
        found.append(("string-concat-in-loop", loop_depth(enclosing)))
    active = enclosing + [new_loop] if new_loop else enclosing
    if loop_depth(active) and is_quadratic_accumulation(code, active):
        found.append(("quadratic-accumulation", loop_depth(active)))
    return found


def declared_names(lines: list[str], pattern: re.Pattern) -> set[str]:
    names = set()
    for line in lines:
        for match in pattern.finditer(STRING_RE.sub('""', line)):
            names.add(next(group for group in match.groups() if group))
    return names


def collection_declarations(code: str) -> list[tuple[int, str, bool]]:
    """(column, name, is_hashed) for every set/map or list/array declaration on the line."""
    if not COLLECTION_HINT_RE.search(code):
        return []
    found = []
    for pattern, hashed in ((HASHED_DECLARATION_RE, True), (LINEAR_DECLARATION_RE, False)):
        for match in pattern.finditer(code):
            found.append((match.start(), next(group for group in match.groups() if group), hashed))
    return sorted(found)


def file_context(lines: list[str], suffix: str) -> FileContext:
    return FileContext(
        string_names=declared_names(lines, STRING_DECLARATION_RE) if suffix in IMMUTABLE_STRING_SUFFIXES else set(),
        render_lines=render_path_lines(lines) if suffix in RENDER_SUFFIXES else set(),
    )


def scan_text(path: str, suffix: str, lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    loops: list[TextLoop] = []
    functions: list[tuple[int, str]] = []
    in_template = False
    context = file_context(lines, suffix)
    hashed: dict[str, bool] = {}
    chain_head = ""  # last line that didn't start with `.`: where a multi-line chain begins
    chain_looped = False  # an earlier link of the current multi-line chain already iterates

    for idx, raw in enumerate(lines, start=1):
        code, in_template = code_only(raw, in_template, suffix)
        stripped = code.strip()
        if not stripped or stripped.startswith(COMMENT_PREFIXES):
            continue
        indent = len(raw) - len(raw.lstrip(" \t"))
        if not stripped.startswith(CONTINUATION_PREFIXES):
            loops = [loop for loop in loops if loop.indent < indent]  # complexity: ignore (bounded by nesting depth)
            functions = [frame for frame in functions if frame[0] < indent]  # complexity: ignore (bounded by nesting depth)
        name = function_name(stripped)
        if name:
            functions.append((indent, name))
        function = functions[-1][1] if functions else MODULE_SCOPE

        for _, declared, is_hashed in collection_declarations(stripped):  # complexity: ignore (matches on one line)
            hashed[declared] = is_hashed
        new_loop = parse_loop(stripped, indent, loop_targets(loops), chain_head)
        if not stripped.startswith("."):
            chain_head, chain_looped = stripped, False
        elif new_loop and chain_looped:
            # `.filter(...)` then `.map(...)`: one more pass over the same collection, already reported.
            new_loop.counts = False
        chain_looped = chain_looped or new_loop is not None
        found = line_findings(stripped, loops, new_loop, context, hashed, function) if loops or new_loop else []
        if idx in context.render_lines and RENDER_TRANSFORM_RE.search(stripped):
            found.append(("render-derived-work", 1))
        findings += [Finding(path, idx, function, kind, max(1, depth), "low") for kind, depth in found]  # complexity: ignore (per line)
        if new_loop and new_loop.keeps_open:
            loops.append(new_loop)

    return findings
