"""Fictional inputs and temporary outputs only."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("nextstep", ROOT / "scripts/nextstep.py")
app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(app)
PLAN = json.loads((ROOT / "examples/study.json").read_text(encoding="utf-8"))


class NextStep(unittest.TestCase):
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
