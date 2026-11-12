"""
[使用工具]: Python 3.11, Playwright (Chromium), RapidOCR, Regex, Base64
[設計目的]: 實現「自然語言 RPA 工作流程引擎 (Natural Language RPA Engine)」。
           讓使用者能以白話中文/英文編寫 RPA 腳本，指定網址、輸入欄位、按鈕、按鍵、
           例外處理規則 (跳過/重試/中斷) 與截圖說明，支援「模式一：背端模式」與「模式二：視窗模式」。
[程式說明]:
    1. `NLScriptParser`: 採用寬容式自然語言語意解析器，支援多種白話句型：
       - 前往 / 導航至 / Open: <URL>
       - 在 <欄位標籤/描述> 輸入: <數值>
       - 按下按鍵 / 按 Enter: <鍵盤按鍵>
       - 點擊 / 點擊按鈕: <按鍵名稱或文字>
       - 等待 / 輪詢: <文字或秒數>
       - 如果失敗 / 錯誤時: <跳過 (skip) / 重試 (retry) / 中斷 (abort)>
       - 截圖說明 / 拍照: <說明文字>
    2. `NLRPARunner`: 雙模執行器：
       - window 模式: 彈出真實瀏覽器視窗，慢動作 (slow_mo) + 霓虹紅框高亮 + 人眼全程可見。
       - backend 模式: 無頭背景高速執行。
    3. 步驟追蹤與視覺證明：自動在每一步截取高亮畫面，保存為 Base64 或 PNG 供 Web 前端即時輪播展示。
[修改日期]: 2026-11-10
[修改概要]: 初始實作自然語言 RPA 解析與雙模執行引擎
[輸入參數]: 自然語言腳本文本, 模式 (window/backend), 慢動作延遲, 參考圖檔 (可選)
[輸出結果]: 執行步驟日誌、每步耗時、狀態 (PASS/FAIL/SKIPPED) 與步驟截圖列表
[關聯測試]: report/BDD/DBB_Pre_Moreem_20261110.md
[工作日誌]: report/work_record/work_record_20261110.md
"""

import base64
import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from playwright.sync_api import sync_playwright, Page, Locator


@dataclass
class RPAAction:
    step_id: int
    raw_text: str
    action_type: str  # GOTO, TYPE, PRESS, CLICK, WAIT, SCREENSHOT, ON_ERROR
    params: Dict[str, Any] = field(default_factory=dict)
    on_error: str = "abort"  # skip, retry, abort
    max_retries: int = 1


@dataclass
class StepResult:
    step_id: int
    action_type: str
    description: str
    status: str  # PASS, FAIL, SKIPPED
    duration_s: float
    error_msg: Optional[str] = None
    screenshot_base64: Optional[str] = None


