"""Optional real-browser acceptance check; pip install playwright first."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("nextstep", ROOT / "scripts/nextstep.py")
app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(app)


def check():
    with tempfile.TemporaryDirectory() as directory, sync_playwright() as pw:
        root = Path(directory).resolve()
        browser = pw.chromium.launch()
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        requests, errors = [], []
        page.on("request", lambda request: requests.append(request.url))
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto((ROOT / "examples/study.html").as_uri())
        page.get_by_role("button", name="标记完成", exact=True).focus()
        page.keyboard.press("Enter")
        assert page.locator("#now").inner_text() == "读完并挑一个问题"
        assert page.locator("#progress").inner_text() == "已完成 1 / 4"
        page.locator("#controls summary").click()
        page.get_by_label("哪里卡住了？").fill("虚构阻塞：材料暂时不可用")
        page.get_by_role("button", name="记录阻塞", exact=True).click()
        assert "先解除阻塞" in page.locator("#now").inner_text()
        page.reload()
        assert "先解除阻塞" in page.locator("#now").inner_text()
        with page.expect_download() as download:
            page.get_by_role("button", name="导出进度").click()
        exported = root / "progress.json"
        download.value.save_as(exported)
        saved = json.loads(exported.read_text())
        assert saved["steps"][1]["status"] == "blocked"
        page.get_by_role("button", name="解除阻塞", exact=True).click()
        assert page.locator("#now").inner_text() == "读完并挑一个问题"
        def accept_dialog(dialog):
            dialog.accept()
        page.on("dialog", accept_dialog)
        page.locator("#import").set_input_files(exported)
        expect(page.locator("#now")).to_contain_text("先解除阻塞")
        bad = root / "wrong.json"
        bad.write_text(json.dumps({**saved, "plan_id": "different"}), encoding="utf-8")
        page.locator("#import").set_input_files(bad)
        expect(page.locator("#message")).not_to_be_empty()
        assert "先解除阻塞" in page.locator("#now").inner_text()
        invalid_encoding = root / "invalid-encoding.json"
        corrupt = copy.deepcopy(saved)
        corrupt["steps"][1]["reason"] = "fictional-encoding-marker"
        invalid_encoding.write_bytes(json.dumps(corrupt).encode("utf-8").replace(b"fictional-encoding-marker", b"\xff"))
        prior_storage = page.evaluate("JSON.stringify(localStorage)")
        page.locator("#import").set_input_files(invalid_encoding)
        expect(page.locator("#import")).to_have_value("")
        assert page.evaluate("JSON.stringify(localStorage)") == prior_storage
        page.get_by_role("button", name="解除阻塞", exact=True).click()
        for _ in range(3):
            page.get_by_role("button", name="标记完成", exact=True).click()
        assert page.locator("#now").inner_text() == "全部步骤已标记完成"
        page.locator("#map-label").click()
        page.get_by_role("button", name="撤销完成", exact=True).first.click()
        assert "请先撤销" in page.locator("#message").inner_text()
        page.set_viewport_size({"width":375,"height":800})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert page.locator("#steps li").count() == 4
        assert not errors, errors
        assert all(url.startswith("file:") or url.startswith("blob:") for url in requests), requests

        hostile = copy.deepcopy(json.loads((ROOT / "examples/study.json").read_text(encoding="utf-8")))
        hostile["title"] = '</script><script>window.evil=1</script>'
        malicious = root / "hostile.html"
        malicious.write_text(app.render(hostile), encoding="utf-8")
        page.goto(malicious.as_uri())
        assert page.locator("h1").inner_text() == hostile["title"]
        assert page.evaluate("window.evil === undefined")
        assert page.locator("#now").inner_text() == "选一小段材料"
        state_key = page.evaluate("'nextstep-v1-' + JSON.parse(document.getElementById('identity').textContent)")
        page.evaluate("key => localStorage.setItem(key, 'fictional corrupt state')", state_key)
        page.reload()
        assert page.evaluate("key => localStorage.getItem(key)", state_key) == "fictional corrupt state"
        assert page.locator("#message").inner_text()
        page.get_by_role("button", name="标记完成", exact=True).click()
        assert page.locator("#now").inner_text() == "读完并挑一个问题"
        assert page.evaluate("key => localStorage.getItem(key)", state_key) == "fictional corrupt state"
        with page.expect_download() as download:
            page.get_by_role("button", name="导出进度").click()
        recovered = root / "recovered.json"
        download.value.save_as(recovered)
        page.remove_listener("dialog", accept_dialog)
        page.once("dialog", lambda dialog: dialog.dismiss())
        page.locator("#import").set_input_files(recovered)
        expect(page.locator("#import")).to_have_value("")
        assert page.evaluate("key => localStorage.getItem(key)", state_key) == "fictional corrupt state"
        page.once("dialog", lambda dialog: dialog.accept())
        page.locator("#import").set_input_files(recovered)
        expect(page.locator("#storage")).to_contain_text("进度已保存在当前浏览器")
        assert json.loads(page.evaluate("key => localStorage.getItem(key)", state_key))["steps"][0]["status"] == "done"
        offline = browser.new_context()
        offline.add_init_script("Storage.prototype.setItem = function() { throw Error('unavailable'); };")
        fallback = offline.new_page()
        fallback.goto((ROOT / "examples/study.html").as_uri())
        assert "关闭页面前请导出" in fallback.locator("#storage").inner_text()
        fallback.get_by_role("button", name="标记完成", exact=True).click()
        assert fallback.locator("#now").inner_text() == "读完并挑一个问题"
        # A successful in-memory click is not enough: the backup must resume
        # in a different browser context with no access to the failed storage.
        with fallback.expect_download() as download:
            fallback.get_by_role("button", name="导出进度").click()
        portable = root / "storage-unavailable-progress.json"
        download.value.save_as(portable)
        restored = browser.new_context().new_page()
        restored.goto((ROOT / "examples/study.html").as_uri())
        assert restored.locator("#progress").inner_text() == "已完成 0 / 4"
        restored.once("dialog", lambda dialog: dialog.accept())
        restored.locator("#import").set_input_files(portable)
        expect(restored.locator("#progress")).to_have_text("已完成 1 / 4")
        restored.reload()
        assert restored.locator("#now").inner_text() == "读完并挑一个问题"
        # Delay the first file read until a later selection has already imported.
        slow_state = copy.deepcopy(saved)
        for step in slow_state["steps"]:
            step.update(status="pending", reason="")
        slow = root / "slow.json"
        slow.write_text(json.dumps(slow_state), encoding="utf-8")
        restored.evaluate("""() => {
          const read = File.prototype.arrayBuffer;
          File.prototype.arrayBuffer = function() {
            if (this.name === 'slow.json') return new Promise(resolve => {
              window.releaseSlowImport = async () => resolve(await read.call(this));
            });
            return read.call(this);
          };
        }""")
        restored.on("dialog", lambda dialog: dialog.accept())
        restored.locator("#import").set_input_files(slow)
        restored.wait_for_function("typeof window.releaseSlowImport === 'function'")
        restored.locator("#import").set_input_files(portable)
        expect(restored.locator("#import")).to_have_value("")
        restored.evaluate("async () => { await window.releaseSlowImport(); await new Promise(resolve => setTimeout(resolve, 0)); }")
        expect(restored.locator("#progress")).to_have_text("已完成 1 / 4")
        restored.reload()
        assert restored.locator("#progress").inner_text() == "已完成 1 / 4"
        # Exercise the advertised English branch in an isolated browser context,
        # including portable progress rather than only checking static labels.
        english_plan = {
            "title": "Fictional reading card", "goal": "Make one short study card.", "language": "en",
            "steps": [
                {"id": "read", "title": "Read one paragraph", "action": "Choose a public paragraph.",
                 "done_when": "One paragraph selected.", "depends_on": []},
                {"id": "card", "title": "Write one answer", "action": "Write an answer in your own words.",
                 "done_when": "One short answer written.", "depends_on": ["read"]},
            ],
        }
        english_file = root / "english.html"
        english_file.write_text(app.render(english_plan), encoding="utf-8")
        english_context = browser.new_context(accept_downloads=True)
        english = english_context.new_page()
        english.goto(english_file.as_uri())
        english.get_by_role("button", name="Mark done", exact=True).focus()
        english.keyboard.press("Enter")
        assert english.locator("#progress").inner_text() == "Completed 1 / 2"
        assert english.locator("#now").inner_text() == "Write one answer"
        english.locator("#controls summary").click()
        english.get_by_role("button", name="Record blocker", exact=True).click()
        assert english.locator("#message").inner_text() == "Enter a blocker first."
        english.get_by_label("What is blocking you?").fill("Fictional missing source")
        english.get_by_role("button", name="Record blocker", exact=True).click()
        english.reload()
        assert english.locator("#now").inner_text() == "Resolve a blocker first · Write one answer"
        with english.expect_download() as download:
            english.get_by_role("button", name="Export progress", exact=True).click()
        english_backup = root / "english-progress.json"
        download.value.save_as(english_backup)
        english.get_by_role("button", name="Unblock", exact=True).click()
        english.once("dialog", lambda dialog: dialog.accept())
        english.get_by_label("Import this plan's progress JSON").set_input_files(english_backup)
        expect(english.locator("#now")).to_have_text("Resolve a blocker first · Write one answer")
        english.get_by_role("button", name="Unblock", exact=True).click()
        english.get_by_role("button", name="Mark done", exact=True).click()
        assert english.locator("#now").inner_text() == "All steps marked done"
        english_context.close()
        disabled = browser.new_context(java_script_enabled=False)
        plain = disabled.new_page()
        plain.goto((ROOT / "examples/study.html").as_uri())
        assert plain.locator("noscript li").count() == 4
        browser.close()
    print("Browser acceptance passed: keyboard, blocker, reload, export/import, dependency guard, mobile, no network, inert HTML.")


if __name__ == "__main__":
    check()
