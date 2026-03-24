"""
Cython 预编译脚本 - macOS 代码保护
将核心 Python 模块编译为原生 .so 二进制，防止反编译还原源码
用于 PyInstaller 打包前的代码保护步骤

用法: python cython_protect.py
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

PROTECTED_DIRS = ["core", "gui", "database"]
PROTECTED_FILES = ["config.py"]
SKIP_NAMES = {"__init__.py", "main.py", "setup.py", "build.py",
              "build_nuitka.py", "cython_protect.py", "dev_run.py",
              "debug_runner.py", "debug_check.py"}


def collect_py_files():
    """收集需要编译的 Python 文件"""
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
    Path("_cython_setup.py").write_text(content)


def compile_with_cython(py_files):
    """执行 Cython 编译"""
    write_setup_script(py_files)

    result = subprocess.run(
        [sys.executable, "_cython_setup.py", "build_ext", "--inplace"],
    )
    if result.returncode != 0:
        print("Cython 编译失败!")
        sys.exit(1)


def cleanup(py_files):
    """清理: 删除源码 .py、中间 .c 文件、构建目录"""
    removed = 0
    for f in py_files:
        p = Path(f)
        # 确认 .so 已生成再删 .py
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
            print(f"  警告: {f} 未找到编译产物，保留 .py")

        c_file = p.with_suffix(".c")
        if c_file.exists():
            c_file.unlink()

    Path("_cython_setup.py").unlink(missing_ok=True)
    if Path("build").exists():
        shutil.rmtree("build")

    return removed


def generate_hidden_imports(py_files):
    """生成 PyInstaller --hidden-import 参数列表"""
    imports = []
    for f in py_files:
        module = f.replace(os.sep, ".").replace("/", ".")
        if module.endswith(".py"):
            module = module[:-3]
        imports.append(module)
    return imports


def main():
    py_files = collect_py_files()
    if not py_files:
        print("没有找到需要编译的文件")
        return

    print("=" * 60)
    print("  Cython 代码保护 - .py -> .so 原生二进制编译")
    print("=" * 60)
    print(f"\n将编译 {len(py_files)} 个模块:\n")
    for f in py_files:
        print(f"  {f}")

    # 生成隐式导入列表 (PyInstaller 需要)
    hidden = generate_hidden_imports(py_files)
    print(f"\n--- PyInstaller hidden imports ({len(hidden)}) ---")
    flags = " ".join(f"--hidden-import={m}" for m in hidden)
    print(flags)

    # 写入文件供 CI 使用
    Path("_hidden_imports.txt").write_text("\n".join(hidden))

    print("\n开始 Cython 编译...\n")
    compile_with_cython(py_files)

    print("\n清理源文件...")
    removed = cleanup(py_files)
    print(f"完成! 已编译 {removed} 个模块为原生二进制")

    # 验证
    so_count = 0
    for d in PROTECTED_DIRS:
        so_count += len(list(Path(d).rglob("*.so")))
        so_count += len(list(Path(d).rglob("*.pyd")))
    for f in PROTECTED_FILES:
        p = Path(f).parent
        so_count += len(list(p.glob(Path(f).stem + ".cpython-*")))

    print(f"\n验证: 共 {so_count} 个 .so/.pyd 二进制模块")
    print("原始 .py 源码已删除，无法被反编译\n")


if __name__ == "__main__":
    main()
