import socket
import threading
import time
import os
from teleport import config

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
    if not config.state["sharing_enabled"]: 
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
    
    while config.state["running"]:
        try:
            sock.settimeout(2.0)
            data, addr = sock.recvfrom(1024)
            message = data.decode('utf-8')
            
            # Sincronização de Descoberta Padrão
            if message == "TELEPORT_HELLO" and addr[0] != config.local_ip:
                if config.peer_ip != addr[0]:
                    print(f"[REDE] Novo PC encontrado! IP: {addr[0]}")
                    config.peer_ip = addr[0]
            
            # MÁQUINA DE ESTADOS DA REDE (A MÁGICA DE SABER QUEM TEM O ARQUIVO)
            elif message.startswith("HOLDING:") and addr[0] != config.local_ip:
                config.network_holder_ip = message.split(":")[1]
                print(f"[*] O PC {config.network_holder_ip} agarrou algo! Vá para outro PC e abra a mão para puxar.")
                
            elif message == "HOLDING:NONE" and addr[0] != config.local_ip:
                config.network_holder_ip = None
                
            elif message.startswith("GIVE_ME:") and addr[0] != config.local_ip:
                target_ip = message.split(":")[1]
                if config.state["current_file"]:
                    print(f"[!!!] O PC {target_ip} abriu a mão pedindo o arquivo! Enviando '{config.state['current_file_name']}'...")
                    threading.Thread(target=send_file, args=(target_ip, config.state["current_file"]), daemon=True).start()
                    config.state["current_file"] = None
                    config.state["current_file_name"] = None
                    broadcast_message("HOLDING:NONE")
                config.network_holder_ip = None # Reseta a posse após enviar

        except socket.timeout:
            continue
        except Exception as e:
            pass

def udp_broadcast_sender():
    """Avisa a rede local que este PC está online e pronto para receber/enviar."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    while config.state["running"]:
        if config.state["sharing_enabled"]:
            try:
                sock.sendto(b"TELEPORT_HELLO", ("<broadcast>", config.UDP_PORT))
            except:
                pass
        time.sleep(3) # Grita na rede a cada 3 segundos

def tcp_file_receiver():
    """Servidor TCP que fica aguardando arquivos sendo jogados para cá."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("", config.TCP_PORT))
    sock.listen(5)
    
    print(f"[REDE] Aguardando arquivos em {config.local_ip}:{config.TCP_PORT}...")
    
    while config.state["running"]:
        sock.settimeout(2.0)
        try:
            conn, addr = sock.accept()
            print(f"[REDE] Recebendo arquivo de {addr[0]}...")
            
            # Lê o nome do arquivo (primeiros 64 bytes) e limpa espaços extras
            file_name_raw = conn.recv(64).decode('utf-8').strip()
            if not file_name_raw:
                continue
                
            # Salva o arquivo na mesma pasta que o script está rodando
            save_path = f"RECEBIDO_{file_name_raw}"
            with open(save_path, 'wb') as f:
                while True:
                    data = conn.recv(4096)
                    if not data:
                        break
                    f.write(data)
            print(f"[REDE] Sucesso! Arquivo salvo como {save_path}")
            conn.close()
        except socket.timeout:
            continue
        except Exception as e:
            pass

def send_file(ip_target, file_path):
    """Envia um arquivo real quando o gesto de arremesso ou puxar é detectado."""
    if not config.state["sharing_enabled"]: 
        return
    if not file_path or not os.path.exists(file_path):
        print(f"[REDE] Erro: arquivo não existe ou caminho inválido: {file_path}")
        return
        
    file_name = os.path.basename(file_path)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip_target, config.TCP_PORT))
        
        # Envia o nome do arquivo garantindo que ocupe 64 bytes (padding)
        padded_name = file_name.encode('utf-8')[:64].ljust(64)
        sock.sendall(padded_name)
        
        # Envia o conteúdo do arquivo em blocos
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(4096)
                if not chunk:
                    break
                sock.sendall(chunk)
                
        print(f"[REDE] ZAP! Arquivo '{file_name}' enviado para {ip_target}!")
        sock.close()
    except Exception as e:
        print(f"[REDE] Erro ao enviar: {e}")

# Inicializa o IP local no módulo de configuração compartilhado
config.local_ip = get_local_ip()
