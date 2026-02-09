@echo off
title Fix Font Issue
echo ============================================
echo   Fix Windows Font Blocking Issue
echo ============================================
echo.

echo [Step 1] Updating registry to allow fonts...
reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\Kernel" /v MitigationOptions /t REG_QWORD /d 0x2000000000000 /f
if %ERRORLEVEL% EQU 0 (
    echo OK - Registry updated successfully!
) else (
    echo FAILED - Please run as Administrator!
)
echo.

echo [Step 2] Copying fonts to system directory...
set "SRC=%LOCALAPPDATA%\Microsoft\Windows\Fonts"
set "DST=%WINDIR%\Fonts"

if exist "%SRC%\materialdesignicons6-webfont-6.9.96.ttf" (
    copy /Y "%SRC%\materialdesignicons6-webfont-6.9.96.ttf" "%DST%\" >nul 2>&1
    echo OK - materialdesignicons font copied!
) else (
    echo SKIP - materialdesignicons font not found in user dir
)

for %%f in ("%SRC%\fontawesome*.ttf") do (
    if exist "%%f" (
        copy /Y "%%f" "%DST%\" >nul 2>&1
        echo OK - Copied: %%~nxf
    )
)

echo.
echo ============================================
echo   DONE! Please RESTART your computer,
echo   then open the program again.
echo ============================================
echo.
pause
