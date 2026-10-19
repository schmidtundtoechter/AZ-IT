"""Refresh the Markdown inventory while preserving the manual changelog."""

import argparse
import ast
import json
from pathlib import Path

from script_inventory import collect_rows, export

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- BEGIN GENERATED INVENTORY -->"
END = "<!-- END GENERATED INVENTORY -->"
BOOKKEEPING = {"name", "doctype", "owner", "creation", "modified", "modified_by", "docstatus", "idx", "module", "is_system_generated"}


def cell(value):
    if value is None:
        return "—"
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("|", "&#124;").replace("\r", "").replace("\n", "<br>") or "—"


def table(headers, rows):
    return "\n".join([
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(cell(value) for value in row) + " |" for row in rows),
    ])


def link(path):
    return f"[{path}]({path})"


def settings(record, exclude=()):
    # Keep explicit false/zero flags: hidden=0 etc. are significant too.
    values = {key: value for key, value in record.items() if key not in BOOKKEEPING | set(exclude) and value is not None and value != ""}
    return json.dumps(values, ensure_ascii=False, sort_keys=True)


def inventory():
    rows = collect_rows()
    parts = ["## Aktueller Bestand", "Automatisch aus den vorhandenen Dateien erzeugt. Links führen zu den jeweiligen Quellen.",
             "### Client und Server Scripts (Datenbankdatensätze)",
             "Die Aktivierungswerte stammen aus den JSON-Dateien. Server Scripts können zusätzlich durch globale Einstellungen oder einen gestoppten Scheduler an der Ausführung gehindert werden."]
    for kind in ("Client Script", "Server Script"):
        selected = [row for row in rows if row[0] == kind]
        parts += [f"#### {kind}: {len(selected)}", table(
            ["Name", "Status", "DocType", "Ereignis / Rhythmus", "Quelle", "Hinweis"],
            [[r[1], r[2], r[3], r[4], link(r[5]), r[6]] for r in selected])]
    parts += ["### Skriptdateien und Werkzeuge", "Dateien mit registrierten Hooks sind entsprechend bezeichnet. Hilfsdateien und bei Bedarf aufgerufene Funktionen haben kein eigenes Aktiviert/Deaktiviert-Feld. Paketinitialisierungen ohne Fachlogik sind ausgenommen.",
              table(["Typ", "Datei", "Einbindung", "Details"], [[r[0], link(r[5]), r[2], r[6]] for r in rows if r[0] not in ("Client Script", "Server Script")])]
    parts += ["### Konfiguration und Automatisierung", table(["Datei", "Aufgabe"], [
        [link("az_it/hooks.py"), "Client-Hooks, Dokumentereignisse, Scheduler, API-Overrides und Fixture-Auswahl"],
        [link("az_it/patches.txt"), "Registrierung einmaliger Migrationspatches"],
        [link(".github/workflows/version.yml"), "Versionstests und automatische Patch-Version auf main"],
        [link("pyproject.toml"), "Paketkonfiguration; dynamische Version aus az_it/__init__.py"],
        [link("AGENTS.md"), "Verbindliche Pflege der Dokumentation bei Änderungen"],
    ])]

    fields, properties, additional = [], [], []
    for path in [ROOT / "az_it/fixtures/custom_field.json", ROOT / "az_it/fixtures/property_setter.json", *sorted((ROOT / "az_it/az_it/custom").glob("*.json"))]:
        data = json.loads(path.read_text(encoding="utf-8"))
        source = path.relative_to(ROOT).as_posix()
        if isinstance(data, list):
            custom_fields = data if path.name == "custom_field.json" else []
            setters = data if path.name == "property_setter.json" else []
        else:
            custom_fields, setters = data.get("custom_fields", []), data.get("property_setters", [])
            for key in ("links", "custom_perms"):
                for item in data.get(key, []):
                    additional.append([data["doctype"], key, settings(item), link(source)])
        for item in custom_fields:
            fields.append([item.get("dt", data.get("doctype") if isinstance(data, dict) else ""), item.get("fieldname"), item.get("label"), item.get("fieldtype"), settings(item, ("dt", "fieldname", "label", "fieldtype")), link(source)])
        for item in setters:
            properties.append([item.get("doc_type", data.get("doctype") if isinstance(data, dict) else ""), item.get("field_name") or "(DocType)", item.get("property"), item.get("value"), settings(item, ("doc_type", "field_name", "property", "value")), link(source)])
    fields.sort(key=lambda row: (str(row[0]), str(row[1]), row[-1]))
    properties.sort(key=lambda row: (str(row[0]), str(row[1]), str(row[2]), row[-1]))
    parts += [f"### Custom Fields: {len(fields)} Definitionen", "Enthält Fixtures und Customization-Dateien einschließlich Layoutfeldern. Derselbe Feldname kann in mehreren Quellen vorkommen; jede Definition bleibt sichtbar. Die Einstellungen zeigen auch explizit gespeicherte Null-/Aus-Werte. Nicht aufgeführte Attribute sind in der jeweiligen Quelle nicht gesetzt oder leer.",
              table(["DocType", "Feldname", "Beschriftung", "Typ", "Weitere Einstellungen", "Quelle"], fields),
              f"### Property Setter: {len(properties)} Definitionen", "Diese Einträge ändern Eigenschaften vorhandener Felder oder DocTypes, etwa Sichtbarkeit, Pflichtstatus, Reihenfolge oder Beschriftung. Werte sind die gespeicherten Zielwerte; der historische Vorher-Wert ist daraus nicht ableitbar.",
              table(["DocType", "Feld / Ziel", "Eigenschaft", "Zielwert", "Weitere Einstellungen", "Quelle"], properties)]
    for path in sorted((ROOT / "az_it/az_it/doctype").glob("*/*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        source = path.relative_to(ROOT).as_posix()
        parts += [f"### Eigener DocType: {data.get('name', path.stem)}", f"Quelle: {link(source)}. {len(data.get('fields', []))} Felder einschließlich Layoutfeldern.",
                  table(["Feldname", "Beschriftung", "Typ", "Weitere Einstellungen"], [[f.get("fieldname"), f.get("label"), f.get("fieldtype"), settings(f, ("fieldname", "label", "fieldtype"))] for f in data.get("fields", [])])]
    # Document the separate setup helper too: its schema differs from the JSON.
    setup = ROOT / "az_it/az_it/setup/create_wa_nummer_doctype.py"
    for node in ast.walk(ast.parse(setup.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get_doc" and node.args and isinstance(node.args[0], ast.Dict):
            definition = ast.literal_eval(node.args[0])
            parts += ["### Abweichende Felddefinition im manuellen WA-Nummer-Setup", f"{link(setup.relative_to(ROOT).as_posix())} ist ein separat aufrufbarer Einrichtungshelfer und kein registrierter Installationshook. Er legt nur bei fehlendem DocType an. Seine Definition enthält unter anderem `auftrag` statt `ausgangsrechnung` und abweichende Pflicht-/Schreibschutzwerte. Beide bestehenden Definitionen sind hier dokumentiert; sie wurden nicht vereinheitlicht.",
                      table(["Feldname", "Beschriftung", "Typ", "Weitere Einstellungen"], [[f.get("fieldname"), f.get("label"), f.get("fieldtype"), settings(f, ("fieldname", "label", "fieldtype"))] for f in definition.get("fields", [])])]
    if additional:
        parts += ["### Weitere Customization-Einträge", table(["DocType", "Art", "Definition", "Quelle"], additional)]
    parts += ["### Vorhandene Migrationspatches", "Die registrierten Patches entfernen alte, abgelöste Skriptdatensätze, bereinigen Leerzeilen in Beschreibungen und deaktivieren die Stock-Einstellung zur HTML-Bereinigung. Einzelheiten und betroffene Namen stehen in den oben verlinkten Patchdateien. Diese Einträge beschreiben bestehenden Code und behaupten keine erfolgreiche Ausführung auf einer Site."]
    return "\n\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify Markdown without changing files")
    args = parser.parse_args()
    path = ROOT / "CHANGELOG.md"
    original = path.read_text(encoding="utf-8")
    if original.count(START) != 1 or original.count(END) != 1:
        raise ValueError("Expected exactly one pair of inventory markers")
    before, rest = original.split(START)
    _, after = rest.split(END)
    updated = before + START + "\n\n" + inventory() + "\n\n" + END + after
    if args.check:
        if original != updated:
            raise SystemExit("Bestandsdokumentation veraltet: python tools/update_documentation.py ausführen")
        print("Bestandsdokumentation aktuell.")
    else:
        export()
        path.write_text(updated, encoding="utf-8")
        print("CHANGELOG.md aktualisiert; manueller Verlauf beibehalten.")


if __name__ == "__main__":
    main()
