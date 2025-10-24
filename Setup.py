from setuptools import setup, find_packages
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def read_requirements():
    req_path = os.path.join(PROJECT_ROOT, "requirements.txt")
    with open(req_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

def read_long_description():
    readme_path = os.path.join(PROJECT_ROOT, "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            return f.read()
    return "GUI tool to package Python files to EXE (PyInstaller/Nuitka)"

setup(
    name="pack-py-exe",
    version="0.2.0",  # 版本号更新（修复所有问题）
    packages=find_packages(),
    include_package_data=True,
    install_requires=read_requirements(),
    entry_points={
        "console_scripts": [
            "pack-py-exe = packpy.main:main",  # 命令行入口
        ],
    },
    author="JGZ_YES",
    author_email="luoriguodu@qq.com",
    description="One-click Python to EXE GUI tool (supports PyInstaller/Nuitka)",
    long_description=read_long_description(),
    long_description_content_type="text/markdown",
    url="https://github.com/JGZYES/pack-py",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires=">=3.6",
)
