param(
    [string]$ProjectRoot = 'C:\Users\Administrator\AppData\Local\ShadowBot\users\894802265707544578\apps\84fca2ea-8671-4147-8b20-99d5663016e6',
    [string]$RuntimePath = 'D:\app\ShadowBot\shadowbot-6.3.31\ShadowBot.Runtime.dll',
    [int]$Port = 8765,
    [string]$LanIp = '192.168.11.10'
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$package = $PSScriptRoot
$root = (Resolve-Path -LiteralPath $ProjectRoot).ProviderPath
$module = Join-Path $root 'xbot_robot\module1.py'
$engine = Join-Path $root 'core_runner.py'
$python = $null
foreach ($candidate in @((Join-Path $root 'venv\Scripts\python.exe'), (Join-Path $root 'venv\python.exe'))) {
    if (Test-Path -LiteralPath $candidate -PathType Leaf) { $python = $candidate; break }
}
if (-not $python) {
    $command = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($command -and $command.Source -notlike '*WindowsApps*') { $python = $command.Source }
}
if (-not $python) { throw '未找到现有Python。请把此窗口输出发回，不要修改影刀任务数据。' }
& $python -c 'import sys,sqlite3,ast; assert sys.version_info >= (3,8)'
if ($LASTEXITCODE -ne 0) { throw '当前Python不能运行工具，需要Python 3.8或以上。' }

$installed = (Test-Path -LiteralPath (Join-Path $root 'lan_tool\server.py')) -and
    ((Get-Content -LiteralPath $module -Raw -Encoding UTF8) -match 'LAN_TOOL_INTAKE_V1') -and
    ((Get-Content -LiteralPath $engine -Raw -Encoding UTF8) -match 'LAN_TOOL_INTAKE_V1')
if (-not $installed) {
    if (Get-Process -Name 'ShadowBot.Shell' -ErrorAction SilentlyContinue) {
        throw '首次安装需要完全退出影刀。退出后重新双击 Start-Tool.cmd；不要删除任务表或运行状态。'
    }
    Write-Host '正在安装工具与必要的数据接入位置……'
    $output = & $python (Join-Path $package 'install_tool.py') --root $root --package $package
    $output | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) { throw '工具安装未完成，原业务文件保留。' }
    $backupLine = @($output | Where-Object { $_ -like 'BACKUP=*' })[-1]
    $backupPath = $backupLine.Substring(7)
    try {
        & (Join-Path $root 'lan_tool\repair_signature.ps1') -ProjectRoot (Join-Path $root 'xbot_robot') -RuntimePath $RuntimePath -Write
        if ($LASTEXITCODE -ne 0) { throw '签名检查未成功。' }
    } catch {
        Copy-Item -LiteralPath (Join-Path $backupPath 'module1.py') -Destination $module -Force
        Copy-Item -LiteralPath (Join-Path $backupPath 'core_runner.py') -Destination $engine -Force
        throw ('安装未完成，已还原原模块和引擎。原因：' + $_.Exception.Message)
    }
    Write-Host '安装完成。可以重新打开影刀，继续使用原主流程。' -ForegroundColor Green
}

$ruleName = 'DouyinLocalTool_' + $Port
$rule = Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue
if (-not $rule) {
    try {
        $principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
        if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
            & (Join-Path $root 'lan_tool\allow_lan.ps1') -Port $Port
        } else {
            $scriptPath = Join-Path $root 'lan_tool\allow_lan.ps1'
            $process = Start-Process powershell.exe -Verb RunAs -Wait -PassThru -ArgumentList ('-NoProfile -ExecutionPolicy Bypass -File "' + $scriptPath + '" -Port ' + $Port)
            if ($process.ExitCode -ne 0) { throw '局域网放行未完成' }
        }
    } catch {
        Write-Host ('局域网放行未完成：' + $_.Exception.Message) -ForegroundColor Yellow
        Write-Host '本机页面仍可启动；其他电脑无法访问时，以管理员身份重新运行 Start-Tool.cmd。'
    }
}

try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri ('http://127.0.0.1:' + $Port + '/api/context') -TimeoutSec 2
    $context = $response.Content | ConvertFrom-Json
    if ($context.data.application -eq 'douyin-local-tool') {
        Start-Process ('http://127.0.0.1:' + $Port)
        Write-Host '工具已经运行，已打开本机管理页面。'
        exit 0
    }
} catch { }
& $python (Join-Path $root 'lan_tool\server.py') --root $root --port $Port --lan-ip $LanIp --open
if ($LASTEXITCODE -ne 0) { throw '网页服务启动失败，请保留窗口中的完整报错。' }
