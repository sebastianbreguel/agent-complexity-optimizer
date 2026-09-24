"""Unit tests for the regex scanner's scope tracking: enclosing function names and blanked strings."""

import pytest

from complexity_scanner.scanners.text_heuristics import code_only, scan_text

NESTED_BODY = ["    for (const a of listA) {", "      for (const b of listB) {", "        use(a, b);", "      }", "    }"]


@pytest.mark.parametrize(
    ("header", "suffix", "expected"),
    [
        (["  async syncAll(orders: Order[]): Promise<void> {"], ".ts", "syncAll"),
        (["  async runDailyMaintenance(input?: {", "    days?: number;", "  }): Promise<void> {"], ".ts", "runDailyMaintenance"),
        (["  private async load(", "    id: string,", "  ): Promise<void> {"], ".ts", "load"),
        (["export function Table({", "  rows,", "}: TableProps) {"], ".tsx", "Table"),
        (["const handler = async (req, res) => {"], ".js", "handler"),
        (["func (s *Server) Handle(w http.ResponseWriter) {"], ".go", "Handle"),
        (["  public List<String> names(int id) throws IOException {"], ".java", "names"),
        (["  public List<String> names(", "      int id) {"], ".java", "names"),
        (["fun build(parts: List<String>): String {"], ".kt", "build"),
    ],
)
def test_enclosing_function_name(header, suffix, expected):
    findings = scan_text("file" + suffix, suffix, header + NESTED_BODY + ["}"])
    assert [f.function for f in findings if f.kind == "nested-loop"] == [expected]


def test_strings_and_comments_are_blanked():
    code, _ = code_only('const label = "for each item"; // for later', False, ".ts")
    assert "for" not in code


def test_multiline_template_is_skipped():
    lines = ["const text = `", "  for every item while we wait", "`;", "for (const x of xs) {", "  for (const y of ys) {}", "}"]
    assert [f.line for f in scan_text("t.ts", ".ts", lines)] == [5]
