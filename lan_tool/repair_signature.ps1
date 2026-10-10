# Adapted from apexcheng/yingdao-xbot-ai-agent:
# project-template/.agents/skills/xbot-tools/scripts/repair_package_sigstore.ps1
# Upstream file SHA: ffd0e010a2247f5d84293ac615ca8a52f19e50ee
# Uses the installed ShadowBot methods, not a replacement signing algorithm.
param(
    [string]$ProjectRoot = 'C:\Users\Administrator\AppData\Local\ShadowBot\users\894802265707544578\apps\84fca2ea-8671-4147-8b20-99d5663016e6\xbot_robot',
    [string]$RuntimePath = 'D:\app\ShadowBot\shadowbot-6.3.31\ShadowBot.Runtime.dll',
    [switch]$Write
)

$ErrorActionPreference = 'Stop'

if (Get-Process -Name 'ShadowBot.Shell' -ErrorAction SilentlyContinue) {
    throw '请完全退出影刀后，再执行此脚本。'
}

$projectRootPath = (Resolve-Path -LiteralPath $ProjectRoot).ProviderPath.TrimEnd('\')
$runtimePathFull = (Resolve-Path -LiteralPath $RuntimePath).ProviderPath
$runtimeDir = Split-Path -Parent $runtimePathFull
$installRoot = Split-Path -Parent $runtimeDir
$dotnetPath = Join-Path $installRoot 'dotnet.win-x64\dotnet.exe'
# Prefer the configuration of the executable that actually loaded this DLL.
$runtimeConfigPath = Join-Path $runtimeDir 'ShadowBot.Shell.runtimeconfig.json'
if (-not (Test-Path -LiteralPath $runtimeConfigPath -PathType Leaf)) {
    $runtimeConfigPath = Join-Path $installRoot 'ShadowBot.runtimeconfig.json'
}
$compilerPath = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$packageJsonPath = Join-Path $projectRootPath 'package.json'

foreach ($requiredPath in @($dotnetPath, $runtimeConfigPath, $compilerPath, $packageJsonPath)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "缺少必需文件：$requiredPath"
    }
}

$manifest = Get-Content -LiteralPath $packageJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
$appId = [string]$manifest.uuid
$appName = [string]$manifest.name
$appFolderId = Split-Path -Leaf (Split-Path -Parent $projectRootPath)
if (-not $appId -or $appId -ne $appFolderId) {
    throw "package.json 的 uuid 与应用编号文件夹不一致。uuid=$appId；文件夹=$appFolderId"
}
if (-not $appName) { throw 'package.json 缺少应用名称。' }

$source = @'
using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;

internal static class SigstoreRepair
{
    private static readonly List<string> ProbeDirectories = new List<string>();

    private static Assembly ResolveAssembly(object sender, ResolveEventArgs args)
    {
        string name = new AssemblyName(args.Name).Name;
        foreach (string directory in ProbeDirectories)
        {
            string candidate = Path.Combine(directory, name + ".dll");
            if (File.Exists(candidate)) return Assembly.LoadFrom(candidate);
        }
        return null;
    }

    private static Type RequiredType(Assembly assembly, string name)
    {
        Type type = assembly.GetType(name, false);
        if (type == null) throw new MissingMemberException("Runtime type unavailable: " + name);
        return type;
    }

    private static void SetProperty(Type type, object instance, string name, string value)
    {
        PropertyInfo property = type.GetProperty(name, BindingFlags.Public | BindingFlags.Instance);
        if (property == null || !property.CanWrite)
            throw new MissingMemberException("Runtime property unavailable: " + type.FullName + "." + name);
        property.SetValue(instance, value, null);
    }

    private static bool Check(MethodInfo test, object package)
    {
        object result = test.Invoke(null, new object[] { package });
        if (!(result is bool)) throw new InvalidOperationException("Signature check did not return a Boolean.");
        return (bool)result;
    }

