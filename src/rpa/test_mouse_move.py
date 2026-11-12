"""
[使用工具]: Python 3.11, PyAutoGUI, AppKit
[設計目的]: 即時驗證 macOS 下 PyAutoGUI 滑鼠接管能力與 Accessibility 權限。
[程式說明]: 
    1. 檢測 macOS 輔助使用權限。
    2. 取得滑鼠當前位置，並在螢幕上畫一個小正方形/平滑游移，讓使用者親眼確認滑鼠真實被程式驅動。
[修改日期]: 2026-11-10
[修改概要]: 新增滑鼠物理移動即時驗證工具
"""

import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import pyautogui
from src.rpa.screen_ocr_locator import check_macos_accessibility

def test_physical_mouse_move():
    print("=" * 60)
    print("🖱️【PyAutoGUI 滑鼠物理移動實機驗證】")
    print("=" * 60)

    has_perm = check_macos_accessibility()
    print(f"1. macOS 輔助使用 (Accessibility) 權限狀態: {'✅ 已授權' if has_perm else '⚠️ 尚未授權'}")
    if not has_perm:
        print("   👉 若稍後滑鼠沒有移動，請至：")
        print("      【系統設定】->【隱私權與安全性】->【輔助使用】-> 勾選您正在使用的 Terminal 或 Antigravity")
        print()

    screen_w, screen_h = pyautogui.size()
    cur_x, cur_y = pyautogui.position()
    print(f"2. 螢幕邏輯解析度: {screen_w} x {screen_h}")
    print(f"3. 當前滑鼠游標位置: ({cur_x}, {cur_y})")

    print("\n🚀 即將在 2 秒後驅動滑鼠游標走一個平滑小軌跡（請將視線放在滑鼠游標上）...")
    for i in range(2, 0, -1):
        print(f"   ⏳ 倒數 {i} 秒...")
        time.sleep(1.0)

    print("✨ 開始移動！")
    # 往右移動 150 點
    target_x1 = min(cur_x + 150, screen_w - 50)
    pyautogui.moveTo(target_x1, cur_y, duration=0.8, tween=pyautogui.easeInOutQuad)
    time.sleep(0.1)

    # 往下移動 100 點
    target_y1 = min(cur_y + 100, screen_h - 50)
    pyautogui.moveTo(target_x1, target_y1, duration=0.8, tween=pyautogui.easeInOutQuad)
    time.sleep(0.1)

    # 移回原點
    pyautogui.moveTo(cur_x, cur_y, duration=0.8, tween=pyautogui.easeInOutQuad)
    print("✅ 移動完成！游標已平滑返回原位。")
    print("=" * 60)

if __name__ == "__main__":
    test_physical_mouse_move()

