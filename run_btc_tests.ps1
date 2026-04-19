param(
    [ValidateSet("btc", "eth")]
    [string]$Target = "btc"
)

$python = "C:\Users\elias\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if (-not (Test-Path $python)) {
    throw "Python runtime not found at $python"
}

$scriptMap = @{
    btc = "scripts\btc_signal.py"
    eth = "scripts\eth_signal.py"
}

& $python $scriptMap[$Target]
