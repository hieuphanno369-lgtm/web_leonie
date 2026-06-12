@echo off
echo Dang them vao Windows Task Scheduler...

schtasks /create ^
  /tn "EmailTaskTracker" ^
  /tr "D:\assitant_tools\tools_performance\task-tracker\start_scheduler.bat" ^
  /sc onlogon ^
  /ru "%USERNAME%" ^
  /rl HIGHEST ^
  /f

if %errorlevel% == 0 (
    echo.
    echo [OK] Da them thanh cong!
    echo Scheduler se tu dong chay moi khi ban dang nhap Windows.
    echo.
    echo Ban co the kiem tra tai: Task Scheduler ^> Task Scheduler Library ^> EmailTaskTracker
) else (
    echo.
    echo [LOI] Khong the them vao Task Scheduler.
    echo Thu chay file nay voi quyen Administrator.
)

pause
