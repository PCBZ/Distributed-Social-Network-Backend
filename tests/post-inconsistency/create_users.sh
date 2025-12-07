#!/bin/bash

# Script to create users 1 to 5000 via the User Service API
# Usage: ./create_users.sh [start_id] [end_id]

ALB_DNS="cs6650-project-dev-alb-697772938.us-west-2.elb.amazonaws.com"
API_URL="http://${ALB_DNS}/api/users"

START_ID=${1:-1}
END_ID=${2:-5000}
TIMESTAMP=$(date +%s)

CREATED=0
FAILED=0
SKIPPED=0

echo "Creating users from $START_ID to $END_ID..."
echo "API Endpoint: $API_URL"
echo "Timestamp: $TIMESTAMP"
echo "---"

for i in $(seq $START_ID $END_ID); do
    USERNAME="user_${i}_${TIMESTAMP}"
    
    RESPONSE=$(curl -s -X POST "$API_URL" \
        -H "Content-Type: application/json" \
        -d "{\"username\": \"$USERNAME\"}" \
        -w "\n%{http_code}")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    
    if [ "$HTTP_CODE" -eq 201 ] || [ "$HTTP_CODE" -eq 200 ]; then
        CREATED=$((CREATED + 1))
        if [ $((i % 500)) -eq 0 ]; then
            echo "[✓] Created $CREATED users so far... (User $i)"
        fi
    elif echo "$BODY" | grep -q "already exists"; then
        SKIPPED=$((SKIPPED + 1))
    else
        FAILED=$((FAILED + 1))
        echo "[✗] Failed to create user $USERNAME (HTTP $HTTP_CODE): $BODY"
    fi
done

echo "---"
echo "Completed!"
echo "✓ Successfully created: $CREATED users"
echo "⊘ Skipped (already existed): $SKIPPED users"
echo "✗ Failed: $FAILED users"
echo "Total attempted: $((CREATED + FAILED + SKIPPED))"
