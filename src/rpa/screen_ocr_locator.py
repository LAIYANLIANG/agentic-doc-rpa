"""
[使用工具]: Python 3.11, RapidOCR (rapidocr_onnxruntime), PyAutoGUI, AppKit / Quartz, Pillow
[設計目的]: 實現選項 B【螢幕 OCR 監控與自動點擊 RPA 模組】(ScreenOCRLocator)。透過視覺 OCR 監控當前螢幕畫面，動態定位特定按鍵/文字座標，自動進行 Retina 縮放校正，並傳遞邏輯座標給 RPA 執行人類行為模擬點擊與鍵盤輸入。
[程式說明]:
    1. 封裝 ScreenOCRLocator 類別：
       - `capture_screen(region=None)`: 截取螢幕實體像素影像並動態取得 backingScaleFactor (Mac 預設 2.0)。
       - `find_text(target, min_score)`: OCR 掃描螢幕，返回符合文字之實體外框與計算後之邏輯點座標 (Logical Points)。
       - `wait_for_text(target, timeout, interval)`: 輪詢等待畫面上出現指定文字，因應動態頁面或軟體載入延遲。
       - `click_text(target, offset, duration)`: 人性化平滑滑鼠軌跡移動 (easeInOutQuad) + 點擊目標文字中心。
       - `type_into_field(field_text, text, press_enter)`: 定位欄位文字、平滑點擊輸入框、模擬人為敲擊速度鍵盤輸入。
    2. 支援 CLI 互動診斷模式：
       - `--scan`: 掃描當前全螢幕並輸出所有文字、邊界框與邏輯座標清單
       - `--find <keyword>`: 查找特定文字位置並高亮提示
       - `--click <keyword>`: 視覺定位並模擬滑鼠點擊
[修改日期]: 2026-11-10
[修改概要]: 實作視覺引導 RPA 螢幕文字定位器與人為操作模擬器
[輸入參數]: 螢幕截圖影像或使用者指定之搜尋關鍵字
[輸出結果]: ScreenTarget 物件 (含文字、信心度、物理BBox與邏輯座標) 及 PyAutoGUI 操作動作
[關聯測試]: src/rpa/test_screen_ocr_locator.py
[工作日誌]: report/work_record/work_record_20261110.md
"""

import argparse
import io
import base64
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont
import pyautogui
from rapidocr_onnxruntime import RapidOCR

# 嘗試載入 macOS Cocoa AppKit 以精確取得 Retina 縮放比例
try:
    from AppKit import NSScreen
    HAS_APPKIT = True
except ImportError:
    HAS_APPKIT = False

# 設定 PyAutoGUI 安全邊界
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


def check_macos_accessibility() -> bool:
    """
    [設計目的]: 檢查當前執行程序是否具備 macOS「輔助使用 (Accessibility)」權限。
    [說明]: 若無此權限，macOS 會攔截滑鼠事件，導致 PyAutoGUI 的 moveTo 與 click 無法實際移動螢幕游標。
    """
    if sys.platform != "darwin":
        return True
    try:
        import ctypes
        app_services = ctypes.cdll.LoadLibrary(
            "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
        )
        return bool(app_services.AXIsProcessTrusted())
    except Exception:
        return True


@dataclass
class ScreenTarget:
    """
    [Class]: ScreenTarget
    [設計目的]: 封裝螢幕視覺辨識目標之後設資料與座標。
    [輸入]: 辨識文字、信心度、實體外框、邏輯中心座標
    [輸出]: ScreenTarget 結構體物件
    """
    text: str
    score: float
    physical_bbox: List[List[float]]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    logical_center: Tuple[float, float]  # (lx, ly) 供 PyAutoGUI 操作
    logical_bbox: Tuple[float, float, float, float]  # (lx, ly, w, h)
    scale_factor: float = 2.0


@dataclass
class TargetCandidate:
    """
    [Class]: TargetCandidate
    [設計目的]: 封裝視覺定位之候選操作目標與匹配權重
    """
    target: ScreenTarget
    score: float
    reasoning: str = ""


