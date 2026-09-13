# 部署：把仓库源码同步到 MaiBot 运行时（单向，repo -> runtime）
# 用法：在仓库任意位置执行  powershell -File apps\luoxue-wb-bridge\deploy.ps1
$ErrorActionPreference = "Stop"
$src = Join-Path $PSScriptRoot "wb_llm_bridge.py"
$dst = "F:\aipengyou\wb_bridge\wb_llm_bridge.py"

if (-not (Test-Path $src)) { throw "源码不存在: $src" }

# 部署前校验语法（用 MaiBot venv 的 python）
& F:\aipengyou\.venv\Scripts\python.exe -m py_compile $src
if ($LASTEXITCODE -ne 0) { throw "语法校验失败，终止部署" }

Copy-Item $src $dst -Force
Write-Host "已部署: $dst"

# 提示重启桥（桥不会热加载）
$conn = Get-NetTCPConnection -LocalPort 8900 -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    Write-Host "桥正在运行 (PID $($conn.OwningProcess))，需重启才能生效："
    Write-Host "  Stop-Process -Id $($conn.OwningProcess) -Force"
    Write-Host "  然后用 yi_jian_qi_dong.ps1 或 schtasks 方式重新拉起"
} else {
    Write-Host "桥当前未运行，下次启动自动生效"
}
