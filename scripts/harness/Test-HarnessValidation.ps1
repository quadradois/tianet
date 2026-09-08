[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$sourceRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$fixtureRoot = Join-Path ([IO.Path]::GetTempPath()) ('tianet-harness-validation-' + [guid]::NewGuid().ToString('N'))
[void](New-Item -ItemType Directory -Path $fixtureRoot)
$passes = 0
function Invoke-Validation {
    $lines = @(& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $sourceRoot 'scripts/harness/Test-Harness.ps1') -RepositoryRoot $fixtureRoot 2>&1)
    return [pscustomobject]@{ Code = $LASTEXITCODE; Text = ($lines -join "`n") }
}
try {
    # Copia somente o Harness e suas fontes documentais declaradas, nunca segredos.
    $files = @('AGENTS.md', 'CONTRIBUTING.md', 'package.json', 'docs/README.md',
        'docs/governance/agents/SPEC-004-regras-normativas-do-codigo.md',
        'docs/governance/agent-loop/AGENT-LOOP-EXECUTION-PROTOCOL.md')
    foreach ($directory in @('.agents', 'scripts/harness', 'docs/governance/agents')) {
        foreach ($item in (Get-ChildItem -LiteralPath (Join-Path $sourceRoot $directory) -Recurse -File)) {
            $files += $item.FullName.Substring($sourceRoot.Length + 1)
        }
    }
    foreach ($relative in ($files | Sort-Object -Unique)) {
        $target = Join-Path $fixtureRoot $relative
        [void](New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force)
        Copy-Item -LiteralPath (Join-Path $sourceRoot $relative) -Destination $target
    }
    # Stubs apenas para alvos externos ao Harness: validacao de links, nao produto.
    foreach ($document in (Get-ChildItem -LiteralPath $fixtureRoot -Recurse -Filter '*.md')) {
        foreach ($match in [regex]::Matches([IO.File]::ReadAllText($document.FullName), '\[[^\]]+\]\(([^)]+)\)')) {
            $target = $match.Groups[1].Value.Trim('<', '>')
            if ($target -match '^(https?:|mailto:|#)') { continue }
            $target = [Uri]::UnescapeDataString(($target -split '#')[0])
            $target = [IO.Path]::GetFullPath((Join-Path $document.DirectoryName $target))
            if (-not $target.StartsWith($fixtureRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
                throw 'Link da fixture saiu da raiz temporaria.'
            }
            if (-not (Test-Path -LiteralPath $target)) {
                [void](New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force)
                if ([IO.Path]::HasExtension($target)) { [IO.File]::WriteAllText($target, '# Fixture') }
                else { [void](New-Item -ItemType Directory -Path $target) }
            }
        }
    }
    $baseline = Invoke-Validation
    if ($baseline.Code -ne 0) { throw "Fixture de baseline invalida: $($baseline.Text)" }
    $passes++
    Write-Output '[PASS] Validador aceita fixture estrutural completa'

    $envelopePath = Join-Path $fixtureRoot '.agents/templates/opencode-task.json'
    $original = [IO.File]::ReadAllText($envelopePath)
    [IO.File]::WriteAllText($envelopePath, $original.Replace('READ_ONLY', 'SCOPED_WRITE'))
    $negative = Invoke-Validation
    if ($negative.Code -eq 0 -or $negative.Text -notmatch '\[FAIL\] Envelope v2 inicia em READ_ONLY') {
        throw 'Validador nao detectou relaxamento da politica de mutacao.'
    }
    $passes++
    Write-Output '[PASS] Validador recusa template com mutacao habilitada por padrao'
    [IO.File]::WriteAllText($envelopePath, $original)

    $entryPath = Join-Path $fixtureRoot 'AGENTS.md'
    [IO.File]::AppendAllText($entryPath, "`n[Alvo inexistente](missing-harness-target.md)`n")
    $negative = Invoke-Validation
    if ($negative.Code -eq 0 -or $negative.Text -notmatch '\[FAIL\] Link: AGENTS.md -> missing-harness-target.md') {
        throw 'Validador nao detectou o link quebrado.'
    }
    $passes++
    Write-Output '[PASS] Validador recusa link de retomada quebrado'
} finally {
    $resolvedFixture = [IO.Path]::GetFullPath($fixtureRoot)
    $tempParent = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\', '/')
    if ((Split-Path -Parent $resolvedFixture) -ne $tempParent -or
        (Split-Path -Leaf $resolvedFixture) -notmatch '^tianet-harness-validation-[a-f0-9]{32}$') {
        throw 'Limpeza recusada: raiz temporaria invalida.'
    }
    Remove-Item -LiteralPath $resolvedFixture -Recurse -Force
}
Write-Output "Checks aprovados: $passes; reprovados: 0"
