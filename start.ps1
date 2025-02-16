# 设置错误处理
$ErrorActionPreference = "Stop"

try {
    # 获取脚本所在目录
    $scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
    
    # 切换到脚本所在目录
    Set-Location -Path $scriptPath
    
    Write-Host "正在激活虚拟环境..." -ForegroundColor Green
    
    # 激活虚拟环境
    & .\venv\Scripts\Activate.ps1
    
    if ($?) {
        Write-Host "虚拟环境已激活" -ForegroundColor Green
        
        Write-Host "正在启动项目..." -ForegroundColor Green
        # 启动项目
        python main.py
    }
}
catch {
    Write-Host "发生错误: $_" -ForegroundColor Red
    exit 1
}