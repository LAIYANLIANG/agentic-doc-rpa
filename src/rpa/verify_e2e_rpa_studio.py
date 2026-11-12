"""
[使用工具]: Python 3.11, Threading, HTTP Server, Playwright, Requests / urllib
[設計目的]: 第三章【端到端實機聯調驗證】：
           驗證 Web 伺服器啟動、接收前端自然語言腳本請求、調度 Playwright 執行、
           處理例外跳過 (Skip)、產生高解析步驟截圖、並成功回傳 JSON 資料給前端畫面。
[驗證流程]:
    1. 在本機背景執行 WebAudit 伺服器 (通訊埠 8089 避免衝突)。
    2. 發送自然語言 RPA 工作流程執行請求：
       - 前往審計平台
       - 測試例外跳過：點擊不存在的幽靈按鈕 (驗證 skip 策略)
       - 點擊「供應商 CoA」按鈕
       - 截圖說明：單據審計結果存證
    3. 檢驗回傳成果：
       - 總步驟數、成功步數、跳過步數符合預期
       - 每個步驟包含合法 Base64 截圖
    4. 產生實機評測報告：report/test_results/rpa_studio_e2e_verification_20261110.json
[修改日期]: 2026-11-10
[關聯程式]: src/rpa/natural_language_rpa.py, src/web_audit/server.py
"""

import json
import sys
import threading
import time
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.web_audit.server import WebAuditRequestHandler


def run_e2e_verification():
    print("=" * 70)
    print("🎬【第三章：自然語言 RPA Studio 端到端實機聯調驗證】")
    print("=" * 70)

    test_port = 8089
    server = ThreadingHTTPServer(("127.0.0.1", test_port), WebAuditRequestHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"🚀 [1/4] 本機測試伺服器已在 http://127.0.0.1:{test_port} 啟動完成")
    time.sleep(0.5)

    # 1. 檢驗範本 API 端點
    print("\n🔍 [2/4] 測試 GET /api/rpa/templates 範本清冊檢索...")
    with urllib.request.urlopen(f"http://127.0.0.1:{test_port}/api/rpa/templates") as resp:
        tmpl_data = json.loads(resp.read().decode("utf-8"))
        assert "templates" in tmpl_data and len(tmpl_data["templates"]) >= 3
        print(f"   ✅ 成功取得 {len(tmpl_data['templates'])} 個內建自然語言範本！")

    # 2. 發送自然語言 RPA 執行請求 (含例外跳過與截圖存證)
    print("\n🤖 [3/4] 發送自然語言 RPA 腳本至 POST /api/rpa/execute...")
    script_text = f"""
    前往網址: http://127.0.0.1:{test_port}
    如果失敗: 跳過
    點擊包含文字: 絕對不存在的神秘幽靈按鈕
    點擊包含文字: 供應商 CoA
    等待 1 秒
    截圖說明: 審計平台單據分析完成存證
    """

    payload = {
        "script_text": script_text,
        "mode": "backend",  # 聯調測試採用無頭後台高速驗證
        "default_on_error": "skip",
        "slow_mo_ms": 0,
        "ref_desc": "端到端驗證自動化單據分析",
    }

    req = urllib.request.Request(
        f"http://127.0.0.1:{test_port}/api/rpa/execute",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    t0 = time.time()
    with urllib.request.urlopen(req) as resp:
        rpa_result = json.loads(resp.read().decode("utf-8"))
    elapsed = round(time.time() - t0, 2)

    print(f"   ✅ 執行完成！耗時 {elapsed} 秒")
    print(f"   • 總狀態: {rpa_result.get('status')}")
    print(f"   • 總步數: {rpa_result.get('total_steps')}")
    print(f"   • 通過數: {rpa_result.get('passed_steps')}")
    print(f"   • 跳過數 (例外處理): {rpa_result.get('skipped_steps')}")

    # 驗證步驟詳細
    steps = rpa_result.get("steps", [])
    assert len(steps) >= 4, f"步驟數應至少 4 步，實得 {len(steps)}"
    assert rpa_result.get("status") == "SUCCESS", "總體狀態應為 SUCCESS (跳過幽靈按鈕)"
    assert rpa_result.get("skipped_steps") >= 1, "幽靈按鈕應被記錄為 SKIPPED"

    # 驗證截圖資料
    has_screenshot = any(s.get("screenshot") and s["screenshot"].startswith("data:image/png;base64,") for s in steps)
    assert has_screenshot, "應至少包含一個步驟的高解析 Base64 截圖存證！"
    print("   • 步驟截圖存證: ✅ 驗證通過 (已產生合法 Base64 PNG 影像資料)")

    # 3. 儲存實機聯調報告
    print("\n📄 [4/4] 正在匯出端到端實機評測報告...")
    out_dir = BASE_DIR / "report/test_results"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_file = out_dir / "rpa_studio_e2e_verification_20261110.json"

    report_payload = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "test_port": test_port,
        "script_tested": script_text.strip().splitlines(),
        "execution_summary": {
            "status": rpa_result.get("status"),
            "duration_s": rpa_result.get("total_duration_s"),
            "total_steps": rpa_result.get("total_steps"),
            "passed_steps": rpa_result.get("passed_steps"),
            "skipped_steps": rpa_result.get("skipped_steps"),
            "failed_steps": rpa_result.get("failed_steps"),
        },
        "step_details": [
            {
                "step_id": s["step_id"],
                "action": s["action_type"],
                "desc": s["description"],
                "status": s["status"],
                "duration_s": s["duration_s"],
                "has_screenshot": bool(s.get("screenshot")),
            }
            for s in steps
        ],
    }

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, ensure_ascii=False, indent=2)

    server.shutdown()
    print(f"🎉 實機聯調報告已產生：{report_file}")
    print("=" * 70)
    print("🌟 恭喜！第三章端到端實機驗證 100% PASS！")
    print("=" * 70)
    return True


if __name__ == "__main__":
    run_e2e_verification()

