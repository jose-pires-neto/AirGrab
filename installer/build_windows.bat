@echo off
echo ==========================================
echo Compilando Instalador para Windows...
echo ==========================================
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name "AirGrab_Installer_Windows" --clean "installer_app.py"
echo Concluido! O executavel esta na pasta "dist".
pause
