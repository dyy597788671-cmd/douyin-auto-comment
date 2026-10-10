param(
    [string]$ProjectRoot = 'C:\Users\Administrator\AppData\Local\ShadowBot\users\894802265707544578\apps\84fca2ea-8671-4147-8b20-99d5663016e6',
    [string]$RuntimePath = 'D:\app\ShadowBot\shadowbot-6.3.31\ShadowBot.Runtime.dll',
    [ValidateRange(1, 65535)][int]$Port = 8765,
    [string]$LanIp = ''
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$package = $PSScriptRoot
# A shared file path identifies storage, not the computer running this script.
# Advertise only an address actually assigned to this computer.
$localAddresses = @(Get-NetIPAddress -AddressFamily IPv4 -AddressState Preferred -ErrorAction Stop |
    Where-Object { $_.IPAddress -notmatch '^(127\.|169\.254\.|0\.)' } |
    Select-Object -ExpandProperty IPAddress -Unique)
if ($LanIp) {
    if ($localAddresses -notcontains $LanIp) {
        throw ('指定网页IP不属于当前运行电脑：' + $LanIp + '。当前有效IPv4：' + ($localAddresses -join '、'))
    }
} elseif ($localAddresses.Count -eq 1) {
    $LanIp = $localAddresses[0]
} elseif ($localAddresses.Count -eq 0) {
    throw '当前电脑没有有效的局域网IPv4地址，网页服务尚未启动。'
} else {
    throw ('当前电脑有多个有效IPv4，请用 -LanIp 指定其中一个：' + ($localAddresses -join '、'))
}
$lanUrl = 'http://' + $LanIp + ':' + $Port
Write-Host ('运行电脑：' + $env:COMPUTERNAME + '；实际网页IP：' + $LanIp)

function Get-ToolContext([string]$Address) {
    # This self-check must not inherit a browser or system HTTP proxy.
    $request = [Net.WebRequest]::Create($Address + '/api/context')
    $request.Proxy = $null
    $request.Timeout = 1000
    $request.ReadWriteTimeout = 1000
    $request.AllowAutoRedirect = $false
    $response = $null
    $reader = $null
    try {
        $response = $request.GetResponse()
        $reader = [IO.StreamReader]::new($response.GetResponseStream())
        return ($reader.ReadToEnd() | ConvertFrom-Json)
    } catch {
        return $null
    } finally {
        if ($reader) { $reader.Dispose() }
        if ($response) { $response.Dispose() }
    }
}

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

$localUrl = 'http://127.0.0.1:' + $Port
$context = Get-ToolContext $localUrl
if ($context -and $context.data.application -eq 'douyin-local-tool') {
    $lanContext = Get-ToolContext $lanUrl
    if ($context.data.lan_url -ne $lanUrl -or -not $lanContext -or $lanContext.data.application -ne 'douyin-local-tool') {
        throw ('端口' + $Port + '已有旧配置的工具在运行。请关闭B电脑原工具后台窗口，再启动；本次实际地址为：' + $lanUrl)
    }
    Write-Host ('已核实网页服务正在运行。其他电脑访问：' + $lanUrl) -ForegroundColor Green
    Write-Host '本次没有新建后台；原工具后台窗口仍需保持开启。'
    try { Start-Process $localUrl } catch { Write-Host ('请手动打开：' + $localUrl) }
    exit 0
}

# Keep Python attached to this console and verify actual HTTP readiness.
# An open PowerShell window alone is not proof that Python is still running.
$serverInfo = [Diagnostics.ProcessStartInfo]::new()
$serverInfo.FileName = $python
$serverInfo.Arguments = '-u "' + (Join-Path $root 'lan_tool\server.py') + '" --root "' + $root + '" --port ' + $Port + ' --lan-ip ' + $LanIp
$serverInfo.WorkingDirectory = $root
$serverInfo.UseShellExecute = $false
$serverProcess = [Diagnostics.Process]::new()
$serverProcess.StartInfo = $serverInfo
$serverStarted = $false
try {
    $serverStarted = $serverProcess.Start()
    $deadline = [DateTime]::UtcNow.AddSeconds(20)
    $ready = $false
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($serverProcess.HasExited) { break }
        $context = Get-ToolContext $localUrl
        $lanContext = Get-ToolContext $lanUrl
        if ($context -and $lanContext -and $context.data.application -eq 'douyin-local-tool' -and
            $context.data.lan_url -eq $lanUrl -and $lanContext.data.application -eq 'douyin-local-tool' -and
            -not $serverProcess.HasExited) {
            $ready = $true
            break
        }
        Start-Sleep -Milliseconds 250
    }
    if (-not $ready) {
        if ($serverProcess.HasExited) {
            $serverProcess.WaitForExit()
            throw ('网页后台已退出，退出码=' + $serverProcess.ExitCode + '。请保留上方原始报错；当前没有可用网页服务。')
        }
        throw ('后台启动后未通过本机HTTP检查：' + $lanUrl + '。本次后台将停止，不把地址文字当作启动成功。')
    }
    Write-Host ('本机HTTP检查通过；其他电脑访问：' + $lanUrl) -ForegroundColor Green
    Write-Host '此检查确认B本机服务已响应；其他电脑能否连接仍取决于实际网络路径。'
    try { Start-Process $localUrl } catch { Write-Host ('请手动打开：' + $localUrl) }
    $serverProcess.WaitForExit()
    throw ('网页后台已经停止，退出码=' + $serverProcess.ExitCode + '。此PowerShell窗口仍开着也不能继续提供网页。')
} finally {
    if ($serverStarted -and -not $serverProcess.HasExited) {
        $serverProcess.Kill()
        $serverProcess.WaitForExit()
    }
    $serverProcess.Dispose()
}
