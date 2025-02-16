#!/bin/bash

# 设置错误时退出
set -e

# 获取脚本所在目录并切换
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
cd "$SCRIPT_DIR"

echo -e "\033[0;32m正在激活虚拟环境...\033[0m"

# 激活虚拟环境
source ./venv/bin/activate

if [ $? -eq 0 ]; then
    echo -e "\033[0;32m虚拟环境已激活\033[0m"
    echo -e "\033[0;32m正在启动项目...\033[0m"
    python main.py
else
    echo -e "\033[0;31m发生错误\033[0m"
    exit 1
fi
