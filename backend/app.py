from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os

app = Flask(__name__, static_folder="../backend/static")
CORS(app)

# Dynamic variable
current_message = "Hello, world!"

# API routes
@app.route("/api/message")
def get_message():
    return jsonify({"message": current_message})

@app.route("/api/message", methods=["POST"])
def set_message():
    global current_message
    data = request.get_json()
    current_message = data.get("message", "")
    return jsonify({"message": current_message})

# Serve React frontend
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    app.run(debug=True)
