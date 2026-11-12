#!/usr/bin/env python3
"""
[使用工具] Playwright, PyAutoGUI, RapidOCR, Temporal, Pydantic v2
[設計目的] 提供使用者端「真實畫面 RPA ＋ 真實 RapidOCR 辨識 ＋ Temporal 狀態機調度」的即時實機體驗。
[程式說明] 包含：1. 實體發票網頁生成與 Playwright 截圖 2. RapidOCR 真實文字與座標框解析 3. 桌面螢幕即時截圖與辨識 4. Temporal 狀態機全流程驅動。
[修改日期] 2026-11-08
[修改概要] 建立真實Playwright與RapidOCR實體測試展示入口 (約30字)
[關聯測試] report/BDD/DBB_Pre_Moreem_20261108.md - Feature 2
[工作日誌] report/work_record/work_record_20261108.md
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rpa.rpa_router import AutoRPARouter
from src.ocr.ocr_pipeline import VisualOCRPipeline
from src.orchestration.temporal_workflow import TemporalRPAWorkflowController, InMemoryDocumentStagingRepository


def generate_sample_web_invoice(html_path: str) -> None:
    """產生一張精緻的 NAND/DRAM 採購發票 HTML 供 Playwright 實體載入"""
    content = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>半導體供應商發票門戶 (Vendor Portal)</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8fafc; padding: 40px; }
  .invoice-card { max-width: 650px; margin: auto; background: white; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); padding: 32px; border: 1px solid #e2e8f0; }
  .header { border-bottom: 2px solid #3b82f6; padding-bottom: 16px; margin-bottom: 24px; }
  .title { font-size: 24px; font-weight: bold; color: #1e293b; margin: 0; }
  .row { display: flex; justify-content: space-between; margin: 12px 0; font-size: 15px; }
  .label { color: #64748b; font-weight: 500; }
  .value { color: #0f172a; font-weight: 600; }
  .amount-box { background: #eff6ff; border-radius: 8px; padding: 16px; text-align: right; margin-top: 24px; }
  .total-label { font-size: 14px; color: #1d4ed8; }
  .total-amount { font-size: 28px; font-weight: 800; color: #1e40af; }
</style>
</head>
<body>
<div class="invoice-card">
  <div class="header">
    <h1 class="title">電子採購單發票憑單 (Electronic Tax Invoice)</h1>
  </div>
  <div class="row">
    <span class="label">採購單號 (Purchase Order):</span>
    <span class="value">PO-2026-8888</span>
  </div>
  <div class="row">
    <span class="label">廠商統一編號 (Vendor Tax ID):</span>
    <span class="value">12345675</span>
  </div>
  <div class="row">
    <span class="label">採購品項 (Product Specification):</span>
    <span class="value">DDR5 64GB ECC RDIMM 5600MT/s (500 PCS)</span>
  </div>
  <div class="row">
    <span class="label">驗收單狀態 (Goods Receipt):</span>
    <span class="value" style="color: #16a34a;">已檢驗合格入庫 (PASSED)</span>
  </div>
  <div class="amount-box">
    <div class="total-label">應付總金額 (Invoice Total Amount)</div>
    <div class="total-amount">NT$ 1,850,000</div>
  </div>
</div>
</body>
</html>
"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    print("=" * 70)
    print("🎬 開始實機展示：地端 RPA 截圖 ➔ RapidOCR 辨識 ➔ Temporal 狀態機調度")
    print("   (模式：完全不接 DB，純粹驗證畫面操作、光學識別與 Pydantic 防漂移)")
    print("=" * 70)

    # 1. 產生真實測試發票網頁
    tmp_dir = PROJECT_ROOT / "report" / "test_results" / "demo"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    sample_html = str(tmp_dir / "sample_invoice.html")
    generate_sample_web_invoice(sample_html)
    print(f"\n[Step 1] 已生成真實半導體發票 HTML: {sample_html}")

    # 2. 啟動 Playwright 進行實體網頁開啟與高品質截圖
    print("\n[Step 2] 啟動 Playwright Chromium 引擎，實體渲染並截取網頁畫面...")
    router = AutoRPARouter(output_dir=str(tmp_dir))
    target_url = f"file://{sample_html}"
    rpa_result = router.capture_target(doc_id="INV-LIVE-8888", target=target_url)
    print(f"  📸 RPA 截圖已儲存: {rpa_result.image_path}")
    print(f"  ⚙️ 使用引擎: {rpa_result.engine_used} | 螢幕倍率: {rpa_result.scale_factor}")

    # 3. 呼叫真實 RapidOCR 進行座標框與文字光學識別
    print("\n[Step 3] 呼叫 RapidOCR (ONNX Runtime) 執行光學文字識別...")
    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR()
    ocr_raw, elapse = ocr(rpa_result.image_path)

    print(f"  ⚡ OCR 辨識耗時: {sum(elapse):.3f} 秒")
    print(f"  🔍 成功辨識出 {len(ocr_raw)} 行文字區塊：")
    for idx, item in enumerate(ocr_raw[:6], 1):
        box, text, score = item[0], item[1], item[2]
        print(f"    [{idx}] 置信度 {score:.4f} | 文字: '{text}'")

    # 4. 透過 Temporal 狀態機進行單據全生命週期調度與 Pydantic 防漂移
    print("\n[Step 4] 啟動 Temporal 持久化狀態機調度單據工作流...")
    workflow_id = "WF-LIVE-PO-8888"
    controller = TemporalRPAWorkflowController(workflow_id=workflow_id)
    wf_result = controller.execute(
        doc_meta={
            "doc_id": "INV-LIVE-8888",
            "batch_id": "BATCH-LIVE",
            "target": target_url,
        },
        simulate_replay=False,
    )

    print(f"  🎉 Temporal 工作流執行狀態: {wf_result['status']}")
    print(f"  📦 經 Pydantic 防漂移清洗後之結構化資料：")
    print(f"     • 採購單號 (PO Number):    {wf_result['po_number']}")
    print(f"     • 發票金額 (Invoice Total): {wf_result['invoice_total']} (已自動清洗貨幣符號與千分位)")
    print(f"     • 最低 OCR 信心度:         {wf_result['min_ocr_score']}")
    print(f"     • 落地模式:                {wf_result['db_connection']}")

    # 5. 輸出成果報告
    result_json_path = tmp_dir / "live_verification_result.json"
    with open(result_json_path, "w", encoding="utf-8") as f:
        json.dump(wf_result, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print(f"🏁 實機驗證圓滿完成！結構化成果已產出至: {result_json_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()

