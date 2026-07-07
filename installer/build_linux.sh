#!/bin/bash
echo "=========================================="
echo "Compilando Instalador para Linux..."
echo "=========================================="
pip3 install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name "AirGrab_Installer_Linux" --clean "installer_app.py"
echo "Concluido! O executavel esta na pasta 'dist'."
