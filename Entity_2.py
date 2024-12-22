import socket
import threading
import time
import random
import logging
import json
from collections import deque

# Configuration
N = 100  # Modulo-10000 sequence numbering
WINDOW_SIZE = 7  # Go-Back-N window size
T1, T2 = 0.1, 0.5  # Packet generation intervals
P = 0.1  # Drop probability
T3, T4 = 0.05, 0.2  # Additional delay intervals
acks_received = [False] * (N+1)  # To track received acknowledgments

server_packet_address = ('localhost', 1003)  # Entity_2 address
server_ack_address = ('localhost', 1004)  # Entity_2 address
client_packet_address = ('localhost', 1001)  # Entity_1 address
client_ack_address = ('localhost', 1002)  # Entity_1 address

# Socket setup
server_packet_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_packet_socket.bind(server_packet_address)

server_ack_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_ack_socket.bind(server_ack_address)

# Queues and variables
outgoing_queue = deque()
left_ptr = 0  # Window control variables
packet_num_sent_last = 0
ack_recieved_upto = 0  # basically it must be left_ptr - 1

# Counters for tracking packets
total_packets_transferred = 0
total_packets_dropped = 0
total_packets_received = 0  # Counter for tracking received packets

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s',
                    filename='entity_2.log', filemode='w')

# Additional variables for tracking times and retransmissions
send_times = {}
receive_times = {}
retransmissions = [0] * N

def create_packet(seq_num):
    """Generate a packet with sequence number."""
    return f"Packet {seq_num}"


def packet_generator():
    """Generate packets at random intervals and add to the queue."""
    global next_seq
    next_seq = 0
    while next_seq < N:
        time.sleep(random.uniform(T1, T2))
        packet = create_packet(next_seq)
        outgoing_queue.append((packet, next_seq))
        logging.info(f"[Entity_2] Generated packet {next_seq}")
        next_seq += 1
    logging.info("All packets generated")


def send_packet(sock, packet, seq_num):
    """Send packet with specified sequence number."""
    global total_packets_transferred, total_packets_dropped
    time.sleep(random.uniform(T3, T4))  # Simulate additional delay
    if random.random() > P or seq_num == N - 1:  # Simulate drop
        frame = f"{seq_num}|{packet}"
        sock.sendto(frame.encode(), client_packet_address)
        if seq_num not in send_times:
            send_times[seq_num] = {'time': time.time(), 'attempts': 1}  # Record first send time and attempt
        else:
            send_times[seq_num]['attempts'] += 1  # Increment send attempts
        retransmissions[seq_num] += 1
        logging.info(f"[Entity_2] Sent packet {seq_num}")
        total_packets_transferred += 1
    else:  # Packet dropped
        logging.info(f"[Entity_2] Packet {seq_num} dropped")
        total_packets_dropped += 1


def sender():
    """Send packets in Go-Back-N protocol, handle acknowledgments and retransmission."""
    global left_ptr, ack_recieved_upto, packet_num_sent_last
    server_ack_socket.settimeout(3)  # Set a timeout for receiving ACKs
    left_ptr = 0
    ack_recieved_upto = -1
    packet_num_sent_last = 0

    while left_ptr < N - 1 or ack_recieved_upto < N - 1:
        if len(outgoing_queue) > 0:
            while packet_num_sent_last + 1 < min(left_ptr + WINDOW_SIZE, N):
                packet, seq_num = outgoing_queue[packet_num_sent_last + 1]
                send_packet(server_ack_socket, packet, seq_num)
                packet_num_sent_last += 1
        else:
            logging.info("Queue is empty")
            time.sleep(3)
            continue
        
        while ack_recieved_upto < N - 1 and not acks_received[ack_recieved_upto + 1]:
            logging.info("LISTENING FOR ACKS")
            try:
                ack, _ = server_ack_socket.recvfrom(1024)
                if ack.decode().startswith("ACK|"):
                    ack_num = int(ack.decode().split('|')[1])
                    if ack_num > ack_recieved_upto:
                        logging.info(f"[Entity_2] Received ACK for packet {ack_num}")
                        for idx in range(left_ptr, ack_num + 1):
                            logging.info(f"Marking {idx} as acked")
                            acks_received[idx] = True
                        left_ptr = ack_num + 1
                        ack_recieved_upto = ack_num
                        with open('entity_2_ack.txt', 'w') as f:
                            f.write(f"{ack_num}\n")
                    elif ack_num < ack_recieved_upto:
                        logging.info(f"Received ack {ack_num} but already received ack upto {ack_recieved_upto}")
                    else:
                        while(1):
                            try:
                                ack, _ = server_ack_socket.recvfrom(1024)
                            except:
                                break
                        for idx in range(left_ptr, min(left_ptr + WINDOW_SIZE, N)):
                            if not acks_received[idx]:
                                send_packet(server_ack_socket, outgoing_queue[idx], idx)
                                logging.info(f"Resending packet {idx}")
                            else:
                                logging.info(f"Packet {idx} already acked but failed to receive ACK for {ack_num}")
                else:
                    logging.info(f"[Entity_2] Received invalid ACK: {ack.decode()}")
            except socket.timeout:
                for idx in range(left_ptr, min(left_ptr + WINDOW_SIZE, N)):
                    if not acks_received[idx]:
                        send_packet(server_ack_socket, outgoing_queue[idx], idx)
                        logging.info(f"Resending packet {idx}")
                    else:
                        logging.info(f"Packet {idx} already acked but failed to receive ACK for {ack_num}")
                logging.info(f"[Entity_2] Timeout, resending window from {left_ptr} to {left_ptr + WINDOW_SIZE}, and ack_recieved_upto: {ack_recieved_upto}")
                break
            except Exception as e:
                logging.info(e)
    logging.info("All packets sent")


