#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import time
import sys
import ipaddress
import argparse

# A2S_INFO 请求包
A2S_INFO_REQUEST_PAYLOAD = b"Source Engine Query\x00"
A2S_INFO_REQUEST = b'\xFF\xFF\xFF\xFFT' + A2S_INFO_REQUEST_PAYLOAD

# 通用 A2S 响应包头前缀
A2S_GENERIC_RESPONSE_PREFIX = b'\xFF\xFF\xFF\xFF'

# 常量定义
SOCKET_TIMEOUT_SECONDS = 5.0  # 套接字接收超时时间，单位：秒
RECEIVE_BUFFER_SIZE = 4096    # 接收缓冲区大小，单位：字节

def parse_address(address_str):
    """
    解析并验证 IP:PORT 格式的地址字符串。
    返回: (ip_str, port_int) 元组
    """
    try:
        if ':' not in address_str:
            raise ValueError("地址格式应为 IP:PORT。缺少 ':'。")
        
        ip_str, port_str = address_str.rsplit(':', 1)
        port = int(port_str)
        if not (1 <= port <= 65535):
            raise ValueError(f"端口号 {port} 无效，必须在 1 到 65535 之间。")

        if ip_str.startswith('[') and ip_str.endswith(']'):
            ip_str = ip_str[1:-1]
        
        ipaddress.ip_address(ip_str)
        return ip_str, port
    except ValueError as e:
        print(f"错误：提供的地址 '{address_str}' 格式无效或不正确。详情：{e}")
        sys.exit(1)
    except Exception as e:
        print(f"错误：解析地址 '{address_str}' 时发生意外错误：{e}")
        sys.exit(1)

def ping_udp(ip, port, single=False):
    """
    执行 UDP ping，发送 A2S_INFO 请求并等待响应。
    single=True 时，仅执行一次 ping 并返回。
    返回：0（成功）或 1（失败）
    """
    print(f"[{time.strftime('%H:%M:%S')}] Starting ping to {ip}:{port}")
    try:
        ip_obj = ipaddress.ip_address(ip)
        address_family = socket.AF_INET if ip_obj.version == 4 else socket.AF_INET6
        udp_socket = socket.socket(address_family, socket.SOCK_DGRAM)
        udp_socket.settimeout(SOCKET_TIMEOUT_SECONDS)
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 严重错误: 无法创建套接字: {e}")
        return 1

    try:
        start_time_ns = time.monotonic_ns()
        udp_socket.sendto(A2S_INFO_REQUEST, (ip, port))
        print(f"[{time.strftime('%H:%M:%S')}] Sent A2S_INFO request to {ip}:{port}")
        data_received, addr_from_recv = udp_socket.recvfrom(RECEIVE_BUFFER_SIZE)
        end_time_ns = time.monotonic_ns()

        print(f"[{time.strftime('%H:%M:%S')}] Received data from {addr_from_recv[0]}:{addr_from_recv[1]}, size: {len(data_received)} bytes")
        if addr_from_recv[0] == ip:
            if data_received.startswith(A2S_GENERIC_RESPONSE_PREFIX):
                ping_duration_ms = (end_time_ns - start_time_ns) / 1_000_000
                print(f"[{time.strftime('%H:%M:%S')}] 来自 {addr_from_recv[0]}:{addr_from_recv[1]} 的回复, Ping: {ping_duration_ms:.3f} ms, 大小: {len(data_received)} 字节")
                return 0
            else:
                print(f"[{time.strftime('%H:%M:%S')}] 警告: 从 {addr_from_recv[0]}:{addr_from_recv[1]} 收到意外的UDP包 (非A2S格式)。大小: {len(data_received)} 字节。")
                return 1
        else:
            print(f"[{time.strftime('%H:%M:%S')}] 警告: 从意外的IP {addr_from_recv[0]}:{addr_from_recv[1]} 收到UDP包 (期望来自 {ip})。已忽略。")
            return 1
    except socket.timeout:
        print(f"[{time.strftime('%H:%M:%S')}] 超时: {ip}:{port} 在 {SOCKET_TIMEOUT_SECONDS} 秒内无响应。")
        return 1
    except ConnectionRefusedError:
        print(f"[{time.strftime('%H:%M:%S')}] 错误: 连接被 {ip}:{port} 拒绝。服务器可能已关闭或端口不开放。")
        return 1
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 错误: Ping {ip}:{port} 时发生意外问题 - {e}")
        return 1
    finally:
        udp_socket.close()
        print(f"[{time.strftime('%H:%M:%S')}] Socket closed for {ip}:{port}")

def main():
    parser = argparse.ArgumentParser(description="Ping a Steam server using A2S_INFO protocol.")
    parser.add_argument("address", help="Server address in IP:PORT format (e.g., 123.1.1.1:12345 or [2001:db8::1]:27015)")
    parser.add_argument("--single", action="store_true", help="Perform a single ping and exit")
    args = parser.parse_args()

    target_ip, target_port = parse_address(args.address)
    
    if args.single:
        result = ping_udp(target_ip, target_port, single=True)
        print(f"[{time.strftime('%H:%M:%S')}] Ping result: {'success' if result == 0 else 'failed'} (returncode: {result})")
        sys.exit(result)
    
    print(f"[{time.strftime('%H:%M:%S')}] 正在使用 A2S_INFO 协议 Ping Steam 服务器: {target_ip}:{target_port}")
    print(f"[{time.strftime('%H:%M:%S')}] 查询间隔: 0.5 秒, 响应超时: {SOCKET_TIMEOUT_SECONDS} 秒。")
    print(f"[{time.strftime('%H:%M:%S')}] 按 Ctrl+C 停止。")
    
    try:
        while True:
            result = ping_udp(target_ip, target_port)
            print(f"[{time.strftime('%H:%M:%S')}] Ping result: {'success' if result == 0 else 'failed'} (returncode: {result})")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print(f"\n[{time.strftime('%H:%M:%S')}] 信息: Ping 进程被用户通过 Ctrl+C 中断。")
    finally:
        print(f"[{time.strftime('%H:%M:%S')}] 程序退出。")
        sys.exit(0)

if __name__ == "__main__":
    main()