"""Python scanner built on the stdlib AST (high confidence).

Loop depth only counts loops that grow with input: loops over small literals / range(<=10) and
walks over an outer loop's element (`for cell in row`) don't multiply the cost.
"""

import ast
from dataclasses import dataclass

from ..findings import MODULE_SCOPE, Finding
from .naming import SEQUENTIAL_NAME_RE, is_batch_name, is_constant_name, is_hashed_name, is_retry_name, name_tokens

# Calls that are I/O whatever the receiver; query-like names need a client-looking receiver or a
# SQL string argument; generic verbs (get, filter, save, ...) always need a client-looking receiver.
IO_CALL_NAMES = {"fetch", "urlopen"}
STRONG_QUERY_NAMES = {"query", "execute", "executemany", "find_one", "find_many", "find_unique", "find_by", "scalars", "scalar"}
GENERIC_QUERY_NAMES = {
    "find",
    "select",
    "where",
    "filter",
    "exclude",
    "get",
    "post",
    "put",
    "patch",
    "delete",
    "request",
    "all",
    "first",
    "last",
    "count",
    "exists",
    "save",
    "create",
    "update",
    "insert",
    "upsert",
    "send",
    "get_object",
    "put_object",
}
CLIENT_RECEIVER_HINTS = {
    "db",
    "database",
    "session",
    "client",
    "conn",
    "connection",
    "cursor",
    "requests",
    "http",
    "httpx",
    "api",
    "repo",
    "repository",
    "collection",
    "engine",
    "orm",
    "supabase",
    "prisma",
    "objects",
    "redis",
    "s3",
    "dao",
}
CONSTANT_TIME_CONSTRUCTORS = {"set", "frozenset", "dict", "Counter", "defaultdict", "OrderedDict", "range"}
CONSTANT_TIME_METHODS = {"keys"}
CONSTANT_TIME_TYPES = {
    "set",
    "Set",
    "frozenset",
    "FrozenSet",
    "AbstractSet",
    "MutableSet",
    "dict",
    "Dict",
    "Mapping",
    "MutableMapping",
    "Counter",
    "defaultdict",
    "DefaultDict",
    "OrderedDict",
    "KeysView",
}
OPTIONAL_WRAPPERS = {"Optional", "Union", "None"}
# Wrappers that keep the iterable's root: `enumerate(row)` still walks `row`.
ITERABLE_WRAPPERS = {"list", "tuple", "enumerate", "sorted", "reversed", "iter"}
BOUNDED_ITERATION_LIMIT = 10
SHORT_STRING_LIMIT = 32
ROW_ITERATORS = {"iterrows", "itertuples"}
ACCUMULATING_CALLS = {"concat", "concatenate", "append", "vstack", "hstack", "union"}
BATCH_AWAIT_NAMES = {"gather", "sleep", "wait", "as_completed"}
# Their `key=` lambda runs once per element, so its body is effectively inside a loop.
KEY_FUNCTION_CALLS = {"sorted", "sort", "min", "max", "groupby", "nlargest", "nsmallest"}
DEEP_COPY_NAMES = {"deepcopy"}


@dataclass
class LoopFrame:
    kind: str  # "for", "while", "comprehension", "lambda"
    targets: set[str]
    counts: bool
    batched: bool = False  # walks chunks/batches/pages: one call per iteration is the intended batching


def call_name(func: ast.AST) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def receiver_name(func: ast.AST) -> str:
    """Innermost attribute receiver: `self.db.get(...)` -> "db", `requests.get(...)` -> "requests"."""
    if isinstance(func, ast.Attribute):
        if isinstance(func.value, ast.Name):
            return func.value.id
        if isinstance(func.value, ast.Attribute):
            return func.value.attr
    return ""


def root_name(node: ast.AST) -> str:
    """Base variable of an expression: `row.cells[0]` -> "row", `enumerate(row.items())` -> "row"."""
    while True:
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ITERABLE_WRAPPERS and node.args:
                node = node.args[0]
            elif isinstance(node.func, ast.Attribute):
                node = node.func.value
            else:
                return ""
        elif isinstance(node, (ast.Attribute, ast.Subscript, ast.Starred)):
            node = node.value
        elif isinstance(node, ast.BoolOp):  # `row.tags or []`
            node = node.values[0]
        elif isinstance(node, ast.IfExp):
            node = node.body
        elif isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):  # `sorted(d for d in names)`
            node = node.generators[0].iter
        elif isinstance(node, ast.Name):
            return node.id
        else:
            return ""


