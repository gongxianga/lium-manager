@echo off
chcp 65001 >nul
title Lium GPU 管理工具 - 安装程序

echo ============================================
echo    Lium GPU 管理工具 - 一键安装
echo ============================================
echo.

:: 检查是否有 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 未检测到 Python，正在下载安装...
    echo.
    :: 下载 Python 安装包
    curl -L -o "%TEMP%\python_installer.exe" "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
    if %errorlevel% neq 0 (
        echo [错误] Python 下载失败，请手动安装 Python 后重试。
        echo 下载地址: https://www.python.org/downloads/
        pause
        exit /b 1
    )
    echo 正在安装 Python（自动添加到 PATH）...
    "%TEMP%\python_installer.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    if %errorlevel% neq 0 (
        echo [错误] Python 安装失败，请手动安装。
        pause
        exit /b 1
    )
    :: 刷新环境变量
    call :RefreshPath
    echo [√] Python 安装完成
    echo.
) else (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo [√] 已检测到 %%v
    echo.
)

:: 设置安装目录
set INSTALL_DIR=%USERPROFILE%\lium-manager
echo [1/3] 下载程序文件...

if exist "%INSTALL_DIR%" (
    echo     检测到旧版本，正在更新...
    cd /d "%INSTALL_DIR%"
    git pull >nul 2>&1
    if %errorlevel% neq 0 (
        rmdir /s /q "%INSTALL_DIR%"
        git clone https://github.com/gongxianga/lium-manager.git "%INSTALL_DIR%" >nul 2>&1
    )
) else (
    git clone https://github.com/gongxianga/lium-manager.git "%INSTALL_DIR%" >nul 2>&1
    if %errorlevel% neq 0 (
        echo [错误] 下载失败，请检查网络连接。
        pause
        exit /b 1
    )
)
echo [√] 文件下载完成

echo.
echo [2/3] 安装依赖库...
python -m pip install requests --quiet
if %errorlevel% neq 0 (
    echo [错误] 依赖安装失败。
    pause
    exit /b 1
)
echo [√] 依赖安装完成

echo.
echo [3/3] 创建桌面快捷方式...
set SHORTCUT=%USERPROFILE%\Desktop\Lium管理工具.bat
(
    echo @echo off
    echo chcp 65001 ^>nul
    echo cd /d "%INSTALL_DIR%"
    echo python lium.py
    echo pause
) > "%SHORTCUT%"
echo [√] 桌面快捷方式已创建

echo.
echo ============================================
echo    安装完成！
echo ============================================
echo.
echo 启动方式：
echo   - 双击桌面上的 [Lium管理工具] 图标
echo   - 或运行: python %INSTALL_DIR%\lium.py
echo.
echo 首次运行需要输入 Lium API Key
echo 获取地址: https://lium.io -> Settings -> API Keys
echo.
set /p START=是否立即启动程序？(y/n):
if /i "%START%"=="y" (
    cd /d "%INSTALL_DIR%"
    python lium.py
)

exit /b 0

:RefreshPath
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "USER_PATH=%%b"
for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "SYS_PATH=%%b"
set "PATH=%SYS_PATH%;%USER_PATH%"
exit /b 0
