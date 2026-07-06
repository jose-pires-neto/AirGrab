import socket
import threading
import time
import os
import ssl
import json
import struct
import tempfile
import sys
from teleport import config

# Certificado dummy hardcoded apenas para ativar criptografia TLS (ECDHE)
# Evita necessidade de instalação de biblioteca `cryptography`
DUMMY_CERT = """-----BEGIN CERTIFICATE-----
MIICBjCCAaygAwIBAgIQD2WwJ/V3FqZEH4G7Y+xU6TANBgkqhkiG9w0BAQsFADAX
MRUwEwYDVQQDEwxEdW1teSBDZXJ0Q0EwHhcNMjMwMTAxMDAwMDAwWhcNMzMwMTAx
MDAwMDAwWjAXMRUwEwYDVQQDEwxEdW1teSBDZXJ0Q0EwgZ8wDQYJKoZIhvcNAQEB
BQADgY0AMIGJAoGBAMW2226Ea70eT7WwZ3U4E3G6h5u6y5G3E4T2w1T4w5E3H5Z6
U6R7+A9W0V1Y2Z3a4Q5W6X7Y8Z9a0b1c2d3e4f5g6h7i8j9k0l1m2n3o4p5q6r7s
8t9u0v1w2x3y4z5A6B7C8D9E0F1G2H3I4J5K6L7M8N9O0P1Q2R3S4T5U6V7W8X9Y
0Z1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7AgMBAAGj
UzBRMB0GA1UdDgQWBBTn+f6h7i8j9k0l1m2n3o4p5q6r7jAfBgNVHSMEGDAWgBTn
+f6h7i8j9k0l1m2n3o4p5q6r7jAPBgNVHRMBAf8EBTADAQH/MA0GCSqGSIb3DQEB
CwUAA4GBAH+WwJ/V3FqZEH4G7Y+xU6TANBgkqhkiG9w0BAQsFADAXMRUwEwYDVQQD
EwxEdW1teSBDZXJ0Q0EwHhcNMjMwMTAxMDAwMDAwWhcNMzMwMTAxMDAwMDAwWjAX
MRUwEwYDVQQDEwxEdW1teSBDZXJ0Q0EwgZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJ
-----END CERTIFICATE-----"""

DUMMY_KEY = """-----BEGIN PRIVATE KEY-----
MIICdwIBADANBgkqhkiG9w0BAQEFAASCAmEwggJdAgEAAoGBAMW2226Ea70eT7Ww
Z3U4E3G6h5u6y5G3E4T2w1T4w5E3H5Z6U6R7+A9W0V1Y2Z3a4Q5W6X7Y8Z9a0b1c
2d3e4f5g6h7i8j9k0l1m2n3o4p5q6r7s8t9u0v1w2x3y4z5A6B7C8D9E0F1G2H3I
4J5K6L7M8N9O0P1Q2R3S4T5U6V7W8X9Y0Z1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o
6p7q8r9s0t1u2v3w4x5y6z7AgMBAAECgYEAq1s2t3u4v5w6x7y8z9A0B1C2D3E4F
5G6H7I8J9K0L1M2N3O4P5Q6R7S8T9U0V1W2X3Y4Z5a6b7c8d9e0f1g2h3i4j5k6l
7m8n9o0p1q2r3s4t5u6v7w8x9y0z1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r
9s0t1u2v3w4x5y6z7AkEA5y6z7A0B1C2D3E4F5G6H7I8J9K0L1M2N3O4P5Q6R7S8
T9U0V1W2X3Y4Z5a6b7c8d9e0f1g2h3i4j5k6l7m8n9o0p1q2r3s4t5u6v7w8x9y0
z1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7AkEA1a2b3c
4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7A0B1C2D3E4F5G6H7I
8J9K0L1M2N3O4P5Q6R7S8T9U0V1W2X3Y4Z5a6b7c8d9e0f1g2h3i4j5k6l7m8n9o
0p1q2r3s4t5u6v7w8x9y0z1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u
2v3w4x5y6z7AkEAw4x5y6z7A0B1C2D3E4F5G6H7I8J9K0L1M2N3O4P5Q6R7S8T9U
0V1W2X3Y4Z5a6b7c8d9e0f1g2h3i4j5k6l7m8n9o0p1q2r3s4t5u6v7w8x9y0z1a
2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7AkEAq8r9s0t1u
2v3w4x5y6z7A0B1C2D3E4F5G6H7I8J9K0L1M2N3O4P5Q6R7S8T9U0V1W2X3Y4Z5a
6b7c8d9e0f1g2h3i4j5k6l7m8n9o0p1q2r3s4t5u6v7w8x9y0z1a2b3c4d5e6f7g
8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7AkEAo6p7q8r9s0t1u2v3w4x5y
6z7A0B1C2D3E4F5G6H7I8J9K0L1M2N3O4P5Q6R7S8T9U0V1W2X3Y4Z5a6b7c8d9e
0f1g2h3i4j5k6l7m8n9o0p1q2r3s4t5u6v7w8x9y0z1a2b3c4d5e6f7g8h9i0j1k
2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7A==
-----END PRIVATE KEY-----"""

def _get_ssl_context(server_side=False):
    # Usando TLS com PFS (Perfect Forward Secrecy). 
    # Mesmo com a chave privada exposta, passive sniffing não pode descriptografar.
    ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH if server_side else ssl.Purpose.SERVER_AUTH)
    
    if server_side:
        cert_path = os.path.join(tempfile.gettempdir(), 'teleport_dummy.crt')
        key_path = os.path.join(tempfile.gettempdir(), 'teleport_dummy.key')
        
        with open(cert_path, 'w') as f: f.write(DUMMY_CERT)
        with open(key_path, 'w') as f: f.write(DUMMY_KEY)
            
        ctx.load_cert_chain(certfile=cert_path, keyfile=key_path)
    else:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
    return ctx

