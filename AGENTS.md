# AGENTS.md

## Cursor Cloud specific instructions

### Project overview
This is a **Python PyQt6 desktop application** (自动表单填写工具 / Auto Form Filler) for automating form submissions on Chinese social media platforms. It uses MongoDB (remote Alibaba Cloud instance) for data storage.

### Key services
| Service | Command | Port | Required |
|---------|---------|------|----------|
| Main PyQt6 GUI | `source venv/bin/activate && python main.py` | N/A (desktop) | Yes |
| Notice API (FastAPI) | `source venv/bin/activate && python -m uvicorn tools.notice_api:app --host 0.0.0.0 --port 8901` | 8901 | Optional |
| Social Media Parser API | `source venv/bin/activate && python -m uvicorn tools.xhs_api:app --host 0.0.0.0 --port 8900` | 8900 | Optional (needs Selenium/Chromium) |

### Critical gotchas

1. **PyQt6-Qt6 version pinning**: After `pip install -r requirements.txt`, you **must** pin the Qt6 runtime versions to match:
   ```
   pip install "PyQt6-Qt6==6.6.1" "PyQt6-WebEngine-Qt6==6.6.0" --force-reinstall
   ```
   Without this, PyQt6 6.6.1 pulls the latest PyQt6-Qt6 (e.g. 6.10.x) which causes `ImportError: undefined symbol` crashes.

2. **Display requirement**: The PyQt6 GUI needs an X11 display. The VM's built-in display (`:1`) works. If running headlessly, start Xvfb first: `Xvfb :99 -screen 0 1920x1080x24 &` and `export DISPLAY=:99`.

3. **MongoDB is remote and mandatory**: The app connects to an Alibaba Cloud MongoDB instance (configured in `config.py`). The app will `sys.exit(1)` if the connection fails. No local MongoDB is needed.

4. **Default admin credentials**: username `admin`, password `admin123`. Admin users see the management dashboard; regular users see the form-filling interface.

5. **Python 3.12 float-to-int**: Some PyQt6 drawing calls (e.g., `drawEllipse`) may need explicit `int()` casts for radius/coordinate parameters due to Python 3.12 stricter type handling.

### Running tests
There is no formal test framework (pytest/unittest). The repo includes ad-hoc test scripts:
- `python test_db.py` — basic MongoDB connection test
- `python test_mongodb_connection.py` — comprehensive CRUD test (note: `create_card` test fails because it lacks the required `user` parameter)
- `python test_gui.py` — minimal PyQt6 import/widget test
- `python test_import.py` — tests import of `gui.new_fill_window`

### Lint
No linter is configured in the repo (no flake8, pylint, mypy, or pyproject.toml). Python's built-in `py_compile` can be used for syntax checking.
