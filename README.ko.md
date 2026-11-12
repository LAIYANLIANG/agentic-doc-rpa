# AgenticDoc RPA (`agentic-doc-rpa`)

> **지능형 문서 에이전트 & 듀얼 엔진 비전 RPA 시스템**  
> *Autonomous Document Intelligence & Dual-Engine Vision RPA Platform*

[ [English](./README.md) ] | [ [繁體中文 (台灣)](./README.zh-TW.md) ] | [ [日本語](./README.ja.md) ] | [ 한국어 ]

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Apple%20Silicon-orange.svg)]()
[![Architecture](https://img.shields.io/badge/Architecture-Dual--Engine%20RPA-purple.svg)]()

---

## 📖 프로젝트 개요 (Overview)

**AgenticDoc RPA**는 기업용 비즈니스 문서의 라이프사이클 감사, 공급망 추적성(Traceability), 최신 데스크톱 및 웹 자동화를 위해 구축된 **지능형 문서 에이전트 & 듀얼 엔진 비전 RPA 시스템**입니다.

본 시스템은 **100% 온프레미스(로컬 환경)** 구동이 가능하여, 민감한 제조 기밀 및 재무 문서가 퍼블릭 클라우드로 유출되는 위험을 원천 차단합니다. 멀티모달 비전 OCR과 듀얼 트랙 RPA 실행기를 통합하여, AI 에이전트가 비즈니스 문서(구매발주서 PO, 검사성적서 CoA, 작업지시서 WO, 도면 DWG, 고장분석서 FA 등)를 정확히 판독하고 시스템 간 자동 기입을 처리합니다.

---

## 🛠️ 사용 언어 및 AI 기술 명시 (Tech Stack & AI)

### 프로그래밍 언어 (Programming Languages)
* **Python (3.11+)**: 백엔드 코어 엔진, 워크플로 오케스트레이션, 문서 데이터 추출, 자동화 드라이버.
* **HTML5 / CSS3**: 문서 품질 감사 대시보드 및 RPA 스튜디오를 위한 반응형 SPA 웹 UI.
* **JavaScript (ES6+)**: 클라이언트 측 Canvas 바운딩 박스 오버레이, 문서 미리보기 및 실시간 실행 인터랙션.
* **Shell (Bash / Zsh)**: 가상환경 경로 자동 복구 및 환경 셋업 유틸리티.

### AI, 컴퓨터 비전 및 자동화 스택 (AI & Vision Stack)
* **딥러닝 비전 OCR 추론**: **ONNX Runtime** 기반 **RapidOCR** 엔진을 적용하여, 오프라인 환경에서 초고속·고정밀 텍스트 및 테이블 구조화 판독 지원.
* **네이티브 고해상도 래스터화**: macOS 네이티브 Quartz (PDFKit) 그래픽 하위 시스템을 활용하여 외부 도구 없이 150+ DPI 고해상도로 PDF 문서 렌더링.
* **기하 공간 및 좌표 보정**: **Shapely** 및 **OpenCV**를 활용한 바운딩 박스(Bounding Box) 연관 검증 및 Retina 디스플레이 배율(2.0x 논리 좌표 매핑) 자동 보정.
* **듀얼 엔진 RPA 아키텍처**:
  * **엔진 A (Web DOM 코어)**: **Playwright** 기반의 백그라운드 배치 실행, DOM 셀렉터 정밀 매칭 및 단계별 Slow-mo 시연.
  * **엔진 B (일상 Chrome 다이렉트)**: **PyAutoGUI** 및 macOS 접근성 API 기반. 기존 로그인된 개인 프로필을 그대로 승계하며 창을 계속 열어둔 채 유지.
* **분산 지속성 오케스트레이션**: **Temporal.io** 내결함성 지속 워크플로 상태 머신 및 **Apache Airflow** 배치 분할 연동.

---

## 🌟 핵심 특징 (Key Highlights)

1. **100% 로컬 온프레미스 안전 구동**: 모든 AI 추론과 비전 OCR이 로컬 프로세서에서만 실행되어 데이터 외부 유출 위험이 없습니다.
2. **엔드투엔드 문서 추적성 (OmniTrace)**: 공급망 단계별 문서(PO ➔ IQC ➔ WO ➔ CoA ➔ SO ➔ RMA)의 스펙 수치(유리전이온도 $T_g$ 등)와 로트 번호를 자동 교차 대조.
3. **자연어 스크립트 파서**: `GOTO`, `TYPE`, `CLICK`, `WAIT`, `SCREENSHOT`과 같은 직관적인 자연어 명령어를 지원하며 `skip` 및 `abort` 오류 처리 전략 제공.

---

## 🏗️ 시스템 아키텍처 (Architecture)

```text
[ 멀티모달 입력 (PDF / 스캔 이미지 / 데스크톱 화면) ]
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│      OmniTrace 비전 OCR 추출 & 품질 감사 파이프라인    │
│      • Quartz / PDFKit 네이티브 래스터화               │
│      • RapidOCR 오프라인 ONNX 고속 추론                │
│      • 물리 픽셀 ➔ Retina 논리 좌표 자동 매핑          │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│       AgenticDoc RPA 지능형 의사결정 & 듀얼 라우터      │
│      • 자연어 의도 분석 및 내결함성 정책 (Skip / Abort) │
│      • 듀얼 엔진 동적 디스패치                         │
└───────────────┬────────────────────────┬───────────────┘
                │                        │
                ▼                        ▼
┌─────────────────────────────┐ ┌─────────────────────────────┐
│ 엔진 A: Web DOM (Playwright)│ │ 엔진 B: 일상 Chrome 직통 (OS) │
│ • DOM 셀렉터 고정밀 제어    │ │ • 기존 로그인 계정 세션 유지 │
│ • 샌드박스 일괄 자동화      │ │ • 매끄러운 마우스 이동/클릭   │
│ • 단계별 스크린샷 기록      │ │ • 작업 후 창 계속 열어두기   │
└─────────────────────────────┘ └─────────────────────────────┘
```

---

## 📁 디렉터리 구조 (Directory Layout)

```text
agentic-doc-rpa/
├── README.md                           # 영문 메인 문서
├── README.zh-TW.md                     # 대만 번체 중국어 문서
├── README.ja.md                        # 일본어 문서
├── README.ko.md                        # 한국어 문서
├── LICENSE                             # MIT 오픈소스 라이선스
├── requirements_rpa_ocr.txt            # RPA 및 비전 OCR 핵심 의존성 목록
├── requirements_airflow.txt            # Airflow 오케스트레이션 의존성 목록
└── src/                                # 애플리케이션 소스 코드
    ├── ocr/                            # RapidOCR 처리 파이프라인
    ├── rpa/                            # 듀얼 엔진 RPA 구현 및 로케이터
    ├── web_audit/                      # 웹 감사 대시보드 & RPA 스튜디오
    ├── scenario/                       # 비즈니스 시나리오 생성 및 검증
    └── utils/                          # 가상환경 복구 및 공통 유틸리티
```

---

## 🚀 빠른 시작 (Quick Start)

### 1. 요구 사항
* macOS (Apple Silicon M 시리즈 권장)
* Python 3.11+

### 2. 환경 설정
```bash
# 가상환경 생성 및 활성화
python3 -m venv .venv_rpa_ocr
source .venv_rpa_ocr/bin/activate

# 필수 의존성 패키지 설치
pip install -r requirements_rpa_ocr.txt

# Playwright 브라우저 설치
playwright install chromium
```

### 3. 웹 감사 및 RPA 스튜디오 실행
```bash
.venv_rpa_ocr/bin/python src/web_audit/server.py --port 8080
```
웹 브라우저를 열고 **`http://127.0.0.1:8080`** 에 접속하여 다음 기능을 체험할 수 있습니다:
* 📄 **비즈니스 문서 OCR 및 품질 감사**: PDF/이미지를 드래그 앤 드롭하여 즉시 구조화 JSON 추출 및 허용오차 검증.
* 🤖 **자연어 RPA 스튜디오**: 직관적인 자연어 스크립트로 웹/브라우저 작업을 지시하고 시각화 캡처 확인.

---

## 📄 라이선스 명시 (License)

본 프로젝트는 **[MIT License](LICENSE)** 에 따라 오픈소스로 배포됩니다.

### 서드파티 오픈소스 라이브러리 고지
* [RapidOCR](https://github.com/RapidAI/RapidOCR) (Apache 2.0)
* [Playwright](https://github.com/microsoft/playwright) (Apache 2.0)
* [PyAutoGUI](https://github.com/asweigart/pyautogui) (BSD)
* [Temporalio Python SDK](https://github.com/temporalio/sdk-python) (MIT)
* [Pydantic](https://github.com/pydantic/pydantic) (MIT)

---

## 🔒 보안 및 개인정보 보호 (Security & Privacy)

* **외부 데이터 전송 제로**: 모든 딥러닝 추론과 문서 OCR 처리는 로컬 메모리와 CPU/GPU에서만 수행됩니다.
* **계정 세션 안전성**: 일상 Chrome 세션을 직접 연동하며, 사용자의 비밀번호나 세션 쿠키를 수집·저장·전송하지 않습니다.
