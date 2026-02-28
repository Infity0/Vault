param(
    [Parameter(Mandatory=$true)]
    [string]$IP,
    [switch]$Restart
)

$scp = "C:\Windows\System32\OpenSSH\scp.exe"
$ssh = "C:\Windows\System32\OpenSSH\ssh.exe"
$LocalPath = Join-Path $PSScriptRoot "desktop"
$Remote = "root@" + $IP + ":/opt/vault/"

Write-Host "Copying files to $IP ..." -ForegroundColor Cyan

& $scp -o "StrictHostKeyChecking=no" -r "$LocalPath\server.py" "$LocalPath\requirements.txt" "$LocalPath\src" "$LocalPath\assets" $Remote

if ($LASTEXITCODE -ne 0) {
    Write-Host "Copy error!" -ForegroundColor Red
    exit 1
}

Write-Host "Files copied successfully." -ForegroundColor Green

if ($Restart) {
    Write-Host "Restarting service..." -ForegroundColor Cyan
    & $ssh -o "StrictHostKeyChecking=no" "root@$IP" "systemctl restart vault-api && systemctl status vault-api --no-pager"
    Write-Host "Done!" -ForegroundColor Green
} else {
    Write-Host "Файлы скопированы. Запусти скрипт с флагом -Restart чтобы перезапустить сервис:" -ForegroundColor Yellow
    Write-Host "  .\deploy.ps1 -IP $IP -Restart" -ForegroundColor White
}
