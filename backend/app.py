from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:krzx@localhost:5432/soc_deadman"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# -----------------------------
# Database Model
# -----------------------------

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(100))
    confidence = db.Column(db.Float)
    screenshot = db.Column(db.String(300))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# -----------------------------
# Routes
# -----------------------------

@app.route("/")
def dashboard():
    events = Event.query.order_by(Event.timestamp.desc()).all()
    return render_template("dashboard.html", events=events)

@app.route("/api/events", methods=["POST"])
def receive_event():
    data = request.json

    event = Event(
        event_type=data.get("event_type"),
        confidence=data.get("confidence", 0),
        screenshot=data.get("screenshot", "")
    )

    db.session.add(event)
    db.session.commit()

    return jsonify({"status": "success"})

@app.route("/api/status", methods=["POST"])
def status():
    return jsonify({"status": "alive"})

# -----------------------------
# Main
# -----------------------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(host="0.0.0.0", port=5000, debug=True)