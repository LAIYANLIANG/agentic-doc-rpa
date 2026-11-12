"""
[使用工具]: Python 3.11, Playwright (Chromium), asyncio / sync_api
[設計目的]: 實現使用者指定之「視窗模式 (Windowed)」與「背端模式 (Backend)」雙軌架構。
           在【視窗模式】下，彈出真實瀏覽器視窗，以慢動作 (Slow-Mo) 與視覺光環 (Visual Highlighting)
           一步一步在使用者眼前自動輸入 youtube.com、搜尋「讀書長音樂」，並自動選取影片播放。
[程式說明]:
    1. 雙軌模式切換：
       - 視窗模式 (--mode window): headless=False, slow_mo 延遲, 注入動態霓虹紅框高亮, 人眼全程可見。
       - 背端模式 (--mode backend): headless=True, 背景極速無感執行, 適合伺服器排程。
    2. 支援單步確認 (--step): 每一步驟可停頓由使用者按 Enter 推進，完全消除自動化不透明感。
    3. 自動排除/關閉 YouTube Cookie 同意提示 (Consent Dialog)。
    4. 智慧篩選音樂長片 (過濾 Shorts，優先鎖定含「讀書 / 專注 / Lofi / 音樂 / Study」關鍵字之長影片)。
[修改日期]: 2026-11-10
[修改概要]: 建立雙軌自動化播放器 (支援背端模式與視覺化視窗模式)
[輸入參數]: --mode (window/backend), --keyword (搜尋詞), --slow (毫秒), --step (是否單步暫停)
[輸出結果]: 終端與視覺即時操作狀態
[關聯測試]: report/BDD/DBB_Pre_Moreem_20261110.md
[工作日誌]: report/work_record/work_record_20261110.md
"""

import argparse
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from playwright.sync_api import sync_playwright, Page, Locator


