#!/bin/bash
echo "=========================================="
echo "Compilando Instalador para Mac..."
echo "=========================================="
pip3 install pyinstaller
pyinstaller --noconfirm --onedir --windowed --name "AirGrab_Installer_Mac" --clean "installer_app.py"
echo "Concluido! O aplicativo (AirGrab_Installer_Mac.app) esta na pasta 'dist'."
