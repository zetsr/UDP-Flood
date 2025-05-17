#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import time
import sys
import ipaddress # For IP validation (standard library in Python 3.3+)

def parse_address_and_validate_args(args):
    """
    Parses and validates command line arguments.
    Expected format: ["script_name.py", "ip:port", "packet_size", "rate_mbps"]
    Returns: (ip_str, port_int, packet_size_int, rate_float_mbps)
    Exits on error.
    """
    if len(args) != 4:
        print(f"Usage: python3 {args[0]} ip:port packet_size rate_mbps")
        print(f"Example (IPv4): python3 {args[0]} 127.0.0.1:12345 1000 10")
        print(f"Example (IPv6): python3 {args[0]} \"[::1]:12345\" 500 5")
        sys.exit(1)

    # 1. Parse ip:port
    address_str = args[1]
    try:
        if ':' not in address_str:
            raise ValueError("Address format should be IP:PORT. Missing ':'.")
        
        ip_str, port_str = address_str.rsplit(':', 1)
        
        port = int(port_str)
        if not (1 <= port <= 65535):
            raise ValueError(f"Port number {port} is invalid. Must be between 1 and 65535.")

        if ip_str.startswith('[') and ip_str.endswith(']'): # Handle IPv6 with brackets
            ip_str = ip_str[1:-1]
        
        ip_obj = ipaddress.ip_address(ip_str) # Validates IP and gives an object
        
    except ValueError as e:
        print(f"Error: Invalid address format '{address_str}'. Details: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: Could not parse address '{address_str}': {e}")
        sys.exit(1)

    # 2. Parse packet_size
    try:
        packet_size = int(args[2])
        if not (1 <= packet_size <= 65500): # Practical UDP payload limit
            raise ValueError("Packet size must be between 1 and 65500 bytes.")
    except ValueError as e:
        print(f"Error: Invalid packet_size '{args[2]}'. {e}")
        sys.exit(1)

    # 3. Parse rate_mbps
    try:
        rate_mbps = float(args[3])
        if rate_mbps < 0:
            raise ValueError("Rate (Mbps) must be non-negative.")
    except ValueError as e:
        print(f"Error: Invalid rate_mbps '{args[3]}'. {e}")
        sys.exit(1)
        
    return ip_obj, port, packet_size, rate_mbps