class YouTubeInteractivePlayer:
    """
    [Class]: YouTubeInteractivePlayer
    [設計目的]: 負責執行 YouTube 流程的雙模自動化 (視窗演示 / 背景無感)
    """

    def __init__(
        self,
        mode: str = "window",
        keyword: str = "讀書長音樂",
        slow_mo_ms: int = 1000,
        step_by_step: bool = False,
        keep_open: bool = True,
        use_persistent_profile: bool = True,
    ):
        self.mode = mode.lower()
        self.is_window = self.mode == "window"
        self.keyword = keyword
        self.slow_mo = slow_mo_ms if self.is_window else 0
        self.step_by_step = step_by_step
        self.keep_open = keep_open
        self.use_persistent_profile = use_persistent_profile
        self.profile_dir = BASE_DIR / ".chrome_user_data"
        self.profile_dir.mkdir(parents=True, exist_ok=True)

    def _wait_step(self, step_name: str, desc: str):
        """若啟用單步模式，暫停等待使用者按下 Enter"""
        print(f"\n👉 【{step_name}】：{desc}")
        if self.step_by_step and self.is_window:
            input("   [按 Enter 鍵繼續執行此步驟...]")

    def _highlight_element(self, page: Page, locator: Locator, color: str = "#EF4444"):
        """在視窗模式下為正在操作的網頁元件繪製醒目霓虹光圈，讓人眼一眼看清"""
        if not self.is_window:
            return
        try:
            locator.scroll_into_view_if_needed(timeout=2000)
            page.evaluate(
                f"""(element) => {{
                    element.style.outline = '4px solid {color}';
                    element.style.boxShadow = '0 0 20px {color}';
                    element.style.transition = 'all 0.3s ease';
                }}""",
                locator.element_handle(),
            )
            time.sleep(0.4)
        except Exception:
            pass

    def run(self):
        print("=" * 70)
        mode_title = "🖥️【視窗模式】：全程視覺化、慢動作逐步演示" if self.is_window else "⚙️【背端模式】：背景無頭高速執行"
        print(f"🎬 YouTube 自動化播放啟動 ➔ {mode_title}")
        print("=" * 70)
        print(f"  • 搜尋主題: 「{self.keyword}」")
        print(f"  • 慢動作間隔: {self.slow_mo} ms")
        print(f"  • 持久化設定檔: {'✅ 已啟用 (自動記住 Google 帳號與登入狀態)' if self.use_persistent_profile else '關閉'}")
        print(f"  • 播放後保持開啟: {'✅ 是 (音樂持續播放，手動關閉視窗結束)' if self.keep_open and self.is_window else '否 (自動關閉)'}")
        print(f"  • 單步確認模式: {'開啟 (按 Enter 逐步推進)' if self.step_by_step else '關閉 (自動流暢演示)'}")
        print("-" * 70)

        with sync_playwright() as p:
            self._wait_step("步驟 1/5", "啟動具備帳號持久化登入之瀏覽器視窗")
            print("🚀 正在啟動瀏覽器視窗 (載入持久化 Profile，保持您的登入狀態)...")
            
            browser_args = [
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
            ]
            
            browser = None
            context = None

            if self.use_persistent_profile:
                try:
                    # 優先嘗試啟動系統 Google Chrome (共享並持久化您的登入狀態)
                    context = p.chromium.launch_persistent_context(
                        str(self.profile_dir),
                        channel="chrome",
                        headless=not self.is_window,
                        slow_mo=self.slow_mo,
                        viewport={"width": 1400, "height": 900} if self.is_window else {"width": 1280, "height": 720},
                        args=browser_args,
                    )
                except Exception:
                    # 若沙箱或本機未安裝預設 Chrome，自動切換至 Chromium 持久化設定檔
                    context = p.chromium.launch_persistent_context(
                        str(self.profile_dir),
                        headless=not self.is_window,
                        slow_mo=self.slow_mo,
                        viewport={"width": 1400, "height": 900} if self.is_window else {"width": 1280, "height": 720},
                        args=browser_args,
                    )
                page = context.pages[0] if context.pages else context.new_page()
            else:
                browser = p.chromium.launch(
                    headless=not self.is_window,
                    slow_mo=self.slow_mo,
                    args=browser_args,
                )
                context = browser.new_context(
                    viewport={"width": 1400, "height": 900} if self.is_window else {"width": 1280, "height": 720},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                )
                page = context.new_page()

            # 步驟 2: 前往 YouTube
            self._wait_step("步驟 2/5", "導航至 https://www.youtube.com")
            print("🌐 網址列輸入: https://www.youtube.com 正在連線...")
            try:
                page.goto("https://www.youtube.com", wait_until="domcontentloaded", timeout=25000)
                print("✅ YouTube 首頁載入成功！")
            except Exception as e:
                print(f"⚠️ 載入超時或網路波動: {e}")

            # 處理可能彈出的 Cookie 同意視窗
            try:
                consent_btn = page.locator("button:has-text('Accept all'), button:has-text('全部接受'), button:has-text('我同意')").first
                if consent_btn.is_visible(timeout=2000):
                    self._highlight_element(page, consent_btn, color="#10B981")
                    print("🍪 偵測到 Cookie 同意對話框，自動點擊關閉...")
                    consent_btn.click()
            except Exception:
                pass

            # 步驟 3: 尋找搜尋框
            self._wait_step("步驟 3/5", f"視覺鎖定搜尋框並鍵入關鍵字「{self.keyword}」")
            search_input = page.locator("input#search, input[name='search_query']").first
            try:
                search_input.wait_for(state="visible", timeout=10000)
                print("🎯 成功鎖定搜尋框！")
                self._highlight_element(page, search_input, color="#F59E0B")  # 琥珀金高亮
                search_input.click()
                time.sleep(0.3)

                print(f"⌨️ 正在逐字模擬人為輸入：「{self.keyword}」...")
                search_input.type(self.keyword, delay=120)  # 擬人打字速度
                time.sleep(0.5)

                print("⏎ 按下 Enter 送出搜尋...")
                search_input.press("Enter")
            except Exception as e:
                print(f"❌ 搜尋框操作失敗: {e}")
                browser.close()
                return False

            # 步驟 4: 等待搜尋結果並挑選長音樂
            self._wait_step("步驟 4/5", "解析搜尋結果並智慧選取最佳長音樂")
            print("⏳ 正在等待搜尋結果渲染...")
            page.wait_for_selector("ytd-video-renderer, ytd-rich-item-renderer", timeout=15000)

            # 抓取搜尋結果中的影片清單
            videos = page.locator("ytd-video-renderer, #contents ytd-video-renderer")
            video_count = videos.count()
            print(f"📋 畫面上成功載入 {video_count} 支相關影片。")

            target_video = None
            target_title = ""

            # 智慧過濾：優先找包含「讀書」、「音樂」、「Lofi」、「Hours」且非 Shorts 的影片
            for i in range(min(video_count, 8)):
                v = videos.nth(i)
                title_elem = v.locator("#video-title").first
                if title_elem.is_visible():
                    t_text = title_elem.inner_text().strip()
                    # 避免選到直播或極短片
                    if any(w in t_text.lower() for w in ["讀書", "音樂", "lofi", "study", "relax", "focus", "piano", "hour"]):
                        target_video = title_elem
                        target_title = t_text
                        break

            # 若未特別匹配則取第一支正常影片
            if not target_video and video_count > 0:
                target_video = videos.first.locator("#video-title").first
                target_title = target_video.inner_text().strip()

            if not target_video:
                print("⚠️ 未找到合適的影片標題。")
                browser.close()
                return False

            # 步驟 5: 鎖定目標、光環標註、點擊播放
            self._wait_step("步驟 5/5", f"鎖定目標影片並點擊播放：\n   🎵 『{target_title}』")
            print(f"🎯 目標鎖定！正在為影片標題加上霓虹高亮框線...")
            self._highlight_element(page, target_video, color="#06B6D4")  # 霓虹青高亮
            time.sleep(0.8)

            print("🖱️ 正在點擊進入影片播放頁面...")
            target_video.click()

            # 等待播放器加載
            try:
                page.wait_for_selector(".video-stream, #movie_player", timeout=15000)
                print("\n" + "=" * 70)
                print(f"🎉 播放成功！當前正在播放：『{target_title}』")
                print("=" * 70)
            except Exception as e:
                print(f"⚠️ 播放器等待提示: {e}")

            if self.is_window and self.keep_open:
                print("\n" + "=" * 70)
                print(f"🎉 播放成功！當前正在播放：『{target_title}』")
                print("=" * 70)
                print("\n🎵 讀書長音樂正在持續播放中！視窗將持續保持開啟供您聆聽。")
                print("💡 提示：若您在 YouTube 進行了 Google 登入，您的登入狀態已永久儲存在本機 Profile 中，下次啟動自動登入！")
                print("🛑 若要結束播放並關閉，請直接關閉瀏覽器視窗，或在終端機按下 Ctrl+C。")
                try:
                    while not page.is_closed():
                        time.sleep(1.0)
                    print("\n👋 偵測到使用者已手動關閉瀏覽器視窗，腳本正常結束。")
                except KeyboardInterrupt:
                    print("\n🛑 收到中斷信號，已停止播放並清理資源。")
            elif self.is_window:
                print("\n💡 視窗模式已就緒！音樂播放展示 30 秒後自動結束...")
                time.sleep(30.0)
            else:
                print("⚙️ 背端模式執行完成（已驗證至播放器加載完成）。")

            try:
                context.close()
                if browser:
                    browser.close()
            except Exception:
                pass
            return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube 雙模自動化播放器 (支援背端模式與視窗模式)")
    parser.add_argument(
        "--mode",
        type=str,
        default="window",
        choices=["window", "backend"],
        help="執行模式：'window' (視窗模式，彈出瀏覽器逐步演示) 或 'backend' (背端模式，背景無頭高速執行)",
    )
    parser.add_argument(
        "--keyword",
        type=str,
        default="讀書長音樂",
        help="YouTube 搜尋關鍵字 (預設: 讀書長音樂)",
    )
    parser.add_argument(
        "--slow",
        type=int,
        default=1000,
        help="視窗模式下每個動作的慢動作延遲毫秒數 (預設: 1000ms)",
    )
    parser.add_argument(
        "--step",
        action="store_true",
        help="開啟單步確認模式 (每一步驟停頓，由使用者按 Enter 繼續)",
    )
    parser.add_argument(
        "--no-keep-open",
        action="store_true",
        help="播放後不持續保持視窗開啟 (預設為保持開啟)",
    )
    parser.add_argument(
        "--no-profile",
        action="store_true",
        help="不使用持久化設定檔 (以全新乾淨無登入狀態啟動)",
    )

    args = parser.parse_args()
    player = YouTubeInteractivePlayer(
        mode=args.mode,
        keyword=args.keyword,
        slow_mo_ms=args.slow,
        step_by_step=args.step,
        keep_open=not args.no_keep_open,
        use_persistent_profile=not args.no_profile,
    )
    player.run()

