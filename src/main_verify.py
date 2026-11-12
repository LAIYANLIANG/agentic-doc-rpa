#!/usr/bin/env python3
"""
[使用工具] Python 3.11, Pydantic v2, Temporal State Machine, Playwright/Quartz Router
[設計目的] 端到端 (End-to-End) 整合驗證入口，檢驗 Airflow 切批、Temporal 主控 RPA 與 OCR 全流程。
[程式說明] 執行六大核心測試，嚴格不接資料庫 (InMemory 落地)，並輸出 JSON 驗收報告供工作日誌追溯。
[修改日期] 2026-11-08
[修改概要] 建立無DB依賴之端到端整合驗收腳本並產出報告 (約30字)
[關聯測試] report/BDD/DBB_Pre_Moreem_20261108.md - 全體 Features & Scenarios
[工作日誌] report/work_record/work_record_20261108.md
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# 將專案根目錄加入模組搜尋路徑
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.schemas import RawInvoiceStagingSchema
from src.rpa.rpa_router import AutoRPARouter
from src.ocr.ocr_pipeline import VisualOCRPipeline
from src.orchestration.temporal_workflow import (
    TemporalRPAWorkflowController,
    InMemoryDocumentStagingRepository,
    LocalDurableEventEngine,
)
from src.orchestration.airflow_macro_dag import fetch_and_chunk_manifests, execute_batch_via_temporal


def run_all_verifications() -> dict:
    """
    [使用工具] Python Test Runner
    [設計目的] 依序執行 6 大單元與整合驗證，檢核系統架構邊界與容錯機制。
    [程式說明] 驗證 Airflow 切批、Temporal 狀態機主控 RPA、OCR 模糊降級、斷點續傳重播與記憶體暫存。
    [修改日期] 2026-11-08
    [修改概要] 整合執行六大架構驗收測試並彙總輸出狀態字典 (約30字)
    [輸入參數] 無
    [輸出結果] dict: 完整測試結果字典包含各項測試之通過狀態
    [關聯測試] report/BDD/DBB_Pre_Moreem_20261108.md
    [工作日誌] report/work_record/work_record_20261108.md
    """
    print("=" * 70)
    print("🚀 啟動地端 RPA + 視覺 OCR + Temporal 持久化狀態機架構整合驗證")
    print("   (執行模式：先不接 DB，純記憶體與 JSON 成果落地；正式庫規格：PostgreSQL)")
    print("=" * 70)

    test_results = {}
    report_dir = PROJECT_ROOT / "report" / "test_results"
    report_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # TC-01: Airflow 宏觀動態切批測試
    # -------------------------------------------------------------------------
    print("\n[TC-01] 驗證 Airflow 宏觀排程切批功能 (600 張單據 ➔ 每批 50 張)...")
    chunks = fetch_and_chunk_manifests(total_docs=600, batch_size=50)
    assert len(chunks) == 12, f"預期切為 12 批，實際切為 {len(chunks)} 批"
    assert len(chunks[0]) == 50, f"預期第 1 批含 50 筆，實際為 {len(chunks[0])} 筆"
    print(f"  ✅ PASS: 成功將 600 張單據切分為 {len(chunks)} 個微批次！")
    test_results["TC-01_Airflow_Chunking"] = "PASS"

    # -------------------------------------------------------------------------
    # TC-02: 雙軌 RPA 路由器探測與視窗定位測試 (Web vs Desktop)
    # -------------------------------------------------------------------------
    print("\n[TC-02] 驗證雙軌 RPA 路由器 (AutoRPARouter) 之協議分派與 Retina 2x 倍率...")
    router = AutoRPARouter()
    web_res = router.capture_target("INV-001", "https://vendor.example.com")
    desktop_res = router.capture_target("INV-002", "window://Microsoft Remote Desktop")
    assert web_res.engine_used == "playwright_dom", f"Web 引擎分派錯誤: {web_res.engine_used}"
    assert desktop_res.engine_used == "quartz_ocr", f"桌面引擎分派錯誤: {desktop_res.engine_used}"
    print(f"  ✅ PASS: Web 標的正確分派至 Playwright；桌面標的正確分派至 Quartz (Retina Scale={web_res.scale_factor})！")
    test_results["TC-02_RPA_Dual_Track_Routing"] = "PASS"

    # -------------------------------------------------------------------------
    # TC-03: 視覺 OCR 座標抽取與置信度門檻檢驗測試 (含 Pre-mortem 模糊降級)
    # -------------------------------------------------------------------------
    print("\n[TC-03] 驗證視覺 OCR 管線 (RapidOCR) 與 Pre-mortem 模糊影像降級 (Qwen2.5-VL 3B)...")
    ocr_pipe = VisualOCRPipeline(min_confidence=0.80)
    normal_ocr = ocr_pipe.parse_document_image("INV-001", web_res.image_path, simulated_blur=False)
    blur_ocr = ocr_pipe.parse_document_image("INV-002", desktop_res.image_path, simulated_blur=True)
    assert normal_ocr.avg_score >= 0.80 and not normal_ocr.vlm_fallback_triggered
    assert blur_ocr.avg_score < 0.80 and blur_ocr.vlm_fallback_triggered
    print(f"  ✅ PASS: 正常影像置信度={normal_ocr.avg_score} (VLM={normal_ocr.vlm_fallback_triggered})；"
          f"模糊影像置信度={blur_ocr.avg_score} 成功自動啟動 VLM 補償！")
    test_results["TC-03_Visual_OCR_and_VLM_Fallback"] = "PASS"

    # -------------------------------------------------------------------------
    # TC-04: Pydantic v2 結構防漂移與清洗測試 (不接 DB)
    # -------------------------------------------------------------------------
    print("\n[TC-04] 驗證 Pydantic v2 結構防漂移與字串金額自動清洗...")
    doc = RawInvoiceStagingSchema(
        doc_id="INV-TEST-999",
        doc_sha256="a" * 64,
        batch_id="BATCH-00",
        source_target="https://vendor.example.com",
        rpa_engine_used="playwright_dom",
        po_number=" po-2026-8888 ",
        vendor_tax_id="12345675",
        invoice_total="NT$ 1,500,000.00",  # 帶有千分位與貨幣符號
        min_ocr_score=0.96,
        git_commit_sha="test-commit-sha",
        clean_json='{"amount": 1500000}',
        captured_at=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    assert doc.po_number == "PO-2026-8888", "採購單號未正確轉大寫去空白"
    assert doc.invoice_total == 1500000.0, "千分位與金錢符號未正確過濾"
    print(f"  ✅ PASS: 單號正規化為 '{doc.po_number}'，金額清洗為標準數值 {doc.invoice_total}！")
    test_results["TC-04_Pydantic_Schema_Guard"] = "PASS"

    # -------------------------------------------------------------------------
    # TC-05: Temporal 持久化狀態機主控 RPA 與斷點續傳重播測試 (Zero-cost Replay)
    # -------------------------------------------------------------------------
    print("\n[TC-05] 驗證 Temporal 主控 RPA+OCR 流程，以及主機重啟時之步驟級零算力續傳...")
    workflow_id = "WF-DURABLE-SMOKE-TEST"
    LocalDurableEventEngine.clear()
    controller = TemporalRPAWorkflowController(workflow_id=workflow_id)

    # 首次執行（全流程運算）
    first_run = controller.execute({
        "doc_id": "INV-20261108-9001",
        "target": "window://Microsoft Remote Desktop",
        "batch_id": "BATCH-00",
    }, simulate_replay=False)
    assert first_run["status"] == "COMPLETED"
    assert len(first_run["replay_cache_hits"]) == 0

    # 模擬主機重啟/斷電後再次重啟（應直接命中快取，0 算力重複開銷）
    second_run = controller.execute({
        "doc_id": "INV-20261108-9001",
        "target": "window://Microsoft Remote Desktop",
        "batch_id": "BATCH-00",
    }, simulate_replay=True)
    assert second_run["status"] == "COMPLETED"
    assert "step1_rpa" in second_run["replay_cache_hits"]
    assert "step2_ocr" in second_run["replay_cache_hits"]
    print(f"  ✅ PASS: 首次運算完成；第二次重播命中步驟快取 {second_run['replay_cache_hits']} (0 算力浪費)！")
    test_results["TC-05_Temporal_Durable_Execution_and_Replay"] = "PASS"

    # -------------------------------------------------------------------------
    # TC-06: 端到端微批次編排整合驗證 (Airflow ➔ Temporal ➔ RPA ➔ OCR ➔ 記憶體暫存)
    # -------------------------------------------------------------------------
    print("\n[TC-06] 驗證端到端微批次編排閉環 (Airflow 交棒 Temporal 主控 RPA，先不接 DB)...")
    InMemoryDocumentStagingRepository.clear()
    sample_batch = [
        {"doc_id": "INV-BATCH-001", "batch_id": "BATCH-TEST", "target": "https://portal.example.com", "po_number": "PO-2026-001"},
        {"doc_id": "INV-BATCH-002", "batch_id": "BATCH-TEST", "target": "window://Microsoft Remote Desktop", "po_number": "PO-2026-002"},
        {"doc_id": "INV-BATCH-003", "batch_id": "BATCH-TEST", "target": "https://vendor.example.com", "po_number": "PO-2026-003"},
    ]
    batch_summary = execute_batch_via_temporal(sample_batch)
    staged_docs = InMemoryDocumentStagingRepository.get_all()

    assert batch_summary["processed_count"] == 3
    assert len(staged_docs) == 3
    print(f"  ✅ PASS: 成功處理 {batch_summary['processed_count']} 筆單據！"
          f"記憶體暫存池確認已存入 {len(staged_docs)} 筆，無 DB 相依！")
    test_results["TC-06_End_to_End_Integration"] = "PASS"

    # -------------------------------------------------------------------------
    # 產出測試報告檔案
    # -------------------------------------------------------------------------
    summary_report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "milestone": "RPA + OCR + Temporal Architecture Verification (Phase 1 Decoupled / No DB)",
        "database_target_spec": "PostgreSQL 200GB (192.168.68.57:5432) for next phase",
        "current_db_status": "NONE (Decoupled, in-memory & JSON artifact only)",
        "rpa_orchestrator": "Temporal (Sole RPA & OCR Controller)",
        "macro_scheduler": "Apache Airflow (Batch chunking & pool locking only)",
        "test_results": test_results,
        "staged_sample_count": len(staged_docs),
        "all_tests_passed": all(v == "PASS" for v in test_results.values()),
    }

    report_path = report_dir / "verify_summary_20261108.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print("🏁 全部 6 項架構驗證測試 100% 通過 (ALL PASS ✅)！")
    print(f"📄 測試結果報告已產生於: {report_path}")
    print("=" * 70)
    return summary_report


if __name__ == "__main__":
    run_all_verifications()
