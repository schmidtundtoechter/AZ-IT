"""Export repository script records and code files without importing Frappe."""

import ast
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def export():
    hooks = {}
    tree = ast.parse((ROOT / "az_it/hooks.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            hooks[node.targets[0].id] = ast.literal_eval(node.value)
    rows = []
    fixture_names = {
        item["doctype"]: set(item["filters"][0][2])
        for item in hooks["fixtures"]
        if item["doctype"] in ("Client Script", "Server Script")
    }
    for kind, filename, flag in (
        ("Client Script", "client_script.json", "enabled"),
        ("Server Script", "server_script.json", "disabled"),
    ):
        path = Path("az_it/fixtures") / filename
        for item in json.loads((ROOT / path).read_text(encoding="utf-8")):
            enabled = item.get(flag)
            status = "unbekannt" if enabled is None else ("aktiviert" if bool(enabled) == (flag == "enabled") else "deaktiviert")
            event = item.get("doctype_event", "") if item.get("script_type") == "DocType Event" else item.get("event_frequency", "")
            note = "Exportierter Datenbankstatus; Live-Installation ungeprüft."
            if item["name"] not in fixture_names[kind]:
                note += " FEHLT in hooks.py fixtures: wird bei erneutem Export nicht ausgewählt."
            rows.append([kind, item["name"], status, item.get("dt", item.get("reference_doctype", "")), event, path.as_posix(), note])

    bindings = {}

    def bind(path, description):
        bindings.setdefault(path, []).append(description)

    for doctype, path in hooks["doctype_js"].items():
        bind("az_it/" + path, f"doctype_js: {doctype}")
    for doctype, events in hooks["doc_events"].items():
        for event, functions in events.items():
            for function in functions if isinstance(functions, list) else [functions]:
                bind(function.rsplit(".", 1)[0].replace(".", "/") + ".py", f"{doctype}.{event}: {function.rsplit('.', 1)[1]}")
    for frequency, functions in hooks["scheduler_events"].items():
        for function in functions:
            bind(function.rsplit(".", 1)[0].replace(".", "/") + ".py", f"Scheduler: {frequency}")
    for original, function in hooks["override_whitelisted_methods"].items():
        bind(function.rsplit(".", 1)[0].replace(".", "/") + ".py", f"API-Override: {original}")
    for line in (ROOT / "az_it/patches.txt").read_text().splitlines():
        if line.startswith("az_it."):
            bind(line.replace(".", "/") + ".py", "Registrierter Migrationspatch; einmalig pro Site")
    for path in sorted(ROOT.rglob("*")):
        if path.suffix not in (".py", ".js", ".sh") or ".git" in path.parts or path.name == "__init__.py":
            continue
        relative = path.relative_to(ROOT).as_posix()
        status = "registriert" if relative in bindings else "bei Aufruf / Hilfsdatei"
        note = "; ".join(bindings.get(relative, []))
        if "/doctype/" in relative and not path.name.startswith("test_"):
            status, note = "DocType-Controller", "Automatisch für WA Nummer; tatsächliche Installation ungeprüft."
        if relative == "az_it/az_it/python_scripts/lead.py":
            status, note = "bei API-Aufruf", "cancel_todos_for_lead; aus js_scripts/lead.js aufgerufen."
        kind = "Client-Code" if path.suffix == ".js" else "Server-Code / Werkzeug"
        rows.append([kind, path.name, status, "", "", relative, note])
    destination = ROOT / "SCRIPT_INVENTORY.csv"
    with destination.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream, delimiter=";")
        writer.writerow(["Typ", "Name", "Status im Repository", "DocType", "Ereignis", "Datei", "Hinweis"])
        writer.writerows(rows)
    print(f"{len(rows)} entries -> {destination.name}")


if __name__ == "__main__":
    export()
