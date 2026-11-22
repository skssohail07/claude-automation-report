"""Validate the claude-automation report PBIP project (standard library only).

Run from anywhere:  python tools/validate_project.py
Exits with code 1 if any check fails.

Checks:
  1. every .json file in the project opens without errors
  2. every table file is listed in model.tmdl (and every ref has a file)
  3. every relationship uses columns that exist
  4. every visual field (table, column, measure) exists in the model
  5. the report has exactly 3 pages: Emp, Dept, HR (OWN)
  plus: TMDL files are indented with tabs, sortByColumn targets exist
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PBIP = ROOT / "claude-automation report.pbip"
EXPECTED_PAGES = ["Emp", "Dept", "HR (OWN)"]

errors = []


def fail(check, msg):
    errors.append(f"[{check}] {msg}")


def rel(p):
    return p.relative_to(ROOT).as_posix()


def unquote(name):
    name = name.strip()
    if len(name) >= 2 and name[0] == name[-1] == "'":
        return name[1:-1].replace("''", "'")
    return name


# TMDL object name: 'quoted name' or bare identifier
NAME = r"('(?:[^']|'')*'|[^\s=:]+)"


def split_ref(ref):
    """Split a TMDL column reference like Table.Column or 'My Table'.'My Col'."""
    m = re.fullmatch(NAME + r"\." + NAME, ref.strip())
    return (unquote(m.group(1)), unquote(m.group(2))) if m else (None, None)


_json_cache = {}


def load_json(path):
    """Parse a JSON file once; report a failure only the first time."""
    if path not in _json_cache:
        try:
            _json_cache[path] = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as e:
            fail("json", f"{rel(path)}: {e}")
            _json_cache[path] = None
    return _json_cache[path]


# ---------- locate project folders ----------
if not PBIP.exists():
    print(f"FAIL: {PBIP.name} not found")
    sys.exit(1)
pbip = load_json(PBIP) or {}
report_dir = ROOT / pbip.get("artifacts", [{}])[0].get("report", {}).get("path", "")
pbir = load_json(report_dir / "definition.pbir") if (report_dir / "definition.pbir").exists() else None
if not pbir:
    fail("structure", f"missing or invalid {rel(report_dir)}/definition.pbir")
    pbir = {}
model_dir = (report_dir / pbir.get("datasetReference", {}).get("byPath", {}).get("path", "")).resolve()
definition = model_dir / "definition"
if not definition.is_dir():
    fail("structure", f"semantic model definition folder not found: {model_dir}")

# ---------- 1. JSON files ----------
json_files = [PBIP]
for folder in (report_dir, model_dir):
    json_files += [p for p in folder.rglob("*") if p.is_file()
                   and (p.suffix in (".json", ".pbir", ".pbism") or p.name == ".platform")
                   and ".pbi" not in p.relative_to(folder).parts]
for p in json_files[1:]:
    load_json(p)

# ---------- parse TMDL ----------
tables = {}  # table name -> {"columns": set, "measures": set, "file": Path}
sort_refs = []  # (table, column, sortByColumn)
for f in sorted((definition / "tables").glob("*.tmdl")):
    text = f.read_text(encoding="utf-8-sig")
    m = re.match(r"\s*table\s+" + NAME, text)
    if not m:
        fail("tmdl", f"{rel(f)}: no 'table' declaration")
        continue
    t = unquote(m.group(1))
    cols, meas = set(), set()
    current_col = None
    for line in text.splitlines():
        if mc := re.match(r"\tcolumn\s+" + NAME, line):
            current_col = unquote(mc.group(1))
            cols.add(current_col)
        elif mm := re.match(r"\tmeasure\s+" + NAME, line):
            meas.add(unquote(mm.group(1)))
            current_col = None
        elif re.match(r"\t\S", line):
            current_col = None
        elif current_col and (ms := re.match(r"\t\tsortByColumn:\s*(.+)", line)):
            sort_refs.append((t, current_col, unquote(ms.group(1))))
    tables[t] = {"columns": cols, "measures": meas, "file": f}

for f in definition.rglob("*.tmdl"):
    for i, line in enumerate(f.read_text(encoding="utf-8-sig").splitlines(), 1):
        if re.match(r"\t* +\S", line) and line.strip():
            fail("tabs", f"{rel(f)}:{i}: indented with spaces")
            break

for t, c, s in sort_refs:
    if s not in tables[t]["columns"]:
        fail("tmdl", f"{t}[{c}] sortByColumn '{s}' does not exist")

# ---------- 2. tables listed in model.tmdl ----------
model_text = (definition / "model.tmdl").read_text(encoding="utf-8-sig") if (definition / "model.tmdl").exists() else ""
refs = {unquote(r) for r in re.findall(r"^ref table\s+" + NAME, model_text, re.M)}
for t, info in tables.items():
    if t not in refs:
        fail("model", f"table '{t}' ({rel(info['file'])}) is not listed in model.tmdl")
for r in refs - tables.keys():
    fail("model", f"model.tmdl references table '{r}' but no table file defines it")

# ---------- 3. relationships ----------
rel_file = definition / "relationships.tmdl"
if rel_file.exists():
    current = None
    for line in rel_file.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("relationship "):
            current = line.split(None, 1)[1].strip()
        elif mr := re.match(r"\t(fromColumn|toColumn):\s*(.+)", line):
            t, c = split_ref(mr.group(2))
            if t is None:
                fail("relationship", f"{current}: cannot parse {mr.group(1)} '{mr.group(2)}'")
            elif t not in tables:
                fail("relationship", f"{current}: {mr.group(1)} table '{t}' does not exist")
            elif c not in tables[t]["columns"]:
                fail("relationship", f"{current}: {mr.group(1)} column {t}[{c}] does not exist")

# ---------- 4. visual fields ----------
def field_refs(node):
    """Yield (kind, entity, property) for every Column/Measure/Hierarchy reference in a visual."""
    if isinstance(node, dict):
        for kind in ("Column", "Measure"):
            ref = node.get(kind)
            if isinstance(ref, dict) and "Property" in ref:
                entity = ref.get("Expression", {}).get("SourceRef", {}).get("Entity")
                yield kind, entity, ref["Property"]
        for v in node.values():
            yield from field_refs(v)
    elif isinstance(node, list):
        for v in node:
            yield from field_refs(v)


pages_dir = report_dir / "definition" / "pages"
for vf in sorted(pages_dir.glob("*/visuals/*/visual.json")):
    data = load_json(vf)
    if data is None:
        continue
    vtype = data.get("visual", {}).get("visualType", "?")
    where = f"{vf.parent.parent.parent.name}/{vtype} ({vf.parent.name})"
    for kind, entity, prop in field_refs(data):
        if entity not in tables:
            fail("visual", f"{where}: table '{entity}' does not exist")
        elif kind == "Column" and prop not in tables[entity]["columns"]:
            fail("visual", f"{where}: column {entity}[{prop}] does not exist")
        elif kind == "Measure" and prop not in tables[entity]["measures"]:
            fail("visual", f"{where}: measure {entity}[{prop}] does not exist")

# ---------- 5. pages ----------
pages_meta = load_json(pages_dir / "pages.json") or {}
order = pages_meta.get("pageOrder", [])
names = []
for pid in order:
    page_file = pages_dir / pid / "page.json"
    if not page_file.exists():
        fail("pages", f"pageOrder lists '{pid}' but {pid}/page.json is missing")
        continue
    page = load_json(page_file)
    if page is None:
        continue
    if page.get("name") != pid:
        fail("pages", f"{pid}/page.json has name '{page.get('name')}'")
    names.append(page.get("displayName"))
folders = sorted(p.name for p in pages_dir.iterdir() if p.is_dir())
if sorted(order) != folders:
    fail("pages", f"page folders {folders} do not match pageOrder {order}")
if names != EXPECTED_PAGES:
    fail("pages", f"expected pages {EXPECTED_PAGES} in that order, found {names}")

# ---------- summary ----------
n_cols = sum(len(t["columns"]) for t in tables.values())
n_meas = sum(len(t["measures"]) for t in tables.values())
n_vis = len(list(pages_dir.glob("*/visuals/*/visual.json")))
print(f"Checked {len(json_files)} JSON files, {len(tables)} tables ({n_cols} columns, {n_meas} measures), "
      f"{len(order)} pages, {n_vis} visuals.")
if errors:
    print(f"FAIL: {len(errors)} problem(s)")
    for e in errors:
        print("  " + e)
    sys.exit(1)
print("OK: all checks passed")