    private static int Run(string[] args)
    {
        if (args.Length != 5 || (args[4] != "write" && args[4] != "check"))
            throw new ArgumentException("Expected: runtimePath projectDir uuid name check|write");

        string runtimePath = Path.GetFullPath(args[0]);
        string projectDir = Path.GetFullPath(args[1]).TrimEnd(Path.DirectorySeparatorChar);
        string runtimeDir = Path.GetDirectoryName(runtimePath);
        ProbeDirectories.Add(runtimeDir);
        ProbeDirectories.Add(Path.Combine(runtimeDir, "support_x64", "ProcessLauncher"));
        AppDomain.CurrentDomain.AssemblyResolve += ResolveAssembly;

        // Framework assemblies come from the host's runtimeconfig. Private
        // ShadowBot dependencies are resolved from this exact runtime version.
        Assembly assembly = Assembly.LoadFrom(runtimePath);
        Console.WriteLine("runtime=" + runtimePath);
        Type appInfoType = RequiredType(assembly, "ShadowBot.Runtime.Packages.PackageAppInfo");
        Type packageType = RequiredType(assembly, "ShadowBot.Runtime.Packages.Package");
        Type helperType = RequiredType(assembly, "ShadowBot.Runtime.Packages.PackageHelper");

        ConstructorInfo constructor = packageType.GetConstructor(new Type[] {
            typeof(string), appInfoType, typeof(bool?), typeof(string), typeof(bool)
        });
        MethodInfo test = helperType.GetMethod("TestPackageSigstore",
            BindingFlags.Public | BindingFlags.Static, null, new Type[] { packageType }, null);
        MethodInfo write = helperType.GetMethod("WritePackageSigstore",
            BindingFlags.Public | BindingFlags.Static, null, new Type[] { packageType }, null);
        if (constructor == null || test == null || test.ReturnType != typeof(bool) || write == null)
            throw new MissingMethodException("Installed Runtime does not expose the expected signature API. No signature written.");

        object appInfo = Activator.CreateInstance(appInfoType);
        SetProperty(appInfoType, appInfo, "AppId", args[2]);
        SetProperty(appInfoType, appInfo, "Name", args[3]);
        object package = constructor.Invoke(new object[] {
            Directory.GetParent(projectDir).FullName, appInfo, null,
            Path.GetFileName(projectDir), false
        });

        bool before = Check(test, package);
        Console.WriteLine("before=" + before);
        if (before)
        {
            Console.WriteLine("RESULT=ALREADY_VALID");
            return 0;
        }
        if (args[4] != "write")
        {
            Console.WriteLine("RESULT=INVALID_SIGNATURE");
            return 0;
        }

        string sigstorePath = Path.Combine(projectDir, "package.sigstore");
        bool hadSignature = File.Exists(sigstorePath);
        string backupPath = null;
        if (hadSignature)
        {
            string backupDir = Path.Combine(Directory.GetParent(projectDir).FullName, "signature-backups");
            Directory.CreateDirectory(backupDir);
            backupPath = Path.Combine(backupDir, "package.sigstore." +
                DateTime.Now.ToString("yyyyMMdd-HHmmss-fff") + "." +
                Guid.NewGuid().ToString("N").Substring(0, 8) + ".bak");
            File.Copy(sigstorePath, backupPath, false);
            Console.WriteLine("backup=" + backupPath);
        }

        try
        {
            write.Invoke(null, new object[] { package });
            bool after = Check(test, package);
            Console.WriteLine("after=" + after);
            if (!after) throw new InvalidOperationException("Rebuilt signature did not pass the Runtime check.");
        }
        catch (Exception repairError)
        {
            try
            {
                if (hadSignature) File.Copy(backupPath, sigstorePath, true);
                else if (File.Exists(sigstorePath)) File.Delete(sigstorePath);
                Console.WriteLine("rollback=RestoredOriginalSignature");
            }
            catch (Exception rollbackError)
            {
                throw new AggregateException("Signature repair and rollback failed. Backup: " + backupPath,
                    repairError, rollbackError);
            }
            throw;
        }

        Console.WriteLine("RESULT=REPAIRED");
        return 0;
    }

    public static int Main(string[] args)
    {
        try { return Run(args); }
        catch (Exception error)
        {
            while (error is TargetInvocationException && error.InnerException != null)
                error = error.InnerException;
            Console.Error.WriteLine("RESULT=ERROR");
            Console.Error.WriteLine(error.ToString());
            return 1;
        }
    }
}
'@

$tempDir = Join-Path $env:TEMP ('shadowbot-sigstore-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tempDir | Out-Null
try {
    $sourcePath = Join-Path $tempDir 'SigstoreRepair.cs'
    $assemblyPath = Join-Path $tempDir 'SigstoreRepair.dll'
    $source | Set-Content -LiteralPath $sourcePath -Encoding UTF8
    & $compilerPath /nologo /target:exe /platform:x64 /optimize+ "/out:$assemblyPath" $sourcePath
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $assemblyPath)) {
        throw '辅助程序编译失败，未执行签名重建。'
    }

    Write-Host "runtime_config=$runtimeConfigPath"
    $mode = if ($Write) { 'write' } else { 'check' }
    & $dotnetPath exec --runtimeconfig $runtimeConfigPath $assemblyPath $runtimePathFull $projectRootPath $appId $appName $mode
    if ($LASTEXITCODE -ne 0) {
        throw '签名处理未成功。请把上方完整输出发回，先保留当前文件。'
    }
} finally {
    Remove-Item -LiteralPath $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}
