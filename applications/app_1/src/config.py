import os

# Environment configuration
is_test = os.getenv("TESTING", "false").lower() == "true" 