#!/usr/bin/env python3
"""
[使用工具] Python 標準庫 (json, pathlib, datetime)，無外部相依
[設計目的] 驗證 RMA 情境種子資料 (plan_doc/scenario/seed_data/rma_chain_seed.json) 之跨單據一致性，
           作為後續 OCR / RPA / MCP / RAG 驗證的「真值基準」。
[程式說明] 檢查金額、數量、批次庫存對帳、日期先後順序，並由 RMA 反向追溯至上游原料商。
[修改日期] 2026-11-10
[修改概要] 新增RMA情境種子資料一致性與追溯鏈驗證腳本 (約30字)
[關聯測試] report/BDD/DBB_Pre_Moreem_20261110.md - Feature 5 (RMA 端到端追溯)
[工作日誌] report/work_record/work_record_20261110.md
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SEED_PATH = PROJECT_ROOT / "plan_doc" / "scenario" / "seed_data" / "rma_chain_seed.json"
REPORT_PATH = PROJECT_ROOT / "report" / "test_results" / "scenario_seed_validation_20261110.json"


def load_seed(path: Path = SEED_PATH) -> Dict[str, Any]:
    """
    [使用工具] json, pathlib
    [設計目的] 載入情境種子資料。
    [程式說明] 讀取 UTF-8 JSON 並回傳字典。
    [修改日期] 2026-11-10
    [修改概要] 讀取RMA種子JSON並回傳字典 (約30字)
    [輸入參數] path (Path): 種子檔路徑
    [輸出結果] Dict[str, Any]: 種子資料
    [關聯測試] report/BDD/DBB_Pre_Moreem_20261110.md - Feature 5
    [工作日誌] report/work_record/work_record_20261110.md
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _d(s: str) -> date:
    return date.fromisoformat(s)


def trace_rma_to_origin(seed: Dict[str, Any]) -> List[str]:
    """
    [使用工具] 純 Python 字典查找
    [設計目的] 由 RMA 單反向追溯至原料商 (模擬 SAP 批次 Where-used / Where-from)。
    [程式說明] RMA → 退貨訂單 → 交貨單 → 成品批 → 生產工單 → 基板批 → 採購單 → 代理工廠 → 原料商批次。
    [修改日期] 2026-11-10
    [修改概要] 實作RMA至原料商之八段追溯鏈查找 (約30字)
    [輸入參數] seed (Dict): 種子資料
    [輸出結果] List[str]: 追溯鏈各節點描述；斷鏈時拋出 KeyError/StopIteration
    [關聯測試] report/BDD/DBB_Pre_Moreem_20261110.md - Feature 5 / Scenario [正例]
    [工作日誌] report/work_record/work_record_20261110.md
    """
    rma = seed["rma"]
    chain = [f"RMA {rma['rma_no']} (客戶 {rma['customer']}, {rma['returned_qty']} pcs)"]

    dlv = next(x for x in seed["deliveries"] if x["delivery"] == rma["ref_delivery"])
    chain.append(f"交貨單 {dlv['delivery']} / SO {dlv['so']} / 成品批 {dlv['batch']}")

    fg = next(x for x in seed["fg_receipts"] if x["batch"] == dlv["batch"])
    wo = next(x for x in seed["production_orders"] if x["wo"] == fg["wo"])
    chain.append(f"生產工單 WO {wo['wo']} (成品入庫 {fg['mat_doc']})")

    sub = next(c for c in wo["components"] if c["material"] == "RM-SUB-BT64")
    chain.append(f"基板批 {sub['batch']} (mvt {sub['mvt']} 領料 {sub['qty']})")

    gr = next(x for x in seed["goods_receipts"] if x["batch"] == sub["batch"])
    po = next(x for x in seed["purchase_orders"] if x["po"] == gr["po"])
    chain.append(f"採購單 PO {po['po']} / 收貨 {gr['mat_doc']} / 供應商 {po['vendor']}")

    vendor = next(v for v in seed["parties"]["vendors"] if v["id"] == po["vendor"])
    chain.append(f"代理工廠 {vendor['name']} ({vendor['id']})")

    maker = next(v for v in seed["parties"]["vendors"] if v["id"] == gr["upstream_maker"])
    chain.append(f"原料商 {maker['name']} ({maker['id']}) 批次 {gr['vendor_batch']}")
    return chain


