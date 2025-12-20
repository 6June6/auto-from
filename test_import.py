import sys
import os
from PyQt6.QtWidgets import QApplication

# 添加项目根目录到 path
sys.path.append(os.getcwd())

try:
    print("Importing NewFillWindow...")
    from gui.new_fill_window import NewFillWindow
    print("Import successful!")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()














