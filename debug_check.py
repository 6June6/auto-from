import sys
import os

# 添加项目根目录到路径
sys.path.append(os.getcwd())

print("尝试导入 gui.main_window...")
try:
    from gui.main_window import MainWindow
    print("导入成功！")
except Exception as e:
    print(f"导入失败: {e}")
    import traceback
    traceback.print_exc()





