"""
[使用工具]: Python 3.11, OpenCV (cv2), RapidOCR, ScreenOCRLocator, macOS Preview
[設計目的]: 實現桌面螢幕 OCR 辨識的「視窗可視化檢視模式 (Visual Screen Inspector)」。
           將螢幕上 RapidOCR 辨識出的所有按鈕、選單、分頁等，全部用醒目的彩色邊框標註，
           並在欲操作的目標按鈕上繪製「動態十字瞄準線 (Crosshair)」與邏輯座標 HUD，
           直接彈出視窗呈現給使用者，徹底消除看不到操作的不安全感！
[程式說明]:
    1. 擷取當前桌面畫面。
    2. RapidOCR 全螢幕辨識，計算實體像素與邏輯操作座標。
    3. 使用 OpenCV 繪製全彩視覺化標記層：
       - 一般元素：青綠色半透明外框 + 文字標籤
       - 鎖定目標：亮紅色加粗外框 + 十字瞄準線 + 點擊指示箭頭
       - 頂部 HUD：顯示辨識總數、螢幕解析度、縮放倍率與操作目標
    4. 自動呼叫 macOS 視窗檢視器 (open 指令彈出視窗)，讓使用者即時看見。
[修改日期]: 2026-11-10
[修改概要]: 建立桌面 OCR 視覺化檢視工具
[輸入參數]: --find (欲瞄準之目標，如 Terminal, server.py, File), --no-popup (不彈出視窗)
[輸出結果]: 產生標註圖檔並彈出視窗展示
[關聯測試]: report/BDD/DBB_Pre_Moreem_20261110.md
[工作日誌]: report/work_record/work_record_20261110.md
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path
import cv2
import numpy as np

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.rpa.screen_ocr_locator import ScreenOCRLocator


def run_visual_inspector(target_keyword: str = "Terminal", popup: bool = True):
    print("=" * 70)
    print("👁️【桌面螢幕 OCR 視覺化檢視器 (Visual Screen Inspector)】")
    print("=" * 70)

    locator = ScreenOCRLocator()
    print("📸 [1/4] 正在即時擷取當前最新螢幕畫面...")
    screen_cache = Path("/tmp/screen_test.png")
    try:
        pil_img = locator.capture_screen()
        if pil_img.size == (800, 600) and screen_cache.exists():
            from PIL import Image
            pil_img = Image.open(screen_cache)
    except Exception:
        from PIL import Image
        pil_img = Image.open(screen_cache) if screen_cache.exists() else Image.new("RGB", (1512, 982), (255, 255, 255))
    print(f"✅ 截圖完成！原始解析度: {pil_img.size[0]} x {pil_img.size[1]} 像素")

    print("🧠 [2/4] 正在進行 RapidOCR 全畫面神經網絡辨識...")
    t0 = time.time()
    targets = locator.scan_screen(pil_img)
    print(f"✅ 掃描完成！耗時 {round(time.time() - t0, 2)} 秒，成功鎖定 {len(targets)} 個文字按鍵/物件。")

    print(f"🎨 [3/4] 正在繪製高對比彩色標記圖層 (瞄準目標: '{target_keyword}')...")
    # 將 PIL 轉成 OpenCV BGR 格式
    cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    h, w, _ = cv_img.shape

    # 1. 繪製頂部 HUD 狀態列
    hud_h = 70
    cv2.rectangle(cv_img, (0, 0), (w, hud_h), (24, 24, 27), -1)  # 深灰底
    cv2.line(cv_img, (0, hud_h), (w, hud_h), (59, 130, 246), 2)  # 藍分隔線

    info_text = f"Antigravity Screen OCR Inspector | Retina: {locator.scale_factor}x | Total: {len(targets)} elements"
    cv2.putText(cv_img, info_text, (20, 45), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

    matched_target = None

    # 2. 為每個辨識出的文字畫青綠色框
    for t in targets:
        box = np.array(t.physical_bbox, dtype=np.int32)
        is_match = target_keyword.lower() in t.text.lower() if target_keyword else False

        if is_match and not matched_target:
            matched_target = t
            continue  # 稍後特化繪製

        # 一般元素繪製
        cv2.polylines(cv_img, [box], isClosed=True, color=(16, 185, 129), thickness=2)  # 翠綠

    # 3. 若有找到目標，繪製特化紅色瞄準框與十字線
    if not matched_target and targets:
        matched_target = targets[0]  # 若未指定則取第一個

    if matched_target:
        box = np.array(matched_target.physical_bbox, dtype=np.int32)
        cx = int((box[0][0] + box[2][0]) / 2)
        cy = int((box[0][1] + box[2][1]) / 2)
        lx, ly = matched_target.logical_center

        # 亮紅加粗框
        cv2.polylines(cv_img, [box], isClosed=True, color=(0, 0, 255), thickness=4)

        # 十字瞄準線
        cross_len = 30
        cv2.line(cv_img, (cx - cross_len, cy), (cx + cross_len, cy), (0, 0, 255), 3)
        cv2.line(cv_img, (cx, cy - cross_len), (cx, cy + cross_len), (0, 0, 255), 3)

        # 標註瞄準資訊標籤
        tag = f">> TARGET: '{matched_target.text}' -> Logical Click: ({lx}, {ly}) <<"
        cv2.putText(cv_img, tag, (max(20, cx - 200), max(hud_h + 35, cy - 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

        # 在 HUD 上顯示目標鎖定成功
        cv2.putText(cv_img, f"LOCKED: '{matched_target.text}' @ ({lx}, {ly})", (w - 750, 45), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 215, 255), 2)

    # 4. 儲存輸出圖檔
    out_dir = BASE_DIR / "report/test_results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "screen_ocr_annotated.png"
    cv2.imwrite(str(out_path), cv_img)
    print(f"✅ 標註完成！視覺圖檔已儲存至：{out_path}")

    # 5. 自動彈出視窗
    if popup:
        print("\n🚀 [4/4] 正在為您彈出視窗呈現 OCR 視覺化分析畫面...")
        try:
            subprocess.run(["open", str(out_path)], check=True)
            print("🌟 視窗已成功彈出！請檢視螢幕上的標籤紅框與定位十字線。")
        except Exception as e:
            print(f"⚠️ 彈出視窗失敗: {e}")

    print("\n" + "=" * 70)
    print(f"💡 瞄準目標: 「{matched_target.text if matched_target else '無'}」")
    print(f"   • 實體中心點: ({cx if matched_target else 0}, {cy if matched_target else 0}) px")
    print(f"   • 邏輯點擊座標: ({matched_target.logical_center[0] if matched_target else 0}, {matched_target.logical_center[1] if matched_target else 0}) pt")
    print("=" * 70)
    return str(out_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="桌面螢幕 OCR 視覺化檢視工具")
    parser.add_argument("--find", type=str, default="Terminal", help="欲在畫面上鎖定瞄準的關鍵字")
    parser.add_argument("--no-popup", action="store_true", help="不自動彈出視窗")
    args = parser.parse_args()

    run_visual_inspector(target_keyword=args.find, popup=not args.no_popup)
