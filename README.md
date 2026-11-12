# AgenticDoc RPA (`agentic-doc-rpa`)

> **Autonomous Document Intelligence & Dual-Engine Vision RPA Platform**  
> *End-to-End Enterprise Document Lifecycle Auditing and Multimodal Workflow Automation*

[ English ] | [ [繁體中文 (台灣)](./README.zh-TW.md) ] | [ [日本語](./README.ja.md) ] | [ [한국어](./README.ko.md) ]

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Apple%20Silicon-orange.svg)]()
[![Architecture](https://img.shields.io/badge/Architecture-Dual--Engine%20RPA-purple.svg)]()

---

## 📖 Overview

**AgenticDoc RPA** is an on-premise, enterprise-grade platform designed for document verification, supply-chain traceability, and desktop/browser visual automation. 

By combining offline multimodal vision OCR with a flexible dual-engine RPA executor, AgenticDoc RPA extracts structured data from complex business documents (PO, CoA, WO, DWG, FA inspection sheets) and automates repetitive data entry tasks without sending sensitive operational data to third-party cloud services.

---

## 🛠️ Languages & AI Technologies Used

### Programming & Scripting Languages
* **Python (3.11+)**: Core application backend, orchestration, document parsing, and automation drivers.
* **HTML5 / CSS3**: Responsive Single-Page Application (SPA) dashboard for visual audit and RPA studio.
* **JavaScript (ES6+)**: Client-side document interaction, bounding box canvas overlay, and real-time execution feedback.
* **Shell (Bash / Zsh)**: Environment bootstrapping and virtual environment configuration utilities.

### AI, Computer Vision & Automation Stack
* **Deep Learning OCR Inference**: **RapidOCR** backed by **ONNX Runtime**, providing fast, high-accuracy text and tabular detection completely offline.
* **Native High-DPI Document Rasterization**: macOS Quartz / PDFKit native integration for rendering PDF pages at 150+ DPI without heavy external tools.
* **Spatial & Geometric Processing**: **Shapely** and **OpenCV** for bounding box validation, coordinate normalization, and Retina display scaling (2.0x).
* **Dual-Engine Execution**:
  * **Engine A (Web DOM)**: Driven by **Playwright**, providing isolated browser automation with selector introspection and step-by-step visual demonstration.
  * **Engine B (Native OS / Chrome Passthrough)**: Driven by **PyAutoGUI** and macOS native accessibility hooks, running directly on personal browser sessions with persistent state.
* **Distributed Orchestration**: **Temporal.io** durable workflow state machines combined with **Apache Airflow** batch coordination.

---

## 🌟 Key Highlights

1. **100% On-Premise Execution**:
   All OCR inference, document extraction, and script parsing execute locally on Apple Silicon / macOS. Zero cloud transmission ensures strict compliance with confidential corporate data policies.
2. **OmniTrace Cross-Document Verification**:
   Automatically audits numeric tolerances, batch lot numbers, and cross-references manufacturing records (PO ➔ IQC ➔ WO ➔ CoA ➔ SO ➔ RMA).
3. **Natural Language Action Parser**:
   Accepts human-readable commands (e.g., `GOTO`, `TYPE`, `CLICK`, `WAIT`, `SCREENSHOT`) with flexible error handling strategies (`skip` vs `abort`).

---

## 🏗️ System Architecture

```text
[ Multimodal Input: PDF / Scanned Images / Desktop Screen ]
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│     OmniTrace Vision OCR & Audit Pipeline             │
│     • Quartz / PDFKit Native Rasterization             │
│     • RapidOCR Offline ONNX Inference                  │
│     • Physical Pixel to Retina Logical Point Mapping    │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│       AgenticDoc RPA Decision & Dual-Track Router      │
│     • Natural Language Intent Extraction               │
│     • Failure Recovery Policies (Skip / Abort)         │
└───────────────┬────────────────────────┬───────────────┘
                │                        │
                ▼                        ▼
┌─────────────────────────────┐ ┌─────────────────────────────┐
│ Engine A: Web DOM           │ │ Engine B: Native Chrome     │
│ • Playwright DOM selectors  │ │ • Retains active profiles   │
│ • Sandboxed batch execution │ │ • Human-like smooth cursor  │
│ • Step screenshot logging   │ │ • Persistent open session   │
└─────────────────────────────┘ └─────────────────────────────┘
```

---

## 📁 Repository Structure

```text
agentic-doc-rpa/
├── README.md                           # Main English documentation
├── README.zh-TW.md                     # Traditional Chinese documentation
├── README.ja.md                        # Japanese documentation
├── README.ko.md                        # Korean documentation
├── LICENSE                             # MIT Open Source License
├── requirements_rpa_ocr.txt            # RPA & Vision OCR core dependencies
├── requirements_airflow.txt            # Airflow orchestration dependencies
└── src/                                # Application source code
    ├── ocr/                            # RapidOCR processing pipeline
    ├── rpa/                            # Dual-engine RPA implementation
    ├── web_audit/                      # Web dashboard & RPA studio interface
    ├── scenario/                       # Document scenario generation & testing
    └── utils/                          # Cross-platform environment tools
```

---

## 🚀 Quick Start

### 1. Requirements
* macOS (optimized for Apple Silicon M-series)
* Python 3.11+

### 2. Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv .venv_rpa_ocr
source .venv_rpa_ocr/bin/activate

# Install dependencies
pip install -r requirements_rpa_ocr.txt

# Install Playwright browser dependencies
playwright install chromium
```

### 3. Launching the Web Audit & RPA Studio
```bash
.venv_rpa_ocr/bin/python src/web_audit/server.py --port 8080
```
Open your browser and navigate to **`http://127.0.0.1:8080`** to access:
* **Document Audit Studio**: Drag-and-drop PDF / image documents for automatic field extraction and quality checks.
* **Natural Language RPA Studio**: Execute multi-step browser tasks using intuitive natural language scripts.

---

## 📄 License & Attribution

This project is licensed under the [MIT License](LICENSE).

### Third-Party Notice
This project integrates open-source components including:
* [RapidOCR](https://github.com/RapidAI/RapidOCR) (Apache 2.0)
* [Playwright](https://github.com/microsoft/playwright) (Apache 2.0)
* [PyAutoGUI](https://github.com/asweigart/pyautogui) (BSD)
* [Temporalio Python SDK](https://github.com/temporalio/sdk-python) (MIT)
* [Pydantic](https://github.com/pydantic/pydantic) (MIT)

---

## 🔒 Security & Privacy

* **Zero Outbound Data Leakage**: All machine learning inference and document processing run locally.
* **Protected Automation**: Engine B interacts with existing local Chrome sessions without logging or transmitting user credentials.
