#!/bin/bash

# Run entity_1.py and entity_2.py simultaneously
python entity_1.py &
pid1=$!
python entity_2.py &
pid2=$!

# Print "Running" while the scripts are executing
echo "Running..."
wait $pid1
status1=$?
wait $pid2
status2=$?

# Check if both scripts completed successfully
if [ $status1 -eq 0 ] && [ $status2 -eq 0 ]; then
    python stats.py > Final_stats.txt
else
    echo "Error: One or both entity scripts failed."
fi