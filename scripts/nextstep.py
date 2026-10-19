"""NextStep: validate a small action DAG and render one offline HTML file."""
import argparse
import base64
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0"


def text(value, limit):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError("missing or oversized text")
    if any(ord(c) < 32 and c not in "\n\t" for c in value):
        raise ValueError("control characters are not allowed")
    value.encode("utf-8")
    return value.strip()


def validate(plan):
    if not isinstance(plan, dict) or set(plan) != {"title", "goal", "language", "steps"}:
        raise ValueError("plan fields: title, goal, language, steps")
    text(plan["title"], 120)
    text(plan["goal"], 1000)
    if plan["language"] not in ("en", "zh"):
        raise ValueError("language must be en or zh")
    steps = plan["steps"]
    if not isinstance(steps, list) or not 1 <= len(steps) <= 12:
        raise ValueError("use 1 to 12 steps; split larger plans")
    ids = set()
    for step in steps:
        if not isinstance(step, dict) or set(step) != {"id", "title", "action", "done_when", "depends_on"}:
            raise ValueError("step fields: id, title, action, done_when, depends_on")
        if not isinstance(step["id"], str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", step["id"]):
            raise ValueError("invalid step id")
        if step["id"] in ids:
            raise ValueError("duplicate step id")
        ids.add(step["id"])
        text(step["title"], 80)
        text(step["action"], 2000)
        text(step["done_when"], 1000)
        deps = step["depends_on"]
        if not isinstance(deps, list) or any(not isinstance(d, str) for d in deps) or len(deps) > 3:
            raise ValueError("use at most 3 dependency ids per step")
        if len(set(deps)) != len(deps):
            raise ValueError("duplicate dependency")
    # Stable topological order keeps every prerequisite above its dependents.
    ordered = []
    pending = list(steps)
    known = set()
    while pending:
        ready = next((s for s in pending if set(s["depends_on"]) <= known), None)
        if ready is None:
            raise ValueError("unknown dependency or cycle")
        ordered.append(ready)
        known.add(ready["id"])
        pending.remove(ready)
    return {**plan, "steps": ordered}


def physical(path):
    path = Path(os.path.abspath(Path(path).expanduser()))
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise ValueError("symlink path refused; use a physical path")
    return path


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def load(path):
    path = physical(path)
    with path.open("rb") as stream:
        data = stream.read(128 * 1024 + 1)
    if len(data) > 128 * 1024:
        raise ValueError("plan exceeds 128 KiB")
    return validate(json.loads(data, object_pairs_hook=unique_object))


def render(plan):
    plan = validate(plan)
    payload = json.dumps(plan, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    identifier = hashlib.sha256(payload.encode()).hexdigest()
    # A JSON data script must not contain a literal HTML closing tag.
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    js = (ROOT / "assets/app.js").read_text(encoding="utf-8")
    css = (ROOT / "assets/style.css").read_text(encoding="utf-8")
    digest = base64.b64encode(hashlib.sha256(js.encode()).digest()).decode()
    fallback = "".join(f"<li><h2>{html.escape(s['title'])}</h2><p>{html.escape(s['action'])}</p>"
                       f"<p>{html.escape(s['done_when'])}</p></li>" for s in plan["steps"])
    template = (ROOT / "assets/page.html").read_text(encoding="utf-8")
    values = {"LANG": plan["language"], "TITLE": html.escape(plan["title"]), "CSS": css,
              "JS": js, "HASH": digest, "PLAN": payload, "ID": identifier, "FALLBACK": fallback}
    # One-pass replacement: user text containing a template token stays literal.
    return re.sub(r"@@([A-Z]+)@@", lambda m: values[m[1]], template)


def write_new(path, content):
    path = physical(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".nextstep-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)  # Atomic no-clobber; existing plans are never overwritten.
    finally:
        Path(temporary).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=VERSION)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "render"):
        command = commands.add_parser(name)
        command.add_argument("plan")
        if name == "render":
            command.add_argument("--out", required=True)
    installer = commands.add_parser("install")
    installer.add_argument("--to", required=True, help="new skill folder named nextstep")
    args = parser.parse_args()
    try:
        if args.command == "install":
            destination = physical(args.to)
            if destination.name != "nextstep" or destination.exists():
                raise ValueError("choose a new skill folder named nextstep")
            destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            # Publish only after all bundled resources have copied successfully.
            with tempfile.TemporaryDirectory(dir=destination.parent, prefix=".nextstep-install-") as temporary:
                stage = Path(temporary) / "nextstep"
                stage.mkdir(mode=0o700)
                shutil.copy2(ROOT / "SKILL.md", stage / "SKILL.md")
                for folder in ("assets", "scripts", "references"):
                    shutil.copytree(ROOT / folder, stage / folder, ignore=shutil.ignore_patterns("__pycache__"))
                destination = physical(destination)
                if destination.exists():
                    raise ValueError("installation destination already exists")
                stage.rename(destination)
            print("Installed. Invoke nextstep in a host supporting local Python and Agent Skills.")
        else:
            plan = load(args.plan)
            if args.command == "render":
                write_new(args.out, render(plan))
            print(json.dumps({"ok": True, "steps": len(plan["steps"])}))
    except (OSError, ValueError, TypeError, RecursionError, UnicodeError):
        print("NextStep failed: check JSON/schema, physical paths, permissions and existing output. No input text is echoed.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
