# סנכרון מ-_לסקירה לריפו GitHub ו-push
$src = "$env:USERPROFILE\Desktop\_לסקירה"
$dst = $PSScriptRoot
$files = @(
    "recent_files_server.py",
    "recent_files_tray.pyw",
    "recent-files.html"
)
foreach ($f in $files) {
    Copy-Item (Join-Path $src $f) (Join-Path $dst $f) -Force
    Write-Host "synced $f"
}
Set-Location $dst
git add -A
$msg = "sync: update from local _לסקירה ($(Get-Date -Format 'yyyy-MM-dd HH:mm'))"
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    git commit -m $msg
    git push
    Write-Host "pushed to GitHub"
} else {
    Write-Host "no changes"
}