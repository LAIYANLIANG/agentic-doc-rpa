"""
[使用工具]: Python 3.11 http.server, RapidOCR (rapidocr_onnxruntime), Quartz / AppKit, Base64
[設計目的]: 實現選項 A【Web 文件上傳與審計平台】伺服器端點。支援 PDF 與圖片原生上傳解析、CORS 跨域支援 (容許 file:// 本地開啟 HTML)、結構化 OCR 抽取與商業風控自動審計。
[程式說明]:
    1. 整合 macOS 原生 Quartz (PDFKit) 圖形子系統：
       - `render_pdf_to_png(pdf_path, output_png_path, page_num=1, dpi=150)`: 無須額外安裝 poppler 或大型依賴，以高解析度 (150 DPI) 將 PDF 首頁原生光柵化為 PNG 影像。
    2. 支援全面 CORS 跨域標頭 (Access-Control-Allow-Origin: *)，即使使用者直接雙擊以 file:// 協定開啟 index.html，亦能無縫呼叫 http://127.0.0.1:8080/api。
    3. 自動單據型態辨識 (CoA, Customer PO, FA 報告, IQC 紀錄, 工程圖) 與審計警示提示。
[修改日期]: 2026-11-10
[修改概要]: 新增原生 Quartz PDF 轉換支援與 CORS 跨域標頭，修復 file:// 開啟時的 fetch 失敗問題
[輸入參數]: CLI 參數 --port (預設 8080), --host (預設 127.0.0.1)
[輸出結果]: 本機 Web 伺服器與 JSON API
[關聯測試]: src/web_audit/test_server.py
[工作日誌]: report/work_record/work_record_20261110.md
"""

import argparse
import base64
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="cgi")
import cgi
import io
import json
import os
import re
import sys
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE_DIR = Path(__file__).resolve().parents[2]
WEB_DIR = BASE_DIR / "src/web_audit"
TEMPLATE_PATH = WEB_DIR / "templates/index.html"
UPLOADS_DIR = WEB_DIR / "uploads"
SAMPLE_DOCS_DIR = BASE_DIR / "plan_doc/scenario/sample_docs"
MANIFEST_PATH = SAMPLE_DOCS_DIR / "manifest.json"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# 匯入 OCR 抽取模組
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
from src.scenario.ocr_extractor import ScenarioOCRExtractor, field_matches

# 嘗試載入 macOS 原生 Quartz 以支援 PDF 原生光柵化
try:
    import Quartz
    from Foundation import NSURL
    HAS_QUARTZ_PDF = True
except ImportError:
    HAS_QUARTZ_PDF = False

GLOBAL_EXTRACTOR: ScenarioOCRExtractor = None


def get_extractor() -> ScenarioOCRExtractor:
    global GLOBAL_EXTRACTOR
    if GLOBAL_EXTRACTOR is None:
        GLOBAL_EXTRACTOR = ScenarioOCRExtractor()
    return GLOBAL_EXTRACTOR


