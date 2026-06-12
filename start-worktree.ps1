$root = "D:\assitant_tools\tools_performance\08_Projects\leonie"

Write-Host "Starting..." -ForegroundColor Cyan

# Backend — dùng uv run (tự sync venv nếu chưa có)
Start-Process "cmd.exe" `
  -ArgumentList "/c", "uv run uvicorn main:app --reload --port 8000" `
  -WorkingDirectory "$root\backend" `
  -WindowStyle Hidden

# Frontend — ẩn hoàn toàn
Start-Process "cmd.exe" `
  -ArgumentList "/c", "npx vite --port 5177" `
  -WorkingDirectory "$root\frontend" `
  -WindowStyle Hidden

# Chờ frontend sẵn sàng
$url = "http://localhost:5177"
Write-Host "Waiting for app..." -ForegroundColor Gray -NoNewline
for ($i = 0; $i -lt 30; $i++) {
  Start-Sleep -Seconds 1
  try {
    $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop
    if ($r.StatusCode -eq 200) { break }
  } catch {}
  Write-Host "." -NoNewline -ForegroundColor Gray
}

Write-Host ""
Write-Host "Ready → $url" -ForegroundColor Green
Start-Process "msedge.exe" $url
