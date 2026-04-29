# PowerShell 脚本：初始化本地仓库并推送到 GitHub
param(
    [Parameter(Mandatory = $true)]
    [string]$RemoteUrl
)

Write-Host "初始化 git 仓库..."
git init
git add -A
git commit -m "Initial commit: Prompt Buddy"

Write-Host "设置远程并推送到 GitHub..."
$existing = git remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0 -and $existing) {
    git remote set-url origin $RemoteUrl
} else {
    git remote add origin $RemoteUrl
}

git branch -M main
git push -u origin main
Write-Host "完成。请确保你已在系统上配置好 Git 凭据。"
