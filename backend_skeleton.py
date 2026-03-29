import asyncio
import json
import math
import cv2  # pip install opencv-python
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import uvicorn
from queue import PriorityQueue
import time

# Try importing YOLO to avoid instant crash if the user hasn't run pip install ultralytics yet
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("[WARNING] 'ultralytics' module not found. Run: pip install ultralytics")

# =========================================================
# 1. CORE LOGIC: Deduplication & Priorities
# =========================================================
class MissionControl:
    def __init__(self):
        self.known_resources = [] # List of (x, y, type)
        self.task_queue = PriorityQueue()
        self.distance_threshold = 2.0 # Minimum meters between distinct items
        
        # Priorities (Lower number = higher priority)
        self.priority_map = {
            "Water_Ice": 1,
            "Regolith": 2,
            "Lava_Tube": 3 
        }

    def register_detection(self, resource_type, global_x, global_y):
        """ Checks if the detection is new. If new, adds to task queue. """
        # Deduplication logic
        for known_x, known_y, k_type in self.known_resources:
            distance = math.sqrt((global_x - known_x)**2 + (global_y - known_y)**2)
            if distance < self.distance_threshold and k_type == resource_type:
                return False # Duplicate! Ignore it.
                
        # It's a new resource!
        self.known_resources.append((global_x, global_y, resource_type))
        priority = self.priority_map.get(resource_type, 10)
        
        self.task_queue.put((priority, {"type": resource_type, "x": global_x, "y": global_y}))
        print(f"[NEW TARGET] YOLO detected {resource_type} at ({global_x:.2f}, {global_y:.2f})")
        return True

    def get_next_task(self):
        if not self.task_queue.empty():
            return self.task_queue.get()[1]
        return None

mission_control = MissionControl()

# =========================================================
# 2. VISION SERVER: YOLOv8 + Camera
# =========================================================
class VisionNode:
    def __init__(self, weights_path="best.pt"):
        self.model = None
        if YOLO_AVAILABLE:
            try:
                self.model = YOLO(weights_path)
                print(f"[VISION] YOLO Model '{weights_path}' loaded successfully.")
            except Exception as e:
                print(f"[VISION] Could not load YOLO weights at {weights_path}: {e}")

        # Example GStreamer/UDP connection for Rover Camera
        # self.cap = cv2.VideoCapture('udp://127.0.0.1:5600', cv2.CAP_FFMPEG)
        self.cap = None

    def process_frame(self, rover_current_x, rover_current_y):
        """ Runs YOLO inference on the camera feed """
        if not self.model or getattr(self, "cap", None) is None or not self.cap.isOpened():
            # Returns empty if camera is not active
            return []

        ret, frame = self.cap.read()
        if not ret: 
            return []
        
        results = self.model(frame, verbose=False)
        detections = []
        
        for r in results:
            for box in r.boxes:
                class_id = int(box.cls[0])
                class_name = self.model.names[class_id] # "Water_Ice", "Regolith"
                
                # Convert pixel offset to global coordinates relative to rover
                estimated_global_x = rover_current_x + (float(box.xywh[0][0]) / 640.0 - 0.5) * 5
                estimated_global_y = rover_current_y + (float(box.xywh[0][1]) / 640.0 - 0.5) * 5
                
                detections.append((class_name, estimated_global_x, estimated_global_y))
                
        return detections

# =========================================================
# 3. MAVLINK INTERFACE
# =========================================================
class MAVLinkInterface:
    def __init__(self):
        # self.rover = mavutil.mavlink_connection('udp:127.0.0.1:14560')
        self.rover_x = 0
        self.rover_y = 0
        
    def get_rover_position(self):
        # Listen to MAVLink GLOBAL_POSITION_INT here
        return self.rover_x, self.rover_y

    def send_rover_waypoint(self, x, y):
        print(f"[MAVLINK] Dispatching Rover to coordinates X:{x:.2f}, Y:{y:.2f}")

mavlink_sys = MAVLinkInterface()

# =========================================================
# 4. FASTAPI & WEBSOCKET SERVER
# =========================================================
app = FastAPI(title="Mars Mission Control Server")
connected_frontends = []

@app.get("/")
async def get_dashboard():
    """ Serves the mars_rover_tua_v0.html frontend directly! """
    try:
        with open("mars_rover_tua_v0.html", "r", encoding="utf-8") as file:
            return HTMLResponse(file.read())
    except FileNotFoundError:
        return HTMLResponse("<h1>Error: mars_rover_tua_v0.html not found!</h1><p>Ensure it is in the same folder as backend_skeleton.py</p>")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_frontends.append(websocket)
    print(f"[WS] Frontend UI Connected. Active clients: {len(connected_frontends)}")
    try:
        while True:
            # Handle commands from the Web Dashboard
            data = await websocket.receive_text()
            print(f"[UI COMMAND] {data}")
    except Exception:
        connected_frontends.remove(websocket)
        print("[WS] Frontend UI Disconnected.")

async def broadcast_to_ui(message_dict):
    """ Push telemetry strings to the HTML map """
    if not connected_frontends:
        return
    msg = json.dumps(message_dict)
    for client in connected_frontends:
        try:
             await client.send_text(msg)
        except:
             pass

# =========================================================
# 5. MAIN AUTONOMY LOOP
# =========================================================
async def autonomous_mission_loop():
    print("--------------------------------------------------")
    print("[SYSTEM] Mission Loop Started. Waiting for Rover data...")
    print("--------------------------------------------------")
    
    vision = VisionNode(weights_path="best.pt")
    
    while True:
        # Update rover coords
        rx, ry = mavlink_sys.get_rover_position()
        
        # Analyze Camera via YOLO
        detections = vision.process_frame(rx, ry)
        
        # --- DEMO GENERATOR --------------------------
        # Random resource spawning for demonstration without actual camera
        import random
        if getattr(vision, "cap", None) is None and random.random() < 0.05:
            res = "Water_Ice" if random.random() > 0.5 else "Regolith"
            r_x = rx + random.uniform(-100, 100)
            r_y = ry + random.uniform(-100, 100)
            detections.append((res, r_x, r_y))
        # ---------------------------------------------
        
        for resource_type, gx, gy in detections:
            # Prevent duplicate targets
            is_new = mission_control.register_detection(resource_type, gx, gy)
            if is_new:
                # Instantly notify the Frontend UI map
                await broadcast_to_ui({
                    "event": "new_resource",
                    "type": resource_type,
                    "x": gx,
                    "y": gy
                })
        
        # Assign prioritized tasks to Rover
        next_task = mission_control.get_next_task()
        if next_task:
            mavlink_sys.send_rover_waypoint(next_task["x"], next_task["y"])
            
        await asyncio.sleep(0.5)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(autonomous_mission_loop())

if __name__ == "__main__":
    print("--------------------------------------------------")
    print("AL-TECH MARS MISSION CONTROL BOOTING")
    print("--------------------------------------------------")
    print("Make sure both backend_skeleton.py and mars_rover_tua_v0.html are in the same folder.")
    uvicorn.run("backend_skeleton:app", host="0.0.0.0", port=8000, reload=True)
