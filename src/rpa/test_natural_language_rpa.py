"""
[使用工具]: Python 3.11 unittest, Playwright, NLScriptParser, NLRPARunner
[設計目的]: 驗證第二章【自然語言 RPA 工作流程引擎】：語法解析、雙模配置、例外策略 (Skip/Abort) 與截圖生成。
[測試案例]:
    - TC-NL01: 完整自然語言語意解析 (GOTO, TYPE, PRESS, CLICK, WAIT, ON_ERROR, SCREENSHOT)
    - TC-NL02: 容錯與多種白話句型解析 (包含中文引號、空格容錯)
    - TC-NL03: 例外策略驗證 (遇到不存在之元素時，指定 skip 能自動跳過並繼續執行下一步)
    - TC-NL04: 終止策略驗證 (遇到錯誤時，指定 abort 能即時中斷保護系統)
    - TC-NL05: 步驟截圖生成驗證 (驗證步驟產生合法 base64 PNG 影像字串)
[修改日期]: 2026-11-10
[關聯程式]: src/rpa/natural_language_rpa.py, src/web_audit/server.py
"""

import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.rpa.natural_language_rpa import NLScriptParser, NLRPARunner, RPAAction


class TestNaturalLanguageRPA(unittest.TestCase):
    def setUp(self):
        self.parser = NLScriptParser()

    def test_tc_nl01_full_syntax_parsing(self):
        """TC-NL01: 測試完整自然語言語法解析"""
        script = """
        前往網址: https://www.youtube.com
        在「搜尋框」輸入: 讀書長音樂
        按下鍵盤: Enter
        點擊包含文字: 讀書
        等待 2 秒
        截圖說明: 音樂播放就緒
        """
        actions = self.parser.parse(script)
        self.assertEqual(len(actions), 6)
        self.assertEqual(actions[0].action_type, "GOTO")
        self.assertEqual(actions[0].params["url"], "https://www.youtube.com")
        self.assertEqual(actions[1].action_type, "TYPE")
        self.assertEqual(actions[1].params["target"], "搜尋框")
        self.assertEqual(actions[1].params["value"], "讀書長音樂")
        self.assertEqual(actions[2].action_type, "PRESS")
        self.assertEqual(actions[2].params["key"], "Enter")
        self.assertEqual(actions[3].action_type, "CLICK")
        self.assertEqual(actions[3].params["target"], "讀書")
        self.assertEqual(actions[4].action_type, "WAIT")
        self.assertEqual(actions[4].params["seconds"], 2.0)
        self.assertEqual(actions[5].action_type, "SCREENSHOT")

    def test_tc_nl02_flexible_synonyms_and_quotes(self):
        """TC-NL02: 測試同義詞、全形半形括號與白話相容性"""
        script = """
        導航至: http://127.0.0.1:8080
        在 帳號 鍵入 admin
        在【密碼】欄位填寫 secret123
        按下 Enter 鍵
        點選「登入」
        """
        actions = self.parser.parse(script)
        self.assertEqual(len(actions), 5)
        self.assertEqual(actions[0].action_type, "GOTO")
        self.assertEqual(actions[1].action_type, "TYPE")
        self.assertEqual(actions[1].params["target"], "帳號")
        self.assertEqual(actions[1].params["value"], "admin")
        self.assertEqual(actions[2].action_type, "TYPE")
        self.assertEqual(actions[2].params["target"], "密碼")
        self.assertEqual(actions[2].params["value"], "secret123")
        self.assertEqual(actions[3].action_type, "PRESS")
        self.assertEqual(actions[3].params["key"], "Enter")
        self.assertEqual(actions[4].action_type, "CLICK")
        self.assertEqual(actions[4].params["target"], "登入")

    def test_tc_nl03_exception_skip_policy(self):
        """TC-NL03: 測試例外策略 (遇到不存在按鈕時，skip 能使流程不中斷並標註 SKIPPED)"""
        runner = NLRPARunner(mode="backend", default_timeout_ms=1000)
        script = """
        前往網址: data:text/html,<html><body><h1>測試頁面</h1><button id='btnA'>按鈕A</button></body></html>
        如果失敗: 跳過
        點擊包含文字: 絕不存在的幽靈按鈕
        點擊包含文字: 按鈕A
        截圖說明: 成功完成
        """
        result = runner.execute_script(script)
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["total_steps"], 4)
        self.assertEqual(result["skipped_steps"], 1)  # 幽靈按鈕被跳過
        self.assertEqual(result["passed_steps"], 3)
        self.assertEqual(result["steps"][1]["status"], "SKIPPED")
        self.assertEqual(result["steps"][2]["status"], "PASS")

    def test_tc_nl04_exception_abort_policy(self):
        """TC-NL04: 測試中斷策略 (遇到錯誤時，abort 能立即終止保護系統)"""
        runner = NLRPARunner(mode="backend", default_timeout_ms=1000)
        script = """
        前往網址: data:text/html,<html><body><h1>安全測試頁面</h1></body></html>
        如果失敗: 中斷
        點擊包含文字: 絕不存在的關鍵按鈕
        點擊包含文字: 後續指令不應被執行
        """
        result = runner.execute_script(script)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["failed_steps"], 1)
        # 後續指令被終止，因此總步數只執行到失敗為止
        self.assertEqual(len(result["steps"]), 2)

    def test_tc_nl05_screenshot_generation(self):
        """TC-NL05: 測試每一步驟自動產生合法的 Base64 PNG 截圖"""
        runner = NLRPARunner(mode="backend", default_timeout_ms=1000)
        script = """
        前往網址: data:text/html,<html><body style='background:lightblue;'><h1>截圖測試</h1></body></html>
        截圖說明: 驗證截圖資料
        """
        result = runner.execute_script(script)
        self.assertEqual(result["status"], "SUCCESS")
        step_snap = result["steps"][0]["screenshot"]
        self.assertIsNotNone(step_snap)
        self.assertTrue(step_snap.startswith("data:image/png;base64,"))


if __name__ == "__main__":
    unittest.main()