class NLScriptParser:
    """
    [Class]: NLScriptParser
    [設計目的]: 將人類自然語言敘述解析為結構化 RPAAction 佇列
    """

    def parse(self, script_text: str, default_on_error: str = "abort") -> List[RPAAction]:
        actions: List[RPAAction] = []
        lines = [line.strip() for line in script_text.strip().splitlines() if line.strip() and not line.strip().startswith("#")]

        current_on_error = default_on_error
        step_counter = 1

        for line in lines:
            action = self._parse_line(line, step_counter, current_on_error)
            if action:
                if action.action_type == "ON_ERROR":
                    current_on_error = action.params.get("strategy", "abort")
                else:
                    actions.append(action)
                    step_counter += 1

        return actions

    def _parse_line(self, line: str, step_id: int, on_error: str) -> Optional[RPAAction]:
        # 1. 前往網址 / 導航至
        m_goto = re.search(
            r"(?:前往|開啟|導航至|網址|打開|open|goto|visit)\s*(?:網址)?[:：\s]+(.+)",
            line,
            re.IGNORECASE,
        )
        if m_goto:
            url_val = m_goto.group(1).strip()
            # 若無協定前綴且非 data:/file:，自動補上 https://
            if not (url_val.startswith("http://") or url_val.startswith("https://") or url_val.startswith("data:") or url_val.startswith("file://")):
                url_val = "https://" + url_val
            return RPAAction(step_id, line, "GOTO", {"url": url_val}, on_error=on_error)

        # 2. 在欄位輸入值
        # 例：在「搜尋框」輸入: 讀書長音樂 或 在 帳號欄位 鍵入 admin 或 在【搜尋】輸入: test
        m_type = re.search(
            r"在\s*[\u300c\u300e【\"'\[\(]?([^\u300c\u300d\u300e\u300f】\"'\[\]\(\):：\s]+)[\u300d\u300f】\"'\]\)]?\s*(?:欄位)?\s*(?:輸入|鍵入|填寫|type|input)[:：\s]+(.+)",
            line,
            re.IGNORECASE,
        )
        if m_type:
            return RPAAction(
                step_id,
                line,
                "TYPE",
                {"target": m_type.group(1).strip(), "value": m_type.group(2).strip()},
                on_error=on_error,
            )

        # 3. 按鍵（Enter, Tab, Esc 等）
        # 例：按下鍵盤: Enter 或 按下 Enter 鍵 或 敲擊 Enter
        m_press = re.search(r"(?:按下|敲擊|鍵盤|press|key)[:：\s]*(?:鍵盤上的?)?\s*([A-Za-z0-9_]+)", line, re.IGNORECASE)
        if m_press:
            key_name = m_press.group(1).strip()
            return RPAAction(step_id, line, "PRESS", {"key": key_name}, on_error=on_error)

        # 4. 點擊按鈕或文字
        # 例：點擊包含文字: 讀書 或 點擊按鈕: 搜尋 或 點選「登入」
        m_click = re.search(r"(?:點擊|點選|按下|click)\s*(?:按鈕|文字|包含文字|目標)?[:：\s]*[\u300c\u300e【\"'\[\(]?([^\u300c\u300d\u300e\u300f】\"'\[\]\(\)]+)[\u300d\u300f】\"'\]\)]?", line, re.IGNORECASE)
        if m_click:
            return RPAAction(step_id, line, "CLICK", {"target": m_click.group(1).strip()}, on_error=on_error)

        # 5. 等待時間或文字
        m_wait_sec = re.search(r"(?:等待|暫停|sleep|wait)\s*(\d+(?:\.\d+)?)\s*(?:秒|s)", line, re.IGNORECASE)
        if m_wait_sec:
            return RPAAction(step_id, line, "WAIT", {"seconds": float(m_wait_sec.group(1))}, on_error=on_error)

        m_wait_text = re.search(r"(?:等待|輪詢|直到畫面出現|wait_for)[:：\s]*[\u300c\u300e【\"'\[\(]?([^\u300c\u300d\u300e\u300f】\"'\[\]\(\)]+)[\u300d\u300f】\"'\]\)]?", line, re.IGNORECASE)
        if m_wait_text:
            return RPAAction(step_id, line, "WAIT", {"target": m_wait_text.group(1).strip()}, on_error=on_error)

        # 6. 例外處理策略宣告
        m_err = re.search(r"(?:如果失敗|若出錯|錯誤時|on_error)[:：\s]*(跳過|重試|中斷|忽略|skip|retry|abort)", line, re.IGNORECASE)
        if m_err:
            strat_raw = m_err.group(1).lower()
            strat = "skip" if ("跳過" in strat_raw or "忽略" in strat_raw or "skip" in strat_raw) else ("retry" if ("重試" in strat_raw or "retry" in strat_raw) else "abort")
            return RPAAction(step_id, line, "ON_ERROR", {"strategy": strat})

        # 7. 截圖說明
        m_snap = re.search(r"(?:截圖|拍照|保存畫面|screenshot)(?:說明)?[:：\s]*(.+)?", line, re.IGNORECASE)
        if m_snap:
            desc = m_snap.group(1).strip() if m_snap.group(1) else "工作流狀態截圖"
            return RPAAction(step_id, line, "SCREENSHOT", {"desc": desc}, on_error="skip")

        # 預設嘗試推導：若含 URL 視為 GOTO
        if "http://" in line or "https://" in line:
            url_match = re.search(r"(https?://[^\s]+)", line)
            if url_match:
                return RPAAction(step_id, line, "GOTO", {"url": url_match.group(1)}, on_error=on_error)

        return None


