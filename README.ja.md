# AgenticDoc RPA (`agentic-doc-rpa`)

> **インテリジェント文書エージェント＆デュアルエンジン視覚RPAシステム**  
> *Autonomous Document Intelligence & Dual-Engine Vision RPA Platform*

[ [English](./README.md) ] | [ [繁體中文 (台灣)](./README.zh-TW.md) ] | [ 日本語 ] | [ [한국어](./README.ko.md) ]

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Apple%20Silicon-orange.svg)]()
[![Architecture](https://img.shields.io/badge/Architecture-Dual--Engine%20RPA-purple.svg)]()

---

## 📖 プロジェクト概要 (Overview)

**AgenticDoc RPA** は、企業向けビジネス文書のライフサイクル監査、サプライチェーン追跡、および最新のデスクトップ/Web自動化のために設計された**インテリジェント文書エージェント＆デュアルエンジン視覚RPAシステム**です。

本システムは **100% オンプレミス（完全ローカル）** で動作可能であり、機密性の高い製造情報や財務帳票が外部パブリッククラウドに流出するリスクを完全に排除します。マルチモーダル視覚OCRとデュアルトラックRPAを統合することで、AIエージェントが帳票（発注書PO、検査成績書CoA、作業指示書WO、図面、不具合分析書FAなど）を精確に読み取り、システム間の自動入力を完遂します。

---

## 🛠️ 使用プログラミング言語＆AI技術の宣言 (Tech Stack & AI)

### 使用プログラミング言語 (Programming Languages)
* **Python (3.11+)**：バックエンドコア、ワークフロー制御、OCRデータ抽出、自動化ドライバー。
* **HTML5 / CSS3**：監査ダッシュボードおよびRPAスタジオ用レスポンシブWeb UI (SPA)。
* **JavaScript (ES6+)**：クライアント側のCanvasバウンディングボックス描画、帳票プレビュー、非同期制御。
* **Shell (Bash / Zsh)**：仮想環境自動修正スクリプトおよびブートストラップ。

### AI・コンピュータビジョン・自動化スタック (AI & Vision Stack)
* **ディープラーニング視覚OCR推論**：**ONNX Runtime** 上で動作する **RapidOCR** を採用。完全オフラインかつ高精度なテキスト・表構造抽出を実現。
* **ネイティブ高解像度ラスタライズ**：macOSネイティブの Quartz (PDFKit) グラフィックサブシステムを活用し、外部ツール不要で150+ DPIの高解像度レンダリングを実行。
* **幾何空間・座標補正**：**Shapely** および **OpenCV** によるバウンディングボックス整合性検証、ならびに Retina ディスプレイ（2.0x 論理座標マッピング）の自動校正。
* **デュアルエンジンRPAアーキテクチャ**：
  * **エンジンA（Web DOMコア）**：**Playwright** による高速バックグラウンド実行、DOM要素特定、ステップ別ハイライト表示。
  * **エンジンB（日常Chromeダイレクト）**：**PyAutoGUI** および macOSアクセシビリティAPIによる駆動。既存のGoogleログイン状態を保持したまま、ウィンドウを維持して操作。
* **分散高信頼オーケストレーション**：**Temporal.io** 耐障害性ワークフローステートマシンおよび **Apache Airflow** バッチ分割制御。

---

## 🌟 主な特長 (Key Highlights)

1. **100% オンプレミス動作**：すべてのOCR推論と文書解析がローカル環境で完結し、機密情報を社外に出しません。
2. **エンドツーエンド文書トレーサビリティ**：サプライチェーン各工程のロット番号や品質スペック値（ガラス転移温度 $T_g$ 等）を自動照合。
3. **自然言語RPAスクリプト**：`前往網址`（URLへ移動）、`輸入`（入力）、`點擊`（クリック）等の自然言語指示に対応し、エラー時のスキップ（skip）および中断（abort）戦略をサポート。

---

## 🏗️ システムアーキテクチャ (Architecture)

```text
[ マルチモーダル入力 (PDF / 画像 / デスクトップ画面) ]
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│     OmniTrace 視覚OCR抽出＆品質監査コア                │
│     • Quartz / PDFKit ネイティブラスタライズ           │
│     • RapidOCR ローカルONNX高速推論                    │
│     • 物理ピクセル ➔ Retina論理座標の自動マッピング     │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│      AgenticDoc RPA インテリジェントデュアルルーター   │
│     • 自然言語意図抽出とフォールトトレランス戦略       │
│     • デュアルエンジンの動的ディスパッチ               │
└───────────────┬────────────────────────┬───────────────┘
                │                        │
                ▼                        ▼
┌─────────────────────────────┐ ┌─────────────────────────────┐
│ エンジンA：Web DOM (Playwright)│ │ エンジンB：日常Chrome直通 (OS) │
│ • DOMセレクター高精度制御   │ │ • 既存ログインセッション維持 │
│ • サンドボックス一括処理    │ │ • 滑らかなカーソル移動/クリック│
│ • 各ステップ画面キャプチャ  │ │ • ウィンドウ常時開いたまま   │
└─────────────────────────────┘ └─────────────────────────────┘
```

---

## 📁 ディレクトリ構造 (Directory Layout)

```text
agentic-doc-rpa/
├── README.md                           # 英語メインドキュメント
├── README.zh-TW.md                     # 台湾繁体字中国語ドキュメント
├── README.ja.md                        # 日本語ドキュメント
├── README.ko.md                        # 韓国語ドキュメント
├── LICENSE                             # MITオープンソースライセンス
├── requirements_rpa_ocr.txt            # RPA・視覚OCRコア依存パッケージ
├── requirements_airflow.txt            # Airflow依存パッケージ
└── src/                                # アプリケーションソースコード
    ├── ocr/                            # RapidOCR処理パイプライン
    ├── rpa/                            # デュアルエンジンRPA実装
    ├── web_audit/                      # Webダッシュボード＆RPAスタジオ
    ├── scenario/                       # 帳票生成・検証シナリオ
    └── utils/                          # 環境補正ユーティリティ
```

---

## 🚀 クイックスタート (Quick Start)

### 1. 動作環境
* macOS (Apple Silicon Mシリーズ推奨)
* Python 3.11+

### 2. 環境構築
```bash
# 仮想環境の作成と有効化
python3 -m venv .venv_rpa_ocr
source .venv_rpa_ocr/bin/activate

# 依存ライブラリのインストール
pip install -r requirements_rpa_ocr.txt

# Playwrightブラウザのインストール
playwright install chromium
```

### 3. Web監査＆RPAスタジオの起動
```bash
.venv_rpa_ocr/bin/python src/web_audit/server.py --port 8080
```
ブラウザで **`http://127.0.0.1:8080`** にアクセスして以下を体験できます：
* 📄 **帳票OCR＆品質監査**：PDF/画像をドラッグ＆ドロップし、構造化JSON抽出と公差チェックを瞬時に実行。
* 🤖 **自然言語RPAスタジオ**：シンプルな自然言語でブラウザ自動化フローを作成・実行。

---

## 📄 ライセンス宣言 (License)

本プロジェクトは **[MIT License](LICENSE)** に基づいて公開されています。

### サードパーティオープンソースライブラリ
* [RapidOCR](https://github.com/RapidAI/RapidOCR) (Apache 2.0)
* [Playwright](https://github.com/microsoft/playwright) (Apache 2.0)
* [PyAutoGUI](https://github.com/asweigart/pyautogui) (BSD)
* [Temporalio Python SDK](https://github.com/temporalio/sdk-python) (MIT)
* [Pydantic](https://github.com/pydantic/pydantic) (MIT)

---

## 🔒 セキュリティとプライバシー保護

* **データ外部流出ゼロ**：すべてのAI推論および文書OCRは完全にローカル環境内で完結します。
* **アカウント認証の安全性**：日常利用しているChromeセッションを直接利用し、ユーザーのパスワードやセッショントークンを取得・保存・送信することは一切ありません。
