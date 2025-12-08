import sys
import os
from PyQt6.QtWidgets import QApplication
from gui import MainWindow
from database import init_database

class MockUser:
    username = "test"
    id = "test_id"
    def is_admin(self): return False

print("Initializing database...")
init_database()

print("Creating QApplication...")
app = QApplication(sys.argv)

print("Instantiating MainWindow...")
try:
    user = MockUser()
    window = MainWindow(current_user=user)
    print("MainWindow instantiated successfully!")
    window.show()
    print("MainWindow shown!")
except Exception as e:
    print(f"Failed to instantiate MainWindow: {e}")
    import traceback
    traceback.print_exc()











