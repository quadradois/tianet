[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$EnvelopePath,

    [string]$RepositoryRoot,

    [string]$OpenCodeCommand = 'opencode',

    [string]$TelemetryPath,

    [switch]$DisableTelemetry
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding

function Write-FailureAndExit {
    param(
        [string]$Code,
        [string]$Message,
        [int]$ExitCode = 2
    )

    [pscustomobject]@{
        succeeded = $false
        errorCode = $Code
        message = $Message
    } | ConvertTo-Json -Depth 5
    exit $ExitCode
}

function Invoke-GitCapture {
    param(
        [string]$Root,
        [string[]]$Arguments
    )

    # O Git usa stderr para avisos nao fatais, como conversao CRLF/LF. Com
    # ErrorActionPreference=Stop, alguns hosts PowerShell transformam esse aviso
    # em excecao antes de podermos observar o exit code real.
    $previousErrorPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = @(& git -C $Root @Arguments 2>$null)
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousErrorPreference
    }
    return [pscustomobject]@{
        Output = @($output)
        ExitCode = $exitCode
    }
}

function Get-RepositorySnapshot {
    param([string]$Root)

    $filesResult = Invoke-GitCapture -Root $Root -Arguments @('ls-files', '--cached', '--others', '--exclude-standard')
    if ($filesResult.ExitCode -ne 0) {
        throw 'Não foi possível enumerar o working tree com Git.'
    }
    $relativePaths = @($filesResult.Output)

    $snapshot = @{}
    foreach ($relativePath in $relativePaths) {
        $normalized = $relativePath.Replace('\', '/')
        $absolutePath = Join-Path $Root $relativePath
        if (Test-Path -LiteralPath $absolutePath -PathType Leaf) {
            $stream = [System.IO.File]::OpenRead($absolutePath)
            $hasher = [System.Security.Cryptography.SHA256]::Create()
            try {
                $snapshot[$normalized] = [System.BitConverter]::ToString($hasher.ComputeHash($stream)).Replace('-', '')
            } finally {
                $hasher.Dispose()
                $stream.Dispose()
            }
        } else {
            $snapshot[$normalized] = '<missing>'
        }
    }
    $indexResult = Invoke-GitCapture -Root $Root -Arguments @('ls-files', '--stage')
    if ($indexResult.ExitCode -ne 0) {
        throw 'Não foi possível capturar o índice Git.'
    }
    $indexState = @($indexResult.Output) -join "`n"
    $worktreeResult = Invoke-GitCapture -Root $Root -Arguments @('diff', '--raw', '--no-ext-diff')
    if ($worktreeResult.ExitCode -ne 0) {
        throw 'Não foi possível capturar o estado versionável do working tree.'
    }
    $worktreeState = @($worktreeResult.Output) -join "`n"
    $headResult = Invoke-GitCapture -Root $Root -Arguments @('rev-parse', '--verify', 'HEAD')
    $headState = @($headResult.Output)
    if ($headResult.ExitCode -ne 0) {
        $headState = @('<unborn>')
    }
    return [pscustomobject]@{
        Files = $snapshot
        IndexState = $indexState
        WorktreeState = ($worktreeState -join "`n")
        HeadState = ($headState -join "`n")
    }
}

function Compare-RepositorySnapshot {
    param(
        [hashtable]$Before,
        [hashtable]$After
    )

    $allPaths = @($Before.Keys) + @($After.Keys) | Sort-Object -Unique
    $changed = [System.Collections.Generic.List[string]]::new()
    foreach ($path in $allPaths) {
        $beforeValue = if ($Before.ContainsKey($path)) { $Before[$path] } else { '<absent>' }
        $afterValue = if ($After.ContainsKey($path)) { $After[$path] } else { '<absent>' }
        if ($beforeValue -ne $afterValue) {
            $changed.Add($path)
        }
    }
    return @($changed)
}

function Test-AllowedPath {
    param(
        [string]$Path,
        [object[]]$AllowedPaths
    )

    $candidate = $Path.Replace('\', '/').TrimStart('./')
    foreach ($allowedPathValue in $AllowedPaths) {
        $allowed = ([string]$allowedPathValue).Replace('\', '/').Trim().TrimStart('./').TrimEnd('/')
        if ([string]::IsNullOrWhiteSpace($allowed)) {
            continue
        }
        if ($candidate -eq $allowed -or $candidate.StartsWith("$allowed/", [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }
    return $false
}

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

if (-not (Test-Path -LiteralPath $EnvelopePath -PathType Leaf)) {
    Write-FailureAndExit -Code 'ENVELOPE_NOT_FOUND' -Message 'O arquivo de envelope não existe.'
}

if ([string]::IsNullOrWhiteSpace($RepositoryRoot)) {
    $RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} elseif (Test-Path -LiteralPath $RepositoryRoot -PathType Container) {
    $RepositoryRoot = (Resolve-Path -LiteralPath $RepositoryRoot).Path
} else {
    Write-FailureAndExit -Code 'REPOSITORY_NOT_FOUND' -Message 'A raiz do repositório não existe.'
}

try {
    $rawEnvelope = [System.IO.File]::ReadAllText((Resolve-Path -LiteralPath $EnvelopePath).Path, [System.Text.UTF8Encoding]::new($false))
    $envelope = $rawEnvelope | ConvertFrom-Json
} catch {
    Write-FailureAndExit -Code 'INVALID_ENVELOPE_JSON' -Message 'O envelope não contém JSON válido.'
}

$requiredFields = @(
    'schemaVersion', 'taskId', 'attempt', 'workflow', 'classification', 'objective',
    'nonObjectives', 'plan', 'slice', 'allowedPaths', 'knownBaseline', 'acceptance',
    'checks', 'allowedCommands', 'prohibitions', 'model', 'agent', 'returnFormat',
    'dataClassification'
)
foreach ($field in $requiredFields) {
    if (-not ($envelope.PSObject.Properties.Name -contains $field)) {
        Write-FailureAndExit -Code 'MISSING_FIELD' -Message "Campo obrigatório ausente: $field"
    }
}

$workflowValues = @('discover', 'architect', 'plan', 'execute', 'verify')
$classificationValues = @('TRIVIAL', 'SMALL', 'STANDARD', 'SUBSTANTIAL', 'ARCHITECTURAL')
if (-not ($envelope.schemaVersion -is [int] -or $envelope.schemaVersion -is [long])) {
    Write-FailureAndExit -Code 'INVALID_FIELD_TYPE' -Message 'schemaVersion deve ser inteiro.'
}
if (-not ($envelope.attempt -is [int] -or $envelope.attempt -is [long])) {
    Write-FailureAndExit -Code 'INVALID_FIELD_TYPE' -Message 'attempt deve ser inteiro.'
}
if (@(1, 2) -notcontains [int]$envelope.schemaVersion) {
    Write-FailureAndExit -Code 'UNSUPPORTED_SCHEMA' -Message 'A versão do schema deve ser 1 ou 2.'
}
if ([int]$envelope.schemaVersion -eq 2) {
    foreach ($field in @('agenticImpact', 'agenticTriggers', 'specialistRole', 'mutationPolicy')) {
        if (-not ($envelope.PSObject.Properties.Name -contains $field)) {
            Write-FailureAndExit -Code 'MISSING_FIELD' -Message "Campo obrigatório ausente no schema 2: $field"
        }
    }

    $agenticImpact = [string]$envelope.agenticImpact
    $specialistRole = [string]$envelope.specialistRole
    $mutationPolicy = [string]$envelope.mutationPolicy
    $agenticTriggers = @($envelope.agenticTriggers)
    if (-not ($envelope.agenticTriggers -is [System.Array]) -or @($agenticTriggers | Where-Object { -not ($_ -is [string]) }).Count -gt 0) {
        Write-FailureAndExit -Code 'INVALID_FIELD_TYPE' -Message 'agenticTriggers deve ser array de strings.'
    }
    if (@('NONE', 'PRESENT') -notcontains $agenticImpact) {
        Write-FailureAndExit -Code 'INVALID_AGENTIC_IMPACT' -Message 'agenticImpact deve ser NONE ou PRESENT.'
    }
    if (@('READ_ONLY', 'SCOPED_WRITE') -notcontains $mutationPolicy) {
        Write-FailureAndExit -Code 'INVALID_MUTATION_POLICY' -Message 'mutationPolicy deve ser READ_ONLY ou SCOPED_WRITE.'
    }
    if (@($agenticTriggers | Where-Object { [string]::IsNullOrWhiteSpace([string]$_) }).Count -gt 0) {
        Write-FailureAndExit -Code 'INVALID_AGENTIC_CONTRACT' -Message 'Gatilhos agentic não podem ser vazios.'
    }
    if ($agenticImpact -eq 'NONE' -and ($agenticTriggers.Count -gt 0 -or -not [string]::IsNullOrWhiteSpace($specialistRole))) {
        Write-FailureAndExit -Code 'INVALID_AGENTIC_CONTRACT' -Message 'NONE não admite gatilhos ou papel especialista.'
    }
    if ($agenticImpact -eq 'PRESENT' -and ($agenticTriggers.Count -eq 0 -or $specialistRole -ne 'ai_architect')) {
        Write-FailureAndExit -Code 'INVALID_AGENTIC_CONTRACT' -Message 'PRESENT exige gatilhos e specialistRole ai_architect.'
    }
    if ($specialistRole -eq 'ai_architect' -and ([string]$envelope.workflow -ne 'architect' -or [string]$envelope.agent -ne 'plan' -or $mutationPolicy -ne 'READ_ONLY')) {
        Write-FailureAndExit -Code 'INVALID_SPECIALIST_CONTRACT' -Message 'ai_architect exige workflow architect, agent plan e mutationPolicy READ_ONLY.'
    }
}
$parsedTaskId = [guid]::Empty
if (-not [guid]::TryParse([string]$envelope.taskId, [ref]$parsedTaskId) -or $parsedTaskId -eq [guid]::Empty) {
    Write-FailureAndExit -Code 'INVALID_TASK_ID' -Message 'taskId deve ser um UUID não vazio.'
}
if ([int]$envelope.attempt -lt 1 -or [int]$envelope.attempt -gt 3) {
    Write-FailureAndExit -Code 'ATTEMPT_LIMIT' -Message 'attempt deve estar entre 1 e 3; não existe terceira correção automática.'
}
if ($workflowValues -notcontains [string]$envelope.workflow) {
    Write-FailureAndExit -Code 'INVALID_WORKFLOW' -Message 'workflow inválido.'
}
if ($classificationValues -notcontains [string]$envelope.classification) {
    Write-FailureAndExit -Code 'INVALID_CLASSIFICATION' -Message 'classification inválida.'
}
if (@('plan', 'build') -notcontains [string]$envelope.agent) {
    Write-FailureAndExit -Code 'INVALID_AGENT' -Message 'agent deve ser plan ou build.'
}
if ([string]$envelope.dataClassification -ne 'REPOSITORY_NO_SECRETS') {
    Write-FailureAndExit -Code 'INVALID_DATA_CLASSIFICATION' -Message 'A classificação de dados obrigatória não foi declarada.'
}
if ([string]::IsNullOrWhiteSpace([string]$envelope.objective) -or
    [string]::IsNullOrWhiteSpace([string]$envelope.model) -or
    [string]::IsNullOrWhiteSpace([string]$envelope.returnFormat) -or
    @($envelope.allowedPaths).Count -eq 0 -or
    @($envelope.acceptance).Count -eq 0 -or
    @($envelope.checks).Count -eq 0 -or
    @($envelope.prohibitions).Count -eq 0) {
    Write-FailureAndExit -Code 'EMPTY_REQUIRED_VALUE' -Message 'O envelope contém valor obrigatório vazio.'
}

$secretPatterns = @(
    '-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    '\bsk-(?:or-v1-)?[A-Za-z0-9_-]{16,}\b',
    '\bgh[pousr]_[A-Za-z0-9]{20,}\b',
    '(?i)\b(?:password|secret|token|api[_-]?key)\s*[:=]\s*["''][^"'']{8,}["'']'
)
foreach ($pattern in $secretPatterns) {
    if ($rawEnvelope -match $pattern) {
        Write-FailureAndExit -Code 'POSSIBLE_SECRET' -Message 'O envelope parece conter um segredo e não será enviado.'
    }
}

if ([string]::IsNullOrWhiteSpace($TelemetryPath)) {
    if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        Write-FailureAndExit -Code 'LOCAL_APP_DATA_UNAVAILABLE' -Message 'LOCALAPPDATA não está disponível para telemetria local.'
    }
    $TelemetryPath = Join-Path $env:LOCALAPPDATA 'TiaNet\engineering-telemetry\opencode-events.jsonl'
}

try {
    $before = Get-RepositorySnapshot -Root $RepositoryRoot
} catch {
    Write-FailureAndExit -Code 'BASELINE_FAILED' -Message $_.Exception.Message
}

$prompt = @"
Execute somente a tarefa descrita no envelope JSON abaixo. Respeite caminhos, comandos, proibições, aceite e formato. Não feche gates, não amplie escopo, não faça commit, push, publicação, produção ou limpeza do working tree. Se houver impedimento, pare e reporte o bloqueio.

$rawEnvelope
"@

$startedAt = [DateTimeOffset]::UtcNow
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$responseLines = @()
$providerExitCode = 0
try {
    if (Test-Path -LiteralPath $OpenCodeCommand -PathType Leaf) {
        $resolvedOpenCodeCommand = (Resolve-Path -LiteralPath $OpenCodeCommand).Path
    } else {
        $resolvedCommand = Get-Command -Name $OpenCodeCommand -ErrorAction Stop
        $resolvedOpenCodeCommand = $resolvedCommand.Source
    }
    Push-Location -LiteralPath $RepositoryRoot
    try {
        $previousErrorPreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        # Prompt segue por stdin. No Windows, encaminhar JSON multiline como
        # argumento pode chegar vazio ou truncado ao shim npm, que entao apenas
        # imprime a ajuda do `opencode run`.
        $responseLines = @($prompt | & $resolvedOpenCodeCommand run --model ([string]$envelope.model) --agent ([string]$envelope.agent) 2>&1)
        $providerExitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousErrorPreference
        Pop-Location
    }
} catch {
    $responseLines = @($_.Exception.Message)
    $providerExitCode = 127
}
$stopwatch.Stop()

$after = Get-RepositorySnapshot -Root $RepositoryRoot
$changedPaths = @(Compare-RepositorySnapshot -Before $before.Files -After $after.Files)
$repositoryStateViolations = [System.Collections.Generic.List[string]]::new()
if ($before.IndexState -ne $after.IndexState) {
    $repositoryStateViolations.Add('<git-index>')
}
if ($before.HeadState -ne $after.HeadState) {
    $repositoryStateViolations.Add('<git-head>')
}
if ($before.WorktreeState -ne $after.WorktreeState -and $changedPaths.Count -eq 0) {
    $repositoryStateViolations.Add('<git-worktree-state>')
}
$mutationPolicy = if ([int]$envelope.schemaVersion -eq 2) { [string]$envelope.mutationPolicy } else { 'SCOPED_WRITE' }
$violations = if ($mutationPolicy -eq 'READ_ONLY') {
    @($changedPaths) + @($repositoryStateViolations)
} else {
    @($changedPaths | Where-Object { -not (Test-AllowedPath -Path $_ -AllowedPaths @($envelope.allowedPaths)) }) + @($repositoryStateViolations)
}
$executionOutcome = if ($providerExitCode -ne 0) { 'BLOQUEADA' } elseif ($violations.Count -gt 0) { 'BLOQUEADA' } else { 'EM_REVIEW' }
$reasonCode = if ($providerExitCode -ne 0) { 'PROVIDER_ERROR' } elseif ($mutationPolicy -eq 'READ_ONLY' -and $violations.Count -gt 0) { 'READ_ONLY_VIOLATION' } elseif ($violations.Count -gt 0) { 'SCOPE_VIOLATION' } else { 'NONE' }
$fallbackFrom = if ($envelope.PSObject.Properties.Name -contains 'fallbackFrom' -and -not [string]::IsNullOrWhiteSpace([string]$envelope.fallbackFrom)) { [string]$envelope.fallbackFrom } else { $null }
$agenticImpact = if ([int]$envelope.schemaVersion -eq 2) { [string]$envelope.agenticImpact } else { $null }
$specialistRole = if ([int]$envelope.schemaVersion -eq 2 -and -not [string]::IsNullOrWhiteSpace([string]$envelope.specialistRole)) { [string]$envelope.specialistRole } else { $null }
$triggerCount = if ([int]$envelope.schemaVersion -eq 2) { @($envelope.agenticTriggers).Count } else { 0 }

if (-not $DisableTelemetry) {
    $event = @{
        schema_version = 1
        event_id = ([guid]::NewGuid().ToString())
        task_id = $parsedTaskId.ToString()
        occurred_at_utc = $startedAt.ToString('o')
        event_type = 'EXECUTION'
        workflow = [string]$envelope.workflow
        classification = [string]$envelope.classification
        model = [string]$envelope.model
        fallback_from = $fallbackFrom
        attempt = [int]$envelope.attempt
        duration_ms = [long]$stopwatch.ElapsedMilliseconds
        exit_code = [int]$providerExitCode
        outcome = $executionOutcome
        reason_code = $reasonCode
        checks_passed = 0
        checks_failed = 0
        checks_not_run = @($envelope.checks).Count
        files_changed = $changedPaths.Count
        lines_added = $null
        lines_removed = $null
        tokens = $null
        cost = $null
        agentic_impact = $agenticImpact
        specialist_role = $specialistRole
        trigger_count = $triggerCount
    }
    try {
        Add-TelemetryLine -Path $TelemetryPath -Event $event
    } catch {
        Write-FailureAndExit -Code 'TELEMETRY_WRITE_FAILED' -Message $_.Exception.Message
    }
}

$result = [pscustomobject]@{
    succeeded = ($providerExitCode -eq 0 -and $violations.Count -eq 0)
    taskId = $parsedTaskId.ToString()
    attempt = [int]$envelope.attempt
    model = [string]$envelope.model
    outcome = $executionOutcome
    reasonCode = $reasonCode
    exitCode = [int]$providerExitCode
    durationMs = [long]$stopwatch.ElapsedMilliseconds
    changedPaths = @($changedPaths)
    scopeViolations = @($violations)
    mutationPolicy = $mutationPolicy
    response = ($responseLines -join [Environment]::NewLine)
}
$result | ConvertTo-Json -Depth 8

if ($providerExitCode -ne 0) {
    exit $providerExitCode
}
if ($violations.Count -gt 0) {
    exit 3
}
exit 0
