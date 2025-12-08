import sys
from PyQt6.QtWidgets import QApplication, QLabel

print("Starting simple GUI test...")
app = QApplication(sys.argv)
label = QLabel("Hello World")
label.show()
print("GUI shown, exiting immediately for test.")
# sys.exit(app.exec()) # 不要阻塞











