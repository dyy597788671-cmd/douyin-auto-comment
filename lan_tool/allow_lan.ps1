param([int]$Port = 8765)
$ErrorActionPreference = 'Stop'
New-NetFirewallRule -Name ('DouyinLocalTool_' + $Port) -DisplayName '抖音任务工具（仅本地子网）' -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port -RemoteAddress LocalSubnet -Profile Any | Out-Null
