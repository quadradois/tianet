[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$TaskId,

    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 3)]
    [int]$Attempt,

    [Parameter(Mandatory = $true)]
    [ValidateSet('discover', 'architect', 'plan', 'execute', 'verify')]
    [string]$Workflow,

    [Parameter(Mandatory = $true)]
    [ValidateSet('TRIVIAL', 'SMALL', 'STANDARD', 'SUBSTANTIAL', 'ARCHITECTURAL')]
    [string]$Classification,

    [Parameter(Mandatory = $true)]
    [string]$Model,

    [Parameter(Mandatory = $true)]
    [ValidateSet('APROVADA', 'CORREÇÃO', 'BLOQUEADA')]
    [string]$Outcome,

    [ValidateSet('NONE', 'ACCEPTANCE_FAILED', 'CHECK_FAILED', 'SCOPE_VIOLATION', 'READ_ONLY_VIOLATION', 'PROVIDER_ERROR', 'INSUFFICIENT_EVIDENCE', 'TASK_TOO_LARGE', 'PRIVACY_BLOCK', 'ENVIRONMENT_ERROR', 'OTHER')]
    [string]$ReasonCode = 'NONE',

    [ValidateRange(0, [int]::MaxValue)]
    [int]$ChecksPassed = 0,

    [ValidateRange(0, [int]::MaxValue)]
    [int]$ChecksFailed = 0,

    [ValidateRange(0, [int]::MaxValue)]
    [int]$ChecksNotRun = 0,

    [ValidateRange(0, [int]::MaxValue)]
    [int]$FilesChanged = 0,

    [Nullable[int]]$LinesAdded,

    [Nullable[int]]$LinesRemoved,

    [Nullable[int64]]$Tokens,

    [Nullable[decimal]]$Cost,

    [string]$FallbackFrom,

    [string]$TelemetryPath,

    [ValidateSet('NONE', 'PRESENT')]
    [string]$AgenticImpact = 'NONE',

    [ValidateSet('none', 'ai_architect')]
    [string]$SpecialistRole = 'none',

    [ValidateRange(0, [int]::MaxValue)]
    [int]$TriggerCount = 0,

    [ValidateSet('NONE', 'APPROVED', 'BLOCKER')]
    [string]$SpecialistVerdict = 'NONE',

    [ValidateRange(0, [int]::MaxValue)]
    [int]$MaterialFindingsCount = 0,

    [ValidateRange(0, [int]::MaxValue)]
    [int]$OpenBlockers = 0,

    [ValidateSet('NONE', 'CODEX', 'OWNER')]
    [string]$AdjudicationActor = 'NONE',

    [ValidateSet('NONE', 'TECHNICAL', 'MATERIAL')]
    [string]$AdjudicationScope = 'NONE'
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding

function Add-TelemetryLine {
    param(
        [string]$Path,
        [hashtable]$Event
    )

    $directory = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $directory)) {
        [void](New-Item -ItemType Directory -Path $directory -Force)
    }

    $json = ($Event | ConvertTo-Json -Compress -Depth 8) + [Environment]::NewLine
    $utf8 = [System.Text.UTF8Encoding]::new($false)
    $bytes = $utf8.GetBytes($json)
    $lastError = $null
    foreach ($tryNumber in 1..5) {
        try {
            $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Append, [System.IO.FileAccess]::Write, [System.IO.FileShare]::Read)
            try {
                $stream.Write($bytes, 0, $bytes.Length)
                $stream.Flush($true)
                return
            } finally {
                $stream.Dispose()
            }
        } catch [System.IO.IOException] {
            $lastError = $_
            Start-Sleep -Milliseconds (25 * $tryNumber)
        }
    }
    throw "Não foi possível acrescentar a telemetria: $($lastError.Exception.Message)"
}

