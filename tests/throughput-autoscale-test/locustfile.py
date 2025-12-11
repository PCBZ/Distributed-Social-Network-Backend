"""
Throughput and AutoScale Test for CS6650 Social Media Platform
Tests system performance under varying load (10 to 1500 concurrent users)
"""

import random
import time
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner, WorkerRunner

# Configuration
ALB_HOST = "http://cs6650-project-dev-alb-1020525438.us-west-2.elb.amazonaws.com"

# User pool configuration
# Assumes you have pre-generated users with IDs from 1 to MAX_USER_ID
MIN_USER_ID = 1
MAX_USER_ID = 1500  # Currently 1500 users loaded in DynamoDB

# Timeline retrieval limit - IMPORTANT to prevent database explosion
# Limit number of posts retrieved per timeline request (reduced to 10)
TIMELINE_LIMIT = 10

# Post content settings
MAX_POST_LENGTH = 280  # Maximum characters per post (Twitter-like limit)

# Test behavior ratios
READ_WEIGHT = 8   # 80% reads (timeline retrieval)
WRITE_WEIGHT = 2  # 20% writes (post creation)

# Test results tracking
test_results = {
    "start_time": None,
    "end_time": None,
    "requests": [],
    "user_counts": []
}


class SocialMediaUser(HttpUser):
    """
    Simulates a user interacting with the social media platform.
    Randomly selects user IDs from the pre-generated pool.
    """

    host = ALB_HOST
    # Wait 2-5 seconds between requests to reduce overall load
    wait_time = between(2, 5)

    def on_start(self):
        """Called when a simulated user starts."""
        # Randomly assign this Locust user a user_id from the pool
        self.user_id = random.randint(MIN_USER_ID, MAX_USER_ID)
        self.target_user_id = random.randint(MIN_USER_ID, MAX_USER_ID)

    @task(READ_WEIGHT)  # 80% - Read operation
    def get_timeline(self):
        """
        GET user timeline - Read-heavy operation
        Tests Timeline Service integration

        IMPORTANT: Uses TIMELINE_LIMIT to prevent excessive data retrieval
        """
        try:
            with self.client.get(
                f"/api/timeline/{self.user_id}",
                # Limit results to prevent database explosion
                params={"limit": TIMELINE_LIMIT},
                catch_response=True,
                name="GET /api/timeline/:user_id"
            ) as response:
                if response.status_code == 200:
                    response.success()
                elif response.status_code == 404:
                    # Acceptable if user has no posts yet
                    response.success()
                elif response.status_code == 504:
                    # 504 Gateway Timeout is acceptable for pull/hybrid with many followings
                    response.success()
                else:
                    response.failure(f"Got status code {response.status_code}")
        except Exception as e:
            print(f"Timeline request failed: {e}")

    @task(WRITE_WEIGHT)  # 20% - Write operation
    def create_post(self):
        """
        POST create new post - Tests Post Service and triggers timeline updates

        IMPORTANT: Limited post content length to prevent storage issues
        """
        try:
            # Generate post content with length limit
            timestamp = int(time.time())
            content = f"Load test post from user {self.user_id} at {timestamp}"

            # Ensure content doesn't exceed maximum length
            if len(content) > MAX_POST_LENGTH:
                content = content[:MAX_POST_LENGTH]

            with self.client.post(
                "/api/posts",
                json={
                    "user_id": self.user_id,
                    "content": content
                },
                catch_response=True,
                name="POST /api/posts"
            ) as response:
                if response.status_code == 200:
                    # POST must return 200 for success
                    response.success()
                elif response.status_code == 201:
                    # 201 Created is also acceptable
                    response.success()
                else:
                    # 503, 504, or any other error codes are failures
                    response.failure(f"Got status code {response.status_code}")
        except Exception as e:
            print(f"Create post request failed: {e}")


# Event listeners for data collection
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test starts."""
    test_results["start_time"] = time.time()
    print(f"\n{'='*60}")
    print(f"Throughput & AutoScale Test Starting")
    print(f"Target: {MIN_USER_ID} to {MAX_USER_ID} user pool")
    print(f"Timeline Limit: {TIMELINE_LIMIT} posts per request")
    print(f"Read/Write Ratio: {READ_WEIGHT*10}% / {WRITE_WEIGHT*10}%")
    print(f"Max Post Length: {MAX_POST_LENGTH} characters")
    print(f"ALB Host: {ALB_HOST}")
    print(f"{'='*60}\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test stops."""
    test_results["end_time"] = time.time()
    duration = test_results["end_time"] - test_results["start_time"]
    print(f"\n{'='*60}")
    print(f"Test Completed")
    print(f"Duration: {duration:.2f} seconds")
    print(f"{'='*60}\n")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Track each request for analysis."""
    test_results["requests"].append({
        "timestamp": time.time(),
        "type": request_type,
        "name": name,
        "response_time": response_time,
        "success": exception is None
    })


# Usage instructions when run directly
if __name__ == "__main__":
    print("""
    Throughput & AutoScale Test - Usage Instructions
    =================================================
    
    This locustfile tests system performance under varying load.
    
    PREREQUISITE:
    1. Ensure you have generated at least 5000 users and social relationships
       in your database using the data generation scripts.
    
    IMPORTANT SETTINGS TO PREVENT DATABASE ISSUES:
    - TIMELINE_LIMIT = 20: Limits posts per timeline request
    - MAX_POST_LENGTH = 280: Prevents excessive content storage
    - READ_WEIGHT = 8 (80%), WRITE_WEIGHT = 2 (20%): Balanced load
    
    RUNNING THE TEST:
    
    Option 1: Web UI (Recommended for visualization)
    ------------------------------------------------
    locust -f locustfile.py --host={ALB_HOST}
    
    Then open http://localhost:8089 and configure:
    - Number of users: Start with 10, ramp up to 1500
    - Spawn rate: 10 users/second (adjust as needed)
    
    Option 2: Headless (For automated testing)
    ------------------------------------------
    # Step load test (recommended)
    locust -f locustfile.py --host={ALB_HOST} \\
           --users 10 --spawn-rate 5 --run-time 5m --headless
    
    # Then increase gradually:
    locust -f locustfile.py --host={ALB_HOST} \\
           --users 50 --spawn-rate 10 --run-time 5m --headless
    
    locust -f locustfile.py --host={ALB_HOST} \\
           --users 100 --spawn-rate 10 --run-time 5m --headless
    
    # ... continue up to 1500 users
    
    Option 3: Automated Step Load Script
    -------------------------------------
    See run_throughput_test.ps1 for automated step-load testing
    
    MONITORING:
    - CloudWatch Dashboard for ECS task count, CPU, memory
    - ALB metrics for request count and response times
    - DynamoDB consumed capacity units
    
    EXPECTED RESULTS:
    - Observe ECS auto-scaling as load increases
    - Measure response time degradation at high load
    - Identify system bottlenecks (DB, ALB, ECS)
    """.format(ALB_HOST=ALB_HOST))