class NLRPARunner:
    """
    [Class]: NLRPARunner
    [設計目的]: 執行自然語言 RPA 腳本，支援雙軌（視窗/背端），提供即時步驟截圖與防禦性錯誤處理
    """

    def __init__(
        self,
        mode: str = "window",
        slow_mo_ms: int = 1000,
        default_timeout_ms: int = 10000,
        reference_image_path: Optional[Path] = None,
        keep_open: bool = False,
        use_persistent_profile: bool = True,
    ):
        self.mode = mode.lower()
        self.is_window = self.mode == "window"
        self.slow_mo = slow_mo_ms if self.is_window else 0
        self.timeout = default_timeout_ms
        self.ref_image = reference_image_path
        self.keep_open = keep_open
        self.use_persistent_profile = use_persistent_profile
        self.profile_dir = BASE_DIR / ".chrome_user_data"
        self.profile_dir.mkdir(parents=True, exist_ok=True)

    def _highlight(self, page: Page, locator: Locator, color: str = "#EF4444"):
        if not self.is_window:
            return
        try:
            locator.scroll_into_view_if_needed(timeout=2000)
            page.evaluate(
                f"""(element) => {{
                    element.style.outline = '4px solid {color}';
                    element.style.boxShadow = '0 0 20px {color}';
                    element.style.transition = 'all 0.3s ease';
                }}""",
                locator.element_handle(),
            )
            time.sleep(0.3)
        except Exception:
            pass

    def _take_screenshot_base64(self, page: Page) -> Optional[str]:
        try:
            png_bytes = page.screenshot(type="png", full_page=False)
            return base64.b64encode(png_bytes).decode("utf-8")
        except Exception:
            return None

    def execute_script(self, script_text: str, default_on_error: str = "abort") -> Dict[str, Any]:
        parser = NLScriptParser()
        actions = parser.parse(script_text, default_on_error=default_on_error)

        results: List[StepResult] = []
        overall_status = "SUCCESS"
        start_total = time.time()

        if not actions:
            return {
                "status": "FAILED",
                "message": "未能從腳本中解析出任何有效動作指令",
                "steps": [],
                "total_duration_s": 0,
            }

        with sync_playwright() as p:
            browser = None
            context = None
            browser_args = ["--start-maximized", "--disable-blink-features=AutomationControlled"]

            if self.use_persistent_profile:
                try:
                    context = p.chromium.launch_persistent_context(
                        str(self.profile_dir),
                        channel="chrome",
                        headless=not self.is_window,
                        slow_mo=self.slow_mo,
                        viewport={"width": 1400, "height": 900} if self.is_window else {"width": 1280, "height": 720},
                        args=browser_args,
                    )
                except Exception:
                    context = p.chromium.launch_persistent_context(
                        str(self.profile_dir),
                        headless=not self.is_window,
                        slow_mo=self.slow_mo,
                        viewport={"width": 1400, "height": 900} if self.is_window else {"width": 1280, "height": 720},
                        args=browser_args,
                    )
                page = context.pages[0] if context.pages else context.new_page()
            else:
                browser = p.chromium.launch(
                    headless=not self.is_window,
                    slow_mo=self.slow_mo,
                    args=browser_args,
                )
                context = browser.new_context(
                    viewport={"width": 1400, "height": 900} if self.is_window else {"width": 1280, "height": 720},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                )
                page = context.new_page()

            for act in actions:
                t0 = time.time()
                res = self._execute_single_action(page, act)
                res.duration_s = round(time.time() - t0, 2)
                results.append(res)

                if res.status == "FAIL":
                    if act.on_error == "skip":
                        print(f"⚠️ 步驟 {act.step_id} 失敗，依使用者設定策略【跳過繼續執行】: {res.error_msg}")
                        res.status = "SKIPPED"
                    elif act.on_error == "retry":
                        print(f"🔄 步驟 {act.step_id} 失敗，依使用者設定策略【立即重試一次】...")
                        time.sleep(1.0)
                        t_retry = time.time()
                        retry_res = self._execute_single_action(page, act)
                        retry_res.duration_s = round(time.time() - t_retry, 2)
                        if retry_res.status == "PASS":
                            results[-1] = retry_res
                        else:
                            overall_status = "FAILED"
                            break
                    else:
                        print(f"🛑 步驟 {act.step_id} 失敗，依使用者設定策略【中斷終止】: {res.error_msg}")
                        overall_status = "FAILED"
                        break

            # 結束前若在視窗模式，依設定持續保持開啟或停留
            if self.is_window and self.keep_open and overall_status == "SUCCESS":
                print("\n💡 視窗模式已就緒！視窗將保持開啟供您操作。若要結束請直接關閉瀏覽器視窗...")
                try:
                    while not page.is_closed():
                        time.sleep(1.0)
                except KeyboardInterrupt:
                    pass
            elif self.is_window and overall_status == "SUCCESS":
                time.sleep(2.0)

            try:
                context.close()
                if browser:
                    browser.close()
            except Exception:
                pass

        total_duration = round(time.time() - start_total, 2)
        return {
            "status": overall_status,
            "mode": self.mode,
            "total_steps": len(results),
            "passed_steps": sum(1 for r in results if r.status == "PASS"),
            "failed_steps": sum(1 for r in results if r.status == "FAIL"),
            "skipped_steps": sum(1 for r in results if r.status == "SKIPPED"),
            "total_duration_s": total_duration,
            "steps": [
                {
                    "step_id": r.step_id,
                    "action_type": r.action_type,
                    "description": r.description,
                    "status": r.status,
                    "duration_s": r.duration_s,
                    "error_msg": r.error_msg,
                    "screenshot": f"data:image/png;base64,{r.screenshot_base64}" if r.screenshot_base64 else None,
                }
                for r in results
            ],
        }

    def _execute_single_action(self, page: Page, act: RPAAction) -> StepResult:
        desc = act.raw_text
        try:
            if act.action_type == "GOTO":
                url = act.params["url"]
                # 處理 data:text/html 若漏填 charset=utf-8 導致非 ASCII 中文亂碼問題
                if url.startswith("data:text/html,") and "charset" not in url:
                    url = url.replace("data:text/html,", "data:text/html;charset=utf-8,", 1)
                page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
                # 處理常見的 Cookie 對話框
                try:
                    c_btn = page.locator("button:has-text('Accept all'), button:has-text('全部接受'), button:has-text('我同意')").first
                    if c_btn.is_visible(timeout=1500):
                        c_btn.click()
                except Exception:
                    pass
                snap = self._take_screenshot_base64(page)
                return StepResult(act.step_id, act.action_type, desc, "PASS", 0.0, screenshot_base64=snap)

            elif act.action_type == "TYPE":
                target_str = act.params["target"]
                val = act.params["value"]

                # 尋找輸入框 (由模糊到精確)
                selector = f"input[placeholder*='{target_str}'], input[aria-label*='{target_str}'], input[name*='{target_str}'], textarea[placeholder*='{target_str}']"
                if "搜尋" in target_str or "search" in target_str.lower():
                    selector = "input#search, input[name='search_query'], input[type='search'], " + selector

                elem = page.locator(selector).first
                if not elem.is_visible(timeout=self.timeout / 2):
                    # 備用：尋找一般文字標籤附近的 input
                    elem = page.locator(f"xpath=//*[contains(text(), '{target_str}')]/following::input[1]").first

                elem.wait_for(state="visible", timeout=self.timeout)
                self._highlight(page, elem, color="#F59E0B")  # 琥珀金
                elem.click()
                elem.fill("")
                elem.type(val, delay=100 if self.is_window else 0)
                snap = self._take_screenshot_base64(page)
                return StepResult(act.step_id, act.action_type, desc, "PASS", 0.0, screenshot_base64=snap)

            elif act.action_type == "PRESS":
                key = act.params["key"]
                page.keyboard.press(key)
                time.sleep(0.5)
                snap = self._take_screenshot_base64(page)
                return StepResult(act.step_id, act.action_type, desc, "PASS", 0.0, screenshot_base64=snap)

            elif act.action_type == "CLICK":
                target_str = act.params["target"]
                # 複合定位器：按鈕、連結、文字或標題
                elem = page.locator(
                    f"button:has-text('{target_str}'), a:has-text('{target_str}'), [role='button']:has-text('{target_str}'), #video-title:has-text('{target_str}'), span:has-text('{target_str}')"
                ).first

                elem.wait_for(state="visible", timeout=self.timeout)
                self._highlight(page, elem, color="#06B6D4")  # 霓虹青
                elem.click()
                snap = self._take_screenshot_base64(page)
                return StepResult(act.step_id, act.action_type, desc, "PASS", 0.0, screenshot_base64=snap)

            elif act.action_type == "WAIT":
                if "seconds" in act.params:
                    time.sleep(act.params["seconds"])
                elif "target" in act.params:
                    t_str = act.params["target"]
                    page.locator(f":has-text('{t_str}')").first.wait_for(state="visible", timeout=self.timeout)
                snap = self._take_screenshot_base64(page)
                return StepResult(act.step_id, act.action_type, desc, "PASS", 0.0, screenshot_base64=snap)

            elif act.action_type == "SCREENSHOT":
                snap = self._take_screenshot_base64(page)
                return StepResult(act.step_id, act.action_type, desc, "PASS", 0.0, screenshot_base64=snap)

            else:
                return StepResult(act.step_id, act.action_type, desc, "SKIPPED", 0.0)

        except Exception as e:
            err = str(e).splitlines()[0] if str(e) else "執行逾時或找不到目標元素"
            snap = self._take_screenshot_base64(page)
            return StepResult(act.step_id, act.action_type, desc, "FAIL", 0.0, error_msg=err, screenshot_base64=snap)