def assigned_names(target: ast.AST) -> set[str]:
    return {node.id for node in ast.walk(target) if isinstance(node, ast.Name)}


def identifiers(node: ast.AST, include_callee: bool = True) -> set[str]:
    """Every variable, attribute and called name in `node`: `range(0, n, self.batch_size)` -> {"range", "n", "self", "batch_size"}."""
    skip = {id(node.func)} if isinstance(node, ast.Call) and not include_callee else set()
    names = set()
    for child in ast.walk(node):
        if id(child) in skip:
            continue
        if isinstance(child, ast.Name):
            names.add(child.id)
        elif isinstance(child, ast.Attribute):
            names.add(child.attr)
    return names


def is_bounded_iterable(node: ast.AST) -> bool:
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id == "enumerate" and node.args:
            return is_bounded_iterable(node.args[0])
        bounds = [a.value for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, int)]
        if node.func.id == "range" and bounds and len(bounds) == len(node.args):
            try:
                return len(range(*bounds)) <= BOUNDED_ITERATION_LIMIT
            except ValueError:
                return False
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return len(node.elts) <= BOUNDED_ITERATION_LIMIT
    if isinstance(node, (ast.Name, ast.Attribute)):
        return is_constant_name(node.id if isinstance(node, ast.Name) else node.attr)
    return isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) <= SHORT_STRING_LIMIT


def is_string_literal(node: ast.AST) -> bool:
    return isinstance(node, ast.JoinedStr) or (isinstance(node, ast.Constant) and isinstance(node.value, str))


def is_zero(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value == 0


def outer_type_names(annotation: ast.AST) -> set[str]:
    """`dict[str, list[int]] | None` -> {"dict", "None"}; `Optional[set[str]]` -> {"set"}."""
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        return outer_type_names(annotation.left) | outer_type_names(annotation.right)
    if isinstance(annotation, ast.Subscript):
        outer = outer_type_names(annotation.value)
        if outer & {"Optional", "Union"}:
            inner = annotation.slice.elts if isinstance(annotation.slice, ast.Tuple) else [annotation.slice]
            return set().union(*(outer_type_names(node) for node in inner))
        return outer
    if isinstance(annotation, ast.Name):
        return {annotation.id}
    if isinstance(annotation, ast.Attribute):
        return {annotation.attr}
    if isinstance(annotation, ast.Constant) and annotation.value is None:
        return {"None"}
    return set()


def is_constant_time_annotation(annotation: ast.AST | None) -> bool:
    names = outer_type_names(annotation) - OPTIONAL_WRAPPERS if annotation is not None else set()
    return bool(names) and names <= CONSTANT_TIME_TYPES


def is_constant_time_value(node: ast.AST, set_returning: frozenset[str] = frozenset()) -> bool:
    """A set/dict literal, constructor, `.keys()`, or a call to a function of this file annotated to return one."""
    if isinstance(node, ast.Await):
        node = node.value
    if isinstance(node, ast.IfExp):
        return is_constant_time_value(node.body, set_returning) and is_constant_time_value(node.orelse, set_returning)
    if isinstance(node, (ast.Set, ast.Dict, ast.SetComp, ast.DictComp)):
        return True
    if isinstance(node, ast.Call):
        name = call_name(node.func)
        return (
            name in CONSTANT_TIME_CONSTRUCTORS
            or name in set_returning
            or (isinstance(node.func, ast.Attribute) and name in CONSTANT_TIME_METHODS)
        )
    return False


def set_returning_functions(tree: ast.AST) -> frozenset[str]:
    return frozenset(
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and is_constant_time_annotation(node.returns)
    )


def constant_time_attributes(tree: ast.AST) -> set[str]:
    """Attribute names that hold a set/dict anywhere in the file (assigned or annotated as one)."""
    attrs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and is_constant_time_value(node.value):
            attrs |= {t.attr for t in node.targets if isinstance(t, ast.Attribute)}
        elif isinstance(node, ast.AnnAssign) and (
            is_constant_time_annotation(node.annotation) or (node.value and is_constant_time_value(node.value))
        ):
            if isinstance(node.target, ast.Attribute):
                attrs.add(node.target.attr)
        elif isinstance(node, ast.ClassDef):
            # dataclass-style fields: `seen: set[str] = field(default_factory=set)` is used as `self.seen`.
            attrs |= {
                stmt.target.id
                for stmt in node.body
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and is_constant_time_annotation(stmt.annotation)
            }
    return attrs


def module_constant_time_names(tree: ast.Module) -> set[str]:
    names = set()
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign) and is_constant_time_value(stmt.value):
            names |= {t.id for t in stmt.targets if isinstance(t, ast.Name)}
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            if is_constant_time_annotation(stmt.annotation) or (stmt.value and is_constant_time_value(stmt.value)):
                names.add(stmt.target.id)
    return names


