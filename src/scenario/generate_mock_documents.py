"""
[使用工具]: Playwright (Chromium headless)
[設計目的]: 生成情境 SCN-RMA-001 所需之模擬商業單據（CoA、客戶 PO、FA 報告、IQC 報告、工程規格圖）之 PDF 與高解析度 PNG 檔案，作為 OCR 抽取與 RPA 驗證之標準測試素材。
[程式說明]:
    1. 讀取 plan_doc/scenario/seed_data/rma_chain_seed.json 作為 Single Source of Truth，確保單號、批次、日期與金額 100% 一致。
    2. 使用 HTML5/CSS3 精確排版真實企業單據（含表格、浮水印、審批章、向量 SVG 失效圖與工程架構圖）。
    3. 透過 Playwright 渲染輸出 PDF (A4 向量無損) 與 PNG (高解析度 1200px 寬度)，儲存於 plan_doc/scenario/sample_docs/。
    4. 產出 sample_docs/manifest.json，記錄所有產出檔案清單、SHA256、單據類型與 OCR 目標抽取欄位。
[修改日期]: 2026-11-10
[修改概要]: 初始建立完整模擬單據產出腳本
[輸入參數]: plan_doc/scenario/seed_data/rma_chain_seed.json
[輸出結果]: 5 份單據共 10 個文件 (5 PDF + 5 PNG) 與 manifest.json 於 plan_doc/scenario/sample_docs/
[關聯測試]: src/scenario/validate_seed_data.py
[工作日誌]: 配合使用者需求建立 OCR 驗證素材與部門單據交叉對照矩陣
"""

import json
import hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parents[2]
SEED_PATH = BASE_DIR / "plan_doc/scenario/seed_data/rma_chain_seed.json"
OUTPUT_DIR = BASE_DIR / "plan_doc/scenario/sample_docs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

with open(SEED_PATH, "r", encoding="utf-8") as f:
    SEED = json.load(f)


def calculate_sha256(filepath: Path) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    return sha.hexdigest()


