"""Extraction primitives (pure functions)."""
from app.scrapers.dskb.adapters.libraries import _radix_tables, extract_component_md, family_of
from app.scrapers.dskb.adapters.repos import js_object_to_python
from app.scrapers.dskb.core import classify_table, md_sections, md_tables


def test_md_tables_respect_backtick_pipes():
    md = "| Name | Type | Default | Description |\n|---|---|---|---|\n| `value` | `string \\| null` | — | The value. |\n| `onChange` | `(v: string) => void` | - | Handler |\n"
    t = md_tables(md)[0]
    assert classify_table(t["header"]) == "props"
    assert t["rows"][0]["Type"] == "string | null"
    assert t["rows"][1]["Name"] == "onChange"


def test_sections_ignore_headings_in_code_fences():
    secs = md_sections("# Title\n```md\n# not a heading\n```\n## Real\ntext")
    assert [s["title"] for s in secs] == ["Title", "Real"]


def test_extract_component_md_frontmatter_and_keyboard():
    md = "---\ntitle: Dialog\ndescription: A FIXTURE dialog.\n---\n## API reference\n### Root\n| Prop | Type | Default | Description |\n| :-- | :-- | :-- | :-- |\n| open | `boolean` | - | Open state |\n## Keyboard interactions\n| Key | Description |\n|---|---|\n| Esc | Closes |\n"
    d = extract_component_md(md)
    assert d["doc_title"] == "Dialog" and d["description"] == "A FIXTURE dialog."
    assert d["subcomponents"][0]["name"] == "Root" and d["props_count"] == 1
    assert d["keyboard"][0]["keys"] == "Esc"


def test_mantine_preamble_is_reduced_to_description():
    d = extract_component_md("# Modal\nPackage: @mantine/core\nImport: import { Modal } from '@mantine/core';\nDescription: An accessible overlay dialog\n")
    assert d["description"] == "An accessible overlay dialog"


def test_radix_jsx_tables():
    src = '### Root\n\n<PropsTable\n\tdata={[\n\t\t{\n\t\t\tname: "open",\n\t\t\ttype: "boolean",\n\t\t\tdescription: "Open state.",\n\t\t},\n\t]}\n/>\n'
    (heading, rows), = _radix_tables(src, "PropsTable")
    assert heading == "Root" and rows[0]["name"] == "open" and rows[0]["type"] == "boolean"


def test_js_object_literal():
    d = js_object_to_python('export default { title: "A: b", items: { "x-y": { title: \'Q\', }, }, n: 1, ok: true, }')
    assert d == {"title": "A: b", "items": {"x-y": {"title": "Q"}}, "n": 1, "ok": True}


def test_family_normalisation():
    assert family_of("AlertDialog") == "Dialog"
    assert family_of("ComboBox") == "Combobox"
    assert family_of("Totally Unknown Widget") is None
