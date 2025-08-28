import os
import subprocess

# Step 1: Build frontend (optional)
subprocess.check_call(["npm", "install"], cwd="frontend")
subprocess.check_call(["npm", "run", "build"], cwd="frontend")

# Step 2: Set environment variables for Flask
os.environ["FLASK_APP"] = "backend.app"
os.environ["FLASK_ENV"] = "development"
os.environ["FLASK_RUN_PORT"] = "5001"

# Step 3: Run Flask
subprocess.run(["flask", "run"])