class PythonVisitor(ast.NodeVisitor):
    def __init__(self, path: str, constant_time_names: set[str], constant_time_attrs: set[str], set_returning: frozenset[str]) -> None:
        self.path = path
        self.set_returning = set_returning
        self.findings: list[Finding] = []
        self.loops: list[LoopFrame] = []
        self.scopes: list[str] = []
        self.constant_time_names = constant_time_names
        self.constant_time_attrs = constant_time_attrs
        self.per_element_lambdas: set[ast.Lambda] = set()
        # Calls that run once per page or leave the loop (`return await ...`), not once per element.
        self.single_shot: set[ast.AST] = set()

    @property
    def depth(self) -> int:
        return sum(frame.counts for frame in self.loops)

    def add(self, node: ast.AST, kind: str, depth: int | None = None) -> None:
        function = ".".join(self.scopes) or MODULE_SCOPE
        self.findings.append(Finding(self.path, getattr(node, "lineno", 1), function, kind, max(1, depth or self.depth), "high"))

    def open_targets(self) -> set[str]:
        return {target for frame in self.loops for target in frame.targets}

    def is_derived(self, node: ast.AST) -> bool:
        """True when `node` comes from an enclosing loop's element, so walking it is not a cross product.

        `row.cells`, `graph[node]`, `index.get(key, [])` and `read_rows(path)` all qualify; `range(i + 1, n)`
        doesn't (that's the pairwise pattern, which is quadratic)."""
        targets = self.open_targets()
        if not targets:
            return False
        if root_name(node) in targets:
            return True
        if isinstance(node, ast.Subscript):
            return bool(assigned_names(node.slice) & targets)
        if isinstance(node, ast.Call) and call_name(node.func) != "range":
            arguments = [*node.args, *(kw.value for kw in node.keywords)]
            return any(root_name(arg) in targets or bool(assigned_names(arg) & targets) for arg in arguments)
        return False

    def is_constant_time(self, node: ast.AST) -> bool:
        if is_constant_time_value(node, self.set_returning) or is_bounded_iterable(node):
            return True
        if isinstance(node, ast.Name):
            return node.id in self.constant_time_names or is_hashed_name(node.id)
        if isinstance(node, ast.Attribute):
            # Attributes are matched by name alone (`self.seen`, `context.render_lines`): fields of this file's classes.
            return node.attr in self.constant_time_attrs or is_hashed_name(node.attr)
        return False

    # -- scopes ------------------------------------------------------------

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        # A nested def's body runs when called, not once per iteration of the loop that defines it.
        outer_loops, self.loops = self.loops, []
        outer_names = self.constant_time_names
        params = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
        self.constant_time_names = outer_names | {arg.arg for arg in params if is_constant_time_annotation(arg.annotation)}
        self.scopes.append(node.name)
        self.generic_visit(node)
        self.scopes.pop()
        self.constant_time_names = outer_names
        self.loops = outer_loops

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.scopes.append(node.name)
        self.generic_visit(node)
        self.scopes.pop()

    def visit_Lambda(self, node: ast.Lambda) -> None:
        if node not in self.per_element_lambdas:
            self.generic_visit(node)
            return
        params = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
        self.loops.append(LoopFrame("lambda", {param.arg for param in params}, True))
        self.generic_visit(node)
        self.loops.pop()

    # -- loops -------------------------------------------------------------

    def enter_loop(self, node: ast.AST, kind: str, iterable: ast.AST | None, target: ast.AST | None) -> None:
        targets = assigned_names(target) if target else set()
        names = targets | (identifiers(iterable) if iterable is not None else set())
        retry = any(is_retry_name(name) for name in names)
        counts = iterable is None or not (self.is_derived(iterable) or is_bounded_iterable(iterable) or retry)
        if counts and self.depth:
            self.add(node, "nested-loop", self.depth + 1)
        if isinstance(iterable, ast.Call) and call_name(iterable.func) in ROW_ITERATORS:
            self.add(node, "dataframe-row-loop", self.depth + 1)
        self.loops.append(LoopFrame(kind, targets, counts, any(is_batch_name(name) for name in names)))

    def innermost_counting_loop(self) -> LoopFrame | None:
        return next((frame for frame in reversed(self.loops) if frame.counts), None)

    def visit_For(self, node: ast.For | ast.AsyncFor) -> None:
        self.visit(node.iter)  # evaluated once, in the enclosing scope
        self.enter_loop(node, "for", node.iter, node.target)
        for child in node.body:
            self.visit(child)
        self.loops.pop()
        for child in node.orelse:
            self.visit(child)

    visit_AsyncFor = visit_For

    def visit_While(self, node: ast.While) -> None:
        self.enter_loop(node, "while", None, None)
        self.visit(node.test)
        for child in node.body:
            self.visit(child)
        self.loops.pop()
        for child in node.orelse:
            self.visit(child)

    def visit_comprehension_node(self, node: ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp) -> None:
        # Each `for` clause is its own loop level: `[x for a in A for b in B]` is O(|A|*|B|).
        for generator in node.generators:
            self.visit(generator.iter)
            self.enter_loop(generator.iter, "comprehension", generator.iter, generator.target)
            for condition in generator.ifs:
                self.visit(condition)
        for child in (node.key, node.value) if isinstance(node, ast.DictComp) else (node.elt,):
            self.visit(child)
        del self.loops[-len(node.generators) :]

    visit_ListComp = visit_SetComp = visit_DictComp = visit_GeneratorExp = visit_comprehension_node

    # -- statements and expressions -----------------------------------------

    def visit_Assign(self, node: ast.Assign) -> None:
        names = {t.id for t in node.targets if isinstance(t, ast.Name)}
        if self.depth and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if rebuilds_itself(node.targets[0].id, node.value):
                self.add(node, "quadratic-accumulation")
        if self.loops and self.is_element_of_loop(node.value):
            # `row = matrix[i]`, `batch = items[i:i + size]`: walking it later is part of this iteration.
            self.loops[-1].targets |= names
        if any(is_batch_name(name) for name in names):
            self.mark_single_shot(node.value)
        if is_constant_time_value(node.value, self.set_returning):
            self.constant_time_names = self.constant_time_names | names
        else:
            self.constant_time_names = self.constant_time_names - names
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name):
            constant_time = is_constant_time_annotation(node.annotation) or (
                node.value is not None and is_constant_time_value(node.value, self.set_returning)
            )
            if constant_time:
                self.constant_time_names = self.constant_time_names | {node.target.id}
            else:
                self.constant_time_names = self.constant_time_names - {node.target.id}
        self.generic_visit(node)

    def is_element_of_loop(self, value: ast.AST) -> bool:
        return self.is_derived(value)

    def mark_single_shot(self, value: ast.AST | None) -> None:
        if value is not None:
            self.single_shot.add(value)
            if isinstance(value, ast.Await):
                self.single_shot.add(value.value)

    def visit_Return(self, node: ast.Return) -> None:
        self.mark_single_shot(node.value)
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        if self.depth:
            for op, comparator in zip(node.ops, node.comparators):
                if isinstance(op, (ast.In, ast.NotIn)) and not self.is_constant_time(comparator) and not self.is_derived(comparator):
                    self.add(node, "membership-in-loop")
                    break
        self.generic_visit(node)

    def visit_Await(self, node: ast.Await) -> None:
        innermost = self.innermost_counting_loop()
        batched = isinstance(node.value, ast.Call) and call_name(node.value.func) in BATCH_AWAIT_NAMES
        intended = node in self.single_shot or any(SEQUENTIAL_NAME_RE.search(scope) for scope in self.scopes)
        if innermost and innermost.kind != "while" and not innermost.batched and not batched and not intended:
            self.add(node, "await-in-loop")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = call_name(node.func)
        if self.depth:
            self.check_call_in_loop(node, name)
        if name == "apply" and any(
            kw.arg == "axis" and isinstance(kw.value, ast.Constant) and kw.value.value in (1, "columns") for kw in node.keywords
        ):
            self.add(node, "dataframe-row-loop", self.depth + 1)
        if name in KEY_FUNCTION_CALLS:
            self.per_element_lambdas |= {kw.value for kw in node.keywords if kw.arg == "key" and isinstance(kw.value, ast.Lambda)}
        if name in {"map", "filter"} and isinstance(node.func, ast.Name) and node.args and isinstance(node.args[0], ast.Lambda):
            self.per_element_lambdas.add(node.args[0])
        self.generic_visit(node)

    def check_call_in_loop(self, node: ast.Call, name: str) -> None:
        receiver = node.func.value if isinstance(node.func, ast.Attribute) else None
        subject = receiver if receiver is not None else (node.args[0] if node.args else None)
        derived = subject is not None and self.is_derived(subject)
        if name in {"sorted", "sort"} and not derived:
            self.add(node, "sort-in-loop")
        if name in {"filter", "map"} and receiver is None and len(node.args) > 1 and not self.is_derived(node.args[1]):
            self.add(node, "repeated-scan")
        if name in DEEP_COPY_NAMES:
            self.add(node, "deep-copy-in-loop")
        innermost = self.innermost_counting_loop()
        # while loops are usually pagination or queue consumers: one call per page/message is the design.
        handles_batch = any(is_batch_name(arg) for arg in identifiers(node, include_callee=False))
        if (
            is_query_call(node, name)
            and innermost is not None
            and innermost.kind != "while"
            and not innermost.batched
            and node not in self.single_shot
            and not handles_batch
        ):
            self.add(node, "io-or-query-in-loop")
        if receiver is None or derived:
            return
        if name in {"pop", "insert"} and node.args and is_zero(node.args[0]):
            self.add(node, "list-shift-in-loop")
        elif name in {"index", "count", "remove"} and node.args and not is_string_literal(node.args[0]):
            if not self.is_constant_time(receiver) and not is_string_literal(receiver):
                self.add(node, "membership-in-loop")


