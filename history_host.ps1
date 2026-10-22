# Copyright (c) 2026 RayRayElite
# SPDX-License-Identifier: MIT
# Independent STA host: a history/UI failure must not terminate ComicRack.
param([Parameter(Mandatory=$true)][string]$RequestPath, [ValidateSet('', 'close', 'retest', 'fail')][string]$SelfTest = '')
$ErrorActionPreference = 'Stop'
try {
    $pluginRoot = $PSScriptRoot
    $sessionRoot = [IO.Path]::GetFullPath((Join-Path $pluginRoot 'Reports/HistorySessions')).TrimEnd('\')
    $resolvedRequest = [IO.Path]::GetFullPath($RequestPath)
    if ([IO.Path]::GetDirectoryName($resolvedRequest) -ne $sessionRoot -or [IO.Path]::GetFileName($resolvedRequest) -notmatch '^[0-9a-f]{32}\.request\.xml$') { throw 'Invalid history session request path.' }
    $document = New-Object System.Xml.XmlDocument
    $document.XmlResolver = $null
    $document.Load($resolvedRequest)
    $runtime = $document.DocumentElement.GetAttribute('runtime')
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    [System.Windows.Forms.Application]::EnableVisualStyles()
    foreach ($dll in @('Microsoft.Scripting.dll', 'Microsoft.Dynamic.dll', 'IronPython.dll')) {
        [Reflection.Assembly]::Load([IO.File]::ReadAllBytes((Join-Path $runtime $dll))) | Out-Null
    }
    [AppDomain]::CurrentDomain.add_AssemblyResolve({ param($sender, $eventArgs)
        $assemblyPath = Join-Path $runtime (($eventArgs.Name.Split(',')[0]) + '.dll')
        if ([IO.File]::Exists($assemblyPath)) { return [Reflection.Assembly]::Load([IO.File]::ReadAllBytes($assemblyPath)) }
        return $null
    })
    $engine = [IronPython.Hosting.Python]::CreateEngine()
    $scope = $engine.CreateScope()
    $scope.SetVariable('plugin_path', [string](Join-Path $pluginRoot 'WebPOptimizer.py'))
    $scope.SetVariable('plugin_source', [IO.File]::ReadAllText((Join-Path $pluginRoot 'WebPOptimizer.py')))
    $engine.Execute("__file__ = plugin_path`nexec compile(plugin_source, str(__file__), 'exec')", $scope) | Out-Null
    $scope.SetVariable('history_request', $resolvedRequest)
    $scope.SetVariable('history_self_test', $SelfTest)
    $engine.Execute([IO.File]::ReadAllText((Join-Path $pluginRoot 'history_host.py')), $scope) | Out-Null
    $engine.Execute('_history_host_main(history_request, history_self_test)', $scope) | Out-Null
    exit 0
} catch {
    [Console]::Error.WriteLine($_.Exception.ToString())
    exit 1
}
