# Phase 5 - Start Agentic Career Platform (experimental workspace)
# Preserves frozen deterministic engine; does not auto-apply to jobs.

$ErrorActionPreference = "Stop"
$PlatformRoot = $PSScriptRoot
Set-Location $PlatformRoot

# Prefer platform venv, then repo-root venv
$VenvCandidates = @(
    (Join-Path $PlatformRoot "venv\Scripts\Activate.ps1"),
    (Join-Path $PlatformRoot "..\venv\Scripts\Activate.ps1")
)
foreach ($activate in $VenvCandidates) {
    if (Test-Path $activate) {
        Write-Host "Activating virtual environment: $activate"
        . $activate
        break
    }
}

# Embedded engine + agent modules resolve from platform root
$env:PYTHONPATH = $PlatformRoot

Write-Host "Initializing application queue storage..."
$InitPython = @'
from applications.application_queue import ApplicationQueue
from memory.application_memory import ApplicationMemory
from review_queue_manager import ReviewQueueManager
from memory.decision_memory import DecisionMemory
from application_workspace.review_manager import ApplicationReviewManager
from application_tracking.tracker import ApplicationTracker

ApplicationQueue().initialize()
ApplicationMemory().initialize()
ReviewQueueManager().initialize()
DecisionMemory().initialize()
ApplicationReviewManager().initialize()
ApplicationTracker().initialize()
'@
python -c $InitPython

$UiPath = Join-Path $PlatformRoot "Home.py"
$VersionPy = @'
from version import __version__, BUILD_INFO
print(__version__, BUILD_INFO.get("release", ""))
'@
$verLine = python -c $VersionPy 2>$null
if ($verLine) { Write-Host "Career Agent Platform $verLine" }
Write-Host "Starting Streamlit UI (Recommendations, Market, Workspace, Dashboard)..."
Write-Host "  $UiPath"
Write-Host "  PYTHONPATH=$env:PYTHONPATH"
streamlit run $UiPath
