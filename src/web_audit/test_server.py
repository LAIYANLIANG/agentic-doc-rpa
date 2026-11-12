"""
[使用工具]: Python 3.11 unittest, io.BytesIO, RapidOCR
[設計目的]: 自動化單元測試 Option A【Web 文件上傳與審計平台】核心請求處理器 (WebAuditRequestHandler)
[程式說明]:
    1. 使用 in-memory MockRequest (io.BytesIO) 模擬 HTTP 網路傳輸，在無須開放外部通訊埠或網路權限之沙箱環境下測試。
    2. 依序執行 5 項單元與整合測試：
       - TC-W01: GET / (驗證回傳 HTML 單頁應用程式，含關鍵字與 UTF-8 編碼)
       - TC-W02: GET /api/sample-docs (驗證回傳 JSON 清冊，清單長度 >= 5)
       - TC-W03: POST /api/analyze-sample (驗證分析預設 CoA 單據，核對 Tg=176.0°C 與 Base64 影像輸出)
       - TC-W04: POST /api/upload (驗證處理 Multipart 檔案上傳並正確調用視覺 OCR 與金額勾稽)
       - TC-W05: GET /api/health (驗證健康檢查端點)
[修改日期]: 2026-11-10
[修改概要]: 改用 in-memory 模擬測試以確保沙箱相容性與無網路依賴執行
[輸入參數]: 無
[輸出結果]: 5 項測試全數 PASS
[關聯測試]: src/web_audit/server.py
[工作日誌]: report/work_record/work_record_20261110.md
"""

import io
import json
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.web_audit.server import WebAuditRequestHandler, TEMPLATE_PATH, SAMPLE_DOCS_DIR


class MockSocket:
    def __init__(self, raw_input: bytes = b""):
        self.raw_input = raw_input

    def makefile(self, mode="r", *args, **kwargs):
        if "b" in mode:
            return io.BytesIO(self.raw_input)
        return io.StringIO(self.raw_input.decode("utf-8"))

    def sendall(self, data):
        pass


class MockServer:
    def __init__(self):
        self.server_name = "127.0.0.1"
        self.server_port = 8080


def create_mock_handler(raw_http_request: bytes) -> WebAuditRequestHandler:
    """建立免連網之 Mock HTTP Request Handler"""
    mock_sock = MockSocket(raw_http_request)
    mock_server = MockServer()
    # 建立一個不呼叫 setup/finish socket 的客製處理實例
    handler = WebAuditRequestHandler.__new__(WebAuditRequestHandler)
    handler.rfile = io.BytesIO(raw_http_request)
    handler.wfile = io.BytesIO()
    handler.server = mock_server
    handler.client_address = ("127.0.0.1", 12345)
    handler.raw_requestline = handler.rfile.readline()
    handler.parse_request()
    return handler


def parse_response(wfile: io.BytesIO):
    """解析 handler 寫入 wfile 之 HTTP 響應頭與內文"""
    wfile.seek(0)
    raw = wfile.read()
    header_end = raw.find(b"\r\n\r\n")
    if header_end == -1:
        return 500, {}, raw
    headers_raw = raw[:header_end].decode("utf-8")
    body = raw[header_end + 4:]
    status_line = headers_raw.splitlines()[0]
    status_code = int(status_line.split()[1])
    return status_code, headers_raw, body


