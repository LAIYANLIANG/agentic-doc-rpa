#!/usr/bin/env python3
"""
[使用工具]: Python 3
[設計目的]: 自動檢測並修復專案資料夾改名後，虛擬環境 (.venv_rpa_ocr, .venv_airflow) 內部寫死的 shebang 與 pyvenv.cfg 路徑。
[說明]:
    當資料夾由 analyse_system 更名為 agentic-doc-rpa (或移至新路徑) 時，
    執行本腳本即可自動完成虛擬環境路徑的自適應修復，無需重新下載安裝套件。
"""

import sys
from pathlib import Path

def fix_virtual_environments():
    project_root = Path(__file__).resolve().parent.parent.parent
    print(f"🔧 開始檢查專案根目錄虛擬環境路徑：{project_root}")

    venvs = [project_root / ".venv_rpa_ocr", project_root / ".venv_airflow"]
    total_fixed_files = 0

    for venv in venvs:
        if not venv.exists():
            continue

        print(f"\n📁 掃描虛擬環境：{venv.name}")
        
        # 1. 修復 pyvenv.cfg
        cfg_file = venv / "pyvenv.cfg"
        if cfg_file.exists():
            content = cfg_file.read_text(encoding="utf-8")
            if "analyse_system" in content:
                new_content = content.replace("analyse_system", project_root.name)
                cfg_file.write_text(new_content, encoding="utf-8")
                print(f"  ✅ 已更新 {cfg_file.name}")
                total_fixed_files += 1

        # 2. 掃描 bin/ 目錄下的所有指令腳本修復 shebang
        bin_dir = venv / "bin"
        if bin_dir.exists():
            for script_path in bin_dir.iterdir():
                if script_path.is_file() and not script_path.is_symlink():
                    try:
                        content_bytes = script_path.read_bytes()
                        # 檢查前 512 bytes 是否為文字且包含舊路徑
                        header_sample = content_bytes[:512]
                        if b"analyse_system" in header_sample:
                            new_bytes = content_bytes.replace(b"analyse_system", project_root.name.encode("utf-8"))
                            script_path.write_bytes(new_bytes)
                            print(f"  ✅ 已修復 shebang: {script_path.name}")
                            total_fixed_files += 1
                    except Exception as e:
                        pass

    print(f"\n🎉 虛擬環境檢查修復完成！共更新 {total_fixed_files} 個設定/執行檔。")

if __name__ == "__main__":
    fix_virtual_environments()