def render_pdf_to_png(pdf_path: Path, output_png_path: Path, page_num: int = 1, dpi: int = 150) -> bool:
    """
    [Method]: render_pdf_to_png
    [設計目的]: 利用 macOS 原生 Quartz 將 PDF 首頁轉換為 150 DPI 高解析度 PNG 影像
    """
    if not HAS_QUARTZ_PDF:
        print("⚠️ 未安裝 pyobjc-framework-Quartz，無法原生轉換 PDF")
        return False
    try:
        url = NSURL.fileURLWithPath_(str(pdf_path))
        pdf = Quartz.CGPDFDocumentCreateWithURL(url)
        if not pdf:
            return False
        total_pages = Quartz.CGPDFDocumentGetNumberOfPages(pdf)
        if total_pages < 1:
            return False

        page = Quartz.CGPDFDocumentGetPage(pdf, page_num)
        rect = Quartz.CGPDFPageGetBoxRect(page, Quartz.kCGPDFMediaBox)

        scale = dpi / 72.0
        width = int(rect.size.width * scale)
        height = int(rect.size.height * scale)

        cs = Quartz.CGColorSpaceCreateDeviceRGB()
        ctx = Quartz.CGBitmapContextCreate(None, width, height, 8, width * 4, cs, Quartz.kCGImageAlphaPremultipliedLast)

        # 填入白色底色
        Quartz.CGContextSetRGBFillColor(ctx, 1.0, 1.0, 1.0, 1.0)
        Quartz.CGContextFillRect(ctx, Quartz.CGRectMake(0, 0, width, height))

        # 縮放繪製 PDF 頁面
        Quartz.CGContextScaleCTM(ctx, scale, scale)
        Quartz.CGContextDrawPDFPage(ctx, page)

        img = Quartz.CGBitmapContextCreateImage(ctx)
        dest_url = NSURL.fileURLWithPath_(str(output_png_path))
        dest = Quartz.CGImageDestinationCreateWithURL(dest_url, "public.png", 1, None)
        Quartz.CGImageDestinationAddImage(dest, img, None)
        Quartz.CGImageDestinationFinalize(dest)
        return True
    except Exception as e:
        print(f"❌ PDF 轉換 PNG 失敗: {e}")
        return False