# ----------------------------------------------------------------------
# 1. Supplier CoA HTML Template
# ----------------------------------------------------------------------
def render_coa_html() -> str:
    po_item = SEED["purchase_orders"][0]
    gr = SEED["goods_receipts"][0]
    eval_spec = SEED["evaluation"]["parameters"]["substrate_spec"]

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<style>
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang TC", "Microsoft JhengHei", sans-serif;
        margin: 0; padding: 40px; color: #222; background: #fff;
    }}
    .header {{ text-align: center; border-bottom: 2px solid #0b4f6c; padding-bottom: 15px; margin-bottom: 25px; }}
    .company-name {{ font-size: 22px; font-weight: bold; color: #0b4f6c; letter-spacing: 1px; }}
    .company-sub {{ font-size: 13px; color: #555; margin-top: 4px; }}
    .doc-title {{ font-size: 20px; font-weight: bold; margin-top: 15px; color: #111; letter-spacing: 2px; }}
    .info-table, .data-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 13px; }}
    .info-table td {{ padding: 6px 10px; }}
    .info-label {{ font-weight: 600; color: #333; width: 18%; background: #f7f9fa; border: 1px solid #dce2e6; }}
    .info-val {{ width: 32%; border: 1px solid #dce2e6; }}
    .data-table th, .data-table td {{ border: 1px solid #c2cdd4; padding: 9px 12px; }}
    .data-table th {{ background: #0b4f6c; color: #fff; text-align: center; font-weight: 600; }}
    .text-center {{ text-align: center; }}
    .text-right {{ text-align: right; }}
    .pass-badge {{ color: #008000; font-weight: bold; }}
    .footer-note {{ font-size: 11px; color: #666; margin-top: 25px; line-height: 1.6; border-top: 1px dashed #ccc; padding-top: 10px; }}
    .stamp-area {{ margin-top: 30px; display: flex; justify-content: flex-end; align-items: center; position: relative; }}
    .stamp-box {{
        width: 130px; height: 130px; border: 3px double #d32f2f; border-radius: 50%;
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        color: #d32f2f; font-weight: bold; font-size: 13px; transform: rotate(-8deg);
        box-shadow: 0 0 2px rgba(211,47,47,0.3); opacity: 0.88;
    }}
    .stamp-inner {{ border-top: 1px dashed #d32f2f; border-bottom: 1px dashed #d32f2f; padding: 3px 0; margin: 3px 0; font-size: 11px; }}
</style>
</head>
<body>
    <div class="header">
        <div class="company-name">宏達電子材料股份有限公司</div>
        <div class="company-sub">HONGDA ELECTRONIC MATERIALS CO., LTD. ｜ 品質保證處</div>
        <div class="doc-title">出廠檢驗證明書 (CERTIFICATE OF ANALYSIS)</div>
    </div>

    <table class="info-table">
        <tr>
            <td class="info-label">客戶名稱 / Customer</td>
            <td class="info-val">宏芯記憶體科技股份有限公司</td>
            <td class="info-label">檢驗編號 / CoA No.</td>
            <td class="info-val"><strong>COA-HD-2606-0418</strong></td>
        </tr>
        <tr>
            <td class="info-label">採購單號 / PO No.</td>
            <td class="info-val">{po_item["po"]} (Item {po_item["item"]})</td>
            <td class="info-label">檢驗日期 / Date</td>
            <td class="info-val">2026-06-28</td>
        </tr>
        <tr>
            <td class="info-label">品名規格 / Description</td>
            <td class="info-val">BT 封裝基板 (64GB 堆疊用)</td>
            <td class="info-label">料件編號 / Part No.</td>
            <td class="info-val">{po_item["material"]}</td>
        </tr>
        <tr>
            <td class="info-label">供應商批號 / Lot No.</td>
            <td class="info-val"><strong>{gr["vendor_batch"]}</strong></td>
            <td class="info-label">交貨數量 / Quantity</td>
            <td class="info-val">{po_item["qty"]:,} PCS</td>
        </tr>
        <tr>
            <td class="info-label">上游材料商 / Maker</td>
            <td class="info-val">晶源材料 (代碼: {gr["upstream_maker"]})</td>
            <td class="info-label">製造日期 / Mfg Date</td>
            <td class="info-val">2026-06-25</td>
        </tr>
    </table>

    <table class="data-table">
        <thead>
            <tr>
                <th style="width: 8%;">項次</th>
                <th style="width: 28%;">檢驗項目 / Test Parameter</th>
                <th style="width: 24%;">技術標準 / Specification</th>
                <th style="width: 20%;">實測結果 / Measured Value</th>
                <th style="width: 20%;">判定 / Verdict</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td class="text-center">1</td>
                <td>外觀檢驗 (Visual Inspection)</td>
                <td>無氧化、無分層、無顯著刮傷</td>
                <td class="text-center">OK (無異常)</td>
                <td class="text-center pass-badge">PASS 合格</td>
            </tr>
            <tr>
                <td class="text-center">2</td>
                <td>外觀長寬尺寸 (Outline Dimension)</td>
                <td>11.50±0.05 × 13.00±0.05 mm</td>
                <td class="text-center">11.50 × 13.01 mm</td>
                <td class="text-center pass-badge">PASS 合格</td>
            </tr>
            <tr>
                <td class="text-center">3</td>
                <td>基板整體厚度 (Total Thickness)</td>
                <td>0.22 ± 0.02 mm</td>
                <td class="text-center">0.221 mm</td>
                <td class="text-center pass-badge">PASS 合格</td>
            </tr>
            <tr>
                <td class="text-center">4</td>
                <td>貫孔銅厚 (Via Barrel Cu Plating)</td>
                <td>&ge; {eval_spec["cu_plating_um_min"]}.0 &mu;m (IPC-6012)</td>
                <td class="text-center">20.2 &mu;m</td>
                <td class="text-center pass-badge">PASS 合格</td>
            </tr>
            <tr>
                <td class="text-center">5</td>
                <td>防焊層厚度 (Solder Mask Thickness)</td>
                <td>10.0 ~ 25.0 &mu;m</td>
                <td class="text-center">15.4 &mu;m</td>
                <td class="text-center pass-badge">PASS 合格</td>
            </tr>
            <tr style="background: #fff9e6;">
                <td class="text-center">6</td>
                <td><strong>玻璃轉移溫度 / Glass Transition (Tg)</strong></td>
                <td><strong>&ge; {eval_spec["tg_c_min"]} &deg;C (TMA)</strong></td>
                <td class="text-center"><strong>{gr["coa_tg_c"]}.0 &deg;C</strong></td>
                <td class="text-center pass-badge">PASS 合格</td>
            </tr>
            <tr>
                <td class="text-center">7</td>
                <td>難燃等級 (Flammability Rating)</td>
                <td>UL 94 V-0</td>
                <td class="text-center">V-0 符合</td>
                <td class="text-center pass-badge">PASS 合格</td>
            </tr>
        </tbody>
    </table>

    <div class="footer-note">
        說明：本出廠檢驗證明書所載之各項測試數據係由宏達品保實驗室及上游原料製造廠（晶源材料）依據標準作業程序測試所得，特此證明本批產品符合雙方議定之工程規格書。
    </div>

    <div class="stamp-area">
        <div style="margin-right: 30px; text-align: right; font-size: 13px;">
            <div>品保部門主管：<strong>張國強 (Kevin Chang)</strong></div>
            <div style="margin-top: 5px; color: #555;">簽發日期：2026-06-28</div>
        </div>
        <div class="stamp-box">
            <div>宏達電子材料</div>
            <div class="stamp-inner">品質檢驗合格</div>
            <div>QA PASSED</div>
        </div>
    </div>
</body>
</html>"""


# ----------------------------------------------------------------------
# 2. Customer PO HTML Template
# ----------------------------------------------------------------------
def render_customer_po_html() -> str:
    cpo = SEED["customer_pos"][0]
    cust = SEED["parties"]["customers"][0]
    co = SEED["parties"]["company"]

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<style>
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang TC", "Microsoft JhengHei", sans-serif;
        margin: 0; padding: 40px; color: #222; background: #fff;
    }}
    .header {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 3px solid #1a365d; padding-bottom: 15px; margin-bottom: 20px; }}
    .co-title {{ font-size: 24px; font-weight: bold; color: #1a365d; }}
    .co-sub {{ font-size: 12px; color: #4a5568; margin-top: 4px; }}
    .po-badge {{
        background: #1a365d; color: #fff; padding: 8px 18px; border-radius: 4px; text-align: right;
    }}
    .po-badge h2 {{ margin: 0; font-size: 18px; letter-spacing: 1px; }}
    .po-badge p {{ margin: 3px 0 0; font-size: 13px; font-weight: bold; }}
    .meta-grid {{ display: flex; justify-content: space-between; margin-bottom: 25px; }}
    .meta-col {{ width: 48%; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px 15px; font-size: 13px; }}
    .meta-col h3 {{ margin: 0 0 8px; font-size: 14px; color: #2d3748; border-bottom: 1px solid #cbd5e1; padding-bottom: 4px; }}
    .meta-row {{ display: flex; margin-bottom: 5px; }}
    .meta-label {{ width: 100px; color: #64748b; font-weight: 500; }}
    .meta-val {{ flex: 1; color: #0f172a; font-weight: 600; }}
    .table {{ width: 100%; border-collapse: collapse; margin-bottom: 25px; font-size: 13px; }}
    .table th, .table td {{ border: 1px solid #cbd5e1; padding: 10px 12px; }}
    .table th {{ background: #2d3748; color: #fff; font-weight: 600; text-align: center; }}
    .text-center {{ text-align: center; }}
    .text-right {{ text-align: right; }}
    .totals-area {{ display: flex; justify-content: flex-end; margin-bottom: 30px; }}
    .totals-box {{ width: 320px; font-size: 13px; }}
    .totals-row {{ display: flex; justify-content: space-between; padding: 6px 10px; border-bottom: 1px solid #e2e8f0; }}
    .totals-grand {{ font-size: 16px; font-weight: bold; color: #1a365d; background: #e2e8f0; border-radius: 4px; }}
    .terms-box {{ font-size: 11px; color: #64748b; border: 1px solid #e2e8f0; padding: 12px; background: #fafafa; border-radius: 4px; line-height: 1.6; }}
    .sig-area {{ margin-top: 30px; display: flex; justify-content: space-between; align-items: flex-end; }}
    .sig-block {{ width: 220px; border-top: 1px solid #333; text-align: center; font-size: 12px; padding-top: 5px; }}
</style>
</head>
<body>
    <div class="header">
        <div>
            <div class="co-title">{cust["name"]}股份有限公司</div>
            <div class="co-sub">LINGYUN ELECTRONICS CO., LTD. ｜ 採購中心</div>
            <div class="co-sub">地址：新竹科學園區研新三路 8 號 ｜ 電話：(03) 578-9900</div>
        </div>
        <div class="po-badge">
            <h2>PURCHASE ORDER</h2>
            <p>採購單號：{cpo["cust_po"]}</p>
        </div>
    </div>

    <div class="meta-grid">
        <div class="meta-col">
            <h3>供應商資訊 / Vendor Info</h3>
            <div class="meta-row"><span class="meta-label">公司名稱：</span><span class="meta-val">{co["name"]}</span></div>
            <div class="meta-row"><span class="meta-label">供應商代號：</span><span class="meta-val">V-HX01-088</span></div>
            <div class="meta-row"><span class="meta-label">聯絡窗口：</span><span class="meta-val">業務部 李世榮經理</span></div>
            <div class="meta-row"><span class="meta-label">聯絡電話：</span><span class="meta-val">(03) 666-8800 #201</span></div>
        </div>
        <div class="meta-col">
            <h3>訂單條款 / Order Terms</h3>
            <div class="meta-row"><span class="meta-label">訂單日期：</span><span class="meta-val">{cpo["date"]}</span></div>
            <div class="meta-row"><span class="meta-label">指定交期：</span><span class="meta-val">{cpo["requested_delivery"]}</span></div>
            <div class="meta-row"><span class="meta-label">付款條件：</span><span class="meta-val">月結 45 天 (NET 45)</span></div>
            <div class="meta-row"><span class="meta-label">交貨地點：</span><span class="meta-val">新竹園區 B 廠碼頭倉庫</span></div>
        </div>
    </div>

    <table class="table">
        <thead>
            <tr>
                <th style="width: 8%;">項次</th>
                <th style="width: 22%;">料號 / Part No.</th>
                <th style="width: 32%;">品名與規格描述 / Description</th>
                <th style="width: 12%;">數量 / Qty</th>
                <th style="width: 12%;">單價 / Unit (USD)</th>
                <th style="width: 14%;">總額 / Amount (USD)</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td class="text-center">10</td>
                <td><strong>FG-EM64-A1</strong></td>
                <td>eMMC 5.1 64GB 嵌入式快閃記憶體晶片 (BGA-153 封裝, 工規 -40~+85&deg;C)</td>
                <td class="text-right"><strong>{cpo["qty"]:,} PCS</strong></td>
                <td class="text-right">${cpo["unit_price"]:.2f}</td>
                <td class="text-right"><strong>${cpo["total"]:,.2f}</strong></td>
            </tr>
        </tbody>
    </table>

    <div class="totals-area">
        <div class="totals-box">
            <div class="totals-row"><span>小計 / Subtotal:</span><span>${cpo["total"]:,.2f}</span></div>
            <div class="totals-row"><span>營業稅 / Tax (0% 保稅):</span><span>$0.00</span></div>
            <div class="totals-row totals-grand"><span>訂單總額 / Total:</span><span>USD ${cpo["total"]:,.2f}</span></div>
        </div>
    </div>

    <div class="terms-box">
        <strong>注意事項與交貨品質要求：</strong><br>
        1. 出貨交貨時必須檢附產品出廠檢驗證明書 (CoA)，並符合雙方簽署之技術規格書規範。<br>
        2. 本批產品供凌雲電子車用娛樂主機板量產使用，嚴格要求回焊耐熱性與高低溫循環可靠度（-55&deg;C ~ +125&deg;C x 500 cycles）。<br>
        3. 如發生進料檢驗不合格或產線批量故障，供應商須於 24 小時內回覆臨時圍堵措施，並於 7 個工作日內提交 8D 根本原因報告。
    </div>

    <div class="sig-area">
        <div class="sig-block">採購經辦：林雅婷 (Yating Lin)</div>
        <div class="sig-block">採購處處長核決：趙志遠</div>
        <div style="width: 110px; height: 110px; border: 2px solid #b91c1c; border-radius: 50%; color: #b91c1c; display: flex; flex-direction: column; justify-content: center; align-items: center; font-size: 11px; font-weight: bold; transform: rotate(-5deg);">
            <div>凌雲電子</div>
            <div style="border-top:1px solid #b91c1c; border-bottom:1px solid #b91c1c; margin:2px 0; padding:1px 0;">採購專用章</div>
            <div>PO APPROVED</div>
        </div>
    </div>
</body>
</html>"""


# ----------------------------------------------------------------------
# 3. FA Report HTML Template
# ----------------------------------------------------------------------
def render_fa_report_html() -> str:
    rma = SEED["rma"]
    fa = rma["fa_report"]
    gr = SEED["goods_receipts"][0]
    spec = SEED["evaluation"]["parameters"]["substrate_spec"]

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<style>
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang TC", "Microsoft JhengHei", sans-serif;
        margin: 0; padding: 40px; color: #1e293b; background: #fff;
    }}
    .header {{ border-bottom: 3px solid #b91c1c; padding-bottom: 12px; margin-bottom: 20px; }}
    .co-name {{ font-size: 20px; font-weight: bold; color: #0f172a; }}
    .rep-title {{ font-size: 22px; font-weight: bold; color: #b91c1c; margin-top: 5px; }}
    .sub-head {{ font-size: 12px; color: #64748b; margin-top: 3px; }}
    .info-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 12px; }}
    .info-table td {{ border: 1px solid #cbd5e1; padding: 6px 10px; }}
    .lbl {{ background: #f1f5f9; font-weight: 600; width: 16%; color: #334155; }}
    .val {{ width: 34%; font-weight: 500; }}
    h3 {{ font-size: 14px; color: #0f172a; border-left: 4px solid #b91c1c; padding-left: 8px; margin: 18px 0 8px; }}
    p, li {{ font-size: 12.5px; line-height: 1.6; color: #334155; }}
    .box {{ background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px; padding: 12px 15px; margin-bottom: 15px; font-size: 12.5px; }}
    .diagram-container {{ display: flex; justify-content: space-around; align-items: center; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 15px; margin: 15px 0; }}
    .diagram-box {{ text-align: center; }}
    .diagram-title {{ font-size: 12px; font-weight: 600; color: #475569; margin-top: 6px; }}
    .data-table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 12px; }}
    .data-table th, .data-table td {{ border: 1px solid #cbd5e1; padding: 7px 10px; text-align: center; }}
    .data-table th {{ background: #e2e8f0; color: #1e293b; font-weight: 600; }}
    .fail-text {{ color: #dc2626; font-weight: bold; }}
    .sig-grid {{ display: flex; justify-content: space-between; margin-top: 35px; border-top: 1px solid #cbd5e1; padding-top: 15px; font-size: 12px; }}
</style>
</head>
<body>
    <div class="header">
        <div class="co-name">宏芯記憶體科技股份有限公司 ｜ 品質保證處 可靠度與失效分析實驗室</div>
        <div class="rep-title">FAILURE ANALYSIS REPORT (工程失效分析報告)</div>
        <div class="sub-head">MACROCHIP RELIABILITY & FAILURE ANALYSIS LAB ｜ 報告編號：{fa["id"]}</div>
    </div>

    <table class="info-table">
        <tr>
            <td class="lbl">客戶名稱</td>
            <td class="val">{SEED["parties"]["customers"][0]["name"]}</td>
            <td class="lbl">報告編號</td>
            <td class="val"><strong>{fa["id"]}</strong></td>
        </tr>
        <tr>
            <td class="lbl">RMA 案號</td>
            <td class="val"><strong>{rma["rma_no"]}</strong></td>
            <td class="lbl">完成日期</td>
            <td class="val">2026-11-04</td>
        </tr>
        <tr>
            <td class="lbl">產品型號</td>
            <td class="val">eMMC 5.1 64GB ({SEED["materials"][0]["id"]})</td>
            <td class="lbl">成品批號</td>
            <td class="val"><strong>{rma["batch"]}</strong></td>
        </tr>
        <tr>
            <td class="lbl">工單編號</td>
            <td class="val">{SEED["production_orders"][0]["wo"]}</td>
            <td class="lbl">關聯基板批號</td>
            <td class="val"><strong>{gr["batch"]}</strong> (原廠批: {gr["vendor_batch"]})</td>
        </tr>
        <tr>
            <td class="lbl">分析樣品數</td>
            <td class="val">收件 20 pcs / 開路確認 18 pcs</td>
            <td class="lbl">失效模式</td>
            <td class="val">{rma["failure_mode"]}</td>
        </tr>
    </table>

    <div class="box">
        <strong>【根本原因摘要 (Root Cause Conclusion)】</strong><br>
        失效品之基板層壓板（BT Resin Laminate）經 TMA 復測，實際玻璃轉移溫度（Tg）僅為 <strong>{rma["retest_tg_c"]}.0 &deg;C</strong>，低於規格標準（&ge; {spec["tg_c_min"]} &deg;C）。<br>
        在高低溫熱循環試驗（-55&deg;C ~ +125&deg;C）中，基板於高於 Tg 時 Z 軸膨脹係數劇烈飆升（CTE &gt; 65 ppm/&deg;C），導致貫穿通孔（Through-hole Via）孔壁銅鍍層承受過量熱機械拉應力而產生<strong>疲勞斷裂（Via Barrel Shear Crack）</strong>，引發間歇性開路。
    </div>

    <h3>1. 失效確認與電性定位 (Electrical Verification & TDR)</h3>
    <p>
        使用 Curve Tracer 與 TDR（時域反射計）對 20 顆客退樣品進行腳位阻抗掃描：其中 18 顆在常溫下表現為高阻抗或開路（Open Circuit），主要集中於訊號傳輸 Pin E3 (CMD) 與 Pin D5 (CLK) 之基板通孔線路。當樣品加熱至 70&deg;C 以上時呈現開路，降溫時部分導通，符合典型「間歇性微裂紋」特徵。
    </p>

    <h3>2. 剖面物性分析與顯微鏡檢 (Cross-Section & SEM Inspection)</h3>
    <p>針對開路通孔進行精密研磨切片（Cross-section）及電子顯微鏡（SEM）檢驗：</p>

    <div class="diagram-container">
        <!-- SVG Schematic Diagram -->
        <div class="diagram-box">
            <svg width="420" height="150" viewBox="0 0 420 150">
                <!-- Substrate Core -->
                <rect x="20" y="20" width="380" height="110" fill="#cbd5e1" stroke="#64748b" stroke-width="1.5"/>
                <text x="35" y="45" font-size="11" fill="#475569" font-weight="bold">BT Substrate Core (LAM-2606-0418)</text>
                
                <!-- Via Barrel -->
                <rect x="180" y="10" width="60" height="130" fill="#f8fafc" stroke="#334155" stroke-width="1.5"/>
                <!-- Copper Plating on Via Walls -->
                <rect x="180" y="10" width="12" height="130" fill="#d97706"/>
                <rect x="228" y="10" width="12" height="130" fill="#d97706"/>
                <text x="140" y="80" font-size="10" fill="#d97706" font-weight="bold">Cu Wall (20&mu;m)</text>

                <!-- Crack on Copper Wall -->
                <path d="M 178 72 L 194 76 L 178 80 Z" fill="#dc2626"/>
                <path d="M 226 73 L 242 77 L 226 81 Z" fill="#dc2626"/>
                
                <!-- Callout Annotation -->
                <line x1="240" y1="77" x2="310" y2="77" stroke="#dc2626" stroke-width="1.5" stroke-dasharray="3,3"/>
                <circle cx="234" cy="77" r="4" fill="#dc2626"/>
                <text x="315" y="75" font-size="11" fill="#dc2626" font-weight="bold">鍍銅孔壁疲勞裂紋</text>
                <text x="315" y="90" font-size="10" fill="#dc2626">(Via Barrel Crack)</text>

                <!-- CTE expansion arrows -->
                <path d="M 100 30 L 100 15 M 100 15 L 97 22 M 100 15 L 103 22" stroke="#2563eb" stroke-width="1.5"/>
                <path d="M 100 120 L 100 135 M 100 135 L 97 128 M 100 135 L 103 128" stroke="#2563eb" stroke-width="1.5"/>
                <text x="60" y="78" font-size="10" fill="#2563eb" font-weight="bold">Z-axis Expansion</text>
            </svg>
            <div class="diagram-title">圖一：通孔截面 SEM 金相示意圖 (Via Cross-Section Analysis)</div>
        </div>
    </div>

    <h3>3. 材料熱特性分析 (TMA Thermal Analysis)</h3>
    <table class="data-table">
        <thead>
            <tr>
                <th>測試項目</th>
                <th>工程規格標準</th>
                <th>供應商出廠 CoA 宣稱</th>
                <th>FA 實驗室復測結果</th>
                <th>判定</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>玻璃轉移溫度 (Tg)</strong></td>
                <td><strong>&ge; {spec["tg_c_min"]} &deg;C</strong></td>
                <td>{gr["coa_tg_c"]}.0 &deg;C (虛報/失真)</td>
                <td class="fail-text"><strong>{rma["retest_tg_c"]}.2 &deg;C</strong></td>
                <td class="fail-text">FAIL 不合格</td>
            </tr>
            <tr>
                <td>Z 軸熱膨脹係數 (&alpha;1, &lt;Tg)</td>
                <td>&le; 45 ppm/&deg;C</td>
                <td>42 ppm/&deg;C</td>
                <td>44.1 ppm/&deg;C</td>
                <td>PASS</td>
            </tr>
            <tr>
                <td>Z 軸熱膨脹係數 (&alpha;2, &gt;Tg)</td>
                <td>&le; 120 ppm/&deg;C</td>
                <td>115 ppm/&deg;C</td>
                <td class="fail-text">148.5 ppm/&deg;C</td>
                <td class="fail-text">FAIL 顯著劣化</td>
            </tr>
        </tbody>
    </table>

    <h3>4. 責任歸屬與處理建議</h3>
    <ol>
        <li><strong>供應鏈責任</strong>：基板批號 {gr["batch"]} 原料係宏達代理工廠（{SEED["parties"]["vendors"][0]["name"]}）向上游晶源材料（{SEED["parties"]["vendors"][1]["name"]}）採購之層壓板批號 {gr["vendor_batch"]}。該批原料 Tg 實測嚴重不符規格，屬原料商品質異常。宏達出具之 CoA 數據未反映真實物性。</li>
        <li><strong>廠內流程檢討</strong>：本公司進料檢驗（IQC）過度信任供應商 CoA，檢驗計畫（QA32 Lot {SEED["inspection_lots"][0]["lot"]}）中未納入 Tg 實測項目，導致問題原料流入封裝工單。</li>
        <li><strong>處置行動</strong>：立即啟動庫存凍結（基板 5,000 pcs、成品 10,000 pcs）、向宏達發出 8D 矯正通知書（QM 通知單 {rma["vendor_complaint"]["qm_notification"]}），並對客戶已出貨批次進行風險清查。</li>
    </ol>

    <div class="sig-grid">
        <div>分析工程師：<strong>黃耀賢 (Jacky Huang)</strong></div>
        <div>實驗室主管：<strong>邱明倫 (Dr. ML Chiu)</strong></div>
        <div>品質保證副總：<strong>葉柏翰 (VP P.H. Yeh)</strong></div>
    </div>
</body>
</html>"""


# ----------------------------------------------------------------------
# 4. IQC Report HTML Template
# ----------------------------------------------------------------------
def render_iqc_report_html() -> str:
    lot = SEED["inspection_lots"][0]
    po = SEED["purchase_orders"][0]
    gr = SEED["goods_receipts"][0]

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<style>
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang TC", "Microsoft JhengHei", sans-serif;
        margin: 0; padding: 40px; color: #1e293b; background: #fff;
    }}
    .header {{ border-bottom: 2px solid #047857; padding-bottom: 12px; margin-bottom: 20px; text-align: center; }}
    .co-title {{ font-size: 20px; font-weight: bold; color: #047857; }}
    .doc-title {{ font-size: 18px; font-weight: bold; color: #0f172a; margin-top: 5px; }}
    .sub {{ font-size: 12px; color: #64748b; }}
    .grid-table {{ width: 100%; border-collapse: collapse; margin-bottom: 18px; font-size: 12px; }}
    .grid-table td {{ border: 1px solid #cbd5e1; padding: 6px 10px; }}
    .lbl {{ background: #f0fdf4; font-weight: 600; width: 16%; color: #166534; }}
    .val {{ width: 34%; }}
    .data-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 12px; }}
    .data-table th, .data-table td {{ border: 1px solid #cbd5e1; padding: 8px 10px; }}
    .data-table th {{ background: #047857; color: #fff; text-align: center; font-weight: 600; }}
    .text-center {{ text-align: center; }}
    .text-right {{ text-align: right; }}
    .pass {{ color: #166534; font-weight: bold; }}
    .exempt {{ color: #d97706; font-weight: bold; background: #fef3c7; }}
    .decision-box {{
        display: flex; justify-content: space-between; align-items: center;
        border: 2px solid #047857; background: #ecfdf5; border-radius: 6px; padding: 15px 20px; margin-top: 25px;
    }}
    .decision-title {{ font-size: 18px; font-weight: bold; color: #047857; }}
    .sig-area {{ display: flex; justify-content: space-between; margin-top: 30px; font-size: 12px; }}
</style>
</head>
<body>
    <div class="header">
        <div class="co-title">宏芯記憶體科技股份有限公司 ｜ 品質保證處 進料品管課</div>
        <div class="doc-title">進料檢驗紀錄表 (IQC INSPECTION RECORD)</div>
        <div class="sub">SAP 檢驗批號 (Inspection Lot)：{lot["lot"]} ｜ 抽樣水準：MIL-STD-105E Level II Normal</div>
    </div>

    <table class="grid-table">
        <tr>
            <td class="lbl">檢驗批號 (Lot)</td>
            <td class="val"><strong>{lot["lot"]}</strong></td>
            <td class="lbl">檢驗日期 (Date)</td>
            <td class="val">{lot["date"]}</td>
        </tr>
        <tr>
            <td class="lbl">採購單號 (PO No.)</td>
            <td class="val">{po["po"]} (Item {po["item"]})</td>
            <td class="lbl">收貨單號 (GR No.)</td>
            <td class="val">{gr["mat_doc"]} (MIGO 101)</td>
        </tr>
        <tr>
            <td class="lbl">物料代號 (Material)</td>
            <td class="val">{po["material"]}</td>
            <td class="lbl">物料描述 (Desc.)</td>
            <td class="val">BT 封裝基板 (64GB 堆疊用)</td>
        </tr>
        <tr>
            <td class="lbl">供應商 (Vendor)</td>
            <td class="val">V100231 宏達代理工廠</td>
            <td class="lbl">廠商出廠批號</td>
            <td class="val">{gr["vendor_batch"]}</td>
        </tr>
        <tr>
            <td class="lbl">本廠庫存批號</td>
            <td class="val"><strong>{gr["batch"]}</strong></td>
            <td class="lbl">進貨總量 (Total Qty)</td>
            <td class="val">{po["qty"]:,} PCS</td>
        </tr>
        <tr>
            <td class="lbl">抽驗數量 (Sample n)</td>
            <td class="val"><strong>{lot["sample_n"]} PCS</strong></td>
            <td class="lbl">允收水準 (AQL)</td>
            <td class="val">AQL 0.65 (Ac: {lot["accept_no"]}, Re: 4)</td>
        </tr>
    </table>

    <table class="data-table">
        <thead>
            <tr>
                <th style="width: 8%;">項次</th>
                <th style="width: 25%;">檢驗項目 / 特性</th>
                <th style="width: 25%;">檢驗規格 / 標準</th>
                <th style="width: 15%;">檢驗樣本數</th>
                <th style="width: 15%;">量測/檢驗結果</th>
                <th style="width: 12%;">判定</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td class="text-center">1</td>
                <td>外觀包裝與防靜電標示</td>
                <td>無破損、真空防潮袋完整、濕度卡正常</td>
                <td class="text-center">200 PCS</td>
                <td class="text-center">1 件外包裝微皺摺 (Ac=3)</td>
                <td class="text-center pass">PASS 合格</td>
            </tr>
            <tr>
                <td class="text-center">2</td>
                <td>外觀尺寸 (2D 影像量測)</td>
                <td>11.50±0.05 × 13.00±0.05 mm</td>
                <td class="text-center">20 PCS</td>
                <td class="text-center">11.502 × 13.008 mm</td>
                <td class="text-center pass">PASS 合格</td>
            </tr>
            <tr>
                <td class="text-center">3</td>
                <td>鍍金層膜厚 (XRF 螢光分析)</td>
                <td>Au &ge; 0.05 &mu;m, Ni &ge; 3.0 &mu;m</td>
                <td class="text-center">5 PCS</td>
                <td class="text-center">Au: 0.054 &mu;m / Ni: 3.25 &mu;m</td>
                <td class="text-center pass">PASS 合格</td>
            </tr>
            <tr>
                <td class="text-center">4</td>
                <td>出廠品質文件查驗 (CoA)</td>
                <td>檢附原廠 CoA (COA-HD-2606-0418)</td>
                <td class="text-center">全檢 (1 份)</td>
                <td class="text-center">齊全 (宣稱 Tg 176&deg;C)</td>
                <td class="text-center pass">PASS 合格</td>
            </tr>
            <tr style="background: #fffbeb;">
                <td class="text-center">5</td>
                <td><strong>基板玻璃轉移溫度 (Tg 實測)</strong></td>
                <td><strong>&ge; 175.0 &deg;C (TMA 熱機械分析)</strong></td>
                <td class="text-center">0 PCS</td>
                <td class="text-center exempt">【免驗 / 採信 CoA】</td>
                <td class="text-center exempt">免驗放行</td>
            </tr>
        </tbody>
    </table>

    <div class="decision-box">
        <div>
            <div class="decision-title">使用決策 (Usage Decision - UD)：合格允收 (ACCEPT)</div>
            <div style="font-size: 12px; color: #047857; margin-top: 4px;">
                SAP 系統使用決策代碼：<strong>A1 (合格入庫)</strong> ｜ 備註：依檢驗基準書 WI-QA-042，原廠檢附合格 CoA 即免抽測破壞性 Tg。
            </div>
        </div>
        <div style="font-size: 24px; font-weight: bold; color: #047857; border: 2px solid #047857; padding: 4px 15px; border-radius: 4px;">
            PASSED
        </div>
    </div>

    <div class="sig-area">
        <div>檢驗員：<strong>陳建志 (J.C. Chen)</strong></div>
        <div>IQC 課長：<strong>林冠宇 (K.Y. Lin)</strong></div>
        <div>品保主管覆核：<strong>邱明倫 (Dr. ML Chiu)</strong></div>
    </div>
</body>
</html>"""


# ----------------------------------------------------------------------
# 5. Engineering Drawing & Substrate Spec HTML Template
# ----------------------------------------------------------------------
def render_drawing_spec_html() -> str:
    eval_spec = SEED["evaluation"]["parameters"]["substrate_spec"]

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<style>
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang TC", "Microsoft JhengHei", sans-serif;
        margin: 0; padding: 40px; color: #0f172a; background: #fff;
    }}
    .header {{ border-bottom: 2px solid #1e3a8a; padding-bottom: 10px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: flex-end; }}
    .co-title {{ font-size: 18px; font-weight: bold; color: #1e3a8a; }}
    .doc-title {{ font-size: 20px; font-weight: bold; color: #0f172a; margin-top: 4px; }}
    .rev-badge {{ background: #1e3a8a; color: #fff; padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
    .grid-info {{ width: 100%; border-collapse: collapse; margin-bottom: 18px; font-size: 12px; }}
    .grid-info td {{ border: 1px solid #cbd5e1; padding: 5px 8px; }}
    .lbl {{ background: #eff6ff; font-weight: 600; width: 16%; color: #1e3a8a; }}
    .val {{ width: 34%; }}
    .blueprint-area {{
        background: #0f172a; border-radius: 8px; padding: 20px; color: #38bdf8;
        display: flex; justify-content: space-around; align-items: center; margin-bottom: 20px;
    }}
    .blueprint-caption {{ color: #94a3b8; font-size: 11px; text-align: center; margin-top: 6px; }}
    .spec-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 12px; }}
    .spec-table th, .spec-table td {{ border: 1px solid #cbd5e1; padding: 7px 10px; }}
    .spec-table th {{ background: #1e3a8a; color: #fff; text-align: center; font-weight: 600; }}
    .critical {{ background: #fef2f2; font-weight: bold; color: #b91c1c; }}
    .sig-area {{ display: flex; justify-content: space-between; margin-top: 25px; border-top: 1px solid #cbd5e1; padding-top: 10px; font-size: 12px; }}
</style>
</head>
<body>
    <div class="header">
        <div>
            <div class="co-title">宏芯記憶體科技 產品研發與元器件工程處</div>
            <div class="doc-title">BT 基板工程規格書與封裝藍圖 (SUBSTRATE ENGINEERING SPEC & DRAWING)</div>
        </div>
        <div class="rev-badge">
            規格代碼：DWG-SUB-BT64-01 (Rev. B)
        </div>
    </div>

    <table class="grid-info">
        <tr>
            <td class="lbl">工程圖號 (Doc ID)</td>
            <td class="val"><strong>DWG-SUB-BT64-01</strong></td>
            <td class="lbl">版次 (Revision)</td>
            <td class="val">Rev. B (2026-05-15 生效)</td>
        </tr>
        <tr>
            <td class="lbl">適用料號 (Part No.)</td>
            <td class="val">RM-SUB-BT64</td>
            <td class="lbl">適用產品 (Product)</td>
            <td class="val">FG-EM64-A1 (eMMC 5.1 64GB)</td>
        </tr>
        <tr>
            <td class="lbl">基板基材 (Base Material)</td>
            <td class="val">High-Tg 無鹵素 BT 樹脂層壓板</td>
            <td class="lbl">堆疊結構 (Stackup)</td>
            <td class="val">2-Layer (1 Core, 2 Cu Layers)</td>
        </tr>
        <tr>
            <td class="lbl">外觀尺寸 (Dimensions)</td>
            <td class="val">11.50 x 13.00 mm</td>
            <td class="lbl">整體厚度 (Thickness)</td>
            <td class="val">0.22 mm (±0.02 mm)</td>
        </tr>
    </table>

    <div class="blueprint-area">
        <!-- SVG Engineering CAD Vector Diagram -->
        <div>
            <svg width="450" height="160" viewBox="0 0 450 160">
                <!-- Outer substrate boundary -->
                <rect x="30" y="20" width="220" height="120" fill="none" stroke="#38bdf8" stroke-width="2" stroke-dasharray="none"/>
                <!-- Die attach area -->
                <rect x="55" y="35" width="170" height="90" fill="#1e293b" stroke="#0284c7" stroke-width="1.5"/>
                <text x="90" y="85" fill="#38bdf8" font-size="11" font-weight="bold">Die Attach Area (10x11.5mm)</text>

                <!-- Ball Grid Array Dots (Schematic) -->
                <g fill="#f59e0b">
                    <circle cx="40" cy="30" r="2.5"/><circle cx="48" cy="30" r="2.5"/><circle cx="56" cy="30" r="2.5"/>
                    <circle cx="40" cy="130" r="2.5"/><circle cx="48" cy="130" r="2.5"/><circle cx="56" cy="130" r="2.5"/>
                    <circle cx="230" cy="30" r="2.5"/><circle cx="238" cy="30" r="2.5"/><circle cx="240" cy="30" r="2.5"/>
                    <circle cx="230" cy="130" r="2.5"/><circle cx="238" cy="130" r="2.5"/><circle cx="240" cy="130" r="2.5"/>
                </g>

                <!-- Dimensions & Annotations -->
                <!-- Width 11.50mm -->
                <line x1="30" y1="12" x2="250" y2="12" stroke="#38bdf8" stroke-width="1"/>
                <line x1="30" y1="8" x2="30" y2="16" stroke="#38bdf8" stroke-width="1"/>
                <line x1="250" y1="8" x2="250" y2="16" stroke="#38bdf8" stroke-width="1"/>
                <text x="110" y="9" fill="#38bdf8" font-size="9" text-anchor="middle">11.50 ± 0.05 mm</text>

                <!-- Height 13.00mm -->
                <line x1="262" y1="20" x2="262" y2="140" stroke="#38bdf8" stroke-width="1"/>
                <line x1="258" y1="20" x2="266" y2="20" stroke="#38bdf8" stroke-width="1"/>
                <line x1="258" y1="140" x2="266" y2="140" stroke="#38bdf8" stroke-width="1"/>
                <text x="268" y="85" fill="#38bdf8" font-size="9">13.00 ± 0.05 mm</text>

                <!-- Layer Stackup Diagram on the Right -->
                <g transform="translate(300, 25)">
                    <rect x="0" y="0" width="130" height="15" fill="#d97706" stroke="#92400e"/>
                    <text x="15" y="11" fill="#fff" font-size="9" font-weight="bold">Top Cu Layer</text>

                    <rect x="0" y="15" width="130" height="60" fill="#334155" stroke="#475569"/>
                    <text x="10" y="48" fill="#38bdf8" font-size="9" font-weight="bold">BT Core (0.16mm)</text>

                    <rect x="0" y="75" width="130" height="15" fill="#d97706" stroke="#92400e"/>
                    <text x="12" y="86" fill="#fff" font-size="9" font-weight="bold">Bottom Cu Layer</text>

                    <!-- Total Thickness indicator -->
                    <line x1="138" y1="0" x2="138" y2="90" stroke="#f1f5f9" stroke-width="1"/>
                    <text x="142" y="50" fill="#f1f5f9" font-size="8">0.22±0.02mm</text>
                </g>
            </svg>
            <div class="blueprint-caption">圖二：基板外觀幾何工程圖與 2-Layer 剖面疊構規格</div>
        </div>
    </div>

    <table class="spec-table">
        <thead>
            <tr>
                <th style="width: 10%;">參數代碼</th>
                <th style="width: 32%;">關鍵品質特性 / Technical Parameter</th>
                <th style="width: 28%;">規格要求 (Specification)</th>
                <th style="width: 30%;">測試標準 / 驗證方法</th>
            </tr>
        </thead>
        <tbody>
            <tr class="critical">
                <td style="text-align: center;">CTQ-01</td>
                <td><strong>玻璃轉移溫度 (Glass Transition Temp, Tg)</strong></td>
                <td><strong>&ge; {eval_spec["tg_c_min"]}.0 &deg;C</strong></td>
                <td>TMA (IPC-TM-650 2.4.24)</td>
            </tr>
            <tr>
                <td style="text-align: center;">CTQ-02</td>
                <td>貫孔孔壁鍍銅厚度 (Via Cu Plating)</td>
                <td>&ge; {eval_spec["cu_plating_um_min"]}.0 &mu;m</td>
                <td>IPC-6012 Class 3 金相切片</td>
            </tr>
            <tr>
                <td style="text-align: center;">CTQ-03</td>
                <td>Z 軸熱膨脹係數 (&alpha;1, 低於 Tg)</td>
                <td>&le; 45.0 ppm/&deg;C</td>
                <td>TMA (IPC-TM-650 2.4.24)</td>
            </tr>
            <tr>
                <td style="text-align: center;">CTQ-04</td>
                <td>Z 軸熱膨脹係數 (&alpha;2, 高於 Tg)</td>
                <td>&le; 120.0 ppm/&deg;C</td>
                <td>TMA (IPC-TM-650 2.4.24)</td>
            </tr>
            <tr>
                <td style="text-align: center;">CTQ-05</td>
                <td>高低溫循環可靠度 (Thermal Cycling)</td>
                <td>-55&deg;C ~ +125&deg;C &times; 500 cycles (零開路)</td>
                <td>JEDEC JESD22-A104</td>
            </tr>
            <tr>
                <td style="text-align: center;">CTQ-06</td>
                <td>難燃性等級 (Flammability)</td>
                <td>UL 94 V-0</td>
                <td>UL94 標準垂直燃燒測試</td>
            </tr>
        </tbody>
    </table>

    <div class="sig-area">
        <div>研發專案負責人：<strong>洪振宇 (Eric Hung)</strong></div>
        <div>封裝設計處長：<strong>何威儀 (Wayne Ho)</strong></div>
        <div>品保處長核定：<strong>邱明倫 (Dr. ML Chiu)</strong></div>
    </div>
</body>
</html>"""


# ----------------------------------------------------------------------
# Generator Execution
# ----------------------------------------------------------------------
def main():
    docs_to_generate = [
        {
            "id": "COA-HD-2606-0418",
            "name": "Supplier CoA (宏達代理工廠出廠檢驗證明)",
            "category": "QM_IQC",
            "html_fn": render_coa_html,
            "target_fields": {
                "coa_no": "COA-HD-2606-0418",
                "vendor": "宏達電子材料股份有限公司",
                "vendor_batch": "LAM-2606-0418",
                "po_number": "4500012345",
                "material": "RM-SUB-BT64",
                "quantity": 45000,
                "claimed_tg_c": 176.0,
                "cu_plating_um": 20.2
            }
        },
        {
            "id": "PO-LY-2608-0075",
            "name": "Customer PO (凌雲電子採購訂單)",
            "category": "SD_SO",
            "html_fn": render_customer_po_html,
            "target_fields": {
                "po_number": "LY-PO-2608-0075",
                "buyer": "凌雲電子股份有限公司",
                "seller": "宏芯記憶體科技股份有限公司",
                "order_date": "2026-08-04",
                "material": "FG-EM64-A1",
                "quantity": 20000,
                "unit_price_usd": 3.85,
                "total_amount_usd": 77000.00,
                "payment_terms": "NET 45"
            }
        },
        {
            "id": "FA-2026-117",
            "name": "FA Report (失效分析報告)",
            "category": "QM_FA",
            "html_fn": render_fa_report_html,
            "target_fields": {
                "report_id": "FA-2026-117",
                "rma_no": "RMA-LY-2610-006",
                "customer": "凌雲電子股份有限公司",
                "fg_batch": "FG-B2607-01",
                "substrate_batch": "SUB-HD-2606-A",
                "vendor_batch": "LAM-2606-0418",
                "failure_mode": "高低溫循環後間歇性開路",
                "retested_tg_c": 168.2,
                "spec_tg_c_min": 175.0,
                "root_cause_summary": "BT層壓板Tg偏低導致通孔銅鍍層疲勞斷裂"
            }
        },
        {
            "id": "IQC-010000003301",
            "name": "IQC Report (進料檢驗紀錄表)",
            "category": "QM_IQC",
            "html_fn": render_iqc_report_html,
            "target_fields": {
                "lot_no": "010000003301",
                "po_number": "4500012345",
                "gr_mat_doc": "5000008812",
                "material": "RM-SUB-BT64",
                "internal_batch": "SUB-HD-2606-A",
                "vendor_batch": "LAM-2606-0418",
                "sample_size": 200,
                "usage_decision": "ACCEPT",
                "tg_tested": False
            }
        },
        {
            "id": "DWG-SUB-BT64-01",
            "name": "Substrate Drawing & Spec (基板工程圖與規格書)",
            "category": "RD_SPEC",
            "html_fn": render_drawing_spec_html,
            "target_fields": {
                "drawing_no": "DWG-SUB-BT64-01",
                "revision": "Rev. B",
                "material": "RM-SUB-BT64",
                "spec_tg_min": 175.0,
                "spec_cu_plating_min": 18.0,
                "dimensions": "11.50 x 13.00 mm",
                "thickness": "0.22 mm"
            }
        }
    ]

    manifest = {
        "generated_at": "2026-11-10",
        "scenario_id": "SCN-RMA-001",
        "description": "情境 SCN-RMA-001 實體單據 OCR 驗證樣本集 (PDF + PNG)",
        "documents": []
    }

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1050, "height": 1400}, device_scale_factor=2)

        for doc in docs_to_generate:
            html_content = doc["html_fn"]()
            page.set_content(html_content, wait_until="networkidle")

            pdf_filename = f"{doc['id']}.pdf"
            png_filename = f"{doc['id']}.png"

            pdf_path = OUTPUT_DIR / pdf_filename
            png_path = OUTPUT_DIR / png_filename

            # Export PDF
            page.pdf(
                path=str(pdf_path),
                format="A4",
                print_background=True,
                margin={"top": "15mm", "bottom": "15mm", "left": "15mm", "right": "15mm"}
            )

            # Export high-DPI screenshot PNG
            page.screenshot(path=str(png_path), full_page=True)

            print(f"✅ Generated: {pdf_filename} & {png_filename}")

            manifest["documents"].append({
                "doc_id": doc["id"],
                "doc_name": doc["name"],
                "category": doc["category"],
                "pdf_file": pdf_filename,
                "png_file": png_filename,
                "pdf_sha256": calculate_sha256(pdf_path),
                "png_sha256": calculate_sha256(png_path),
                "target_fields": doc["target_fields"]
            })

        browser.close()

    manifest_path = OUTPUT_DIR / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"✅ Generated manifest: {manifest_path}")


if __name__ == "__main__":
    main()