def main():
    ip_obj, target_port, packet_size_bytes, rate_mbps = parse_address_and_validate_args(sys.argv)
    target_ip_str = str(ip_obj) # Get string representation for socket
    server_address_tuple = (target_ip_str, target_port)

    print(f"Target: {target_ip_str}:{target_port}")
    print(f"Packet Size: {packet_size_bytes} bytes")
    print(f"Target Rate: {rate_mbps} Mbps")
    print("Starting UDP send. Press Ctrl+C to stop.")

    # Determine address family for socket
    if ip_obj.version == 4:
        address_family = socket.AF_INET
    elif ip_obj.version == 6:
        address_family = socket.AF_INET6
    else:
        print(f"Error: Unknown IP address version for {target_ip_str}") # Should not happen
        sys.exit(1)

    udp_socket = None
    try:
        udp_socket = socket.socket(address_family, socket.SOCK_DGRAM)
    except socket.error as e:
        print(f"Fatal: Could not create socket: {e}")
        sys.exit(1)

    # Construct the message payload
    message_payload = bytes(packet_size_bytes) # Zero-filled payload of specified size

    # Calculate send interval
    send_interval_seconds = 0
    if rate_mbps > 0:
        target_bits_per_second = rate_mbps * 1_000_000
        bits_per_packet = packet_size_bytes * 8
        if bits_per_packet > 0: # Avoid division by zero if packet_size is somehow 0 (already validated though)
            packets_per_second = target_bits_per_second / bits_per_packet
            if packets_per_second > 0:
                 send_interval_seconds = 1.0 / packets_per_second
            else: # Rate is too low for even one packet per second, or packet size is huge
                send_interval_seconds = float('inf') # Effectively means send very slowly or not at all if rate is extremely low
        else: # packet_size is 0
            print("Warning: Packet size is 0. No data will be effectively sent per packet payload.")
            send_interval_seconds = float('inf') # No sending if no data per packet.
    elif rate_mbps == 0:
        print("Rate is 0 Mbps. No packets will be sent continuously. Stopping.")
        if udp_socket:
            udp_socket.close()
        return # Exit if rate is 0

    print(f"Calculated send interval: {send_interval_seconds:.9f} seconds (approx {1.0/send_interval_seconds if send_interval_seconds > 0 else 0:.2f} pps)")
    
    packets_sent_total = 0
    bytes_sent_total = 0
    overall_start_time = time.monotonic()

    # For periodic stats
    last_stats_print_time = overall_start_time
    packets_sent_this_period = 0
    bytes_sent_this_period = 0

    try:
        while True:
            loop_iteration_start_time = time.monotonic()
            
            try:
                udp_socket.sendto(message_payload, server_address_tuple)
                packets_sent_total += 1
                bytes_sent_total += packet_size_bytes # Actual payload size

                packets_sent_this_period += 1
                bytes_sent_this_period += packet_size_bytes
            except socket.error as e:
                print(f"Socket send error: {e} - Retrying shortly.")
                time.sleep(0.1) # Brief pause on send error
                continue # Skip rest of this iteration's logic, try sending again

            current_time = time.monotonic()
            
            # Print stats approximately every second
            if current_time - last_stats_print_time >= 1.0:
                elapsed_period = current_time - last_stats_print_time
                current_rate_actual_mbps = 0
                if elapsed_period > 0:
                    current_rate_actual_mbps = (bytes_sent_this_period * 8) / (elapsed_period * 1_000_000)
                
                total_elapsed_time = current_time - overall_start_time
                overall_avg_rate_mbps = 0
                if total_elapsed_time > 0:
                    overall_avg_rate_mbps = (bytes_sent_total * 8) / (total_elapsed_time * 1_000_000)

                print(f"[{time.strftime('%H:%M:%S')}] Sent {packets_sent_this_period} pkts last {elapsed_period:.2f}s. "
                      f"Rate: {current_rate_actual_mbps:.2f} Mbps. "
                      f"Total: {packets_sent_total} pkts ({(bytes_sent_total / (1024*1024)):.2f} MiB). "
                      f"Avg Rate: {overall_avg_rate_mbps:.2f} Mbps.")
                
                bytes_sent_this_period = 0
                packets_sent_this_period = 0
                last_stats_print_time = current_time

            # Rate control: Calculate time to sleep
            time_taken_this_iteration = time.monotonic() - loop_iteration_start_time
            sleep_duration = send_interval_seconds - time_taken_this_iteration
            
            if sleep_duration > 0:
                time.sleep(sleep_duration)

    except KeyboardInterrupt:
        print("\nSending stopped by user (Ctrl+C).")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        if udp_socket:
            udp_socket.close()
            print("Socket closed.")
        
        final_elapsed_time = time.monotonic() - overall_start_time
        final_avg_rate_mbps = 0
        if final_elapsed_time > 0 and bytes_sent_total > 0 :
            final_avg_rate_mbps = (bytes_sent_total * 8) / (final_elapsed_time * 1_000_000)
        
        print("\n--- Summary ---")
        print(f"Total packets sent: {packets_sent_total}")
        print(f"Total data sent: {bytes_sent_total} bytes ({(bytes_sent_total / (1024*1024)):.3f} MiB)")
        print(f"Total duration: {final_elapsed_time:.2f} seconds")
        print(f"Overall average sending rate: {final_avg_rate_mbps:.2f} Mbps")
        print("Exiting.")

if __name__ == "__main__":
    main()