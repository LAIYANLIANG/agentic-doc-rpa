#!/usr/bin/env python3
"""
[使用工具] Python 3.11, Pydantic v2
[設計目的] 定義全系統單據資料契約與結構防漂移規格，此階段純記憶體運作、完全不接資料庫。
[程式說明] 包含單據落地、批次清單與驗證結果物件；未來階段將接軌同網段 200GB PostgreSQL (192.168.68.57:5432)。
[修改日期] 2026-11-08
[修改概要] 建立無DB相依之Pydantic契約並註記未來PostgreSQL規劃 (約30字)
[關聯測試] report/BDD/DBB_Pre_Moreem_20261108.md - Feature 3 (資料庫架構演進規範)
[工作日誌] report/work_record/work_record_20261108.md
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime


try:
    from pydantic import BaseModel, Field, field_validator

    class RawInvoiceStagingSchema(BaseModel):
        """
        [使用工具] Pydantic v2 BaseModel
        [設計目的] 規範單據入庫前的結構防漂移強校驗契約，目前在記憶體與 JSON 成果中流轉。
        [程式說明] 嚴格檢查採購單號格式、統一編號 8 碼、金額大於 0 與置信度，並自動清洗千分位符號。
        [修改日期] 2026-11-08
        [修改概要] 實作發票字串金額清洗與統編格式防漂移校驗 (約30字)
        [輸入參數] doc_id, doc_sha256, batch_id, source_target, rpa_engine_used, po_number, vendor_tax_id, invoice_total, min_ocr_score, git_commit_sha, clean_json, captured_at
        [輸出結果] 經標準化校驗之單據資料物件 (Pydantic Model Instance)
        [關聯測試] report/BDD/DBB_Pre_Moreem_20261108.md - Feature 2 / Scenario [正例]
        [工作日誌] report/work_record/work_record_20261108.md
        """
        doc_id: str = Field(..., description="全系統唯一單據 ID")
        doc_sha256: str = Field(..., min_length=64, max_length=64, description="影像 SHA256 防竄改特徵碼")
        batch_id: str = Field(..., description="所屬 Airflow 微批次編號")
        source_target: str = Field(..., description="來源標的 (URL 或 桌面視窗)")
        rpa_engine_used: str = Field(..., description="使用的 RPA 引擎模式 (playwright_dom, quartz_ocr 等)")
        po_number: str = Field(..., pattern=r"^PO-\d{4}-\d+$", description="正規化採購單號")
        vendor_tax_id: str = Field(..., pattern=r"^\d{8}$", description="廠商統一編號 (8 碼數字)")
        invoice_total: float = Field(..., ge=0.0, description="發票總金額 (清洗後之純浮點數)")
        min_ocr_score: float = Field(..., ge=0.0, le=1.0, description="關鍵欄位最低 OCR 置信度")
        git_commit_sha: str = Field(default="git-init-pending", description="版本控制 Commit Hash，確保可重現性")
        clean_json: str = Field(..., description="標準化 JSON 字串")
        captured_at: str = Field(..., description="畫面擷取時間 (ISO 8601)")

        @field_validator("po_number", mode="before")
        @classmethod
        def normalize_po_number(cls, v: Any) -> str:
            """
            [使用工具] Pydantic validator
            [設計目的] 採購單號格式正規化。
            [程式說明] 自動去除前後空白並強制轉換為大寫。
            [修改日期] 2026-11-08
            [修改概要] 實作採購單號前後去空白與大寫轉換 (約30字)
            [輸入參數] v (Any): 原始輸入單號
            [輸出結果] str: 正規化後大寫單號
            [關聯測試] report/BDD/DBB_Pre_Moreem_20261108.md - Feature 2
            [工作日誌] report/work_record/work_record_20261108.md
            """
            return str(v).strip().upper()

        @field_validator("invoice_total", mode="before")
        @classmethod
        def clean_currency_string(cls, v: Any) -> float:
            """
            [使用工具] Pydantic validator
            [設計目的] 金額字串容錯清洗。
            [程式說明] 移除千分位逗號、貨幣符號 ($、NT) 並轉換為標準浮點數。
            [修改日期] 2026-11-08
            [修改概要] 實作金錢符號與千分位逗號過濾並轉為浮點數 (約30字)
            [輸入參數] v (Any): 原始金額字串或數值
            [輸出結果] float: 清洗後之數值
            [關聯測試] report/BDD/DBB_Pre_Moreem_20261108.md - Feature 2
            [工作日誌] report/work_record/work_record_20261108.md
            """
            if isinstance(v, str):
                v = v.replace("$", "").replace(",", "").replace("NT", "").strip()
            return float(v)

    class BatchManifestItem(BaseModel):
        """
        [使用工具] Pydantic BaseModel
        [設計目的] 封裝上游批次清單項目。
        [程式說明] 供 Airflow 進行動態切批傳遞至 Temporal。
        [修改日期] 2026-11-08
        [修改概要] 宣告批次單據清單傳遞資料結構 (約30字)
        [輸入參數] doc_id, batch_id, target, po_number
        [輸出結果] BatchManifestItem 物件
        [關聯測試] report/BDD/DBB_Pre_Moreem_20261108.md - Feature 1
        [工作日誌] report/work_record/work_record_20261108.md
        """
        doc_id: str
        batch_id: str
        target: str
        po_number: str

except ImportError:
    # 輕量 Fallback 定義，若未安裝 pydantic 亦可運行單元自檢
    @dataclass
    class RawInvoiceStagingSchema:  # type: ignore[no-redef]
        doc_id: str
        doc_sha256: str
        batch_id: str
        source_target: str
        rpa_engine_used: str
        po_number: str
        vendor_tax_id: str
        invoice_total: float
        min_ocr_score: float
        git_commit_sha: str = "git-init-pending"
        clean_json: str = "{}"
        captured_at: str = ""

        def __post_init__(self):
            self.po_number = str(self.po_number).strip().upper()
            if not re.match(r"^PO-\d{4}-\d+$", self.po_number):
                raise ValueError(f"非法採購單號格式: {self.po_number}")
            if not re.match(r"^\d{8}$", str(self.vendor_tax_id)):
                raise ValueError(f"非法統編格式 (需為8碼數字): {self.vendor_tax_id}")
            if isinstance(self.invoice_total, str):
                cleaned = self.invoice_total.replace("$", "").replace(",", "").replace("NT", "").strip()
                self.invoice_total = float(cleaned)
            else:
                self.invoice_total = float(self.invoice_total)

    @dataclass
    class BatchManifestItem:  # type: ignore[no-redef]
        doc_id: str
        batch_id: str
        target: str
        po_number: str
