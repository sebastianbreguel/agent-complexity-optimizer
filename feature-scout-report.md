# Feature Scout Report — agent-complexity-optimizer

## Context (from interview)
- **Users:** Reclutadores / comunidad evaluando craft (portfolio). Usuario secundario real: un dev o agente IA leyendo findings.
- **Product goal:** Skill que escanea un repo por hotspots de complejidad algorítmica y propone optimizaciones seguras sin romper comportamiento.
- **Key metric:** Precisión — cada finding debe ser real y accionable. Precisión > cobertura. Los falsos positivos erosionan confianza.
- **Constraints:** Single-file, stdlib-only. El scanner se debe leer de una sentada. Sin deps nuevas.

## Map summary
El core es `skills/complexity-optimizer/scripts/analyze_complexity.py` (~418 líneas) con **dos motores**: un AST visitor real (`PythonVisitor`, líneas 132-225) para `.py` — preciso — y un scanner regex línea-por-línea (`scan_text`, líneas 255-332) para ~30 lenguajes — best-effort, ruidoso. Findings salen como `Finding` dataclass → markdown o JSON (líneas 370-413). El producto envuelve esto en `SKILL.md` (workflow de 7 pasos: baseline → rank → prove → optimize → verify → benchmark → report) + `references/` + reglas para 10 plataformas de agentes. La CI corre pytest en 3.10/3.12/3.13. Tests usan un fixture por patrón, y `clean_code.py` exige **cero FP**.

## Gap & opportunity report
- **Falso positivo vivo en `visit_Compare` (líneas 175-184):** marca `x in y` dentro de loop sin importar que `y` ya sea un `set`/`dict`. Contradice el ethos de cero-FP que el propio `test_scanner.py:80` defiende.
- **Profundidad de loop binaria (`_visit_loop`, línea 163):** `loop_depth >= 1` trata un triple-nested igual que un doble. Ya tenés el contador — desperdiciado.
- **Sin campo de confianza:** un finding AST (real) y uno regex (adivinanza) se ven idénticos en el output. El usuario no puede calibrar. La honestidad es justo el activo de un portfolio.
- **Solo markdown/json:** hay un workflow de CI (`ci.yml`) pero el scanner no emite **SARIF** — el formato que GitHub renderiza como anotaciones inline en PRs. Un "scanner" sin esa integración deja valor de portfolio en la mesa.
- **Sin gate de CI:** no hay flag `--fail-on-severity`; el scanner no puede romper un build aunque haya un O(n³).
- **Sin supresión inline:** una vez que dispara un FP, el usuario no tiene forma de silenciarlo (estilo `# noqa`).
- **`visit_Call` es una escalera de `if`s creciente (186-225):** deuda que compounde con cada patrón nuevo.
- **No hace dogfood:** no hay test que verifique que el scanner pasa limpio sobre su propio código.
- **`scan_text` es un techo:** el heurístico de indentación (línea 266) y el brace-counting de `component_ranges` son adivinanzas. Extenderlo = reinventar tree-sitter mal. **No es oportunidad — es zona congelada.**

## Ranked features

### 1. Membership scope-aware (suprimir si el target ya es set/dict)  ·  Value 4/5 · Difficulty 2/5 · Time S
- **What:** Rastrear asignaciones locales (`name = set(...)` / `{...}` / `dict(...)`) en una tabla de símbolos plana por función vía `visit_Assign`; no marcar `x in name` si `name` ya es O(1).
- **Karpathy (leverage):** Arregla el FP exacto de las líneas 175-184. Symbol table plana = ~80% de los casos al 20% del esfuerzo; no construyas scope-stack anidado todavía.
- **Product (value):** Mata la mayor fuente de falsos positivos en el detector más usado. Precisión pura — el valor #1 del proyecto.
- **Builds on:** `PythonVisitor.visit_Compare` (175-184), nuevo `visit_Assign`.

### 2. Campo `confidence` en cada finding (ast=high, regex=low)  ·  Value 4/5 · Difficulty 1/5 · Time S
- **What:** Agregar `confidence: str` al `Finding` dataclass; AST findings = "high", regex = "low". Mostrarlo en tabla/JSON.
- **Karpathy (leverage):** Un campo en el dataclass + setearlo en dos sitios. Cero análisis nuevo.
- **Product (value):** Convierte la debilidad del path regex en honestidad explícita. Para un portfolio, "sé qué tan confiable es cada finding" es señal de madurez de ingeniería.
- **Builds on:** `Finding` (94-101), `render_markdown` (370-384).

### 3. Profundidad real de loop → O(n^k)  ·  Value 3/5 · Difficulty 1/5 · Time S
- **What:** Reportar la profundidad real (`depth 2 → O(n²)`, `depth 3 → O(n³)`) en vez de un flag binario; subir severidad con la profundidad.
- **Karpathy (leverage):** Ya tenés `loop_depth`. Es un f-string y un map depth→exponente.
- **Product (value):** El finding pasa de "hay algo" a "esto es O(n³)" — más accionable, mejor tabla de reporte.
- **Builds on:** `_visit_loop` (162-173).

