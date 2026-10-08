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
        page.on("dialog", lambda dialog: dialog.accept())
        page.locator("#import").set_input_files(exported)
        expect(page.locator("#now")).to_contain_text("先解除阻塞")
        bad = root / "wrong.json"
        bad.write_text(json.dumps({**saved, "plan_id": "different"}), encoding="utf-8")
        page.locator("#import").set_input_files(bad)
        expect(page.locator("#message")).not_to_be_empty()
        assert "先解除阻塞" in page.locator("#now").inner_text()
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
        offline = browser.new_context()
        offline.add_init_script("Storage.prototype.setItem = function() { throw Error('unavailable'); };")
        fallback = offline.new_page()
        fallback.goto((ROOT / "examples/study.html").as_uri())
        assert "关闭页面前请导出" in fallback.locator("#storage").inner_text()
        fallback.get_by_role("button", name="标记完成", exact=True).click()
        assert fallback.locator("#now").inner_text() == "读完并挑一个问题"
        disabled = browser.new_context(java_script_enabled=False)
        plain = disabled.new_page()
        plain.goto((ROOT / "examples/study.html").as_uri())
        assert plain.locator("noscript li").count() == 4
        browser.close()
    print("Browser acceptance passed: keyboard, blocker, reload, export/import, dependency guard, mobile, no network, inert HTML.")


if __name__ == "__main__":
    check()
