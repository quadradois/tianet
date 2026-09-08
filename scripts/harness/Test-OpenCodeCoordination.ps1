[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$invokeScript = Join-Path $PSScriptRoot 'Invoke-OpenCodeTask.ps1'
$reviewScript = Join-Path $PSScriptRoot 'Add-OpenCodeReview.ps1'
$reportScript = Join-Path $PSScriptRoot 'Get-OpenCodeTelemetry.ps1'
$script:Passes = 0
$script:Failures = [System.Collections.Generic.List[string]]::new()

function Add-TestResult {
    param([bool]$Succeeded, [string]$Message)
    if ($Succeeded) {
        $script:Passes++
        Write-Host "[PASS] $Message"
    } else {
        $script:Failures.Add($Message)
        Write-Host "[FAIL] $Message"
    }
}

function Invoke-ChildScript {
    param([string]$Path, [object[]]$Arguments)
    $previousErrorPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = @(& powershell -NoProfile -ExecutionPolicy Bypass -File $Path @Arguments 2>&1)
        $childExitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousErrorPreference
    }
    return [pscustomobject]@{
        ExitCode = $childExitCode
        Text = ($output -join [Environment]::NewLine)
    }
}

function New-Envelope {
    param(
        [string]$Path,
        [int]$Attempt = 1,
        [string[]]$AllowedPaths = @('allowed.txt'),
        [int]$SchemaVersion = 1,
        [string]$Classification = 'SMALL',
        [string]$Workflow = 'execute',
        [string]$Agent = 'build',
        [string]$AgenticImpact = 'NONE',
        [string[]]$AgenticTriggers = @(),
        [AllowNull()][string]$SpecialistRole = $null,
        [string]$MutationPolicy = 'SCOPED_WRITE'
    )
    $envelope = [ordered]@{
        schemaVersion = $SchemaVersion
        taskId = ([guid]::NewGuid().ToString())
        attempt = $Attempt
        workflow = $Workflow
        classification = $Classification
        objective = 'SENTINEL_PROMPT Execute a fixture controlada.'
        nonObjectives = @('Não toque outros arquivos.')
        plan = 'Plano de teste.'
        slice = 'fixture'
        allowedPaths = $AllowedPaths
        knownBaseline = 'preexisting.txt já existe e deve ser preservado.'
        acceptance = @('A resposta contém a sentinela prevista.')
        checks = @('Inspecionar a fixture.')
        allowedCommands = @('nenhum comando externo')
        prohibitions = @('Sem commit, push, publicação ou limpeza.')
        model = 'opencode/test-model'
        agent = $Agent
        returnFormat = 'Resumo curto.'
        dataClassification = 'REPOSITORY_NO_SECRETS'
    }
    if ($SchemaVersion -eq 2) {
        $envelope['agenticImpact'] = $AgenticImpact
        $envelope['agenticTriggers'] = $AgenticTriggers
        $envelope['specialistRole'] = $SpecialistRole
        $envelope['mutationPolicy'] = $MutationPolicy
    }
    [System.IO.File]::WriteAllText($Path, ($envelope | ConvertTo-Json -Depth 8), [System.Text.UTF8Encoding]::new($false))
    return $envelope
}

function Convert-ResultJson {
    param([string]$Text)
    try {
        return $Text | ConvertFrom-Json
    } catch {
        return $null
    }
}

$temporaryRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("tianet-opencode-test-" + [guid]::NewGuid().ToString('N'))
[void](New-Item -ItemType Directory -Path $temporaryRoot)
try {
    $fixtureRepo = Join-Path $temporaryRoot 'repo'
    [void](New-Item -ItemType Directory -Path $fixtureRepo)
    & git -C $fixtureRepo init --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar repositório de fixture.' }
    [System.IO.File]::WriteAllText((Join-Path $fixtureRepo 'tracked.txt'), 'base', [System.Text.UTF8Encoding]::new($false))
    & git -C $fixtureRepo add tracked.txt
    & git -C $fixtureRepo -c user.name=TiaNetTest -c user.email=tianet-test@example.invalid commit --quiet -m baseline
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar commit de fixture.' }
    & git -C $fixtureRepo config core.autocrlf true
    & git -C $fixtureRepo config core.safecrlf warn
    [System.IO.File]::WriteAllText((Join-Path $fixtureRepo 'tracked.txt'), "base`nlocal-change`n", [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText((Join-Path $fixtureRepo 'preexisting.txt'), 'user-state', [System.Text.UTF8Encoding]::new($false))

    $fakeOpenCode = Join-Path $temporaryRoot 'fake-opencode.ps1'
$fakeSource = @'
[CmdletBinding(PositionalBinding = $false)]
param(
    [Parameter(ValueFromPipeline = $true)]
    [AllowEmptyString()]
    [string]$PromptLine,

    [Parameter(ValueFromRemainingArguments = $true)]
    [object[]]$Remaining
)

begin {
    $receivedLines = [System.Collections.Generic.List[string]]::new()
}

process {
    [void]$receivedLines.Add($PromptLine)
}

end {
    $receivedPrompt = $receivedLines -join [Environment]::NewLine
    if ($receivedPrompt -notmatch 'SENTINEL_PROMPT') {
        [Console]::Error.WriteLine('prompt ausente no stdin')
        exit 19
    }
    $mode = $env:TIANET_OPENCODE_TEST_MODE
    if ($mode -eq 'provider-error') {
        [Console]::Error.WriteLine('SENTINEL_RESPONSE provider unavailable')
        exit 17
    }
    if ($mode -eq 'allowed-change') {
        [System.IO.File]::WriteAllText((Join-Path (Get-Location) 'allowed.txt'), 'allowed-change')
    }
    if ($mode -eq 'outside-change') {
        [System.IO.File]::WriteAllText((Join-Path (Get-Location) 'outside.txt'), 'outside-change')
    }
    if ($mode -eq 'stage-only') {
        & git add preexisting.txt
        exit $LASTEXITCODE
    }
    if ($mode -eq 'head-only') {
        & git -c user.name=TiaNetTest -c user.email=tianet-test@example.invalid commit --quiet --allow-empty -m test-head-change
        exit $LASTEXITCODE
    }
    Write-Output 'SENTINEL_RESPONSE fixture complete'
    exit 0
}
'@
    [System.IO.File]::WriteAllText($fakeOpenCode, $fakeSource, [System.Text.UTF8Encoding]::new($false))
    $fakeProviderError = Join-Path $temporaryRoot 'fake-provider-error.cmd'
    [System.IO.File]::WriteAllText($fakeProviderError, "@echo SENTINEL_RESPONSE provider unavailable 1>&2`r`n@exit /b 17`r`n", [System.Text.ASCIIEncoding]::new())

    $telemetryPath = Join-Path $temporaryRoot 'telemetry\events.jsonl'
    $envelopePath = Join-Path $temporaryRoot 'envelope.json'
    $envelope = New-Envelope -Path $envelopePath

    $env:TIANET_OPENCODE_TEST_MODE = 'read-only'
    $run = Invoke-ChildScript -Path $invokeScript -Arguments @('-EnvelopePath', $envelopePath, '-RepositoryRoot', $fixtureRepo, '-OpenCodeCommand', $fakeOpenCode, '-TelemetryPath', $telemetryPath)
    $result = Convert-ResultJson -Text $run.Text
    if ($run.ExitCode -ne 0) { throw "Fixture inicial falhou: $($run.Text)" }
    Add-TestResult ($run.ExitCode -eq 0 -and $null -ne $result -and $result.outcome -eq 'EM_REVIEW') 'execução read-only chega a EM_REVIEW'
    Add-TestResult ($result.response -match 'SENTINEL_RESPONSE') 'executor entrega o prompt por stdin'
    Add-TestResult ($run.Text -notmatch 'BASELINE_FAILED') 'aviso nao fatal do Git nao invalida baseline'
    Add-TestResult ((Get-Content -LiteralPath (Join-Path $fixtureRepo 'preexisting.txt') -Raw) -eq 'user-state') 'baseline preexistente é preservado'
    $telemetryText = Get-Content -LiteralPath $telemetryPath -Raw
    Add-TestResult (-not $telemetryText.Contains('SENTINEL_PROMPT') -and -not $telemetryText.Contains('SENTINEL_RESPONSE')) 'telemetria não persiste prompt ou resposta'

    $v2CommonPath = Join-Path $temporaryRoot 'v2-common.json'
    [void](New-Envelope -Path $v2CommonPath -SchemaVersion 2 -Classification 'STANDARD' -MutationPolicy 'READ_ONLY')
    $v2Common = Invoke-ChildScript -Path $invokeScript -Arguments @('-EnvelopePath', $v2CommonPath, '-RepositoryRoot', $fixtureRepo, '-OpenCodeCommand', $fakeOpenCode, '-TelemetryPath', $telemetryPath)
    $v2CommonResult = Convert-ResultJson -Text $v2Common.Text
    Add-TestResult ($v2Common.ExitCode -eq 0 -and $v2CommonResult.outcome -eq 'EM_REVIEW' -and $v2CommonResult.mutationPolicy -eq 'READ_ONLY') 'schema v2 comum aceita STANDARD e triagem NONE'

    $v2SpecialistPath = Join-Path $temporaryRoot 'v2-specialist.json'
    [void](New-Envelope -Path $v2SpecialistPath -SchemaVersion 2 -Classification 'ARCHITECTURAL' -Workflow 'architect' -Agent 'plan' -AgenticImpact 'PRESENT' -AgenticTriggers @('budget de chamadas') -SpecialistRole 'ai_architect' -MutationPolicy 'READ_ONLY')
    $v2Specialist = Invoke-ChildScript -Path $invokeScript -Arguments @('-EnvelopePath', $v2SpecialistPath, '-RepositoryRoot', $fixtureRepo, '-OpenCodeCommand', $fakeOpenCode, '-TelemetryPath', $telemetryPath)
    $v2SpecialistResult = Convert-ResultJson -Text $v2Specialist.Text
    Add-TestResult ($v2Specialist.ExitCode -eq 0 -and $v2SpecialistResult.outcome -eq 'EM_REVIEW') 'schema v2 aceita contrato válido do ai_architect'

    $v2MissingPath = Join-Path $temporaryRoot 'v2-missing.json'
    $v2Missing = New-Envelope -Path $v2MissingPath -SchemaVersion 2
    $v2Missing.Remove('mutationPolicy')
    [System.IO.File]::WriteAllText($v2MissingPath, ($v2Missing | ConvertTo-Json -Depth 8), [System.Text.UTF8Encoding]::new($false))
    $v2MissingRun = Invoke-ChildScript -Path $invokeScript -Arguments @('-EnvelopePath', $v2MissingPath, '-RepositoryRoot', $fixtureRepo, '-OpenCodeCommand', $fakeOpenCode, '-TelemetryPath', $telemetryPath)
    Add-TestResult ($v2MissingRun.ExitCode -eq 2 -and $v2MissingRun.Text.Contains('MISSING_FIELD')) 'schema v2 exige campos agentic e mutationPolicy'

    $v2InvalidNonePath = Join-Path $temporaryRoot 'v2-invalid-none.json'
    [void](New-Envelope -Path $v2InvalidNonePath -SchemaVersion 2 -SpecialistRole 'ai_architect')
    $v2InvalidNone = Invoke-ChildScript -Path $invokeScript -Arguments @('-EnvelopePath', $v2InvalidNonePath, '-RepositoryRoot', $fixtureRepo, '-OpenCodeCommand', $fakeOpenCode, '-TelemetryPath', $telemetryPath)
    Add-TestResult ($v2InvalidNone.ExitCode -eq 2 -and $v2InvalidNone.Text.Contains('INVALID_AGENTIC_CONTRACT')) 'NONE recusa papel especialista'

    $v2MissingSpecialistPath = Join-Path $temporaryRoot 'v2-missing-specialist.json'
    [void](New-Envelope -Path $v2MissingSpecialistPath -SchemaVersion 2 -AgenticImpact 'PRESENT' -AgenticTriggers @('modelo'))
    $v2MissingSpecialist = Invoke-ChildScript -Path $invokeScript -Arguments @('-EnvelopePath', $v2MissingSpecialistPath, '-RepositoryRoot', $fixtureRepo, '-OpenCodeCommand', $fakeOpenCode, '-TelemetryPath', $telemetryPath)
    Add-TestResult ($v2MissingSpecialist.ExitCode -eq 2 -and $v2MissingSpecialist.Text.Contains('INVALID_AGENTIC_CONTRACT')) 'PRESENT exige papel ai_architect'

    $v2InvalidTypePath = Join-Path $temporaryRoot 'v2-invalid-type.json'
    $v2InvalidType = New-Envelope -Path $v2InvalidTypePath -SchemaVersion 2
    $v2InvalidType['schemaVersion'] = $true
    [System.IO.File]::WriteAllText($v2InvalidTypePath, ($v2InvalidType | ConvertTo-Json -Depth 8), [System.Text.UTF8Encoding]::new($false))
    $v2InvalidTypeRun = Invoke-ChildScript -Path $invokeScript -Arguments @('-EnvelopePath', $v2InvalidTypePath, '-RepositoryRoot', $fixtureRepo, '-OpenCodeCommand', $fakeOpenCode, '-TelemetryPath', $telemetryPath)
    Add-TestResult ($v2InvalidTypeRun.ExitCode -eq 2 -and $v2InvalidTypeRun.Text.Contains('INVALID_FIELD_TYPE')) 'schemaVersion booleano é recusado sem coerção'

    $v2ScalarTriggersPath = Join-Path $temporaryRoot 'v2-scalar-triggers.json'
    $v2ScalarTriggers = New-Envelope -Path $v2ScalarTriggersPath -SchemaVersion 2 -AgenticImpact 'PRESENT' -AgenticTriggers @('modelo') -SpecialistRole 'ai_architect' -Workflow 'architect' -Agent 'plan' -MutationPolicy 'READ_ONLY'
    $v2ScalarTriggers['agenticTriggers'] = 'modelo'
    [System.IO.File]::WriteAllText($v2ScalarTriggersPath, ($v2ScalarTriggers | ConvertTo-Json -Depth 8), [System.Text.UTF8Encoding]::new($false))
    $v2ScalarTriggersRun = Invoke-ChildScript -Path $invokeScript -Arguments @('-EnvelopePath', $v2ScalarTriggersPath, '-RepositoryRoot', $fixtureRepo, '-OpenCodeCommand', $fakeOpenCode, '-TelemetryPath', $telemetryPath)
    Add-TestResult ($v2ScalarTriggersRun.ExitCode -eq 2 -and $v2ScalarTriggersRun.Text.Contains('INVALID_FIELD_TYPE')) 'agenticTriggers escalar é recusado'

    $v2InvalidSpecialistPath = Join-Path $temporaryRoot 'v2-invalid-specialist.json'
    [void](New-Envelope -Path $v2InvalidSpecialistPath -SchemaVersion 2 -AgenticImpact 'PRESENT' -AgenticTriggers @('modelo') -SpecialistRole 'ai_architect' -MutationPolicy 'READ_ONLY')
    $v2InvalidSpecialist = Invoke-ChildScript -Path $invokeScript -Arguments @('-EnvelopePath', $v2InvalidSpecialistPath, '-RepositoryRoot', $fixtureRepo, '-OpenCodeCommand', $fakeOpenCode, '-TelemetryPath', $telemetryPath)
    Add-TestResult ($v2InvalidSpecialist.ExitCode -eq 2 -and $v2InvalidSpecialist.Text.Contains('INVALID_SPECIALIST_CONTRACT')) 'ai_architect recusa workflow execute e agente build'

    $invalidEnvelopePath = Join-Path $temporaryRoot 'invalid-envelope.json'
    $invalidEnvelope = New-Envelope -Path $invalidEnvelopePath
    $invalidEnvelope.Remove('returnFormat')
    [System.IO.File]::WriteAllText($invalidEnvelopePath, ($invalidEnvelope | ConvertTo-Json -Depth 8), [System.Text.UTF8Encoding]::new($false))
    $missing = Invoke-ChildScript -Path $invokeScript -Arguments @('-EnvelopePath', $invalidEnvelopePath, '-RepositoryRoot', $fixtureRepo, '-OpenCodeCommand', $fakeOpenCode, '-TelemetryPath', $telemetryPath)
    Add-TestResult ($missing.ExitCode -eq 2 -and $missing.Text.Contains('MISSING_FIELD')) 'envelope incompleto falha antes do executor'

    $attemptEnvelopePath = Join-Path $temporaryRoot 'attempt-envelope.json'
    [void](New-Envelope -Path $attemptEnvelopePath -Attempt 4)
    $attempt = Invoke-ChildScript -Path $invokeScript -Arguments @('-EnvelopePath', $attemptEnvelopePath, '-RepositoryRoot', $fixtureRepo, '-OpenCodeCommand', $fakeOpenCode, '-TelemetryPath', $telemetryPath)
    Add-TestResult ($attempt.ExitCode -eq 2 -and $attempt.Text.Contains('ATTEMPT_LIMIT')) 'quarta tentativa é recusada'

    $env:TIANET_OPENCODE_TEST_MODE = 'allowed-change'
    $allowedEnvelopePath = Join-Path $temporaryRoot 'allowed-envelope.json'
    [void](New-Envelope -Path $allowedEnvelopePath)
    $allowed = Invoke-ChildScript -Path $invokeScript -Arguments @('-EnvelopePath', $allowedEnvelopePath, '-RepositoryRoot', $fixtureRepo, '-OpenCodeCommand', $fakeOpenCode, '-TelemetryPath', $telemetryPath)
    $allowedResult = Convert-ResultJson -Text $allowed.Text
    Add-TestResult ($allowed.ExitCode -eq 0 -and @($allowedResult.changedPaths) -contains 'allowed.txt') 'alteração permitida é identificada'

    Remove-Item -LiteralPath (Join-Path $fixtureRepo 'allowed.txt') -Force
    $env:TIANET_OPENCODE_TEST_MODE = 'allowed-change'
    $readOnlyEnvelopePath = Join-Path $temporaryRoot 'readonly-change.json'
    [void](New-Envelope -Path $readOnlyEnvelopePath -SchemaVersion 2 -MutationPolicy 'READ_ONLY')
    $readOnly = Invoke-ChildScript -Path $invokeScript -Arguments @('-EnvelopePath', $readOnlyEnvelopePath, '-RepositoryRoot', $fixtureRepo, '-OpenCodeCommand', $fakeOpenCode, '-TelemetryPath', $telemetryPath)
    $readOnlyResult = Convert-ResultJson -Text $readOnly.Text
    Add-TestResult ($readOnly.ExitCode -eq 3 -and $readOnlyResult.reasonCode -eq 'READ_ONLY_VIOLATION') 'READ_ONLY bloqueia qualquer mudança versionável'
    Remove-Item -LiteralPath (Join-Path $fixtureRepo 'allowed.txt') -Force

    $env:TIANET_OPENCODE_TEST_MODE = 'stage-only'
    $stageOnlyEnvelopePath = Join-Path $temporaryRoot 'stage-only.json'
    [void](New-Envelope -Path $stageOnlyEnvelopePath -SchemaVersion 2 -MutationPolicy 'READ_ONLY')
    $stageOnly = Invoke-ChildScript -Path $invokeScript -Arguments @('-EnvelopePath', $stageOnlyEnvelopePath, '-RepositoryRoot', $fixtureRepo, '-OpenCodeCommand', $fakeOpenCode, '-TelemetryPath', $telemetryPath)
    $stageOnlyResult = Convert-ResultJson -Text $stageOnly.Text
    Add-TestResult ($stageOnly.ExitCode -eq 3 -and $stageOnlyResult.reasonCode -eq 'READ_ONLY_VIOLATION' -and @($stageOnlyResult.scopeViolations) -contains '<git-index>') 'READ_ONLY detecta staging sem mudança de bytes'
    & git -C $fixtureRepo reset --quiet

    $env:TIANET_OPENCODE_TEST_MODE = 'head-only'
    $headOnlyEnvelopePath = Join-Path $temporaryRoot 'head-only.json'
    [void](New-Envelope -Path $headOnlyEnvelopePath -SchemaVersion 2 -MutationPolicy 'READ_ONLY')
    $headOnly = Invoke-ChildScript -Path $invokeScript -Arguments @('-EnvelopePath', $headOnlyEnvelopePath, '-RepositoryRoot', $fixtureRepo, '-OpenCodeCommand', $fakeOpenCode, '-TelemetryPath', $telemetryPath)
    $headOnlyResult = Convert-ResultJson -Text $headOnly.Text
    Add-TestResult ($headOnly.ExitCode -eq 3 -and $headOnlyResult.reasonCode -eq 'READ_ONLY_VIOLATION' -and @($headOnlyResult.scopeViolations) -contains '<git-head>') 'READ_ONLY detecta mudança de HEAD sem mudança de bytes'

    $env:TIANET_OPENCODE_TEST_MODE = 'outside-change'
    $outsideEnvelopePath = Join-Path $temporaryRoot 'outside-envelope.json'
    [void](New-Envelope -Path $outsideEnvelopePath)
    $outside = Invoke-ChildScript -Path $invokeScript -Arguments @('-EnvelopePath', $outsideEnvelopePath, '-RepositoryRoot', $fixtureRepo, '-OpenCodeCommand', $fakeOpenCode, '-TelemetryPath', $telemetryPath)
    $outsideResult = Convert-ResultJson -Text $outside.Text
    Add-TestResult ($outside.ExitCode -eq 3 -and @($outsideResult.scopeViolations) -contains 'outside.txt') 'alteração fora do escopo bloqueia sem limpeza'
    Add-TestResult (Test-Path -LiteralPath (Join-Path $fixtureRepo 'outside.txt')) 'arquivo fora do escopo permanece para review'

    $env:TIANET_OPENCODE_TEST_MODE = 'provider-error'
    $providerEnvelopePath = Join-Path $temporaryRoot 'provider-envelope.json'
    $providerEnvelope = New-Envelope -Path $providerEnvelopePath
    $provider = Invoke-ChildScript -Path $invokeScript -Arguments @('-EnvelopePath', $providerEnvelopePath, '-RepositoryRoot', $fixtureRepo, '-OpenCodeCommand', $fakeProviderError, '-TelemetryPath', $telemetryPath)
    $providerResult = Convert-ResultJson -Text $provider.Text
    Add-TestResult ($provider.ExitCode -eq 17 -and $null -ne $providerResult -and $providerResult.reasonCode -eq 'PROVIDER_ERROR') "erro do provedor é distinguido (exit=$($provider.ExitCode), reason=$($providerResult.reasonCode))"

    $review = Invoke-ChildScript -Path $reviewScript -Arguments @('-TaskId', $envelope.taskId, '-Attempt', '1', '-Workflow', 'execute', '-Classification', 'SMALL', '-Model', 'opencode/test-model', '-Outcome', 'APROVADA', '-ChecksPassed', '2', '-FilesChanged', '0', '-TelemetryPath', $telemetryPath)
    $reviewResult = Convert-ResultJson -Text $review.Text
    Add-TestResult ($review.ExitCode -eq 0 -and $null -ne $reviewResult -and $reviewResult.recorded -eq $true) 'review aprovado é registrado'
    foreach ($counter in @('-ChecksFailed', '-ChecksNotRun')) {
        $beforeReviewLines = @(Get-Content -LiteralPath $telemetryPath).Count
        $invalidReview = Invoke-ChildScript -Path $reviewScript -Arguments @('-TaskId', $envelope.taskId, '-Attempt', '1', '-Workflow', 'execute', '-Classification', 'SMALL', '-Model', 'opencode/test-model', '-Outcome', 'APROVADA', $counter, '1', '-TelemetryPath', $telemetryPath)
        $afterReviewLines = @(Get-Content -LiteralPath $telemetryPath).Count
        Add-TestResult ($invalidReview.ExitCode -ne 0 -and $beforeReviewLines -eq $afterReviewLines) "review recusa $counter sem persistir falsa aprovacao"
    }

    $correction = Invoke-ChildScript -Path $reviewScript -Arguments @('-TaskId', ([guid]::NewGuid().ToString()), '-Attempt', '1', '-Workflow', 'architect', '-Classification', 'ARCHITECTURAL', '-Model', 'opencode/test-model', '-Outcome', 'CORREÇÃO', '-ReasonCode', 'ACCEPTANCE_FAILED', '-AgenticImpact', 'PRESENT', '-SpecialistRole', 'ai_architect', '-TriggerCount', '1', '-SpecialistVerdict', 'BLOCKER', '-MaterialFindingsCount', '1', '-OpenBlockers', '1', '-TelemetryPath', $telemetryPath)
    Add-TestResult ($correction.ExitCode -eq 0) 'parecer incompleto pode ser registrado como CORREÇÃO/ACCEPTANCE_FAILED'

    $openBlocker = Invoke-ChildScript -Path $reviewScript -Arguments @('-TaskId', ([guid]::NewGuid().ToString()), '-Attempt', '1', '-Workflow', 'architect', '-Classification', 'ARCHITECTURAL', '-Model', 'opencode/test-model', '-Outcome', 'APROVADA', '-AgenticImpact', 'PRESENT', '-SpecialistRole', 'ai_architect', '-TriggerCount', '1', '-SpecialistVerdict', 'BLOCKER', '-MaterialFindingsCount', '1', '-OpenBlockers', '1', '-AdjudicationActor', 'CODEX', '-AdjudicationScope', 'TECHNICAL', '-TelemetryPath', $telemetryPath)
    Add-TestResult ($openBlocker.ExitCode -ne 0 -and $openBlocker.Text.Contains('BLOCKER aberto')) 'review não aprova BLOCKER aberto'

    $missingAdjudication = Invoke-ChildScript -Path $reviewScript -Arguments @('-TaskId', ([guid]::NewGuid().ToString()), '-Attempt', '1', '-Workflow', 'architect', '-Classification', 'ARCHITECTURAL', '-Model', 'opencode/test-model', '-Outcome', 'APROVADA', '-AgenticImpact', 'PRESENT', '-SpecialistRole', 'ai_architect', '-TriggerCount', '1', '-SpecialistVerdict', 'BLOCKER', '-MaterialFindingsCount', '1', '-OpenBlockers', '0', '-TelemetryPath', $telemetryPath)
    Add-TestResult ($missingAdjudication.ExitCode -ne 0 -and $missingAdjudication.Text.Contains('adjudicação explícita')) 'parecer BLOCKER exige adjudicação antes de aprovação'

    $adjudicated = Invoke-ChildScript -Path $reviewScript -Arguments @('-TaskId', ([guid]::NewGuid().ToString()), '-Attempt', '1', '-Workflow', 'architect', '-Classification', 'ARCHITECTURAL', '-Model', 'opencode/test-model', '-Outcome', 'APROVADA', '-AgenticImpact', 'PRESENT', '-SpecialistRole', 'ai_architect', '-TriggerCount', '1', '-SpecialistVerdict', 'BLOCKER', '-MaterialFindingsCount', '2', '-OpenBlockers', '0', '-AdjudicationActor', 'CODEX', '-AdjudicationScope', 'TECHNICAL', '-TelemetryPath', $telemetryPath)
    Add-TestResult ($adjudicated.ExitCode -eq 0) 'parecer BLOCKER técnico admite adjudicação CODEX'

    $materialCodex = Invoke-ChildScript -Path $reviewScript -Arguments @('-TaskId', ([guid]::NewGuid().ToString()), '-Attempt', '1', '-Workflow', 'architect', '-Classification', 'ARCHITECTURAL', '-Model', 'opencode/test-model', '-Outcome', 'APROVADA', '-AgenticImpact', 'PRESENT', '-SpecialistRole', 'ai_architect', '-TriggerCount', '1', '-SpecialistVerdict', 'BLOCKER', '-MaterialFindingsCount', '1', '-OpenBlockers', '0', '-AdjudicationActor', 'CODEX', '-AdjudicationScope', 'MATERIAL', '-TelemetryPath', $telemetryPath)
    Add-TestResult ($materialCodex.ExitCode -ne 0 -and $materialCodex.Text.Contains('MATERIAL exige OWNER')) 'adjudicação MATERIAL recusa CODEX'

    $materialOwner = Invoke-ChildScript -Path $reviewScript -Arguments @('-TaskId', ([guid]::NewGuid().ToString()), '-Attempt', '1', '-Workflow', 'architect', '-Classification', 'ARCHITECTURAL', '-Model', 'opencode/test-model', '-Outcome', 'APROVADA', '-AgenticImpact', 'PRESENT', '-SpecialistRole', 'ai_architect', '-TriggerCount', '1', '-SpecialistVerdict', 'BLOCKER', '-MaterialFindingsCount', '1', '-OpenBlockers', '0', '-AdjudicationActor', 'OWNER', '-AdjudicationScope', 'MATERIAL', '-TelemetryPath', $telemetryPath)
    Add-TestResult ($materialOwner.ExitCode -eq 0) 'adjudicação MATERIAL admite OWNER'

    $noneWithFindings = Invoke-ChildScript -Path $reviewScript -Arguments @('-TaskId', ([guid]::NewGuid().ToString()), '-Attempt', '1', '-Workflow', 'verify', '-Classification', 'SMALL', '-Model', 'opencode/test-model', '-Outcome', 'APROVADA', '-MaterialFindingsCount', '1', '-TelemetryPath', $telemetryPath)
    Add-TestResult ($noneWithFindings.ExitCode -ne 0) 'impacto NONE exige metadados agentic zerados'

    $blockerWithoutFinding = Invoke-ChildScript -Path $reviewScript -Arguments @('-TaskId', ([guid]::NewGuid().ToString()), '-Attempt', '1', '-Workflow', 'architect', '-Classification', 'ARCHITECTURAL', '-Model', 'opencode/test-model', '-Outcome', 'BLOQUEADA', '-ReasonCode', 'INSUFFICIENT_EVIDENCE', '-AgenticImpact', 'PRESENT', '-SpecialistRole', 'ai_architect', '-TriggerCount', '1', '-SpecialistVerdict', 'BLOCKER', '-MaterialFindingsCount', '0', '-OpenBlockers', '0', '-TelemetryPath', $telemetryPath)
    Add-TestResult ($blockerWithoutFinding.ExitCode -ne 0) 'parecer BLOCKER exige achado material'

    $approvedWithOpenBlocker = Invoke-ChildScript -Path $reviewScript -Arguments @('-TaskId', ([guid]::NewGuid().ToString()), '-Attempt', '1', '-Workflow', 'architect', '-Classification', 'ARCHITECTURAL', '-Model', 'opencode/test-model', '-Outcome', 'BLOQUEADA', '-ReasonCode', 'INSUFFICIENT_EVIDENCE', '-AgenticImpact', 'PRESENT', '-SpecialistRole', 'ai_architect', '-TriggerCount', '1', '-SpecialistVerdict', 'APPROVED', '-MaterialFindingsCount', '1', '-OpenBlockers', '1', '-TelemetryPath', $telemetryPath)
    Add-TestResult ($approvedWithOpenBlocker.ExitCode -ne 0) 'parecer APPROVED não admite BLOCKER aberto'

    $invalidAdjudicator = Invoke-ChildScript -Path $reviewScript -Arguments @('-TaskId', ([guid]::NewGuid().ToString()), '-Attempt', '1', '-Workflow', 'architect', '-Classification', 'ARCHITECTURAL', '-Model', 'opencode/test-model', '-Outcome', 'APROVADA', '-AgenticImpact', 'PRESENT', '-SpecialistRole', 'ai_architect', '-TriggerCount', '1', '-SpecialistVerdict', 'APPROVED', '-AdjudicationActor', 'MODEL', '-TelemetryPath', $telemetryPath)
    Add-TestResult ($invalidAdjudicator.ExitCode -ne 0) 'adjudicador fora de CODEX/OWNER é recusado'

    [System.IO.File]::AppendAllText($telemetryPath, "not-json$([Environment]::NewLine)", [System.Text.UTF8Encoding]::new($false))
    $report = Invoke-ChildScript -Path $reportScript -Arguments @('-TelemetryPath', $telemetryPath)
    $reportResult = Convert-ResultJson -Text $report.Text
    Add-TestResult ($report.ExitCode -eq 0 -and $reportResult.invalidLines -eq 1 -and $reportResult.reviews -eq 4) 'relatório tolera e contabiliza linha inválida'
    Add-TestResult ($reportResult.checks.passed -eq 2 -and $reportResult.byModel.Count -ge 1) 'relatório agrega checks e modelos'
    Add-TestResult ($reportResult.agentic.specialistReviews -eq 3 -and $reportResult.agentic.blockerVerdicts -eq 3 -and $reportResult.agentic.materialFindings -eq 4) 'relatório agrega metadados agentic sem conteúdo'

    $missingReport = Invoke-ChildScript -Path $reportScript -Arguments @('-TelemetryPath', (Join-Path $temporaryRoot 'missing.jsonl'))
    $missingReportResult = Convert-ResultJson -Text $missingReport.Text
    Add-TestResult ($missingReport.ExitCode -eq 0 -and -not $missingReportResult.exists) 'relatório trata arquivo ausente'

    $concurrentPath = Join-Path $temporaryRoot 'telemetry\concurrent.jsonl'
    $processes = [System.Collections.Generic.List[System.Diagnostics.Process]]::new()
    foreach ($number in 1..5) {
        $taskId = [guid]::NewGuid().ToString()
        $argumentLine = "-NoProfile -ExecutionPolicy Bypass -File `"$reviewScript`" -TaskId $taskId -Attempt 1 -Workflow verify -Classification SMALL -Model opencode/test-model -Outcome APROVADA -ChecksPassed 1 -TelemetryPath `"$concurrentPath`""
        $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
        $startInfo.FileName = 'powershell.exe'
        $startInfo.Arguments = $argumentLine
        $startInfo.UseShellExecute = $false
        $startInfo.CreateNoWindow = $true
        $startInfo.RedirectStandardOutput = $true
        $startInfo.RedirectStandardError = $true
        $processes.Add([System.Diagnostics.Process]::Start($startInfo))
    }
    foreach ($process in $processes) {
        $process.WaitForExit()
    }
    $concurrentLines = @(Get-Content -LiteralPath $concurrentPath)
    $validConcurrent = @($concurrentLines | ForEach-Object { try { $_ | ConvertFrom-Json } catch { $null } } | Where-Object { $null -ne $_ })
    Add-TestResult ($concurrentLines.Count -eq 5 -and $validConcurrent.Count -eq 5) 'append concorrente preserva cinco eventos válidos'
} finally {
    $resolvedTemporaryRoot = [System.IO.Path]::GetFullPath($temporaryRoot)
    $resolvedTempParent = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd('\', '/')
    if ((Split-Path -Parent $resolvedTemporaryRoot) -ne $resolvedTempParent -or
        (Split-Path -Leaf $resolvedTemporaryRoot) -notmatch '^tianet-opencode-test-[a-f0-9]{32}$') {
        throw 'Limpeza recusada: destino fora da fixture temporária esperada.'
    }
    Remove-Item -LiteralPath $resolvedTemporaryRoot -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item Env:TIANET_OPENCODE_TEST_MODE -ErrorAction SilentlyContinue
}

Write-Host ''
Write-Host "Checks aprovados: $script:Passes"
Write-Host "Checks reprovados: $($script:Failures.Count)"
if ($script:Failures.Count -gt 0) {
    foreach ($failure in $script:Failures) {
        Write-Host "- $failure"
    }
    exit 1
}
Write-Host 'Coordenação Codex–OpenCode verificada com sucesso.'
exit 0