### 4. Output SARIF (`--format sarif`)  ·  Value 4/5 · Difficulty 2/5 · Time M
- **What:** Tercer formato de salida en SARIF 2.1.0 (JSON estándar), consumible por GitHub Code Scanning → anotaciones inline en PRs.
- **Karpathy (leverage):** SARIF es solo JSON con un schema fijo; compone el `Finding` y el `--format` que ya existen. Stdlib puro.
- **Product (value):** El diferenciador de portfolio: "mi scanner se integra con GitHub PRs". Demuestra que entendés el ecosistema de tooling, no solo el algoritmo.
- **Builds on:** `main` (`--format`, 390), `asdict(f)` loop (410).

### 5. Refactor `visit_Call` → tabla de detectores  ·  Value 3/5 · Difficulty 2/5 · Time S
- **What:** Reemplazar la escalera de `if self.loop_depth and name in {...}` por una tabla `kind → (predicate, Finding template)`.
- **Karpathy (leverage):** Es el enabler de #6 — sin esto, cada patrón nuevo agranda la escalera. Pagás la deuda una vez.
- **Product (value):** Indirecto pero alto para portfolio: legibilidad y extensibilidad es craft visible. Mantiene el "léelo de una sentada".
- **Builds on:** `visit_Call` (186-225).

### 6. Nuevos patrones AST (concat-in-loop, loop-invariant, deque, pandas)  ·  Value 4/5 · Difficulty 2/5 · Time M
- **What:** `s += x` en loop (O(n²)); `re.compile`/`set(literal)` loop-invariant; `pop(0)`/`insert(0)` → deque; pandas `iterrows`/concat-in-loop (gate detrás de "pandas importado"). **Cortar:** `len`-in-loop, `.apply`, recursión-sin-memo (mienten seguido).
- **Karpathy (leverage):** Todos leen estado que el visitor ya tiene. Caen limpios en la tabla de #5.
- **Product (value):** Patrones comunes y reales con fix mecánico seguro. Cada uno con su fixture (el patrón de test ya está establecido).
- **Builds on:** tabla de #5, nuevo `visit_AugAssign`, `tests/fixtures/`.

### 7. Flag `--fail-on-severity` (gate de CI)  ·  Value 3/5 · Difficulty 1/5 · Time S
- **What:** `--fail-on high` → exit code ≠ 0 si hay findings de esa severidad o peor.
- **Karpathy (leverage):** Un `if` sobre la lista ya ordenada + `return 1`. Compone `severity_rank` (365).
- **Product (value):** Hace que el `ci.yml` que ya shippeás signifique algo: el scanner puede bloquear regresiones de complejidad. Cierra el loop portfolio "tengo CI".
- **Builds on:** `main` (387-413), `severity_rank`.

### 8. Test de dogfooding en CI  ·  Value 3/5 · Difficulty 1/5 · Time S
- **What:** Test que corre el scanner sobre su propio `skills/` y asegura que pasa limpio (o con findings esperados documentados).
- **Karpathy (leverage):** ~15 líneas de pytest reusando `run_scanner`.
- **Product (value):** Credibilidad barata: "el scanner de complejidad no tiene hotspots de complejidad". Buena historia.
- **Builds on:** `tests/test_scanner.py`.

### 9. Supresión inline (`# complexity: ignore`)  ·  Value 3/5 · Difficulty 2/5 · Time S
- **What:** Saltar findings en líneas con un comentario marcador.
- **Karpathy (leverage):** Chequear el texto de la línea antes de emitir el `Finding`. Compone el `lines` que ya tenés.
- **Product (value):** Da escape a los FP que queden. Patrón que todo linter serio tiene — señal de que pensaste en uso real.
- **Builds on:** ambos motores antes de `findings.append`.

### 10. Modo diff (`--since <ref>`)  ·  Value 3/5 · Difficulty 3/5 · Time M
- **What:** Escanear solo archivos cambiados vs un git ref — ideal para correr en PRs.
- **Karpathy (leverage):** Un `git diff --name-only` filtrando `iter_files`. Pierde "single-file puro" si shellea git, pero stdlib `subprocess` lo cubre.
- **Product (value):** Hace el scanner usable como check de PR sin ruido del repo entero. Pareja natural de #4 y #7.
- **Builds on:** `iter_files` (104-110), `main`.

**Dropped (1):** Interprocedural call graph + per-function Big-O. Value alto pero Difficulty 5/5: exige two-pass driver, resolución de llamadas (dynamic dispatch en Python = no sound), manejo de ciclos y un `Finding` más rico. Viola single-file stdlib y, para portfolio, "lee como un junior que no distingue un problema difícil de uno imposible". Es un v2 separado, no una extensión.

## Quadrant view (Value vs Difficulty)

|                      | Low Difficulty (1–2)             | High Difficulty (3–5)   |
|----------------------|----------------------------------|-------------------------|
| **High Value (4–5)** | **Build now:** #1, #2, #4, #6    | **Big bets:** (ninguno) |
| **Low Value (1–3)**  | **Quick wins:** #3, #5, #7, #8, #9 | **Later:** #10        |