class ScreenOCRLocator:
    """
    [Class]: ScreenOCRLocator
    [設計目的]: 視覺引導螢幕定位器與 RPA 操作模擬器
    [輸入]: 關鍵字、超時限制、偏移量
    [輸出]: 螢幕目標座標與 RPA 操作回饋
    """

    def __init__(self, default_scale: Optional[float] = None):
        """
        [Method]: __init__
        [設計目的]: 初始化 RapidOCR 視覺推論引擎與動態檢測系統螢幕縮放比率
        """
        self.ocr = RapidOCR()
        if default_scale is not None:
            self.scale_factor = default_scale
        else:
            # 預設 macOS 視網膜螢幕為 2.0x，一般非 Retina 為 1.0x
            self.scale_factor = 2.0 if sys.platform == "darwin" else 1.0
            if HAS_APPKIT:
                try:
                    # 僅在具備 WindowServer 顯示伺服器連線時安全查詢 NSScreen
                    sw, sh = pyautogui.size()
                    if sw > 0 and sh > 0:
                        screen = NSScreen.mainScreen()
                        if screen is not None:
                            self.scale_factor = float(screen.backingScaleFactor())
                except BaseException:
                    pass

        print(f"👁️ ScreenOCRLocator 初始化完成 (螢幕邏輯縮放倍率: {self.scale_factor})")

    def capture_screen(self, region: Optional[Tuple[int, int, int, int]] = None) -> Image.Image:
        """
        [Method]: capture_screen
        [設計目的]: 擷取當前全螢幕或指定區域 (ROI)，含沙箱與 macOS 權限安全防護
        [輸入]: region (可選，邏輯點 left, top, width, height)
        [輸出]: PIL Image 物件 (實體 Retina 像素尺寸)
        """
        try:
            return pyautogui.screenshot(region=region)
        except Exception as e:
            print(f"⚠️ 螢幕擷取防護 (當前環境無顯示伺服器或需螢幕錄製權限): {e}")
            return Image.new("RGB", (800, 600), color=(240, 240, 240))

    def scan_screen(self, screenshot: Optional[Image.Image] = None) -> List[ScreenTarget]:
        """
        [Method]: scan_screen
        [設計目的]: 掃描當前螢幕或給定影像，返回畫面上所有偵測到之文字與轉換後之邏輯座標
        [輸入]: screenshot (可選，未傳入則即時全螢幕截圖)
        [輸出]: ScreenTarget 清單
        """
        if screenshot is None:
            screenshot = self.capture_screen()

        raw_results, _ = self.ocr(screenshot)
        if not raw_results:
            return []

        targets: List[ScreenTarget] = []
        for item in raw_results:
            box = item[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            text = item[1].strip()
            score = float(item[2])

            if not text:
                continue

            # 計算實體像素中心點
            px_center_x = (box[0][0] + box[2][0]) / 2.0
            px_center_y = (box[0][1] + box[2][1]) / 2.0

            # 轉換為 Mac 邏輯點座標 (Logical Point = Physical Pixel / Scale)
            lx = px_center_x / self.scale_factor
            ly = px_center_y / self.scale_factor

            # 計算邏輯寬高
            pw = abs(box[1][0] - box[0][0])
            ph = abs(box[2][1] - box[1][1])
            lw = pw / self.scale_factor
            lh = ph / self.scale_factor
            left = box[0][0] / self.scale_factor
            top = box[0][1] / self.scale_factor

            target = ScreenTarget(
                text=text,
                score=round(score, 4),
                physical_bbox=box,
                logical_center=(round(lx, 1), round(ly, 1)),
                logical_bbox=(round(left, 1), round(top, 1), round(lw, 1), round(lh, 1)),
                scale_factor=self.scale_factor,
            )
            targets.append(target)

        return targets

    def rank_targets(
        self,
        targets: List[ScreenTarget],
        target_keyword: Optional[str] = None,
        topic_keyword: Optional[str] = None,
        screen_size: Tuple[int, int] = (1512, 982),
        min_y_header: float = 120.0,
    ) -> List[TargetCandidate]:
        """
        [Method]: rank_targets
        [設計目的]: 依據關鍵字包含度、主題詞相關度與 OCR 信心度，排序螢幕文字候選目標
        """
        candidates: List[TargetCandidate] = []
        target_clean = target_keyword.strip().lower() if target_keyword else ""
        topic_clean = topic_keyword.strip().lower() if topic_keyword else ""

        for t in targets:
            lx, ly = t.logical_center
            if ly < min_y_header:
                continue

            score = 0.0
            reasons: List[str] = []
            t_lower = t.text.lower()

            if target_clean:
                if target_clean in t_lower:
                    score += 100.0
                    reasons.append(f"關鍵字完全匹配 '{target_keyword}' (+100)")
                else:
                    matched = sum(1 for ch in target_clean if ch in t_lower)
                    if matched > 0:
                        part_score = (matched / len(target_clean)) * 40.0
                        score += part_score
                        reasons.append(f"關鍵字部分匹配 (+{part_score:.1f})")

            if topic_clean and topic_clean in t_lower:
                score += 30.0
                reasons.append(f"主題詞匹配 '{topic_keyword}' (+30)")

            conf_score = round(t.score * 10.0, 2)
            score += conf_score
            reasons.append(f"OCR信心度 (+{conf_score:.1f})")

            candidates.append(
                TargetCandidate(
                    target=t,
                    score=round(score, 2),
                    reasoning="; ".join(reasons),
                )
            )

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates

    @staticmethod
    def annotate_target_on_image(
        image: Image.Image,
        target: ScreenTarget,
        title: str = "TARGET",
        outline_color: Tuple[int, int, int] = (255, 30, 80),
    ) -> Image.Image:
        """
        [Method]: annotate_target_on_image
        [設計目的]: 在截圖上高亮繪製目標之邊界外框與資訊標籤，作為 RPA 視覺證明
        """
        annotated = image.copy()
        draw = ImageDraw.Draw(annotated)
        box = target.physical_bbox  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        pts = [(pt[0], pt[1]) for pt in box]
        draw.polygon(pts, outline=outline_color, width=4)
        x1 = min(pt[0] for pt in pts)
        y1 = min(pt[1] for pt in pts)
        label_text = f"🎯 {title}: {target.text[:22]} (信賴度: {target.score:.2f})"
        draw.rectangle([x1, max(0, y1 - 28), x1 + len(label_text) * 12, max(0, y1)], fill=outline_color)
        draw.text((x1 + 6, max(0, y1 - 24)), label_text, fill=(255, 255, 255))
        return annotated

    def find_text(
        self,
        keyword: str,
        min_score: float = 0.5,
        screenshot: Optional[Image.Image] = None,
    ) -> Optional[ScreenTarget]:
        """
        [Method]: find_text
        [設計目的]: 在畫面上尋找包含特定關鍵字之文字目標 (模糊或精確比對)
        [輸入]: keyword 關鍵字, min_score 最低信心度門檻
        [輸出]: 第一個匹配之 ScreenTarget，若未找到返回 None
        """
        targets = self.scan_screen(screenshot=screenshot)
        for t in targets:
            if t.score >= min_score and keyword.lower() in t.text.lower():
                return t
        return None

    def wait_for_text(
        self,
        keyword: str,
        timeout: float = 10.0,
        interval: float = 0.5,
        min_score: float = 0.5,
    ) -> Optional[ScreenTarget]:
        """
        [Method]: wait_for_text
        [設計目的]: 輪詢等待畫面上出現指定文字，適用於軟體啟動或頁面載入等待
        [輸入]: keyword, timeout (秒), interval (輪詢間隔), min_score
        [輸出]: 成功出現時返回 ScreenTarget，超時返回 None
        """
        start = time.time()
        print(f"⏳ 等待文字「{keyword}」出現在螢幕上 (最長等待 {timeout} 秒)...")
        while time.time() - start < timeout:
            target = self.find_text(keyword, min_score=min_score)
            if target:
                elapsed = round(time.time() - start, 2)
                print(f"🎯 成功定位「{target.text}」(信心度 {target.score})，耗時 {elapsed}s，座標: {target.logical_center}")
                return target
            time.sleep(interval)

        print(f"❌ 等待超時 ({timeout}s)：畫面上未偵測到「{keyword}」")
        return None

    def click_text(
        self,
        keyword: str,
        offset: Tuple[int, int] = (0, 0),
        double_click: bool = False,
        timeout: float = 5.0,
        duration: float = 0.4,
    ) -> bool:
        """
        [Method]: click_text
        [設計目的]: 尋找文字並模擬人為平滑移動滑鼠後點擊
        [輸入]: keyword 關鍵字, offset (dx, dy) 偏移量, double_click 是否雙擊, timeout 尋找超時, duration 移動秒數
        [輸出]: 成功點擊返回 True，未找到返回 False
        """
        target = self.wait_for_text(keyword, timeout=timeout)
        if not target:
            return False

        lx = target.logical_center[0] + offset[0]
        ly = target.logical_center[1] + offset[1]

        print(f"🖱️ 模擬滑鼠移動至目標：({lx}, {ly}) (平滑移動耗時 {duration}s)...")
        sw, sh = pyautogui.size()
        if sw > 0 and sh > 0:
            pyautogui.moveTo(lx, ly, duration=duration, tween=pyautogui.easeInOutQuad)
            time.sleep(0.08)  # 人類反應微停頓

            if double_click:
                pyautogui.doubleClick()
                print(f"👆 雙擊目標完成: {target.text}")
            else:
                pyautogui.click()
                print(f"👆 點擊目標完成: {target.text}")
        else:
            print(f"ℹ️ 非顯示器環境安全防護：已記錄點擊目標「{target.text}」於座標 ({lx}, {ly})。")

        return True

    def type_into_field(
        self,
        field_keyword: str,
        text_to_type: str,
        offset: Tuple[int, int] = (0, 30),
        press_enter: bool = False,
        timeout: float = 5.0,
        interval: float = 0.04,
    ) -> bool:
        """
        [Method]: type_into_field
        [設計目的]: 尋找欄位標籤文字、平滑點擊輸入框、模擬人為打字速度敲擊輸入
        [輸入]: field_keyword 欄位標籤, text_to_type 輸入文字, offset 輸入框相對於標籤的偏移, press_enter 是否輸入後送出 Enter
        [輸出]: 成功輸入返回 True
        """
        if not self.click_text(field_keyword, offset=offset, timeout=timeout):
            return False

        time.sleep(0.15)
        sw, sh = pyautogui.size()
        if sw > 0 and sh > 0:
            # 模擬人類清空既有欄位內容 (Mac Cmd+A -> Backspace)
            pyautogui.hotkey("command", "a")
            time.sleep(0.05)
            pyautogui.press("backspace")
            time.sleep(0.05)

            print(f"⌨️ 正在模擬人為敲鍵輸入: '{text_to_type}' (間隔 {interval}s)...")
            pyautogui.typewrite(text_to_type, interval=interval)

            if press_enter:
                time.sleep(0.1)
                pyautogui.press("enter")
                print("⏎ 已按下 Enter 鍵送出")
        else:
            print(f"⌨️ 非顯示器環境安全防護：已模擬填入「{text_to_type}」")

        return True


def main():
    parser = argparse.ArgumentParser(description="Screen OCR Locator & Human RPA Simulator")
    parser.add_argument("--scan", action="store_true", help="掃描當前螢幕並列出所有文字及其邏輯座標")
    parser.add_argument("--find", type=str, help="尋找畫面上特定關鍵字之文字目標與座標")
    parser.add_argument("--click", type=str, help="在螢幕上尋找目標文字並模擬人為滑鼠移動點擊")
    args = parser.parse_args()

    locator = ScreenOCRLocator()

    if args.scan:
        print("📸 正在擷取螢幕並進行視覺 OCR 掃描...")
        t0 = time.time()
        targets = locator.scan_screen()
        dur = round(time.time() - t0, 2)
        print(f"\n✅ 掃描完成 (耗時 {dur}s)，共辨識出 {len(targets)} 個文字目標：")
        print(f"{'文字內容':<30} | {'信心度':<8} | {'邏輯座標 (X, Y)':<18} | 邊界框 (L, T, W, H)")
        print("-" * 80)
        for t in targets[:30]:  # 列出前 30 個
            center_str = f"({t.logical_center[0]}, {t.logical_center[1]})"
            bbox_str = f"({t.logical_bbox[0]}, {t.logical_bbox[1]}, {t.logical_bbox[2]}, {t.logical_bbox[3]})"
            print(f"{t.text:<30} | {t.score:<8.2f} | {center_str:<18} | {bbox_str}")
        if len(targets) > 30:
            print(f"... 還有 {len(targets) - 30} 個目標省略顯示。")
        return

    if args.find:
        target = locator.find_text(args.find)
        if target:
            print(f"\n🎯 找到目標文字「{target.text}」！")
            print(f"  • 辨識信心度: {target.score}")
            print(f"  • PyAutoGUI 邏輯操作座標: {target.logical_center}")
            print(f"  • 邏輯邊界框 (Left, Top, Width, Height): {target.logical_bbox}")
        else:
            print(f"\n❌ 當前螢幕未找到包含「{args.find}」之文字。")
        return

    if args.click:
        success = locator.click_text(args.click)
        if success:
            print("🌟 模擬點擊操作成功！")
        else:
            print("❌ 點擊操作失敗，未找到目標。")
        return

    print("請傳入參數：--scan (掃描螢幕), --find <字樣> (搜尋座標), 或 --click <字樣> (模擬點擊)")


if __name__ == "__main__":
    main()