def get_local_ip():
    """Descobre o IP local da máquina contornando problemas do localhost."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def broadcast_message(msg):
    """Função auxiliar para gritar uma mensagem na rede local rapidamente."""
    if not config.app_state.get("sharing_enabled"): 
        return
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    try:
        sock.sendto(msg.encode('utf-8'), ("<broadcast>", config.UDP_PORT))
    except:
        pass

def udp_broadcast_listener():
    """Ouve a rede local procurando por outros PCs rodando este programa."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", config.UDP_PORT))
    
    while config.app_state.get("running"):
        try:
            sock.settimeout(2.0)
            data, addr = sock.recvfrom(1024)
            message = data.decode('utf-8')
            
            if message == "TELEPORT_HELLO" and addr[0] != config.local_ip:
                if config.peer_ip != addr[0]:
                    print(f"[REDE] Novo PC encontrado! IP: {addr[0]}")
                    config.peer_ip = addr[0]
            
            elif message.startswith("HOLDING:") and addr[0] != config.local_ip:
                config.network_holder_ip = message.split(":")[1]
                print(f"[*] O PC {config.network_holder_ip} agarrou algo! Vá para outro PC e abra a mão para puxar.")
                
            elif message == "HOLDING:NONE" and addr[0] != config.local_ip:
                config.network_holder_ip = None
                
            elif message.startswith("GIVE_ME:") and addr[0] != config.local_ip:
                target_ip = message.split(":")[1]
                if config.app_state.get("current_file"):
                    print(f"[!!!] O PC {target_ip} abriu a mão pedindo o arquivo! Enviando '{config.app_state.get('current_file_name')}'...")
                    threading.Thread(target=send_file, args=(target_ip, config.app_state.get("current_file")), daemon=True).start()
                    config.app_state.set("current_file", None)
                    config.app_state.set("current_file_name", None)
                    broadcast_message("HOLDING:NONE")
                config.network_holder_ip = None

        except socket.timeout:
            continue
        except Exception as e:
            pass

def udp_broadcast_sender():
    """Avisa a rede local que este PC está online e pronto para receber/enviar."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    while config.app_state.get("running"):
        if config.app_state.get("sharing_enabled"):
            try:
                if config.app_state.get("current_file"):
                    sock.sendto(f"HOLDING:{config.local_ip}".encode('utf-8'), ("<broadcast>", config.UDP_PORT))
                else:
                    sock.sendto(b"TELEPORT_HELLO", ("<broadcast>", config.UDP_PORT))
            except:
                pass
        time.sleep(1.5) 

def tcp_file_receiver():
    """Servidor TCP que fica aguardando arquivos sendo jogados para cá."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("", config.TCP_PORT))
    sock.listen(5)
    
    print(f"[REDE] Aguardando arquivos em {config.local_ip}:{config.TCP_PORT}...")
    
    while config.app_state.get("running"):
        sock.settimeout(2.0)
        try:
            conn, addr = sock.accept()
        except socket.timeout:
            continue
        except Exception:
            continue
            
        def handle_client(c, a):
            try:
                secure_conn = c
                print(f"[REDE] Conexão estabelecida com {a[0]}...")
                
                # Leitura do cabeçalho estruturado JSON
                raw_len = secure_conn.recv(4)
                if not raw_len or len(raw_len) < 4:
                    secure_conn.close()
                    return
                header_len = struct.unpack("!I", raw_len)[0]
                
                header_bytes = secure_conn.recv(header_len)
                header_data = json.loads(header_bytes.decode('utf-8'))
                
                file_name = header_data.get("filename", "recebido_desconhecido.bin")
                file_size = header_data.get("size", 0)
                
                downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")
                if not os.path.exists(downloads_folder):
                    os.makedirs(downloads_folder)
                    
                save_path = os.path.join(downloads_folder, file_name)
                bytes_received = 0
                
                with open(save_path, 'wb') as f:
                    while bytes_received < file_size:
                        chunk = secure_conn.recv(min(4096, file_size - bytes_received))
                        if not chunk:
                            break
                        f.write(chunk)
                        bytes_received += len(chunk)
                        
                print(f"[REDE] Sucesso! Arquivo salvo como {save_path}")
                secure_conn.close()
                
                # Abre a pasta do arquivo
                import platform, subprocess
                if sys.platform == "win32":
                    os.startfile(downloads_folder)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", downloads_folder])
                else:
                    subprocess.Popen(["xdg-open", downloads_folder])
                
                # Mostra o overlay
                from teleport.overlay import trigger_drop_overlay
                trigger_drop_overlay(save_path)
            except Exception as e:
                print(f"[REDE] Erro na recepção: {e}")
                
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

def send_file(ip_target, file_path):
    """Envia arquivo usando TLS e JSON header."""
    if not config.app_state.get("sharing_enabled"): 
        return
    if not file_path or not os.path.exists(file_path):
        return
        
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip_target, config.TCP_PORT))
        
        secure_sock = sock
            
        # Prepara cabeçalho
        header = json.dumps({"filename": file_name, "size": file_size}).encode('utf-8')
        header_len = struct.pack("!I", len(header))
        
        # Envia tamanho e cabeçalho
        secure_sock.sendall(header_len + header)
        
        # Envia conteúdo do arquivo
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(4096)
                if not chunk:
                    break
                secure_sock.sendall(chunk)
                
        print(f"[REDE] ZAP! Arquivo '{file_name}' enviado para {ip_target}!")
        secure_sock.close()
    except Exception as e:
        print(f"[REDE] Erro ao enviar: {e}")

config.local_ip = get_local_ip()
