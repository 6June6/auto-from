import sys
from database import init_database
import config

print("Testing database connection...")
try:
    if init_database():
        print("Database connected successfully!")
    else:
        print("Database connection failed.")
except Exception as e:
    print(f"Exception: {e}")










