# TUA Hackathon: Mars Autonomous Exploration System

Welcome to the Al-Tech Mars Exploration project! This repository contains a fully automated, closed-loop AI software suite designed to autonomously identify critical Initial In-Situ Resource Utilization (ISRU) elements—such as Water Ice and Regolith—and deploy an autonomous rover to collect them. 

## 🚀 System Architecture
We have designed a Centralized Hub pattern where a Python Mission Control securely talks to our Rover (via MAVLink), processes vision (YOLOv8), and serves live telemetry to a beautiful interactive Web Dashboard.

```mermaid
graph TD
    %% Define Components
    subgraph Gazebo Simulation
        Rover[Autonomous Rover<br>(ArduRover)]
        Camera[Rover Camera]
    end

    subgraph Python Backend (Mission Control)
        Vision[YOLOv8 Detection Module]
        Logic[Decision & Task Manager<br>(Priority Queue)]
        MAVLink[PyMAVLink Interface]
        WS_Server[WebSocket Server<br>(FastAPI)]
    end

    subgraph User Interface (Frontend)
        UI[HTML + JS Dashboard<br>(mars_rover_tua_v0.html)]
    end

    %% Define Connections
    Camera -- "Video Stream" --> Vision
    Vision -- "Bounding Boxes + Classes" --> Logic
    Rover -- "Telemetry (GPS, Heading)" --> MAVLink
    MAVLink -- "Rover X, Y" --> Logic
    
    Logic -- "Resource Coords (X, Y)" --> WS_Server
    MAVLink -- "Rover Status" --> WS_Server
    
    WS_Server <== "Real-Time JSON (Bi-directional)" ==> UI
    
    Logic -- "Target Waypoint (X, Y)" --> MAVLink
    MAVLink -- "Command: DRIVE TO" --> Rover
```

## 📁 Repository Structure
* **`martian.world`**: A lightweight, robust Gazebo XML environment with dummy test objects (White cylinders = Ice, Brown spheres = Regolith).
* **`backend_skeleton.py`**: The central brain. Runs a FastAPI Web Server and WebSocket link while orchestrating YOLO vision and PyMAVLink paths.
* **`mars_rover_tua_v0.html`**: A natively served, JavaScript-powered interactive HTML Canvas map. No external libraries needed, lightning-fast telemetry visualization!
* **`best.pt`**: Our optimized YOLO model weights, trained specifically on Martian datasets.

## 🛠 Prerequisites & Installation
1. Install necessary Python packages:
```bash
pip install fastapi uvicorn websockets opencv-python ultralytics
```

## 🎮 How to Run (The Construct Cloud / Local)
**Terminal 1: Start the simulated Mars World**
```bash
gazebo martian.world
```

**Terminal 2: Boot Mission Control**
```bash
python3 backend_skeleton.py
```
*Wait for the `Uvicorn running on http://0.0.0.0:8000` text.*

**View the Real-Time Dashboard:**
Open your browser and navigate to the exposed Web Port 8000 via your IDE / Localhost!

## 🧩 Advanced Logic Explained
1. **Deduplication:** When the rover camera looks at an item across multiple video frames, the backend enforces a spatial threshold (e.g., 2 meters) to guarantee tasks are not duplicated.
2. **Prioritization Framework:** Water Ice is critical for ISRU. The `PriorityQueue` automatically pushes Water Ice detections to the top over standard Regolith sampling requests.