def run_checks(seed: Dict[str, Any]) -> List[Tuple[str, bool, str]]:
    """
    [使用工具] 純 Python 斷言式檢查
    [設計目的] 對種子資料執行 12 項一致性檢查。
    [程式說明] 每項回傳 (名稱, 是否通過, 說明)；不拋例外，由呼叫端彙總。
    [修改日期] 2026-11-10
    [修改概要] 執行金額數量庫存日期與追溯鏈共12項檢查 (約30字)
    [輸入參數] seed (Dict): 種子資料
    [輸出結果] List[Tuple[str, bool, str]]: 檢查結果清單
    [關聯測試] report/BDD/DBB_Pre_Moreem_20261110.md - Feature 5
    [工作日誌] report/work_record/work_record_20261110.md
    """
    results: List[Tuple[str, bool, str]] = []

    def check(name: str, fn: Callable[[], Tuple[bool, str]]) -> None:
        try:
            ok, msg = fn()
        except Exception as e:  # 斷鏈或欄位缺失視為失敗
            ok, msg = False, f"例外: {type(e).__name__}: {e}"
        results.append((name, ok, msg))

    check("C01 PO 金額 = 數量 x 單價", lambda: (
        all(round(p["qty"] * p["unit_price"], 2) == p["total"] for p in seed["purchase_orders"]), "三張 PO"))
    check("C02 收貨量 <= PO 量", lambda: (
        all(g["qty"] <= next(p for p in seed["purchase_orders"] if p["po"] == g["po"])["qty"]
            for g in seed["goods_receipts"]), "GR vs PO"))
    check("C03 BOM 領料量 = (入庫+報廢) x BOM", lambda: (
        all(c["qty"] == (seed["fg_receipts"][0]["qty"] + seed["fg_receipts"][0]["scrap"])
            * seed["production_plan"]["bom_per_unit"][c["material"]]
            for c in seed["production_orders"][0]["components"]), "WO 1000004521"))
    check("C04 良率 = 入庫 / (入庫+報廢)", lambda: (
        round(seed["fg_receipts"][0]["qty"] / (seed["fg_receipts"][0]["qty"] + seed["fg_receipts"][0]["scrap"]) * 100, 1)
        == seed["fg_receipts"][0]["yield_pct"], "98.0%"))
    check("C05 SO 金額 = 客戶 PO 金額", lambda: (
        all(s["total"] == next(c for c in seed["customer_pos"] if c["cust_po"] == s["cust_po"])["total"]
            for s in seed["sales_orders"]), "SO vs 客戶PO"))
    check("C06 發票 = SO 金額；收款 = 發票", lambda: (
        all(b["amount"] == next(s for s in seed["sales_orders"] if s["so"] == b["so"])["total"] for b in seed["billing"])
        and all(p["amount"] == next(b for b in seed["billing"] if b["billing"] == p["billing"])["amount"]
                for p in seed["payments"]), "SO→Billing→Payment"))
    check("C07 成品批庫存對帳 (入庫-出貨=剩餘)", lambda: (
        seed["fg_receipts"][0]["qty"] - sum(d["qty"] for d in seed["deliveries"])
        == next(x for x in seed["containment"]["blocked_stock"] if x["material"] == "FG-EM64-A1")["qty"],
        "39200-20000-9200=10000"))
    check("C08 基板批庫存對帳", lambda: (
        seed["goods_receipts"][0]["qty"] - seed["production_orders"][0]["components"][0]["qty"]
        == next(x for x in seed["containment"]["blocked_stock"] if x["material"] == "RM-SUB-BT64")["qty"],
        "45000-40000=5000"))
    check("C09 RMA 量 <= 該交貨量", lambda: (
        seed["rma"]["returned_qty"] <= next(
            d for d in seed["deliveries"] if d["delivery"] == seed["rma"]["ref_delivery"])["qty"], "312<=20000"))
    check("C10 授信退款 = RMA 量 x 單價", lambda: (
        round(seed["rma"]["credit_memo"]["qty"] * seed["rma"]["credit_memo"]["unit_price"], 2)
        == seed["rma"]["credit_memo"]["amount"], "312 x 3.85 = 1201.20"))
    check("C11 日期單調: 評估<PO<收貨<入庫<SO<出貨<發票<收款<RMA<貸項", lambda: (
        (lambda ds: all(ds[i] <= ds[i + 1] for i in range(len(ds) - 1)))([
            _d(seed["evaluation"]["date"]), _d(seed["purchase_orders"][0]["date"]),
            _d(seed["goods_receipts"][0]["date"]), _d(seed["fg_receipts"][0]["date"]),
            _d(seed["sales_orders"][0]["date"]), _d(seed["deliveries"][0]["pgi_date"]),
            _d(seed["billing"][0]["date"]), _d(seed["payments"][0]["date"]),
            _d(seed["rma"]["reported"]), _d(seed["rma"]["credit_memo"]["date"])]), "時間軸"))
    check("C12 RMA 可追溯至原料商 (7 節點)", lambda: (
        len(trace_rma_to_origin(seed)) == 7
        and trace_rma_to_origin(seed)[-1].startswith("原料商 晶源材料"), "完整追溯鏈"))
    return results


def main() -> int:
    """
    [使用工具] json, sys
    [設計目的] 命令列入口：執行檢查、輸出報告 JSON。
    [程式說明] 全部通過回傳 0，否則 1；報告寫入 report/test_results/。
    [修改日期] 2026-11-10
    [修改概要] 執行檢查並輸出終端與JSON驗證報告 (約30字)
    [輸入參數] 無
    [輸出結果] int: 結束碼
    [關聯測試] report/BDD/DBB_Pre_Moreem_20261110.md - Feature 5
    [工作日誌] report/work_record/work_record_20261110.md
    """
    seed = load_seed()
    results = run_checks(seed)
    print("=" * 66)
    print("RMA 情境種子資料一致性驗證 (SCN-RMA-001)")
    print("=" * 66)
    for name, ok, msg in results:
        print(f"  {'PASS' if ok else 'FAIL'} | {name} | {msg}")
    print("\n追溯鏈 (RMA → 原料商):")
    try:
        for i, node in enumerate(trace_rma_to_origin(seed), 1):
            print(f"  {i}. {node}")
    except Exception as e:
        print(f"  追溯失敗: {e}")

    all_ok = all(ok for _, ok, _ in results)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "scenario": seed["_meta"]["scenario_id"],
            "all_passed": all_ok,
            "checks": [{"name": n, "passed": ok, "detail": m} for n, ok, m in results],
        }, f, ensure_ascii=False, indent=2)
    print(f"\n{'ALL PASS' if all_ok else 'HAS FAILURES'} → {REPORT_PATH}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