def image_to_base64_data_url(img_path: Path) -> str:
    ext = img_path.suffix.lower().replace(".", "")
    if ext == "jpg":
        ext = "jpeg"
    with open(img_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/{ext};base64,{data}"


class WebAuditRequestHandler(BaseHTTPRequestHandler):

    def _send_json(self, data: dict, status: int = HTTPStatus.OK):
        try:
            payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.end_headers()
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _send_html(self, html_content: str, status: int = HTTPStatus.OK):
        try:
            payload = html_content.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self):
        url = urlparse(self.path)

        if url.path == "/" or url.path == "/index.html":
            if TEMPLATE_PATH.exists():
                with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
                    content = f.read()
                self._send_html(content)
            else:
                self._send_html("<h1>Template not found</h1>", status=HTTPStatus.NOT_FOUND)
            return

        elif url.path == "/api/sample-docs":
            ext = get_extractor()
            self._send_json({"documents": ext.manifest.get("documents", [])})
            return

        elif url.path == "/api/health":
            self._send_json({"status": "healthy", "service": "Web Document OCR & Audit Platform", "timestamp": time.time()})
            return

        elif url.path == "/api/rpa/templates":
            templates = [
                {
                    "id": "youtube_music",
                    "title": "🎵 YouTube 自動搜尋與播放讀書長音樂 (視窗模式)",
                    "mode": "window",
                    "default_on_error": "skip",
                    "script": "前往網址: https://www.youtube.com\n在「搜尋」輸入: 讀書長音樂\n按下鍵盤: Enter\n如果失敗: 跳過\n點擊包含文字: 讀書\n截圖說明: 音樂播放完成存證",
                    "desc": "彈出視窗導航至 YouTube，霓虹光圈高亮搜尋框並輸入，選取長音樂影片播放。"
                },
                {
                    "id": "web_audit_auto",
                    "title": "📊 本地 Web 審計平台單據自動上傳核驗 (純地端)",
                    "mode": "window",
                    "default_on_error": "abort",
                    "script": "前往網址: http://127.0.0.1:8080\n點擊按鈕: 上傳並執行 AI 審計\n等待: 2 秒\n截圖說明: 審計不合格警示存證",
                    "desc": "純本地離線自動化，載入單據審計平台並觸發 RapidOCR 與品質規則比對。"
                },
                {
                    "id": "form_submit_demo",
                    "title": "⚙️ 例外策略示範：遇到錯誤自動跳過並截圖存證",
                    "mode": "backend",
                    "default_on_error": "skip",
                    "script": "前往網址: http://127.0.0.1:8080\n在「搜尋」輸入: PO-LY-2608-0075\n按下鍵盤: Enter\n如果失敗: 跳過\n點擊包含文字: 不存在的按鈕名稱\n截圖說明: 最終狀態存證",
                    "desc": "示範如果失敗時依自然語言宣告自動跳過，並以截圖存證。"
                }
            ]
            self._send_json({"templates": templates})
            return

        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self):
        url = urlparse(self.path)

        if url.path == "/api/analyze-sample":
            query = parse_qs(url.query)
            doc_id = query.get("doc_id", [""])[0]
            if not doc_id:
                self._send_json({"error": "Missing doc_id"}, status=HTTPStatus.BAD_REQUEST)
                return

            ext = get_extractor()
            target_item = None
            for item in ext.manifest["documents"]:
                if item["doc_id"].lower() == doc_id.lower():
                    target_item = item
                    break

            if not target_item:
                self._send_json({"error": f"Sample document '{doc_id}' not found"}, status=HTTPStatus.NOT_FOUND)
                return

            png_path = SAMPLE_DOCS_DIR / target_item["png_file"]
            self._process_ocr_and_respond(png_path, doc_id=target_item["doc_id"], doc_name=target_item["doc_name"])

        elif url.path == "/api/upload":
            content_type = self.headers.get("Content-Type", "")
            if not content_type.startswith("multipart/form-data"):
                self._send_json({"error": "Content-Type must be multipart/form-data"}, status=HTTPStatus.BAD_REQUEST)
                return

            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 30 * 1024 * 1024:
                self._send_json({"error": "File size exceeds 30MB limit"}, status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
                return

            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": content_type}
            )

            if "file" not in form:
                self._send_json({"error": "No 'file' field found in form upload"}, status=HTTPStatus.BAD_REQUEST)
                return

            file_item = form["file"]
            filename = file_item.filename or "upload.png"
            file_bytes = file_item.file.read()

            save_base = f"upload_{int(time.time() * 1000)}"
            saved_raw_path = UPLOADS_DIR / f"{save_base}_{Path(filename).name}"

            with open(saved_raw_path, "wb") as f:
                f.write(file_bytes)

            print(f"📥 收到上傳檔案：{filename} ({len(file_bytes)} bytes)")

            # 若為 PDF，進行原生 Quartz 轉圖
            if filename.lower().endswith(".pdf"):
                converted_png = UPLOADS_DIR / f"{save_base}_converted.png"
                print(f"🔄 偵測到 PDF 文件，正在使用 macOS Quartz 進行原生高解析度轉圖...")
                success = render_pdf_to_png(saved_raw_path, converted_png, dpi=150)
                if not success:
                    self._send_json({"error": "Failed to render PDF document to image via Quartz"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                    return
                image_to_process = converted_png
            else:
                image_to_process = saved_raw_path

            self._process_ocr_and_respond(image_to_process, doc_id="UPLOADED", doc_name=filename)

        elif url.path == "/api/rpa/execute":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode("utf-8"))
            except Exception as e:
                self._send_json({"error": f"Invalid JSON payload: {e}"}, status=HTTPStatus.BAD_REQUEST)
                return

            script_text = payload.get("script_text", "")
            mode = payload.get("mode", "window")
            default_on_error = payload.get("default_on_error", "abort")
            slow_mo = int(payload.get("slow_mo_ms", 1000))
            keep_open = bool(payload.get("keep_open", False))
            use_profile = bool(payload.get("use_persistent_profile", True))

            print(f"🤖 收到 RPA 工作流程執行請求：模式={mode}, 保持開啟={keep_open}, 記住登入={use_profile}, 預設策略={default_on_error}")

            if mode == "real_chrome":
                print("🌐 啟動『真實日常 Chrome 帳號直通模式』...")
                from src.rpa.natural_language_rpa import NLScriptParser
                from src.rpa.youtube_flow import RealChromeYouTubeFlow

                parser = NLScriptParser()
                parsed_actions = parser.parse(script_text, default_on_error=default_on_error)

                # 動態從自然語言解析動作中提取搜尋關鍵字、點擊標的與截圖說明
                kw = None
                target_click = None
                screenshot_desc = "真實帳號視窗持續播放中"

                for act in parsed_actions:
                    if act.action_type == "TYPE":
                        kw = act.params.get("value")
                    elif act.action_type == "CLICK":
                        target_click = act.params.get("target")
                    elif act.action_type == "SCREENSHOT":
                        screenshot_desc = act.params.get("desc", screenshot_desc)

                # 若未特別解析到 TYPE 動作，備用正則推導或預設
                if not kw:
                    m_kw = re.search(r"輸入[:：\s]+(.+)", script_text)
                    kw = m_kw.group(1).strip() if m_kw else "讀書長音樂"

                if not target_click:
                    m_click = re.search(r"(?:點擊|包含文字)[:：\s]+(.+)", script_text)
                    if m_click:
                        target_click = m_click.group(1).strip()

                print(f"🎯 自然語言指令抽取結果：搜尋關鍵字=『{kw}』, 目標關鍵字=『{target_click}』, 截圖說明=『{screenshot_desc}』")

                flow = RealChromeYouTubeFlow(
                    keyword=kw,
                    target_click_text=target_click,
                    screenshot_desc=screenshot_desc,
                    direct_search=True,
                )
                success = flow.run()

                steps_data = []
                for st in flow.execution_steps:
                    snap_b64 = st.get("screenshot_base64") or flow.last_screenshot_base64
                    steps_data.append({
                        "step_id": st["step_id"],
                        "action_type": st["action_type"],
                        "description": st["description"],
                        "status": st["status"],
                        "duration_s": st["duration_s"],
                        "error_msg": st.get("error_msg"),
                        "screenshot": f"data:image/jpeg;base64,{snap_b64}" if snap_b64 else None,
                    })

                total_dur = round(sum(s.get("duration_s", 0.0) for s in steps_data), 2)
                passed_cnt = sum(1 for s in steps_data if s["status"] == "PASS")
                failed_cnt = sum(1 for s in steps_data if s["status"] == "FAIL")

                self._send_json({
                    "status": "SUCCESS" if success else "FAILED",
                    "mode": "real_chrome",
                    "total_steps": len(steps_data),
                    "passed_steps": passed_cnt,
                    "failed_steps": failed_cnt,
                    "skipped_steps": 0,
                    "total_duration_s": total_dur,
                    "steps": steps_data,
                    "final_screenshot": f"data:image/jpeg;base64,{flow.last_screenshot_base64}" if flow.last_screenshot_base64 else None,
                })
                return

            from src.rpa.natural_language_rpa import NLRPARunner
            runner = NLRPARunner(
                mode=mode,
                slow_mo_ms=slow_mo,
                keep_open=keep_open,
                use_persistent_profile=use_profile,
            )
            res = runner.execute_script(script_text, default_on_error=default_on_error)
            self._send_json(res)
            return

        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def _process_ocr_and_respond(self, img_path: Path, doc_id: str, doc_name: str):
        ext = get_extractor()
        t0 = time.time()
        raw_result, _ = ext.ocr(str(img_path))
        ocr_dur = time.time() - t0

        lines: List[str] = []
        raw_blocks: List[dict] = []
        if raw_result:
            for item in raw_result:
                box = item[0]
                text = item[1].strip()
                score = round(float(item[2]), 4)
                if text:
                    lines.append(text)
                    raw_blocks.append({"box": box, "text": text, "score": score})

        full_text = " \n ".join(lines)
        detected_type = "UNKNOWN"
        extracted = {}

        if "出廠檢驗" in full_text or "COA" in full_text or "CERTIFICATE" in full_text or "檢驗證明" in full_text:
            detected_type = "CoA (出廠檢驗證明)"
            extracted = ext.parse_coa(lines)
        elif "PURCHASE" in full_text or "採購單" in full_text or "探購單" in full_text or "LY-PO" in full_text or "凌雲電子" in full_text:
            detected_type = "Customer PO (客戶採購單)"
            extracted = ext.parse_customer_po(lines)
        elif "FAILURE" in full_text or "FA-" in full_text or "失效分析" in full_text or "通孔" in full_text:
            detected_type = "FA Report (失效分析報告)"
            extracted = ext.parse_fa_report(lines)
        elif "IQC" in full_text or "進料" in full_text or "010000003301" in full_text or "抽驗" in full_text:
            detected_type = "IQC Report (進料檢驗紀錄)"
            extracted = ext.parse_iqc_report(lines)
        elif "DWG-SUB" in full_text or "規格書" in full_text or "藍圖" in full_text or "2-Layer" in full_text:
            detected_type = "Drawing & Spec (工程規格圖)"
            extracted = ext.parse_spec_drawing(lines)
        else:
            detected_type = "通用商業文件"
            m_po = re.search(r"(\b45000\d{5}\b)", full_text)
            if m_po:
                extracted["po_number"] = m_po.group(1)
            m_batch = re.search(r"([A-Z0-9]{3,}-[A-Z0-9]{4,}-[A-Z0-9]+)", full_text)
            if m_batch:
                extracted["batch_no"] = m_batch.group(1)

        audit_notes: List[str] = []
        if "claimed_tg_c" in extracted:
            audit_notes.append(f"供應商 CoA 宣稱玻璃轉移溫度 Tg 為 <strong>{extracted['claimed_tg_c']}°C</strong> (聲稱 PASS)")
        if "retested_tg_c" in extracted:
            retested = extracted["retested_tg_c"]
            spec_min = extracted.get("spec_tg_c_min", 175.0)
            if retested < spec_min:
                audit_notes.append(f"🚨 <strong>重大品質異常警告：</strong>FA 實驗室復測 Tg 僅 <strong>{retested}°C</strong>，低於技術標準下限 {spec_min}°C！直接證實上游原料商層壓板瑕疵。")
        if extracted.get("tg_tested") is False:
            audit_notes.append("⚠️ <strong>內部作業流程缺失：</strong>IQC 紀錄證實未執行破壞性 Tg 抽驗，註記為『免驗放行』，導致瑕疵原料流入投產工單。")
        if "quantity" in extracted and "unit_price_usd" in extracted and "total_amount_usd" in extracted:
            q = extracted["quantity"]
            p = extracted["unit_price_usd"]
            tot = extracted["total_amount_usd"]
            if round(q * p, 2) == tot:
                audit_notes.append(f"✅ <strong>財務金額勾稽無誤：</strong>數量 {q:,} PCS × 單價 ${p:.2f} = 總金額 ${tot:,.2f} USD")
            else:
                audit_notes.append(f"🚨 <strong>金額不符警告：</strong>{q} × ${p} ≠ 總額 ${tot}")

        try:
            image_data = image_to_base64_data_url(img_path)
        except Exception:
            image_data = ""

        resp = {
            "doc_id": doc_id,
            "doc_name": doc_name,
            "detected_type": detected_type,
            "ocr_seconds": round(ocr_dur, 2),
            "total_text_blocks": len(lines),
            "extracted_fields": extracted,
            "audit_notes": audit_notes,
            "raw_lines": lines,
            "raw_blocks": raw_blocks,
            "image_data": image_data,
        }
        self._send_json(resp)


def run_server(port: int = 8080, host: str = "127.0.0.1"):
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, WebAuditRequestHandler)
    print(f"🌟 宏芯記憶體科技 ｜ 智慧單據 OCR 視覺審計平台已啟動！")
    print(f"🌐 服務網址：http://{host}:{port}")
    print(f"📁 上傳暫存目錄：{UPLOADS_DIR}")
    print("💡 按 Ctrl+C 可隨時停止服務。")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 正在停止服務...")
        httpd.server_close()
        print("✅ 服務已正常停止。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Web Document OCR & Quality Audit Platform Server")
    parser.add_argument("--port", type=int, default=8080, help="Web 伺服器監聽通訊埠 (預設 8080)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Web 伺服器綁定 IP (預設 127.0.0.1)")
    args = parser.parse_args()

    run_server(port=args.port, host=args.host)
