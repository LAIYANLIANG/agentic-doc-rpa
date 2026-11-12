"""
[使用工具]: Python 3.11, ScreenOCRLocator, RapidOCR, PyAutoGUI, AppKit / Quartz
[設計目的]: 展示功能二【螢幕即時監控 + OCR 尋找按鍵座標 + RPA 模擬操作】之即時螢幕探測與人為操作演算示範。
[程式說明]:
    1. 擷取使用者當前正在操作的桌面螢幕。
    2. 調用 ScreenOCRLocator 執行視覺 OCR 全畫面掃描，輸出所有文字區塊、信心度與經過 Retina 2.0x 校正之邏輯點擊座標。
    3. 示範搜尋畫面上特定目標（例如上方選單列之 'Terminal'、'File'、或當前開啟分頁之 'server.py'）。
    4. 印出視覺定位軌跡與 PyAutoGUI 人類行為模擬演算法 (easeInOutQuad 平滑移動與點擊參數)。
[修改日期]: 2026-11-10
[修改概要]: 初始建立即時螢幕監控與 OCR 座標定位實機演練腳本
[輸入參數]: 可選關鍵字 --find (預設尋找當前畫面上常見元素)
[輸出結果]: 終端即時顯示螢幕各元素之實體像素與邏輯操作座標
[關聯測試]: src/rpa/test_screen_ocr_locator.py
[工作日誌]: report/work_record/work_record_20261110.md
"""

import argparse
import sys
import time
from pathlib import Path
from PIL import Image

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.rpa.screen_ocr_locator import ScreenOCRLocator, HAS_APPKIT, check_macos_accessibility

try:
    import pyautogui
except ImportError:
    pyautogui = None


