#!/usr/bin/env python3
"""
[使用工具] Apache Airflow 2.10 (LocalExecutor), Python 3.11
[設計目的] 外層「宏觀排程總管」，專職定時排程、動態批次切分與記憶體資源池保護。
[程式說明] 嚴格不直接介入底層 RPA 與視窗控制，將微批次清單交棒給 Temporal 持久化狀態機執行。
[修改日期] 2026-11-08
[修改概要] 建立Airflow宏觀排程器與切批交棒Temporal調度邏輯 (約30字)
[關聯測試] report/BDD/DBB_Pre_Moreem_20261108.md - Feature 1 (宏觀排程與動態切批)
[工作日誌] report/work_record/work_record_20261108.md
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List

# 確保專案根目錄納入 Python 搜尋路徑 (解決 Airflow dags 掃描時找不到 src 的問題)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.resource_manager import M5ResourceMultiplexer


# =============================================================================
# 1. 宏觀排程業務函式 (可獨立調用或由 Airflow DAG 裝飾)
# =============================================================================
def fetch_and_chunk_manifests(total_docs: int = 600, batch_size: int = 50) -> List[List[Dict[str, Any]]]:
    """
    [使用工具] Python List Slicing
    [設計目的] 【Airflow 宏觀 Step A】清點今日單據並動態切分為微批次 (Micro-batches)。
    [程式說明] 產生模擬或真實來源清冊，按 batch_size 切割成子列表，供 Airflow 動態展開 (.expand())。
    [修改日期] 2026-11-08
    [修改概要] 實作單據清單動態切分函式並回傳二維批次陣列 (約30字)
    [輸入參數] total_docs (int): 總單據數量; batch_size (int): 每批次容量 (預設 50)
    [輸出結果] List[List[Dict[str, Any]]]: 切分後之二維微批次陣列
    [關聯測試] report/BDD/DBB_Pre_Moreem_20261108.md - Feature 1 / Scenario [正例]
    [工作日誌] report/work_record/work_record_20261108.md
    """
    manifests: List[Dict[str, Any]] = []
    for i in range(1, total_docs + 1):
        target = "https://vendor-portal.example.com/invoices" if i % 4 != 0 else "window://Microsoft Remote Desktop"
        manifests.append({
            "doc_id": f"INV-20261108-{i:04d}",
            "batch_id": f"BATCH-{i // batch_size:02d}",
            "target": target,
            "po_number": f"PO-2026-{2000 + i}",
        })

    # 動態切割為每批 batch_size 筆
    chunks = [manifests[i: i + batch_size] for i in range(0, len(manifests), batch_size)]
    return chunks


def execute_batch_via_temporal(doc_batch: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    [使用工具] Temporal Workflow Client, M5ResourceMultiplexer
    [設計目的] 【Airflow 宏觀 Step B】微批次交棒給 Temporal，並在批次前後執行記憶體分時管理。
    [程式說明] 進入批次時將模型熱駐留 (keep_alive=5m)，逐張委派 Temporal 主控 RPA+OCR，結束瞬間立即釋放 VRAM。
    [修改日期] 2026-11-08
    [修改概要] Airflow交棒Temporal並於批次結束釋放模型記憶體 (約30字)
    [輸入參數] doc_batch (List[Dict[str, Any]]): 50 筆單據微批次清單
    [輸出結果] Dict[str, Any]: 微批次執行彙總統計
    [關聯測試] report/BDD/DBB_Pre_Moreem_20261108.md - Feature 1 & Feature 2
    [工作日誌] report/work_record/work_record_20261108.md
    """
    if not doc_batch:
        return {"processed_count": 0, "status": "EMPTY_BATCH_SKIPPED"}

    batch_id = doc_batch[0]["batch_id"]
    processed_count = 0
    start_time = time.time()

    # 高資源使用率：微批次開始時鎖定模型，讓 50 張單據共用 1 次載入開銷
    M5ResourceMultiplexer.pin_model_for_active_batch("poc-text-4b", keep_alive="5m")

    try:
        try:
            from src.orchestration.temporal_workflow import TemporalRPAWorkflowController

            for item in doc_batch:
                # 關鍵邊界：Airflow 不碰 RPA，而是呼叫 Temporal 持久化控制器！
                workflow_id = f"WF-{item['doc_id']}"
                controller = TemporalRPAWorkflowController(workflow_id=workflow_id)
                res = controller.execute(doc_meta=item, simulate_replay=False)
                if res.get("status") == "COMPLETED":
                    processed_count += 1
        except (ImportError, ModuleNotFoundError):
            # 當前直譯器為獨立的 .venv_airflow，透過跨環境子程序委派 .venv_rpa_ocr 執行 Temporal 與 GUI RPA
            python_bin = PROJECT_ROOT / ".venv_rpa_ocr" / "bin" / "python"
            if not python_bin.exists():
                python_bin = Path(sys.executable)

            payload_json = json.dumps(doc_batch)
            runner_script = (
                "import json, sys\n"
                "from src.orchestration.temporal_workflow import TemporalRPAWorkflowController\n"
                "batch = json.loads(sys.argv[1])\n"
                "for item in batch:\n"
                "    c = TemporalRPAWorkflowController(f\"WF-{item['doc_id']}\")\n"
                "    c.execute(item)\n"
            )
            subprocess.run(
                [str(python_bin), "-c", runner_script, payload_json],
                check=True,
                cwd=str(PROJECT_ROOT),
            )
            processed_count = len(doc_batch)
    finally:
        # 極低閒置耗用：微批次結束瞬間強制釋放模型，將常駐 VRAM 歸零
        M5ResourceMultiplexer.evict_all_models_for_zero_idle("poc-text-4b")

    elapsed = round(time.time() - start_time, 2)
    return {
        "batch_id": batch_id,
        "processed_count": processed_count,
        "elapsed_seconds": elapsed,
        "status": "BATCH_COMPLETED",
        "controller": "Temporal (Sole RPA & OCR Orchestrator)",
    }


# =============================================================================
# 2. Apache Airflow 官方 DAG 宣告 (Airflow 執行環境下自動註冊)
# =============================================================================
try:
    from airflow.decorators import dag, task

    @dag(
        dag_id="m5_macro_airflow_to_temporal_pipeline",
        description="Airflow宏觀排程切批交棒Temporal主控RPA與OCR (先不接DB，保留PostgreSQL規範)",
        schedule="0 6 * * *",
        start_date=datetime(2026, 11, 1),
        catchup=False,
        max_active_runs=1,
        tags=["m5", "airflow", "temporal", "rpa", "ocr", "no_db_phase1"],
    )
    def m5_macro_airflow_to_temporal_pipeline():
        @task
        def task_chunk_manifests() -> List[List[Dict[str, Any]]]:
            return fetch_and_chunk_manifests(total_docs=600, batch_size=50)

        @task(
            pool="m5_heavy_worker_pool",            # 嚴格鎖定 slots=1，保護 M5 24GB 記憶體
            execution_timeout=timedelta(minutes=5),
        )
        def task_dispatch_to_temporal(doc_batch: List[Dict[str, Any]]) -> Dict[str, Any]:
            return execute_batch_via_temporal(doc_batch)

        batches = task_chunk_manifests()
        task_dispatch_to_temporal.expand(doc_batch=batches)

    dag_instance = m5_macro_airflow_to_temporal_pipeline()

except ImportError:
    # 離線或一般 Python 直譯器環境下安全略過 Airflow 裝飾器
    pass

