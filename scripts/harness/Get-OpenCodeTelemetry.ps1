[CmdletBinding()]
param(
    [string]$TelemetryPath
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding

function Get-Percentile {
    param(
        [object[]]$Values,
        [double]$Percentile
    )

    $numbers = @($Values | Where-Object { $null -ne $_ } | ForEach-Object { [double]$_ } | Sort-Object)
    if ($numbers.Count -eq 0) {
        return $null
    }
    $index = [Math]::Ceiling($Percentile * $numbers.Count) - 1
    $index = [Math]::Max(0, [Math]::Min($numbers.Count - 1, $index))
    return [long]$numbers[$index]
}

if ([string]::IsNullOrWhiteSpace($TelemetryPath)) {
    if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        throw 'LOCALAPPDATA não está disponível para telemetria local.'
    }
    $TelemetryPath = Join-Path $env:LOCALAPPDATA 'TiaNet\engineering-telemetry\opencode-events.jsonl'
}

if (-not (Test-Path -LiteralPath $TelemetryPath -PathType Leaf)) {
    [pscustomobject]@{
        telemetryPath = $TelemetryPath
        exists = $false
        validEvents = 0
        invalidLines = 0
        tasks = 0
        executions = 0
        reviews = 0
        approvalFirstAttemptRate = $null
        byModel = @()
        byWorkflow = @()
        reasonCodes = @()
        agentic = [pscustomobject]@{
            events = 0
            specialistReviews = 0
            blockerVerdicts = 0
            materialFindings = 0
        }
    } | ConvertTo-Json -Depth 8
    exit 0
}

$events = [System.Collections.Generic.List[object]]::new()
$invalidLines = 0
foreach ($line in [System.IO.File]::ReadLines($TelemetryPath, [System.Text.UTF8Encoding]::new($false))) {
    if ([string]::IsNullOrWhiteSpace($line)) {
        continue
    }
    try {
        $event = $line | ConvertFrom-Json
        $required = @('schema_version', 'event_id', 'task_id', 'event_type', 'workflow', 'classification', 'model', 'attempt', 'outcome', 'reason_code')
        $missing = @($required | Where-Object { -not ($event.PSObject.Properties.Name -contains $_) })
        if ($event.schema_version -ne 1 -or $missing.Count -gt 0 -or @('EXECUTION', 'REVIEW') -notcontains [string]$event.event_type) {
            $invalidLines++
            continue
        }
        $events.Add($event)
    } catch {
        $invalidLines++
    }
}

$executions = @($events | Where-Object { $_.event_type -eq 'EXECUTION' })
$reviews = @($events | Where-Object { $_.event_type -eq 'REVIEW' })
$firstAttemptReviews = @($reviews | Where-Object { [int]$_.attempt -eq 1 })
$approvedFirstAttempt = @($firstAttemptReviews | Where-Object { $_.outcome -eq 'APROVADA' }).Count
$approvalRate = if ($firstAttemptReviews.Count -eq 0) { $null } else { [Math]::Round(($approvedFirstAttempt * 100.0) / $firstAttemptReviews.Count, 2) }

$byModel = @($executions | Group-Object model | Sort-Object Name | ForEach-Object {
    $group = @($_.Group)
    [pscustomobject]@{
        model = $_.Name
        executions = $group.Count
        providerErrors = @($group | Where-Object { $_.reason_code -eq 'PROVIDER_ERROR' }).Count
        fallbacks = @($group | Where-Object { $null -ne $_.fallback_from -and -not [string]::IsNullOrWhiteSpace([string]$_.fallback_from) }).Count
        durationMedianMs = Get-Percentile -Values @($group.duration_ms) -Percentile 0.50
        durationP95Ms = Get-Percentile -Values @($group.duration_ms) -Percentile 0.95
    }
})

$byWorkflow = @($events | Group-Object workflow | Sort-Object Name | ForEach-Object {
    $group = @($_.Group)
    [pscustomobject]@{
        workflow = $_.Name
        events = $group.Count
        approved = @($group | Where-Object { $_.event_type -eq 'REVIEW' -and $_.outcome -eq 'APROVADA' }).Count
        corrections = @($group | Where-Object { $_.event_type -eq 'REVIEW' -and $_.outcome -eq 'CORREÇÃO' }).Count
        blocked = @($group | Where-Object { $_.event_type -eq 'REVIEW' -and $_.outcome -eq 'BLOQUEADA' }).Count
    }
})

$reasonCodes = @($events | Where-Object { $_.reason_code -ne 'NONE' } | Group-Object reason_code | Sort-Object Name | ForEach-Object {
    [pscustomobject]@{
        reasonCode = $_.Name
        count = $_.Count
    }
})
$agenticEvents = @($events | Where-Object { $_.PSObject.Properties.Name -contains 'agentic_impact' -and $_.agentic_impact -eq 'PRESENT' })
$specialistReviews = @($reviews | Where-Object { $_.PSObject.Properties.Name -contains 'specialist_role' -and $_.specialist_role -eq 'ai_architect' })

[pscustomobject]@{
    telemetryPath = $TelemetryPath
    exists = $true
    validEvents = $events.Count
    invalidLines = $invalidLines
    tasks = @($events.task_id | Sort-Object -Unique).Count
    executions = $executions.Count
    reviews = $reviews.Count
    approvalFirstAttemptRate = $approvalRate
    checks = [pscustomobject]@{
        passed = [long](($reviews | Measure-Object -Property checks_passed -Sum).Sum)
        failed = [long](($reviews | Measure-Object -Property checks_failed -Sum).Sum)
        notRun = [long](($reviews | Measure-Object -Property checks_not_run -Sum).Sum)
    }
    changeVolume = [pscustomobject]@{
        files = [long](($reviews | Measure-Object -Property files_changed -Sum).Sum)
        linesAdded = [long](($reviews | Where-Object { $null -ne $_.lines_added } | Measure-Object -Property lines_added -Sum).Sum)
        linesRemoved = [long](($reviews | Where-Object { $null -ne $_.lines_removed } | Measure-Object -Property lines_removed -Sum).Sum)
    }
    byModel = $byModel
    byWorkflow = $byWorkflow
    reasonCodes = $reasonCodes
    agentic = [pscustomobject]@{
        events = $agenticEvents.Count
        specialistReviews = $specialistReviews.Count
        blockerVerdicts = @($specialistReviews | Where-Object { $_.specialist_verdict -eq 'BLOCKER' }).Count
        materialFindings = [long](($specialistReviews | Where-Object { $null -ne $_.material_findings_count } | Measure-Object -Property material_findings_count -Sum).Sum)
    }
} | ConvertTo-Json -Depth 8
