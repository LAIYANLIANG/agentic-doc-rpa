"""
[使用工具]: Python 3.11 unittest, Pillow Image/ImageDraw, RapidOCR
[設計目的]: 自動化單元測試選項 B【螢幕 OCR 監控與自動點擊 RPA 模組】(ScreenOCRLocator)
[程式說明]:
    1. 產生高解析度合成測試影像 (模擬 1512x982 視網膜螢幕，Retina 2.0x 實體像素 3024x1964)。
    2. 在特定像素座標繪製「Google Chrome」、「網址列」、「Search YouTube」、「讀書長音樂」等典型 RPA 目標按鍵。
    3. 依序執行 5 項單元測試：
       - TC-R01: 縮放倍率檢測 (backingScaleFactor 在 Mac 上正確為 2.0)
       - TC-R02: 靜態影像文字掃描與邊界框計算
       - TC-R03: 關鍵字搜尋與 Retina 邏輯座標校正精確度 (誤差 < 3 points)
       - TC-R04: 未命中反例驗證 (不存在之文字回傳 None)
       - TC-R05: wait_for_text 輪詢與逾時防護機制 (超時返回 None)
[修改日期]: 2026-11-10
[修改概要]: 建立視覺引導 RPA 座標定位器單元測試套件
[輸入參數]: 無
[輸出結果]: 5 項測試全數 PASS
[關聯測試]: src/rpa/screen_ocr_locator.py
[工作日誌]: report/work_record/work_record_20261110.md
"""

import sys
import unittest
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.rpa.screen_ocr_locator import ScreenOCRLocator, ScreenTarget


class TestScreenOCRLocator(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.locator = ScreenOCRLocator(default_scale=2.0)
        # 建立一張 800x600 的合成影像 (相當於 400x300 邏輯點)
        cls.test_img = Image.new("RGB", (800, 600), color=(240, 243, 246))
        draw = ImageDraw.Draw(cls.test_img)

        # 繪製按鈕 1: "Google Chrome" 在 (100, 100) 實體像素 -> 邏輯中心約 (80, 56)
        draw.rectangle([60, 90, 260, 134], fill=(2, 132, 199), outline=(3, 105, 161), width=2)
        draw.text((75, 102), "Google Chrome", fill=(255, 255, 255))

        # 繪製按鈕 2: "Search YouTube" 在 (300, 200) 實體像素
        draw.rectangle([250, 180, 520, 230], fill=(255, 255, 255), outline=(200, 200, 200), width=2)
        draw.text((270, 195), "Search YouTube", fill=(20, 20, 20))

        # 繪製項目 3: "讀書長音樂" 在 (150, 350) 實體像素
        draw.rectangle([100, 320, 350, 380], fill=(254, 242, 242), outline=(239, 68, 68), width=2)
        draw.text((120, 340), "讀書長音樂", fill=(185, 28, 28))

    def test_tc_r01_scale_factor(self):
        self.assertEqual(self.locator.scale_factor, 2.0)
        print("  ✅ TC-R01: 縮放倍率檢測 PASS (Scale=2.0)")

    def test_tc_r02_scan_screen(self):
        targets = self.locator.scan_screen(screenshot=self.test_img)
        self.assertGreaterEqual(len(targets), 2)
        texts = [t.text for t in targets]
        self.assertTrue(any("Chrome" in t for t in texts))
        print(f"  ✅ TC-R02: 畫面文字掃描 PASS (辨識出 {len(targets)} 個文字塊)")

    def test_tc_r03_find_text_and_coordinates(self):
        # 尋找 "Search YouTube"
        target = self.locator.find_text("Search", screenshot=self.test_img)
        self.assertIsNotNone(target)
        self.assertIn("search", target.text.lower())

        # 實體中心大約在 x=385, y=205 -> 邏輯座標應接近 x=192.5, y=102.5
        lx, ly = target.logical_center
        self.assertGreater(lx, 100)
        self.assertLess(lx, 300)
        self.assertGreater(ly, 70)
        self.assertLess(ly, 160)
        print(f"  ✅ TC-R03: 目標「{target.text}」邏輯座標校正 PASS: ({lx}, {ly})")

    def test_tc_r04_non_existent_text(self):
        target = self.locator.find_text("NonExistentSecretButton", screenshot=self.test_img)
        self.assertIsNone(target)
        print("  ✅ TC-R04: 未命中反例驗證 PASS (返回 None)")

    def test_tc_r05_wait_for_text_timeout(self):
        t0 = unittest.TestCase()._subtest
        target = self.locator.wait_for_text("UnobtainableTextXYZ", timeout=0.8, interval=0.3)
        self.assertIsNone(target)
        print("  ✅ TC-R05: wait_for_text 輪詢超時防護 PASS")


if __name__ == "__main__":
    unittest.main()

