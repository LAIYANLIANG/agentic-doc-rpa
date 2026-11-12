# AgenticDoc RPA (`agentic-doc-rpa`)

> **智能單據代理與雙引擎視覺 RPA 系統**  
> *Autonomous Document Intelligence & Dual-Engine Vision RPA Platform*

[ [English](./README.md) ] | [ 繁體中文 (台灣) ] | [ [日本語](./README.ja.md) ] | [ [한국어](./README.ko.md) ]

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Apple%20Silicon-orange.svg)]()
[![Architecture](https://img.shields.io/badge/Architecture-Dual--Engine%20RPA-purple.svg)]()

---

## 📖 專案簡介 (Overview)

**AgenticDoc RPA** 是一套專為企業級單據生命週期審計、供應鏈追溯與現代化桌面/網頁自動化設計的**智能單據代理與雙引擎視覺 RPA 系統**。

本系統全程具備 **100% 地端原生運作 (On-Premise Ready)** 能力，免除機敏商業製造機密與財務單據上傳公有雲的外洩風險。透過整合多模態視覺 OCR 與雙軌 RPA 執行器，AI 代理能精確辨識商業單據（PO 採購單、CoA 檢驗證明、工單、工程圖面、失效分析報告等），並透過雙引擎執行自動化填報與流程串接。

---

## 🛠️ 使用之程式語言與 AI 技術宣告 (Tech Stack & AI)

### 程式與腳本語言 (Programming Languages)
* **Python (3.11+)**：系統核心後端、工作流編排、單據特徵抽取與自動化驅動。
* **HTML5 / CSS3**：響應式單頁應用 (SPA)，提供即時審計視覺化與 RPA 操作台。
* **JavaScript (ES6+)**：前端動態欄位呈現、Canvas 外框繪製與即時狀態輪詢。
* **Shell (Bash / Zsh)**：環境自動化引導與虛擬環境路徑校正工具。

### AI、電腦視覺與自動化技術宣告 (AI & Vision Stack)
* **深度學習視覺 OCR 推論**：採用 **RapidOCR** 核心配合 **ONNX Runtime** 加速引擎，提供全地端、高精度的多語系印刷與表格文字識別。
* **原生高解析度光柵化**：結合 macOS 原生 Quartz (PDFKit) 圖形子系統，以 150+ DPI 高解析度原生渲染 PDF 單據，不依賴外部龐大工具。
* **空間幾何與座標校準**：使用 **Shapely** 與 **OpenCV** 進行邊界框（Bounding Box）關聯分析，並自動校準 Retina 螢幕解析度倍率（2.0x 邏輯座標映射）。
* **雙引擎 RPA 架構**：
  * **引擎 A (Web DOM 核心)**：由 **Playwright** 驅動，適用於無感批次執行、DOM 元素精確定位與 Slow-mo 示範。
  * **引擎 B (日常 Chrome 直通)**：由 **PyAutoGUI** 與 macOS 系統輔助功能驅動，直接喚醒已登入個人帳號之日常 Chrome，保持視窗常開。
* **分散式持久化狀態機**：整合 **Temporal.io** 耐久工作流程與 **Apache Airflow** 宏觀排程切批。

---

## 🌟 核心特色 (Core Highlights)

1. **100% 純地端安全運作**：所有 OCR 推論與單據分析皆於本地完成，數據絕不流出內網。
2. **端到端單據追溯 (OmniTrace)**：自動交叉比對供應鏈各階段數值（PO ➔ IQC ➔ WO ➔ CoA ➔ SO ➔ RMA 8D）。
3. **白話自然語言腳本解析器**：支援直覺的自然語言指令（如 `前往網址`、`輸入`、`點擊`、`等待`、`截圖`），並具備 `跳過 (skip)` 與 `中斷 (abort)` 容錯策略。

---

## 🏗️ 系統架構圖 (Architecture)

```text
[ 多模態輸入 (PDF / 圖檔 / 桌面畫面) ]
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│     OmniTrace 視覺 OCR 抽取與審計核心                  │
│     • Quartz / PDFKit 原生光柵化                       │
│     • RapidOCR 地端 ONNX 深度推論                      │
│     • 螢幕物理像素 ➔ Retina 邏輯座標自動映射            │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│       AgenticDoc RPA 智能決策與雙軌路由器              │
│     • 自然語言意圖抽取與失敗容錯策略 (Skip / Abort)     │
│     • 雙引擎動態分派                                   │
└───────────────┬────────────────────────┬───────────────┘
                │                        │
                ▼                        ▼
┌─────────────────────────────┐ ┌─────────────────────────────┐
│ 引擎 A：Web DOM 引擎 (Playwright)│ │ 引擎 B：日常 Chrome 直通引擎 (OS)│
│ • DOM 樹精確定位回放        │ │ • 帳號登入態完全繼承        │
│ • 沙盒批次無感執行          │ │ • 人類平滑游標移動 / 實體點擊│
│ • 步驟截圖即時產生          │ │ • 視窗持續保持開啟播放      │
└─────────────────────────────┘ └─────────────────────────────┘
```

---

## 📁 目錄結構說明 (Directory Layout)

```text
agentic-doc-rpa/
├── README.md                           # 英文主說明文件
├── README.zh-TW.md                     # 台灣繁體中文說明文件
├── README.ja.md                        # 日文說明文件
├── README.ko.md                        # 韓文說明文件
├── LICENSE                             # MIT 開源授權協議
├── requirements_rpa_ocr.txt            # RPA 與視覺 OCR 核心相依套件清冊
├── requirements_airflow.txt            # 宏觀排程相依套件清冊
└── src/                                # 核心原始碼
    ├── ocr/                            # RapidOCR 視覺抽取管線
    ├── rpa/                            # 雙引擎 RPA 實作與定位器
    ├── web_audit/                      # 智慧審計與 RPA Studio Web 介面
    ├── scenario/                       # 單據情境與測試驗證資料
    └── utils/                          # 通用工具與環境修復腳本
```

---

## 🚀 快速上手 (Quick Start)

### 1. 環境準備
* **作業系統**：macOS (推薦 Apple Silicon M 系列晶片)
* **Python 版本**：Python 3.11+

### 2. 安裝相依套件
```bash
# 建立並啟用虛擬環境
python3 -m venv .venv_rpa_ocr
source .venv_rpa_ocr/bin/activate

# 安裝核心依賴
pip install -r requirements_rpa_ocr.txt

# 安裝 Playwright 瀏覽器核心
playwright install chromium
```

### 3. 啟動 Web 審計與 RPA Studio
```bash
.venv_rpa_ocr/bin/python src/web_audit/server.py --port 8080
```
開啟瀏覽器訪問：**`http://127.0.0.1:8080`** 即可體驗：
* 📄 **商業單據 OCR 與品質審計**：支援拖曳上傳單據，即時抽取結構化 JSON 與欄位公差校驗。
* 🤖 **自然語言 RPA Studio**：以白話自然語言指令執行雙引擎自動化操作與視覺高亮截圖。

---

## 📄 授權協議宣告 (License)

本專案採用 **[MIT License](LICENSE)** 授權協議開放原始碼。

### 第三方開源套件聲明
本專案整合之第三方重要開源組件：
* [RapidOCR](https://github.com/RapidAI/RapidOCR) (Apache 2.0)
* [Playwright](https://github.com/microsoft/playwright) (Apache 2.0)
* [PyAutoGUI](https://github.com/asweigart/pyautogui) (BSD)
* [Temporalio Python SDK](https://github.com/temporalio/sdk-python) (MIT)
* [Pydantic](https://github.com/pydantic/pydantic) (MIT)

---

## 🔒 資訊安全與隱私宣告 (Security & Privacy)

* **數據不出地端**：全流程 AI 推論與視覺辨識皆在本地記憶體與核心處理器運行。
* **真實帳號安全直通**：直接操控本機日常 Chrome 視窗，完全不讀取、不儲存亦不上傳使用者的密碼或 Session Cookie。
