import os
import sys
import urllib.request
import zipfile
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

GITHUB_ZIP_URL = "https://github.com/jose-pires-neto/AirGrab/archive/refs/heads/main.zip"
FOLDER_NAME_IN_ZIP = "AirGrab-main"

class AirGrabInstaller(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Instalador AI Teleport (AirGrab)")
        self.geometry("500x350")
        self.resizable(False, False)
        
        # Centralizar a janela
        self.eval('tk::PlaceWindow . center')
        
        self.system = sys.platform
        self.install_dir = Path.home() / "AirGrab"
        
        self.setup_ui()
        
    def setup_ui(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        
        main_frame = ttk.Frame(self, padding="20 20 20 20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        title_lbl = ttk.Label(main_frame, text="AI Teleport - Instalador", font=("Segoe UI", 18, "bold"))
        title_lbl.pack(pady=(0, 10))
        
        sys_name = "Windows" if sys.platform == "win32" else "Mac" if sys.platform == "darwin" else "Linux"
        desc_lbl = ttk.Label(main_frame, text=f"Este instalador configurará o AirGrab para {sys_name}.", font=("Segoe UI", 11))
        desc_lbl.pack(pady=(0, 20))
        
        self.status_var = tk.StringVar(value="Pronto para instalar.")
        status_lbl = ttk.Label(main_frame, textvariable=self.status_var, font=("Segoe UI", 10), foreground="gray")
        status_lbl.pack(pady=(0, 10))
        
        self.progress = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, length=400, mode='determinate')
        self.progress.pack(pady=(0, 20))
        
        self.btn_install = ttk.Button(main_frame, text="Instalar", command=self.start_installation)
        self.btn_install.pack(ipadx=20, ipady=5)
        
    def start_installation(self):
        self.btn_install.config(state=tk.DISABLED)
        self.progress['value'] = 0
        threading.Thread(target=self.install_process, daemon=True).start()
        
    def update_status(self, text, progress_val):
        self.status_var.set(text)
        self.progress['value'] = progress_val
        self.update_idletasks()
        
    def install_process(self):
        try:
            # 1. Download
            self.update_status("Baixando arquivos do GitHub...", 10)
            zip_path = Path.home() / "AirGrab_Download.zip"
            urllib.request.urlretrieve(GITHUB_ZIP_URL, zip_path)
            
            # 2. Extract
            self.update_status("Extraindo arquivos...", 30)
            if self.install_dir.exists():
                shutil.rmtree(self.install_dir)
                
            extract_temp = Path.home() / "AirGrab_Extract"
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_temp)
                
            shutil.move(str(extract_temp / FOLDER_NAME_IN_ZIP), str(self.install_dir))
            
            # Cleanup
            os.remove(zip_path)
            shutil.rmtree(extract_temp)
            
            # 3. Virtual Environment
            self.update_status("Criando Ambiente Virtual (isso pode demorar)...", 50)
            
            python_cmd = "python" if self.system == "win32" else "python3"
            try:
                subprocess.run([python_cmd, "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except FileNotFoundError:
                raise Exception(f"O {python_cmd} não foi encontrado no sistema. Por favor, instale o Python 3.10+ e adicione ao PATH.")
                
            subprocess.run([python_cmd, "-m", "venv", "venv"], cwd=self.install_dir, check=True)
            
            # 4. Install Dependencies
            self.update_status("Instalando Motor de Inteligência Artificial...", 70)
            if self.system == "win32":
                pip_exe = self.install_dir / "venv" / "Scripts" / "pip.exe"
            else:
                pip_exe = self.install_dir / "venv" / "bin" / "pip"
                
            subprocess.run([str(pip_exe), "install", "-r", "requirements.txt"], cwd=self.install_dir, check=True)
            
            # 5. Create Shortcuts
            self.update_status("Criando atalhos...", 90)
            self.create_shortcuts()
            
            self.update_status("Instalação Concluída com Sucesso!", 100)
            messagebox.showinfo("Sucesso", "O AI Teleport (AirGrab) foi instalado com sucesso!\nUm atalho foi criado na sua Área de Trabalho.")
            self.destroy()
            
        except Exception as e:
            self.update_status(f"Erro: {str(e)}", 0)
            messagebox.showerror("Erro na Instalação", f"Ocorreu um erro:\n{str(e)}")
            self.btn_install.config(state=tk.NORMAL)
            
    def create_shortcuts(self):
        desktop = Path.home() / "Desktop"
        
        if not desktop.exists():
            desktop = Path.home() / "Área de Trabalho"
            if not desktop.exists():
                desktop = Path.home()
        
        if self.system == "win32":
            # Criar VBS para rodar invisível
            vbs_runner = self.install_dir / "Executar_AirGrab.vbs"
            with open(vbs_runner, "w") as f:
                f.write('Set WshShell = CreateObject("WScript.Shell")\n')
                f.write(f'WshShell.Run "cmd.exe /c call venv\\Scripts\\activate.bat & python teleport_app.py", 0, False\n')
                
            # Criar Atalho no Desktop via VBS
            shortcut_path = desktop / "AI Teleport.lnk"
            shortcut_script = self.install_dir / "CreateShortcut.vbs"
            with open(shortcut_script, "w") as f:
                f.write('Set oWS = WScript.CreateObject("WScript.Shell")\n')
                f.write(f'sLinkFile = "{shortcut_path}"\n')
                f.write('Set oLink = oWS.CreateShortcut(sLinkFile)\n')
                f.write(f'oLink.TargetPath = "{vbs_runner}"\n')
                f.write(f'oLink.WorkingDirectory = "{self.install_dir}"\n')
                f.write('oLink.Description = "AI Teleport (AirGrab)"\n')
                f.write('oLink.Save\n')
                
            subprocess.run(["cscript", "//nologo", str(shortcut_script)], check=True)
            os.remove(shortcut_script)
            
        elif self.system == "darwin":
            # Mac OS - Cria um AppleScript App na mesa
            app_path = desktop / "AI Teleport.app"
            script = f'''
            tell application "Terminal"
                do script "cd '{self.install_dir}' && source venv/bin/activate && python teleport_app.py"
            end tell
            '''
            subprocess.run(["osacompile", "-e", script, "-o", str(app_path)], check=True)
            
        else:
            # Linux - Cria arquivo .desktop
            desktop_file = desktop / "AI-Teleport.desktop"
            
            content = f"""[Desktop Entry]
Name=AI Teleport
Comment=AirGrab AI Teleport App
Exec=bash -c 'cd "{self.install_dir}" && source venv/bin/activate && python teleport_app.py'
Terminal=false
Type=Application
Categories=Utility;
"""
            with open(desktop_file, "w") as f:
                f.write(content)
            
            os.chmod(desktop_file, 0o755)

if __name__ == "__main__":
    app = AirGrabInstaller()
    app.mainloop()