class TestWebAuditServerLogic(unittest.TestCase):

    def test_tc_w01_index_html(self):
        req = b"GET / HTTP/1.1\r\nHost: 127.0.0.1:8080\r\n\r\n"
        h = create_mock_handler(req)
        h.do_GET()
        status, _, body = parse_response(h.wfile)
        self.assertEqual(status, 200)
        html_text = body.decode("utf-8")
        self.assertTrue("智能單據" in html_text or "智慧單據" in html_text)
        self.assertIn("RPA", html_text)
        self.assertIn("Studio", html_text)
        self.assertIn("AgenticDoc", html_text)
        print("  ✅ TC-W01: GET / 回傳前端單頁應用程式 PASS")

    def test_tc_w02_sample_docs_list(self):
        req = b"GET /api/sample-docs HTTP/1.1\r\nHost: 127.0.0.1:8080\r\n\r\n"
        h = create_mock_handler(req)
        h.do_GET()
        status, _, body = parse_response(h.wfile)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("documents", data)
        self.assertGreaterEqual(len(data["documents"]), 5)
        print("  ✅ TC-W02: GET /api/sample-docs 回傳單據清冊 PASS")

    def test_tc_w03_analyze_sample_coa(self):
        req = b"POST /api/analyze-sample?doc_id=COA-HD-2606-0418 HTTP/1.1\r\nHost: 127.0.0.1:8080\r\nContent-Length: 0\r\n\r\n"
        h = create_mock_handler(req)
        h.do_POST()
        status, _, body = parse_response(h.wfile)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["doc_id"], "COA-HD-2606-0418")
        self.assertIn("extracted_fields", data)
        fields = data["extracted_fields"]
        self.assertEqual(fields.get("vendor_batch"), "LAM-2606-0418")
        self.assertEqual(fields.get("claimed_tg_c"), 176.0)
        self.assertTrue(data.get("image_data", "").startswith("data:image/"))
        print(f"  ✅ TC-W03: POST /api/analyze-sample 分析預設 CoA PASS (耗時 {data.get('ocr_seconds')}s)")

    def test_tc_w04_upload_file(self):
        sample_img = BASE_DIR / "plan_doc/scenario/sample_docs/PO-LY-2608-0075.png"
        self.assertTrue(sample_img.exists())

        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        body = io.BytesIO()
        body.write(f"--{boundary}\r\n".encode("utf-8"))
        body.write(b'Content-Disposition: form-data; name="file"; filename="test_po.png"\r\n')
        body.write(b"Content-Type: image/png\r\n\r\n")
        with open(sample_img, "rb") as f:
            body.write(f.read())
        body.write(f"\r\n--{boundary}--\r\n".encode("utf-8"))
        payload = body.getvalue()

        header = (
            f"POST /api/upload HTTP/1.1\r\n"
            f"Host: 127.0.0.1:8080\r\n"
            f"Content-Type: multipart/form-data; boundary={boundary}\r\n"
            f"Content-Length: {len(payload)}\r\n\r\n"
        ).encode("utf-8")

        h = create_mock_handler(header + payload)
        h.do_POST()
        status, _, resp_body = parse_response(h.wfile)
        self.assertEqual(status, 200)
        data = json.loads(resp_body.decode("utf-8"))
        self.assertIn("extracted_fields", data)
        fields = data["extracted_fields"]
        self.assertEqual(fields.get("po_number"), "LY-PO-2608-0075")
        self.assertEqual(fields.get("total_amount_usd"), 77000.0)
        print(f"  ✅ TC-W04: POST /api/upload 上傳並辨識凌雲電子 PO PASS (耗時 {data.get('ocr_seconds')}s)")

    def test_tc_w05_health_check(self):
        req = b"GET /api/health HTTP/1.1\r\nHost: 127.0.0.1:8080\r\n\r\n"
        h = create_mock_handler(req)
        h.do_GET()
        status, _, body = parse_response(h.wfile)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "healthy")
        print("  ✅ TC-W05: GET /api/health 健康檢查 PASS")

    def test_tc_w06_rpa_templates(self):
        req = b"GET /api/rpa/templates HTTP/1.1\r\nHost: 127.0.0.1:8080\r\n\r\n"
        h = create_mock_handler(req)
        h.do_GET()
        status, _, body = parse_response(h.wfile)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("templates", data)
        self.assertTrue(len(data["templates"]) >= 3)
        print("  ✅ TC-W06: GET /api/rpa/templates 範本清單檢索 PASS")

    def test_tc_w07_rpa_execute_api(self):
        payload_dict = {
            "script_text": "前往網址: data:text/html;charset=utf-8,<h1>RPA API Test</h1>\n截圖說明: 成功",
            "mode": "backend",
            "default_on_error": "abort",
            "slow_mo_ms": 0
        }
        body_bytes = json.dumps(payload_dict).encode("utf-8")
        req = (
            f"POST /api/rpa/execute HTTP/1.1\r\n"
            f"Host: 127.0.0.1:8080\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body_bytes)}\r\n\r\n"
        ).encode("utf-8") + body_bytes

        h = create_mock_handler(req)
        h.do_POST()
        status, _, resp_body = parse_response(h.wfile)
        self.assertEqual(status, 200)
        data = json.loads(resp_body.decode("utf-8"))
        self.assertEqual(data.get("status"), "SUCCESS")
        self.assertEqual(data.get("total_steps"), 2)
        print("  ✅ TC-W07: POST /api/rpa/execute 自然語言 RPA 端點整合測試 PASS")

    def test_tc_w08_rpa_real_chrome_script_parsing(self):
        """驗證真實 Chrome 直通模式對自然語言指令之語意解析與參數傳遞 (李聖傑 + 精選 + 截圖)"""
        from unittest.mock import patch

        user_script = (
            "喚醒日常真實瀏覽器: Google Chrome\n"
            "前往網址: https://www.youtube.com\n"
            "在「搜尋」輸入: 李聖傑\n"
            "按下鍵盤: Enter\n"
            "如果失敗: 跳過\n"
            "點擊包含文字: 精選\n"
            "截圖說明: 真實帳號視窗持續播放中"
        )

        payload_dict = {
            "script_text": user_script,
            "mode": "real_chrome",
            "default_on_error": "skip",
        }
        body_bytes = json.dumps(payload_dict).encode("utf-8")
        req = (
            f"POST /api/rpa/execute HTTP/1.1\r\n"
            f"Host: 127.0.0.1:8080\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body_bytes)}\r\n\r\n"
        ).encode("utf-8") + body_bytes

        with patch("src.rpa.youtube_flow.RealChromeYouTubeFlow") as MockFlowClass:
            mock_flow = MockFlowClass.return_value
            mock_flow.run.return_value = True
            mock_flow.execution_steps = [
                {"step_id": 1, "action_type": "GOTO", "description": "開啟 Chrome", "status": "PASS", "duration_s": 0.5},
                {"step_id": 2, "action_type": "CLICK", "description": "視覺鎖定精選並點擊", "status": "PASS", "duration_s": 1.0},
            ]
            mock_flow.last_screenshot_base64 = "MOCK_BASE64_IMAGE"

            h = create_mock_handler(req)
            h.do_POST()
            status, _, resp_body = parse_response(h.wfile)
            self.assertEqual(status, 200)
            data = json.loads(resp_body.decode("utf-8"))
            self.assertEqual(data.get("status"), "SUCCESS")
            self.assertEqual(data.get("mode"), "real_chrome")
            self.assertEqual(data.get("total_steps"), 2)
            MockFlowClass.assert_called_once_with(
                keyword="李聖傑",
                target_click_text="精選",
                screenshot_desc="真實帳號視窗持續播放中",
                direct_search=True,
            )
            print("  ✅ TC-W08: POST /api/rpa/execute 真實 Chrome 模式自然語言指令解析與目標傳參 PASS")


if __name__ == "__main__":
    unittest.main()
