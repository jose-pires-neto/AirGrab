import os
import tempfile
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from teleport import config

WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "web")
PORT = 50002

class WebAppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def log_message(self, format, *args):
        # Muta logs do servidor web para não sujar o terminal
        pass

    def do_POST(self):
        if self.path == '/upload':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                file_name_encoded = self.headers.get('X-File-Name')
                
                if content_length > 0 and file_name_encoded:
                    import urllib.parse
                    filename = urllib.parse.unquote(file_name_encoded)
                    
                    # Salva em pasta temporária
                    temp_dir = tempfile.gettempdir()
                    temp_path = os.path.join(temp_dir, f"airgrab_web_{filename}")
                    
                    with open(temp_path, 'wb') as f:
                        f.write(self.rfile.read(content_length))
                        
                    # Sinaliza ao estado do app que o Web App agarrou algo
                    config.app_state.set("web_app_file_ready", temp_path)
                    config.app_state.set("web_app_file_name", filename)
                    config.network_holder_ip = "WEB_APP"
                    
                    print(f"[*] O Celular (Web App) agarrou '{filename}'! Abra a mão na frente do PC para puxar.")
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(b'{"status": "success"}')
                    return
                
                self.send_error(400, "Invalid Request")
            except Exception as e:
                print(f"[WEB] Erro no upload: {e}")
                self.send_error(500, "Internal Server Error")
        elif self.path == '/cancel':
            config.app_state.set("web_app_file_ready", None)
            config.app_state.set("web_app_file_name", None)
            if config.network_holder_ip == "WEB_APP":
                config.network_holder_ip = None
            print("[WEB] O Celular cancelou a transferência.")
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "success"}')
        else:
            self.send_error(404, "File Not Found")

def run_web_server():
    # Cria a pasta web se não existir
    if not os.path.exists(WEB_DIR):
        os.makedirs(WEB_DIR)
        
    server_address = ('', PORT)
    try:
        httpd = HTTPServer(server_address, WebAppHandler)
        httpd.timeout = 1.0
        print(f"[WEB] Web App rodando em http://{config.local_ip}:{PORT}")
        
        while config.app_state.get("running"):
            httpd.handle_request()
            
    except Exception as e:
        print(f"[WEB] Erro no servidor: {e}")