def rebuilds_itself(name: str, value: ast.expr) -> bool:
    """`x = x + [..]`, `s = s | {y}`, `x = [*x, y]`, `x = {**x, k: v}`, `df = pd.concat([df, row])`, `a = np.append(a, v)`."""

    def is_self(node: ast.AST) -> bool:
        return isinstance(node, ast.Name) and node.id == name

    if isinstance(value, ast.BinOp) and isinstance(value.op, (ast.Add, ast.BitOr)) and is_self(value.left):
        return isinstance(value.right, (ast.List, ast.ListComp, ast.Tuple, ast.Set, ast.SetComp, ast.Dict, ast.DictComp))
    if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
        return any(isinstance(e, ast.Starred) and is_self(e.value) for e in value.elts)
    if isinstance(value, ast.Dict):
        return any(key is None and is_self(val) for key, val in zip(value.keys, value.values))
    if isinstance(value, ast.Call) and call_name(value.func) in ACCUMULATING_CALLS:
        if isinstance(value.func, ast.Attribute) and is_self(value.func.value):
            return True
        args = [e for a in value.args for e in (a.elts if isinstance(a, (ast.List, ast.Tuple)) else [a])]
        return any(is_self(a) for a in args)
    return False


def is_query_call(node: ast.Call, name: str) -> bool:
    lowered = name.lower()
    if lowered in IO_CALL_NAMES:
        return True
    receiver = receiver_name(node.func)
    client_like = bool(receiver) and bool(CLIENT_RECEIVER_HINTS & {*name_tokens(receiver), receiver.lower()})
    if lowered in STRONG_QUERY_NAMES:
        return client_like or (bool(node.args) and is_string_literal(node.args[0]))
    return lowered in GENERIC_QUERY_NAMES and client_like


def scan_python_tree(path: str, tree: ast.Module) -> list[Finding]:
    visitor = PythonVisitor(path, module_constant_time_names(tree), constant_time_attributes(tree), set_returning_functions(tree))
    visitor.visit(tree)
    return visitor.findings
