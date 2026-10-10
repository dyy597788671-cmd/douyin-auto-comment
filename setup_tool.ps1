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
# Select by successful execution, not merely by python.exe being present.
$python = $null
$pythonCandidates = [Collections.Generic.List[string]]::new()
$pythonFailures = [Collections.Generic.List[string]]::new()
$seenPython = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
$probeCode = "import sys,json; print('PYTHON_PROBE='+json.dumps(dict(executable=sys.executable,version=sys.version.split()[0]))); sys.stdout.flush(); sys.exit('PYTHON_VERSION_TOO_OLD: need 3.8+') if sys.version_info < (3,8) else None; import sqlite3,ast; sqlite3.connect(':memory:').execute('select 1'); print('PYTHON_READY=1')"

function Test-ToolPython([string]$Candidate, [string]$Prefix = '') {
    $info = [Diagnostics.ProcessStartInfo]::new()
    $info.FileName = $Candidate
    $info.Arguments = $Prefix + '-c "' + $probeCode + '"'
    $info.WorkingDirectory = $root
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $info.StandardOutputEncoding = [Text.Encoding]::UTF8
    $info.StandardErrorEncoding = [Text.Encoding]::UTF8
    $probeProcess = [Diagnostics.Process]::new()
    $probeProcess.StartInfo = $info
    try {
        [void]$probeProcess.Start()
        $stdout = $probeProcess.StandardOutput.ReadToEndAsync()
        $stderr = $probeProcess.StandardError.ReadToEndAsync()
        if (-not $probeProcess.WaitForExit(15000)) {
            $probeProcess.Kill()
            throw '解释器启动检查超过15秒'
        }
        $probeProcess.WaitForExit()
        $text = $stdout.Result
        $errorText = $stderr.Result
        if ($probeProcess.ExitCode -eq 0 -and $text -match '(?m)^PYTHON_READY=1\r?$') {
            $line = @($text -split '\r?\n' | Where-Object { $_.StartsWith('PYTHON_PROBE=') })[-1]
            $details = $line.Substring(13) | ConvertFrom-Json
            if (-not (Test-Path -LiteralPath $details.executable -PathType Leaf)) { throw '解释器没有返回有效路径' }
            Write-Host ('使用Python ' + $details.version + '：' + $details.executable)
            return [string]$details.executable
        }
        $reason = ('退出码=' + $probeProcess.ExitCode + "`n" + $text + $errorText).Trim()
        $pythonFailures.Add($Candidate + "`n" + $reason)
    } catch {
        $pythonFailures.Add($Candidate + "`n" + $_.Exception.Message)
    } finally {
        $probeProcess.Dispose()
    }
    return $null
}

$pythonCandidates.Add((Join-Path $root 'venv\Scripts\python.exe'))
$pythonCandidates.Add((Join-Path $root 'venv\python.exe'))
# The virtual environment itself may be unavailable; its recorded base is evidence.
$venvConfig = Join-Path $root 'venv\pyvenv.cfg'
if (Test-Path -LiteralPath $venvConfig -PathType Leaf) {
    foreach ($line in Get-Content -LiteralPath $venvConfig) {
        if ($line -match '^\s*home\s*=\s*(.+?)\s*$') {
            $pythonCandidates.Add((Join-Path $Matches[1] 'python.exe'))
        }
    }
}
foreach ($name in @('python.exe', 'python3.exe')) {
    foreach ($command in @(Get-Command $name -All -CommandType Application -ErrorAction SilentlyContinue)) {
        if ($command.Source -notlike '*\WindowsApps\*') { $pythonCandidates.Add($command.Source) }
    }
}
foreach ($candidate in $pythonCandidates) {
    if ((Test-Path -LiteralPath $candidate -PathType Leaf) -and $seenPython.Add($candidate)) {
        $python = Test-ToolPython $candidate
        if ($python) { break }
    }
}
if (-not $python) {
    foreach ($launcher in @(Get-Command py.exe -All -CommandType Application -ErrorAction SilentlyContinue)) {
        if ($launcher.Source -notlike '*\WindowsApps\*') {
            $python = Test-ToolPython $launcher.Source '-3 '
            if ($python) { break }
        }
    }
}
if (-not $python) {
    # Inspect existing ShadowBot installation files only after earlier candidates fail.
    $shadowBotRoot = Split-Path -Parent (Split-Path -Parent $RuntimePath)
    foreach ($directory in @($shadowBotRoot, (Join-Path $env:ProgramData 'ShadowBot'))) {
        if (-not (Test-Path -LiteralPath $directory -PathType Container)) { continue }
        foreach ($file in @(Get-ChildItem -LiteralPath $directory -Filter python.exe -File -Recurse -ErrorAction SilentlyContinue)) {
            if ($file.FullName -like '*\WindowsApps\*' -or -not $seenPython.Add($file.FullName)) { continue }
            $python = Test-ToolPython $file.FullName
            if ($python) { break }
        }
        if ($python) { break }
    }
}
if (-not $python) {
    Write-Host '未找到能够启动且具备sqlite3的Python 3.8或以上解释器。实际检查结果：' -ForegroundColor Yellow
    if ($pythonFailures.Count) { foreach ($failure in $pythonFailures) { Write-Host $failure } }
    else { Write-Host '未发现Python可执行文件。' }
    throw 'Python检查未通过，尚未安装或修改项目。请发送上方实际检查结果。'
}
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
