@echo off
setlocal enabledelayedexpansion
title Instalador AI Teleport (AirGrab)
color 0B

:: =========================================================
:: CONFIGURACOES DO SEU GITHUB (EDITE AQUI ANTES DE POSTAR)
:: =========================================================
set GITHUB_ZIP_URL=https://github.com/jose-pires-neto/AirGrab/archive/refs/heads/main.zip
set FOLDER_NAME_IN_ZIP=AirGrab-main
:: =========================================================

set INSTALL_DIR=%USERPROFILE%\AirGrab
set ZIP_FILE=%TEMP%\AirGrab_Download.zip

echo ===================================================
echo       BEM VINDO AO INSTALADOR DO AI TELEPORT
echo ===================================================
echo.

:: 1. Verificacao do Python
echo [1/4] Verificando dependencias do sistema (Python)...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] O Python nao foi encontrado no sistema.
    echo Por favor, instale o Python 3.10 ou superior e adicione-o ao PATH.
    echo Baixe em: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
echo [OK] Python detectado!
echo.

:: 2. Download e Extracao
echo [2/4] Baixando a ultima versao do AI Teleport...
if exist "%INSTALL_DIR%" (
    echo Limpando instalacao antiga...
    rmdir /S /Q "%INSTALL_DIR%"
)

echo Fazendo download de %GITHUB_ZIP_URL% ...
powershell -Command "Invoke-WebRequest -Uri '%GITHUB_ZIP_URL%' -OutFile '%ZIP_FILE%'"
if not exist "%ZIP_FILE%" (
    echo [ERRO] Falha ao baixar o arquivo. Verifique sua conexao ou o link do Github.
    pause
    exit /b 1
)

echo Extraindo os arquivos...
powershell -Command "Expand-Archive -Path '%ZIP_FILE%' -DestinationPath '%TEMP%\AirGrab_Extract' -Force"
move "%TEMP%\AirGrab_Extract\%FOLDER_NAME_IN_ZIP%" "%INSTALL_DIR%" >nul
del "%ZIP_FILE%"
rmdir /S /Q "%TEMP%\AirGrab_Extract"
echo [OK] Arquivos baixados e posicionados em %INSTALL_DIR%!
echo.

:: 3. Ambiente Virtual
echo [3/4] Criando o Motor de Inteligencia Artificial (pode demorar)...
cd /d "%INSTALL_DIR%"
python -m venv venv
call venv\Scripts\activate.bat
pip install -r requirements.txt
echo [OK] Motor de IA pronto!
echo.

:: 4. Atalhos Silenciosos
echo [4/4] Criando atalhos...
set VBS_RUNNER=Executar_AirGrab.vbs

echo Set WshShell = CreateObject("WScript.Shell") > %VBS_RUNNER%
echo WshShell.Run "cmd.exe /c call venv\Scripts\activate.bat & python teleport_app.py", 0, False >> %VBS_RUNNER%

set SHORTCUT_PATH=%USERPROFILE%\Desktop\AI Teleport.lnk
set TEMP_VBS=CreateShortcut.vbs

echo Set oWS = WScript.CreateObject("WScript.Shell") > %TEMP_VBS%
echo sLinkFile = "%SHORTCUT_PATH%" >> %TEMP_VBS%
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %TEMP_VBS%
echo oLink.TargetPath = "%INSTALL_DIR%\%VBS_RUNNER%" >> %TEMP_VBS%
echo oLink.WorkingDirectory = "%INSTALL_DIR%" >> %TEMP_VBS%
echo oLink.Description = "AI Teleport (AirGrab)" >> %TEMP_VBS%
echo oLink.Save >> %TEMP_VBS%

cscript //nologo %TEMP_VBS%
del %TEMP_VBS%

echo.
echo ===================================================
echo       INSTALACAO CONCLUIDA COM SUCESSO!
echo ===================================================
echo.
echo Um atalho chamado "AI Teleport" foi criado na sua Area de Trabalho.
echo Ao abrir, a janela nao aparecera, ele ficara invisivel (em background) 
echo monitorando apenas os gestos e a transferencia de arquivos!
echo.
pause