def receiver():
    """Receive packets and send back acknowledgments in the Go-Back-N protocol."""
    global total_packets_received
    expected_seq_num = 0
    while True:
        try:
            frame, _ = server_packet_socket.recvfrom(1024)
            time.sleep(random.uniform(T3, T4))  # Simulate additional delay
            data = frame.decode()
            if not data.startswith("ACK|"):
                seq_num, packet = data.split('|')
                seq_num = int(seq_num)
                if seq_num == expected_seq_num:
                    logging.info(f"[Entity_2] Received in-sequence packet {seq_num}")
                    total_packets_received += 1
                    receive_times[seq_num] = time.time()  # Record receive time
                    ack_frame = f"ACK|{seq_num}"
                    server_packet_socket.sendto(ack_frame.encode(), client_ack_address)
                    logging.info(f"[Entity_2] Sent ACK for packet {seq_num}")
                    expected_seq_num += 1
                else:
                    ack_frame = f"ACK|{expected_seq_num - 1}"
                    server_packet_socket.sendto(ack_frame.encode(), client_ack_address)
                    logging.info(f"[Entity_2] Out-of-order packet {seq_num} received, expected {expected_seq_num}, consider it as dropped")
            else:
                logging.info(f"[Entity_2] Received invalid packet: {data}")
        except socket.timeout:
            logging.info("[Entity_2] Receiver timeout waiting for packets")
        except ConnectionResetError:
            logging.info("[Entity_2] Connection reset by peer, stopping receiver")
            break
    logging.info("All packets received")


def write_times_to_json():
    """Write send and receive times to a JSON file."""
    send = {
        "send_times": send_times,
    }
    receive = {
        "receive_times": receive_times
    }
    with open('entity_2_send_time.json', 'w') as f:
        json.dump(send, f)
    with open('entity_1_receive_time.json', 'w') as f:
        json.dump(receive, f)


def start_entity():
    server_ack_socket.settimeout(6.0)
    threading.Thread(target=packet_generator, daemon=True).start()
    threading.Thread(target=sender, daemon=True).start()
    threading.Thread(target=receiver, daemon=True).start()
    while True:
        time.sleep(2)
        logging.info(f"Total packets transferred: {total_packets_transferred}")
        logging.info(f"Total packets dropped: {total_packets_dropped}")
        logging.info(f"Total packets received: {total_packets_received}")
        check = 0
        with open('entity_1_ack.txt', 'r') as f:
            check = int(f.read())
        if total_packets_received == N and ack_recieved_upto == N - 1 and check == N - 1:
            time.sleep(5)
            write_times_to_json()
            logging.info(f"Total packets transferred: {total_packets_transferred}")
            logging.info(f"Total packets dropped: {total_packets_dropped}")
            logging.info(f"Total packets received: {total_packets_received}")
            break


if __name__ == "__main__":
    server_ack_socket.settimeout(10)
    while True:
        frame, addr = server_ack_socket.recvfrom(1024)
        if frame.decode() == "CHECK":
            server_ack_socket.sendto(b"CHECK_ACK", addr)
            break
    start_entity()
