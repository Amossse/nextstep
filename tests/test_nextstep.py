"""Fictional inputs and temporary outputs only."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("nextstep", ROOT / "scripts/nextstep.py")
app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(app)
PLAN = json.loads((ROOT / "examples/study.json").read_text(encoding="utf-8"))


class NextStep(unittest.TestCase):
    def test_plan_encoding_is_explicit_utf8_not_json_auto_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "plan.json"
            raw = json.dumps(PLAN, ensure_ascii=False)
            for encoding in ("utf-16", "utf-32"):
                source.write_bytes(raw.encode(encoding))
                output = root / f"{encoding}.html"
                result = subprocess.run([sys.executable, str(ROOT / "scripts/nextstep.py"), "render",
                                         str(source), "--out", str(output)], capture_output=True)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(output.exists())
                self.assertNotIn(b"Traceback", result.stderr)
                self.assertNotIn(str(source).encode(), result.stderr)
            for encoding in ("utf-8", "utf-8-sig"):
                source.write_bytes(raw.encode(encoding))
                self.assertEqual(app.load(source), app.validate(PLAN))

    def test_competing_output_created_after_staging_is_preserved(self):
        original_link = app.os.link
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "plan.json"
            source.write_text(json.dumps(PLAN), encoding="utf-8")
            source_before = source.read_bytes()
            output = root / "action.html"
            sentinel = b"Fictional competing writer output"

            def competing_link(staged, destination):
                self.assertTrue(Path(staged).read_text(encoding="utf-8").startswith("<!doctype html>"))
                Path(destination).write_bytes(sentinel)
                original_link(staged, destination)

            argv = ["nextstep", "render", str(source), "--out", str(output)]
            with patch.object(sys, "argv", argv), patch.object(app.os, "link", competing_link), \
                    patch("sys.stderr", io.StringIO()) as errors:
                self.assertEqual(app.main(), 2)
            self.assertNotIn(str(output), errors.getvalue())
            self.assertEqual(output.read_bytes(), sentinel)
            self.assertEqual(source.read_bytes(), source_before)
            self.assertFalse(list(root.glob(".nextstep-*")))

    def test_copy_failure_does_not_publish_a_partial_install_and_retry_works(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            destination = root / "skills/nextstep"
            note = root / "notes.txt"
            note.write_text("Fictional note", encoding="utf-8")
            argv = ["nextstep", "install", "--to", str(destination)]
            with patch.object(sys, "argv", argv), patch.object(app.shutil, "copytree", side_effect=OSError("fictional copy failure")), \
                    patch("sys.stderr", io.StringIO()):
                self.assertEqual(app.main(), 2)
            self.assertFalse(destination.exists())
            self.assertFalse(list(destination.parent.glob(".nextstep-install-*")))
            with patch.object(sys, "argv", argv), patch("sys.stdout", io.StringIO()):
                self.assertEqual(app.main(), 0)
            self.assertEqual((destination / "SKILL.md").read_bytes(), (ROOT / "SKILL.md").read_bytes())
            result = subprocess.run([sys.executable, str(destination / "scripts/nextstep.py"),
                                     "render", str(ROOT / "examples/study.json"), "--out", str(root / "map.html")],
                                    capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(note.read_text(encoding="utf-8"), "Fictional note")

    def test_duplicate_json_fields_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "plan.json"
            for key in ("title", "done_when"):
                with self.subTest(key=key):
                    output = root / f"{key}.html"
                    raw = json.dumps(PLAN).replace(f'"{key}":', f'"{key}":"fictional-marker","{key}":', 1)
                    source.write_text(raw, encoding="utf-8")
                    result = subprocess.run([sys.executable, str(ROOT / "scripts/nextstep.py"),
                                             "render", str(source), "--out", str(output)], capture_output=True)
                    self.assertEqual(result.returncode, 2)
                    self.assertNotIn(b"fictional-marker", result.stderr)
                    self.assertFalse(output.exists())

    def test_plan_and_safe_render(self):
        self.assertEqual(app.render(PLAN), (ROOT / "examples/study.html").read_text(encoding="utf-8"))
        reverse = {**PLAN, "steps": list(reversed(PLAN["steps"]))}
        self.assertEqual(app.validate(reverse)["steps"], PLAN["steps"])
        for change in ("cycle", "unknown", "duplicate", "html"):
            value = copy.deepcopy(PLAN)
            if change == "cycle":
                value["steps"][0]["depends_on"] = ["check"]
            elif change == "unknown":
                value["steps"][0]["depends_on"] = ["missing"]
            elif change == "duplicate":
                value["steps"][1]["id"] = "choose"
            else:
                value["extra"] = "unused"
            with self.assertRaises(ValueError):
                app.validate(value)
        hostile = copy.deepcopy(PLAN)
        hostile["title"] = '</script><script>alert("fictional")</script> @@JS@@'
        result = app.render(hostile)
        self.assertNotIn(hostile["title"], result)
        self.assertIn("\\u003c/script", result)
        self.assertIn("&lt;/script&gt;", result)
        self.assertIn("connect-src 'none'", result)
        self.assertIn('@@JS@@', result)  # User text is not a second-pass template.
        with self.assertRaises(ValueError):
            app.validate({**PLAN, "title": "\x00"})

    def test_cli_install_and_no_clobber(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            target = root / "skills/nextstep"
            def run(*args):
                return subprocess.run([sys.executable, str(ROOT / "scripts/nextstep.py"), *map(str,args)],
                                      capture_output=True, text=True)
            self.assertEqual(run("install", "--to", target).returncode, 0)
            self.assertEqual(run("install", "--to", target).returncode, 2)
            out = root / "action.html"
            installed = subprocess.run([sys.executable, str(target / "scripts/nextstep.py"),
                                        "render", str(ROOT / "examples/study.json"), "--out", str(out)], capture_output=True)
            self.assertEqual(installed.returncode, 0, installed.stderr)
            before = out.read_bytes()
            self.assertEqual(run("render", ROOT / "examples/study.json", "--out", out).returncode, 2)
            self.assertEqual(before, out.read_bytes())
            invalid = root / "bad.json"
            invalid.write_text('{"private":"fictional-marker"}', encoding="utf-8")
            result = run("validate", invalid)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("fictional-marker", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            try:
                link = root / "alias"
                link.symlink_to(root, target_is_directory=True)
            except OSError:
                pass
            else:
                self.assertEqual(run("render", ROOT / "examples/study.json", "--out", link / "other.html").returncode, 2)


if __name__ == "__main__":
    unittest.main()
