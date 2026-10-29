"""Fictional inputs and temporary outputs only."""
import copy
import importlib.util
import io
import json
import os
import runpy
import stat
from contextlib import contextmanager
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("nextstep", ROOT / "scripts/nextstep.py")
app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(app)
PLAN = json.loads((ROOT / "examples/study.json").read_text(encoding="utf-8"))


class NextStep(unittest.TestCase):
    def test_read_io_failure_closes_resources_without_publishing_output(self):
        original_fdopen, opened, streams = os.fdopen, [], []

        class FailingRead:
            def read(self, size):
                raise OSError("Fictional read failure")

        @contextmanager
        def fail_read(descriptor, *args, **kwargs):
            opened.append(descriptor)
            with original_fdopen(descriptor, *args, **kwargs) as stream:
                streams.append(stream)
                yield FailingRead()

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source, output = root / "fictional.json", root / "action.html"
            source.write_text(json.dumps(PLAN), encoding="utf-8")
            before, errors = source.read_bytes(), io.StringIO()
            args = [str(ROOT / "scripts/nextstep.py"), "render", str(source), "--out", str(output)]
            with patch.object(os, "fdopen", side_effect=fail_read), patch.object(sys, "argv", args), \
                    patch.object(sys, "stderr", errors), patch.object(sys, "stdout", io.StringIO()):
                with self.assertRaises(SystemExit) as exited:
                    runpy.run_path(args[0], run_name="__main__")
            self.assertEqual(exited.exception.code, 2)
            self.assertEqual(len(opened), 1)
            self.assertTrue(streams[0].closed)
            with self.assertRaises(OSError):
                os.fstat(opened[0])
            self.assertEqual(source.read_bytes(), before)
            self.assertFalse(output.exists())
            self.assertEqual(list(root.glob(".nextstep-*")), [])
            for detail in (str(source), "Fictional", "Traceback"):
                self.assertNotIn(detail, errors.getvalue())
            self.assertEqual(app.load(source), app.validate(PLAN))

    def test_sync_failure_does_not_publish_output_and_cleans_staging(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            target = root / "fictional.html"
            with patch.object(app.os, "fsync", side_effect=OSError("Fictional sync failure")), \
                    patch.object(app.os, "link") as publish:
                with self.assertRaises(OSError):
                    app.write_new(target, "Fictional map")
                publish.assert_not_called()
            self.assertFalse(target.exists())
            self.assertEqual(list(root.glob(".nextstep-*")), [])
            app.write_new(target, "Fictional retry")
            self.assertEqual(target.read_text(encoding="utf-8"), "Fictional retry")

    def test_plan_byte_limit_accepts_the_boundary_and_refuses_one_more_byte(self):
        raw = json.dumps(PLAN, ensure_ascii=False).encode("utf-8")
        limit = 128 * 1024
        self.assertLess(len(raw), limit)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "fictional.json"
            boundary = raw + b" " * (limit - len(raw))
            source.write_bytes(boundary)
            self.assertEqual(app.load(source), app.validate(PLAN))
            oversized = boundary + b" "
            source.write_bytes(oversized)
            for action in ("validate", "render"):
                output = root / "action.html"
                command = [sys.executable, str(ROOT / "scripts/nextstep.py"), action, str(source)]
                result = subprocess.run(command + (["--out", str(output)] if action == "render" else []),
                                        capture_output=True)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(output.exists())
                self.assertEqual(source.read_bytes(), oversized)
                self.assertNotIn(str(source).encode(), result.stderr)
                self.assertNotIn(b"Traceback", result.stderr)

    def test_rejected_plan_and_read_stream_failure_close_the_descriptor(self):
        original_open = app.os.open
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory).resolve() / "plan.json"
            source.write_text(json.dumps(PLAN), encoding="utf-8")
            for failure in ("type", "stream"):
                opened = []

                def record_open(*args, **kwargs):
                    descriptor = original_open(*args, **kwargs)
                    opened.append(descriptor)
                    return descriptor

                injection = (patch.object(app.os, "fstat", return_value=SimpleNamespace(st_mode=stat.S_IFIFO))
                             if failure == "type" else
                             patch.object(app.os, "fdopen", side_effect=OSError("Fictional read stream failure")))
                try:
                    with patch.object(app.os, "open", record_open), injection:
                        with self.assertRaises((OSError, ValueError)):
                            app.load(source)
                    self.assertEqual(len(opened), 1)
                    with self.assertRaises(OSError):
                        app.os.fstat(opened[0])
                finally:
                    for descriptor in opened:
                        try:
                            app.os.close(descriptor)
                        except OSError:
                            pass
            self.assertEqual(app.load(source), app.validate(PLAN))

    def test_plan_input_requires_a_regular_opened_file(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory).resolve() / "plan.json"
            source.write_text(json.dumps(PLAN), encoding="utf-8")
            with patch.object(app.os, "fstat", return_value=SimpleNamespace(st_mode=stat.S_IFIFO)):
                with self.assertRaises(ValueError):
                    app.load(source)
            self.assertEqual(app.load(source), app.validate(PLAN))

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX FIFO check")
    def test_fifo_input_does_not_wait_for_a_writer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source, output = root / "plan.pipe", root / "action.html"
            os.mkfifo(source)
            result = subprocess.run([sys.executable, str(ROOT / "scripts/nextstep.py"), "render",
                                     str(source), "--out", str(output)], capture_output=True, timeout=3)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(output.exists())
            self.assertNotIn(b"Traceback", result.stderr)
            self.assertNotIn(str(source).encode(), result.stderr)

    def test_stream_setup_failure_closes_staged_descriptor(self):
        original_mkstemp = app.tempfile.mkstemp
        opened = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()

            def record_open(*args, **kwargs):
                descriptor, filename = original_mkstemp(*args, **kwargs)
                opened.append(descriptor)
                return descriptor, filename

            try:
                with patch.object(app.tempfile, "mkstemp", record_open), \
                        patch.object(app.os, "fdopen", side_effect=OSError("fictional stream setup failure")):
                    with self.assertRaises(OSError):
                        app.write_new(root / "action.html", "Fictional map")
                self.assertEqual(len(opened), 1)
                with self.assertRaises(OSError):
                    app.os.fstat(opened[0])
                self.assertFalse((root / "action.html").exists())
                self.assertFalse(list(root.glob(".nextstep-*")))
            finally:
                for descriptor in opened:
                    try:
                        app.os.close(descriptor)
                    except OSError:
                        pass

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
