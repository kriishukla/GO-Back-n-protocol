import json

def load_times(file_path):
    """Load times from a JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)

def calculate_delays_and_average(send_times, receive_times):
    """Calculate the delay for each packet and the average delay."""
    total_delay = 0
    count = 0
    for seq_num, send_time in send_times.items():
        if seq_num in receive_times:
            delay = receive_times[seq_num] - send_time['time']
            if delay >= 0:
                total_delay += delay
                count += 1
    average_delay = total_delay / count if count > 0 else 0
    return average_delay

def calculate_average_attempts(send_times):
    """Calculate the average number of send attempts."""
    total_attempts = 0
    count = 0
    for seq_num, data in send_times.items():
        total_attempts += data['attempts']
        count += 1
    return total_attempts / count if count > 0 else 0

def main():
    # Load times from JSON files
    entity_1_send_times = load_times('entity_1_send_time.json')
    entity_1_receive_times = load_times('entity_1_receive_time.json')
    entity_2_send_times = load_times('entity_2_send_time.json')
    entity_2_receive_times = load_times('entity_2_receive_time.json')

    # Calculate average delays
    avg_delay_entity_1 = calculate_delays_and_average(entity_1_send_times['send_times'], entity_1_receive_times['receive_times'])
    avg_delay_entity_2 = calculate_delays_and_average(entity_2_send_times['send_times'], entity_2_receive_times['receive_times'])

    # Calculate average send attempts
    avg_attempts_entity_1 = calculate_average_attempts(entity_1_send_times['send_times'])
    avg_attempts_entity_2 = calculate_average_attempts(entity_2_send_times['send_times'])

    print(f"Average delay for packets sent from Entity 1 to Entity 2: {avg_delay_entity_1} seconds")
    print(f"Average delay for packets sent from Entity 2 to Entity 1: {avg_delay_entity_2} seconds")
    print(f"Average number of send attempts for Entity 1: {avg_attempts_entity_1}")
    print(f"Average number of send attempts for Entity 2: {avg_attempts_entity_2}")

if __name__ == "__main__":
    main()
