```ruby                                                                         
▄█████ ▄████▄ ▄█████     ████▄  ██████ ▄████▄ ████▄  ██▄  ▄██ ▄████▄ ███  ██ 
▀▀▀▄▄▄ ██  ██ ██     ▄▄▄ ██  ██ ██▄▄   ██▄▄██ ██  ██ ██ ▀▀ ██ ██▄▄██ ██ ▀▄██ 
█████▀ ▀████▀ ▀█████     ████▀  ██▄▄▄▄ ██  ██ ████▀  ██    ██ ██  ██ ██   ██ 
```                                                                             
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)                                                                                                                        
![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-Backend-black?style=for-the-badge&logo=flask)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue?style=for-the-badge&logo=postgresql)
![YOLOv8](https://img.shields.io/badge/YOLOv8-AI-green?style=for-the-badge)
![SOC](https://img.shields.io/badge/SOC-Monitoring-red?style=for-the-badge)         

> AI-powered SOC monitoring and forensic dashboard for real-time unauthorized user detection and incident logging.

## What It Does

- Monitors live camera feeds for unauthorized users
- Detects faces using OpenCV and YOLOv8
- Compares detected faces against authorized profiles
- Captures forensic screenshots when unknown users appear
- Sends detection events to a Flask backend API
- Stores incidents and metadata in PostgreSQL
- Displays real-time monitoring data in a SOC-style dashboard
- Logs timestamps, confidence scores, and screenshot evidence
- Provides a lightweight incident response monitoring workflow
- Simulates real-world SOC alerting and forensic collection systems
---
## Features

- Real-time face detection
- Unauthorized user monitoring
- Automatic screenshot capture
- Flask web dashboard
- PostgreSQL event storage
- Event confidence tracking
- Incident logging system
---

## Architecture

```text
Camera Feed
    ↓
YOLO/OpenCV Detection
    ↓
Detection Agent
    ↓
Flask API Backend
    ↓
PostgreSQL Database
    ↓
SOC Dashboard
```
---

## Tech Stack

| Component | Technology |
|----------|-------------|
| Backend | Flask |
| Database | PostgreSQL |
| Detection | OpenCV + YOLOv8 |
| ORM | SQLAlchemy |
| Frontend | HTML/CSS |
| Language | Python |

---

## Installation

### Clone Repository

```bash
git clone https://github.com/prajavkrish/SOC-DEADMAN.git
cd SOC-DEADMAN
```

### Create Virtual Environment

```bash
python -m venv venv
```

### Activate

#### Windows

```bash
venv\Scripts\activate
```

#### Linux

```bash
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Setup PostgreSQL

Create database:

```sql
CREATE DATABASE soc_deadman;
```

Update `.env`

```env
DATABASE_URL=postgresql://postgres:password@localhost/soc_deadman
```

---

## Run Backend

```bash
cd backend
python app.py
```

Backend runs on:

```text
http://127.0.0.1:5000
```

---

## Run Detection Agent

```bash
python detection_agent.py
```

---

## Detection Workflow

1. Camera captures frame
2. Face detection runs
3. Authorized face comparison
4. Unknown user detected
5. Screenshot captured
6. Event sent to backend
7. Dashboard updated

---

## Future Improvements

- Telegram alerts
- Email notifications
- Docker deployment
- Multi-camera support
- Threat severity scoring
- User authentication
- Live websocket alerts
- Linux deployment

---

## Disclaimer

Educational and defensive security monitoring project.

                                                                                                                             
                                                                                                                             
                                                                                                                             