def run_live_demo(target_word: str = None, do_move: bool = False, do_click: bool = False):
    print("=" * 70)
    print("🎯【功能二實機展示】：螢幕即時監控 + OCR 尋找按鍵座標 + RPA 人為操作模擬")
    print("=" * 70)

    locator = ScreenOCRLocator()
    screen_size = pyautogui.size() if pyautogui else (1512, 982)
    print(f"🖥️ 當前顯示器環境資訊：")
    print(f"  • 邏輯操作解析度 (Logical Points): {screen_size.width} x {screen_size.height}")
    print(f"  • Retina 縮放倍率 (Backing Scale): {locator.scale_factor}x (M5 內建視網膜螢幕)")
    print(f"  • 實體渲染像素 (Physical Pixels) : {int(screen_size.width * locator.scale_factor)} x {int(screen_size.height * locator.scale_factor)}")

    print("\n📸 [步驟 1] 正在擷取當前螢幕即時畫面 (Live Capture)...")
    # 即時擷取最新螢幕畫面
    img = locator.capture_screen()
    print(f"✅ 截圖完成！影像尺寸: {img.size[0]} x {img.size[1]} 像素")

    print("\n👁️ [步驟 2] 正在進行 RapidOCR 視覺全螢幕辨識...")
    t0 = time.time()
    targets = locator.scan_screen(img)
    dur = round(time.time() - t0, 2)
    print(f"✅ 視覺掃描完成！耗時 {dur} 秒，在螢幕上辨識出 {len(targets)} 個可操作文字按鍵/標籤。")

    print("\n📍 [步驟 3] 隨機抽樣展示畫面上即時鎖定的 10 個按鍵位置與點擊座標：")
    print(f"{'序號':<4} | {'辨識文字標籤':<24} | {'實體像素中心 (px)':<18} | {'PyAutoGUI 邏輯操作座標 (lx, ly)':<28} | 信心度")
    print("-" * 90)
    for i, t in enumerate(targets[:10]):
        px_cx = round((t.physical_bbox[0][0] + t.physical_bbox[2][0]) / 2.0, 1)
        px_cy = round((t.physical_bbox[0][1] + t.physical_bbox[2][1]) / 2.0, 1)
        px_str = f"({px_cx}, {px_cy})"
        lx_str = f"({t.logical_center[0]}, {t.logical_center[1]})"
        print(f"[{i+1:02d}] | {t.text:<24} | {px_str:<18} | {lx_str:<28} | {t.score:.2f}")

    # 步驟 4: 目標檢索與實際滑鼠移動示範
    search_keywords = [target_word] if target_word else ["Terminal", "server.py", "Edit", "Antigravity"]
    print(f"\n🎯 [步驟 4] 模擬 RPA 尋找特定按鍵位置：")
    matched_target = None
    for kw in search_keywords:
        match = locator.find_text(kw, screenshot=img)
        if match:
            matched_target = match
            print(f"  👉 成功鎖定按鍵「{match.text}」！")
            print(f"     • 邏輯點擊座標：x={match.logical_center[0]}, y={match.logical_center[1]}")
            print(f"     • 實體外框範圍：{match.physical_bbox}")
            break

    if not matched_target and targets:
        matched_target = targets[0]
        print(f"  👉 選取畫面上第一個目標「{matched_target.text}」：x={matched_target.logical_center[0]}, y={matched_target.logical_center[1]}")

    if matched_target and pyautogui:
        lx, ly = matched_target.logical_center
        if do_move or do_click:
            has_perm = check_macos_accessibility()
            if not has_perm:
                print("\n⚠️ 【macOS 系統權限提示】：")
                print("   偵測到當前終端機尚未獲得 macOS『輔助使用 (Accessibility)』權限！")
                print("   macOS 基於安全考量會攔截模擬滑鼠移動與點擊事件。")
                print("   👉 啟用方式：開啟【系統設定】->【隱私權與安全性】->【輔助使用】-> 將您的終端機 (Terminal / iTerm / Antigravity) 勾選開啟即可。")
                print("   (程式仍會嘗試發送事件，若游標未動請開啟上述權限)\n")

            print(f"\n🚀 [步驟 5] 實際滑鼠接管演出（注意看您的螢幕游標！）：")
            print(f"   倒數 2 秒... 請不要晃動滑鼠...")
            time.sleep(2.0)
            
            # 取得當前滑鼠位置
            cur_x, cur_y = pyautogui.position()
            print(f"   📍 滑鼠目前在 ({cur_x}, {cur_y}) -> 正在平滑游移至目標 ({lx}, {ly})...")
            
            # 人性化平滑移動 (拉長 duration 到 1.2 秒讓肉眼清晰可見)
            pyautogui.moveTo(lx, ly, duration=1.2, tween=pyautogui.easeInOutQuad)
            print(f"   🎯 滑鼠已精準到達「{matched_target.text}」上方！")

            if do_click:
                time.sleep(0.3)
                print(f"   👆 執行真實左鍵點擊！")
                pyautogui.click()
            else:
                print(f"   💡 (純游標移動展示模式，未執行實體點擊以保安全；若要點擊請加 --click)")
        else:
            print("\n💡 提示：目前為『唯讀座標探測模式』，未實際驅動滑鼠游標。")
            print(f"   👉 若要讓滑鼠【真實動起來】移到按鈕上，請執行：")
            print(f"      .venv_rpa_ocr/bin/python src/rpa/demo_live_screen_rpa.py --move")
            print(f"   👉 若要讓滑鼠【移動並實際點擊】，請執行：")
            print(f"      .venv_rpa_ocr/bin/python src/rpa/demo_live_screen_rpa.py --move --click")

    print("\n" + "=" * 70)
    print("💡 結論：")
    print("1. RPA 不需寫死固定座標，當視窗被拖動或字體縮放時，OCR 能像人眼一樣即時定位！")
    print("2. 自動除以 Retina 2.0x 倍率，精確計算出 macOS 系統事件能準確命中的座標。")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live Screen OCR & RPA Demo")
    parser.add_argument("--find", type=str, help="指定要在螢幕上尋找的文字 (例如: Terminal, File, server.py)")
    parser.add_argument("--move", action="store_true", help="真實接管滑鼠，平滑移動游標到目標座標")
    parser.add_argument("--click", action="store_true", help="滑鼠移動到位後執行實體點擊")
    args = parser.parse_args()

    run_live_demo(target_word=args.find, do_move=args.move, do_click=args.click)