$parsedTaskId = [guid]::Empty
if (-not [guid]::TryParse($TaskId, [ref]$parsedTaskId) -or $parsedTaskId -eq [guid]::Empty) {
    throw 'TaskId deve ser um UUID não vazio.'
}
if (($Outcome -eq 'APROVADA' -and $ReasonCode -ne 'NONE') -or ($Outcome -ne 'APROVADA' -and $ReasonCode -eq 'NONE')) {
    throw 'Outcome e ReasonCode são incompatíveis.'
}
if ($Outcome -eq 'APROVADA' -and ($ChecksFailed -gt 0 -or $ChecksNotRun -gt 0)) {
    throw 'Review aprovado exige zero checks falhos e zero checks pendentes.'
}
if (($AgenticImpact -eq 'NONE' -and ($SpecialistRole -ne 'none' -or $TriggerCount -gt 0 -or $SpecialistVerdict -ne 'NONE' -or $MaterialFindingsCount -gt 0 -or $OpenBlockers -gt 0 -or $AdjudicationActor -ne 'NONE' -or $AdjudicationScope -ne 'NONE')) -or
    ($AgenticImpact -eq 'PRESENT' -and ($SpecialistRole -ne 'ai_architect' -or $TriggerCount -eq 0 -or $SpecialistVerdict -eq 'NONE'))) {
    throw 'Metadados de revisão agentic são incompatíveis.'
}
if ($OpenBlockers -gt $MaterialFindingsCount) {
    throw 'OpenBlockers não pode exceder MaterialFindingsCount.'
}
if ($SpecialistVerdict -eq 'BLOCKER' -and $MaterialFindingsCount -eq 0) {
    throw 'Parecer BLOCKER exige ao menos um achado material.'
}
if ($SpecialistVerdict -ne 'BLOCKER' -and $OpenBlockers -gt 0) {
    throw 'Somente parecer BLOCKER pode declarar OpenBlockers.'
}
if ($SpecialistVerdict -ne 'BLOCKER' -and ($AdjudicationActor -ne 'NONE' -or $AdjudicationScope -ne 'NONE')) {
    throw 'Adjudicação só é aplicável a parecer BLOCKER.'
}
if (($AdjudicationActor -eq 'NONE') -ne ($AdjudicationScope -eq 'NONE')) {
    throw 'Ator e escopo de adjudicação devem ser informados juntos.'
}
if ($AdjudicationScope -eq 'MATERIAL' -and $AdjudicationActor -ne 'OWNER') {
    throw 'Adjudicação MATERIAL exige OWNER.'
}
if ($Outcome -eq 'APROVADA' -and $OpenBlockers -gt 0) {
    throw 'Review não pode ser aprovado com BLOCKER aberto.'
}
if ($SpecialistVerdict -eq 'BLOCKER' -and $Outcome -eq 'APROVADA' -and ($AdjudicationActor -eq 'NONE' -or $AdjudicationScope -eq 'NONE')) {
    throw 'Parecer BLOCKER exige adjudicação explícita antes de aprovação.'
}
if ($AdjudicationActor -ne 'NONE' -and $SpecialistRole -ne 'ai_architect') {
    throw 'Adjudicação especializada exige specialistRole ai_architect.'
}
foreach ($nullableValue in @($LinesAdded, $LinesRemoved, $Tokens, $Cost)) {
    if ($null -ne $nullableValue -and $nullableValue -lt 0) {
        throw 'Contagens e custo não podem ser negativos.'
    }
}
if ([string]::IsNullOrWhiteSpace($Model)) {
    throw 'Model é obrigatório.'
}
if ([string]::IsNullOrWhiteSpace($TelemetryPath)) {
    if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        throw 'LOCALAPPDATA não está disponível para telemetria local.'
    }
    $TelemetryPath = Join-Path $env:LOCALAPPDATA 'TiaNet\engineering-telemetry\opencode-events.jsonl'
}

$event = @{
    schema_version = 1
    event_id = ([guid]::NewGuid().ToString())
    task_id = $parsedTaskId.ToString()
    occurred_at_utc = [DateTimeOffset]::UtcNow.ToString('o')
    event_type = 'REVIEW'
    workflow = $Workflow
    classification = $Classification
    model = $Model
    fallback_from = if ([string]::IsNullOrWhiteSpace($FallbackFrom)) { $null } else { $FallbackFrom }
    attempt = $Attempt
    duration_ms = $null
    exit_code = $null
    outcome = $Outcome
    reason_code = $ReasonCode
    checks_passed = $ChecksPassed
    checks_failed = $ChecksFailed
    checks_not_run = $ChecksNotRun
    files_changed = $FilesChanged
    lines_added = if ($null -eq $LinesAdded) { $null } else { [int]$LinesAdded }
    lines_removed = if ($null -eq $LinesRemoved) { $null } else { [int]$LinesRemoved }
    tokens = if ($null -eq $Tokens) { $null } else { [int64]$Tokens }
    cost = if ($null -eq $Cost) { $null } else { [decimal]$Cost }
    agentic_impact = if ($AgenticImpact -eq 'NONE') { $null } else { $AgenticImpact }
    specialist_role = if ($SpecialistRole -eq 'none') { $null } else { $SpecialistRole }
    trigger_count = $TriggerCount
    specialist_verdict = if ($SpecialistVerdict -eq 'NONE') { $null } else { $SpecialistVerdict }
    material_findings_count = $MaterialFindingsCount
    open_blockers = $OpenBlockers
    adjudication_actor = if ($AdjudicationActor -eq 'NONE') { $null } else { $AdjudicationActor }
    adjudication_scope = if ($AdjudicationScope -eq 'NONE') { $null } else { $AdjudicationScope }
}

Add-TelemetryLine -Path $TelemetryPath -Event $event
[pscustomobject]@{
    recorded = $true
    eventId = $event.event_id
    taskId = $event.task_id
    outcome = $event.outcome
    telemetryPath = $TelemetryPath
} | ConvertTo-Json -Depth 4
