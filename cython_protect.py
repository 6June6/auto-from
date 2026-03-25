"""
Cython 预编译脚本 - 代码保护
将核心 Python 模块编译为原生 .so/.pyd 二进制，防止反编译还原源码
同时扫描所有源码的 import 依赖，生成 PyInstaller 所需的 hidden-import 列表

用法: python cython_protect.py
"""
import ast
import os
import sys
import shutil
import subprocess
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROTECTED_DIRS = ["core", "gui", "database"]
PROTECTED_FILES = []
SKIP_NAMES = {"__init__.py", "main.py", "setup.py", "build.py",
              "build_nuitka.py", "cython_protect.py", "dev_run.py",
              "debug_runner.py", "debug_check.py"}

# 本地项目包名（不需要作为 hidden-import 传给 PyInstaller）
LOCAL_PACKAGES = {"core", "gui", "database", "config", "tools"}


def collect_py_files():
    """收集需要 Cython 编译的 Python 文件"""
    py_files = []
    for dir_name in PROTECTED_DIRS:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            continue
        for f in sorted(dir_path.rglob("*.py")):
            if f.name not in SKIP_NAMES:
                py_files.append(str(f))

    for f in PROTECTED_FILES:
        if Path(f).exists() and f not in SKIP_NAMES:
            py_files.append(f)

    return py_files


SCAN_EXCLUDE_DIRS = {"tools"}

def collect_all_py_for_scan():
    """收集所有需要扫描 import 的 .py 文件（不扫描 tools/ 里的非必要脚本）"""
    scan_dirs = PROTECTED_DIRS
    files = []
    for dir_name in scan_dirs:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            continue
        for f in sorted(dir_path.rglob("*.py")):
            files.append(str(f))

    # tools 只扫描被主程序引用的文件
    tools_scan = ["tools/link_utils.py", "tools/__init__.py"]
    for f in tools_scan:
        if Path(f).exists():
            files.append(f)

    for f in ["main.py", "config.py"]:
        if Path(f).exists():
            files.append(f)

    return files


def scan_imports(py_files):
    """
    用 AST 扫描所有 .py 文件中的 import 语句，
    返回去重后的完整第三方模块依赖集合。
    """
    all_imports = set()

    for filepath in py_files:
        try:
            source = Path(filepath).read_text(encoding='utf-8', errors='ignore')
            tree = ast.parse(source, filename=filepath)
        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"  warning: skip parsing {filepath}: {e}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    all_imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    all_imports.add(node.module)
                    # 也加入子模块，比如 from logging.handlers import X -> logging.handlers
                    parts = node.module.split('.')
                    for i in range(1, len(parts)):
                        all_imports.add('.'.join(parts[:i+1]))

    return all_imports


def classify_imports(all_imports):
    """
    将 import 分为：本地项目模块 和 第三方/标准库模块。
    本地项目模块会作为 PyInstaller hidden-import（因为源码被 Cython 编译后丢失）。
    第三方和标准库模块也全部加入 hidden-import 确保 PyInstaller 能找到。
    """
    hidden_imports = set()
    for mod in all_imports:
        top = mod.split('.')[0]
        # 跳过明显不需要的
        if top.startswith('_') and top != '_thread':
            continue
        hidden_imports.add(mod)

    return sorted(hidden_imports)


def write_setup_script(py_files):
    """生成临时 Cython 编译脚本"""
    content = f"""\
from setuptools import setup
from Cython.Build import cythonize

setup(
    ext_modules=cythonize(
        {py_files!r},
        compiler_directives={{"language_level": 3}},
        force=True,
    ),
)
"""
    Path("_cython_setup.py").write_text(content, encoding="utf-8")


def compile_with_cython(py_files):
    """执行 Cython 编译"""
    write_setup_script(py_files)

    result = subprocess.run(
        [sys.executable, "_cython_setup.py", "build_ext", "--inplace"],
    )
    if result.returncode != 0:
        print("Cython compile failed!")
        sys.exit(1)


def cleanup(py_files):
    """清理: 删除源码 .py、中间 .c 文件、构建目录"""
    removed = 0
    for f in py_files:
        p = Path(f)
        so_pattern = p.stem + ".cpython-*.so"
        pyd_pattern = p.stem + ".cpython-*.pyd"
        parent = p.parent
        has_compiled = (
            list(parent.glob(so_pattern)) or list(parent.glob(pyd_pattern))
        )
        if has_compiled:
            if p.exists():
                p.unlink()
                removed += 1
        else:
            print(f"  warning: {f} has no compiled output, keeping .py")

        c_file = p.with_suffix(".c")
        if c_file.exists():
            c_file.unlink()

    Path("_cython_setup.py").unlink(missing_ok=True)
    if Path("build").exists():
        shutil.rmtree("build")

    return removed


def main():
    # ---- Step 1: 扫描所有 import 依赖 (在 Cython 编译前，源码还在) ----
    scan_files = collect_all_py_for_scan()
    print("=" * 60)
    print("  Step 1: Scan imports from all source files")
    print("=" * 60)
    print(f"\n  Scanning {len(scan_files)} files for import statements...\n")

    all_imports = scan_imports(scan_files)
    hidden_imports = classify_imports(all_imports)

    print(f"  Found {len(hidden_imports)} unique imports")
    Path("_hidden_imports.txt").write_text("\n".join(hidden_imports), encoding="utf-8")
    print(f"  Written to _hidden_imports.txt\n")

    # ---- Step 2: Cython 编译 ----
    py_files = collect_py_files()
    if not py_files:
        print("No files to compile")
        return

    print("=" * 60)
    print("  Step 2: Cython compile (.py -> native binary)")
    print("=" * 60)
    print(f"\n  Compiling {len(py_files)} modules:\n")
    for f in py_files:
        print(f"    {f}")

    print("\n  Running Cython...\n")
    compile_with_cython(py_files)

    # ---- Step 3: 清理源码 ----
    print("\n  Cleaning up source files...")
    removed = cleanup(py_files)

    # ---- 验证 ----
    ext_count = 0
    for d in PROTECTED_DIRS:
        if Path(d).exists():
            ext_count += len(list(Path(d).rglob("*.so")))
            ext_count += len(list(Path(d).rglob("*.pyd")))
    for f in PROTECTED_FILES:
        p = Path(f).parent
        ext_count += len(list(p.glob(Path(f).stem + ".cpython-*")))

    print(f"\n  Done! Compiled {removed} modules, {ext_count} native binaries total")
    print(f"  Hidden imports: {len(hidden_imports)} entries in _hidden_imports.txt\n")


if __name__ == "__main__":
    main()
