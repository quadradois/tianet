[CmdletBinding()]
param([string]$RepositoryRoot)

$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($RepositoryRoot)) {
    $RepositoryRoot = Join-Path $PSScriptRoot '../..'
}
$RepositoryRoot = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$script:passes = 0
$script:failures = 0
function Test-Check {
    param([bool]$Condition, [string]$Message)
    if ($Condition) {
        $script:passes++
        Write-Host "[PASS] $Message"
    } else {
        $script:failures++
        Write-Host "[FAIL] $Message"
    }
}
function Read-Text {
    param([string]$RelativePath)
    $path = Join-Path $RepositoryRoot $RelativePath
    if (Test-Path -LiteralPath $path -PathType Leaf) {
        return [IO.File]::ReadAllText($path)
    }
    return ''
}

$required = @(
    'AGENTS.md', 'CONTRIBUTING.md', 'docs/README.md',
    'docs/governance/agents/SPEC-004-regras-normativas-do-codigo.md',
    'docs/governance/agent-loop/AGENT-LOOP-EXECUTION-PROTOCOL.md',
    'docs/governance/agents/HARNESS.md', 'docs/governance/agents/HANDOFF.md',
    'docs/governance/agents/HARNESS-ADOPTION.md', 'docs/governance/agents/HARNESS-VERIFICATION.md',
    '.agents/principles/engineering.md', '.agents/policies/classification-and-gates.md',
    '.agents/policies/knowledge-and-evidence.md', '.agents/policies/agentic-review.md',
    '.agents/templates/opencode-task.json', '.agents/templates/ai-architect-review.md',
    '.agents/templates/adr.md', '.agents/templates/design.md', '.agents/templates/exec-plan.md',
    '.agents/templates/verification.md', '.agents/templates/review.md', '.agents/templates/handoff.md',
    'scripts/harness/Invoke-OpenCodeTask.ps1', 'scripts/harness/Add-OpenCodeReview.ps1',
    'scripts/harness/Get-OpenCodeTelemetry.ps1', 'scripts/harness/Test-OpenCodeCoordination.ps1',
    'scripts/harness/Test-Harness.ps1', 'scripts/harness/Test-HarnessValidation.ps1'
)
foreach ($workflow in @('discover', 'architect', 'plan', 'execute', 'verify')) {
    $required += ".agents/skills/$workflow/SKILL.md"
    $required += ".agents/skills/$workflow/agents/openai.yaml"
    $skill = Read-Text ".agents/skills/$workflow/SKILL.md"
    Test-Check ($skill -match "(?m)^name: $workflow\s*$" -and $skill -match '(?m)^description: .+') "Skill $workflow possui nome e descricao"
    $metadata = Read-Text ".agents/skills/$workflow/agents/openai.yaml"
    Test-Check ($metadata.Contains('display_name:') -and $metadata.Contains('default_prompt:')) "Skill $workflow possui metadados de interface"
}
foreach ($relative in $required) {
    Test-Check (Test-Path -LiteralPath (Join-Path $RepositoryRoot $relative) -PathType Leaf) "Arquivo: $relative"
}

# Links e sintaxe sao verificados nos arquivos do Harness; docs:validate cobre docs/.
foreach ($relative in $required) {
    $path = Join-Path $RepositoryRoot $relative
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { continue }
    $content = [IO.File]::ReadAllText($path)
    if ($relative.EndsWith('.md')) {
        foreach ($match in [regex]::Matches($content, '\[[^\]]+\]\(([^)]+)\)')) {
            $target = $match.Groups[1].Value.Trim('<', '>')
            if ($target -match '^(https?:|mailto:|#)') { continue }
            $target = ($target -split '#')[0]
            $target = [Uri]::UnescapeDataString($target)
            Test-Check (Test-Path -LiteralPath (Join-Path (Split-Path -Parent $path) $target)) "Link: $relative -> $target"
        }
    }
    if ($relative.EndsWith('.ps1')) {
        $tokens = $null
        $parseErrors = $null
        [void][Management.Automation.Language.Parser]::ParseFile($path, [ref]$tokens, [ref]$parseErrors)
        Test-Check (@($parseErrors).Count -eq 0) "Sintaxe PowerShell: $relative"
    }
    if ($relative.StartsWith('.agents/') -or ($relative.StartsWith('scripts/harness/') -and $relative -ne 'scripts/harness/Test-Harness.ps1')) {
        Test-Check ($content -notmatch '(?i)C:[\\/]Viagens|doc/06_engenharia|doc/governanca|Nox[\\/]engineering-telemetry') "Portabilidade: $relative"
    }
}

try {
    $envelope = (Read-Text '.agents/templates/opencode-task.json') | ConvertFrom-Json
    Test-Check ($envelope.schemaVersion -eq 2 -and $envelope.mutationPolicy -eq 'READ_ONLY') 'Envelope v2 inicia em READ_ONLY'
    Test-Check ($envelope.agenticImpact -eq 'NONE' -and @($envelope.agenticTriggers).Count -eq 0 -and $null -eq $envelope.specialistRole) 'Template comum sem parecer especialista implicito'
    Test-Check ($envelope.model -eq 'opencode/muse-spark-1.3-contributor-free') 'Identificador inicial corresponde ao modelo verificado na adocao'
} catch { Test-Check $false 'Envelope deve ser JSON valido' }

foreach ($scriptName in @('Invoke-OpenCodeTask.ps1', 'Add-OpenCodeReview.ps1', 'Get-OpenCodeTelemetry.ps1')) {
    $content = Read-Text "scripts/harness/$scriptName"
    Test-Check ($content.Contains('TiaNet\engineering-telemetry\opencode-events.jsonl')) "Telemetria separada: $scriptName"
}
$entry = Read-Text 'AGENTS.md'
Test-Check ($entry.Contains('SPEC-004') -and $entry.Contains('ALP-001') -and $entry.Contains('frontend/AGENTS.md')) 'Entrada aponta normas e instrucoes locais existentes'
$gates = Read-Text '.agents/policies/classification-and-gates.md'
Test-Check ($gates.Contains('GATE-E') -and $gates.Contains('ALP-001')) 'Gates do executor vinculados a governanca existente'
try {
    $package = (Read-Text 'package.json') | ConvertFrom-Json
    foreach ($command in @('harness:check', 'harness:test')) {
        $value = $package.scripts.PSObject.Properties[$command].Value
        Test-Check (-not [string]::IsNullOrWhiteSpace($value)) "Comando npm: $command"
    }
} catch { Test-Check $false 'Scripts npm acessiveis' }

Write-Host "Checks aprovados: $script:passes"
Write-Host "Checks reprovados: $script:failures"
if ($script:failures -gt 0) { exit 1 }
exit 0
