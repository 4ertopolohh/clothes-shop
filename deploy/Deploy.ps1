param(
    [string]$SshTarget = 'root@121.127.37.245'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$projectName = Split-Path -Leaf $projectRoot
if ($projectName -notin @('auto-shop','manicure','clothes-shop','conditioners')) { throw 'Unexpected project path' }
$remoteRoot = "/srv/webprojects/$projectName"
$scratch = Join-Path ([System.IO.Path]::GetTempPath()) ("demo-release-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $scratch | Out-Null
function Check-Result { if ($LASTEXITCODE -ne 0) { throw "Command failed: $LASTEXITCODE" } }
try {
    $env:PYTHONUTF8 = '1'
    Push-Location (Join-Path $projectRoot 'frontend')
    try {
        if ($projectName -eq 'conditioners') {
            $snapshotCommand = 'cd {0} && docker compose exec -T backend python manage.py export_home_prerender --include-services --output /data/prerender-input.json && docker compose exec -T backend python manage.py shell -c ''exec(open("/data/export_demo_snapshot.py").read())''' -f $remoteRoot
            ssh $SshTarget $snapshotCommand
            Check-Result
            scp "${SshTarget}:$remoteRoot/data/prerender-input.json" (Join-Path $scratch 'public.json')
            Check-Result
            npm run build:prerender -- --data (Join-Path $scratch 'public.json')
        } else {
            if ($projectName -eq 'clothes-shop') { $env:PUBLIC_SITE_URL = "https://$projectName.nemida-studio.com" }
            npm run build
        }
        Check-Result
    } finally {
        Pop-Location
        Remove-Item Env:PUBLIC_SITE_URL -ErrorAction SilentlyContinue
    }
    $archive = Join-Path $scratch 'release.tar.gz'
    python (Join-Path $PSScriptRoot 'build_release.py') $projectRoot $archive
    Check-Result
    scp $archive "${SshTarget}:$remoteRoot/release-next.tar.gz"
    Check-Result
    ssh $SshTarget "set -eu; cd $remoteRoot; ./ops.sh backup; tar -xzf release-next.tar.gz; chmod 700 ops.sh; ./ops.sh update; docker compose ps"
    Check-Result
} finally {
    $resolvedScratch = [System.IO.Path]::GetFullPath($scratch)
    $tempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
    if ($resolvedScratch.StartsWith($tempRoot, [System.StringComparison]::OrdinalIgnoreCase) -and (Split-Path -Leaf $resolvedScratch).StartsWith('demo-release-')) {
        Remove-Item -LiteralPath $resolvedScratch -Recurse -Force -ErrorAction SilentlyContinue
    }
}
