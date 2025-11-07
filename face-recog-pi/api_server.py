"""
FastAPI Server - REST API for Multi-Camera CCTV System
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import cv2
import numpy as np
import asyncio
import json
import logging
from datetime import datetime
import face_recognition
import config
from database import db
from camera_manager import camera_manager
from detection_engine import detection_engine

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Multi-Camera CCTV System",
    description="Smart CCTV system with face recognition and threat detection",
    version="1.0.0"
)

# CORS middleware for mobile access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")


# Pydantic models for API
class CameraCreate(BaseModel):
    name: str
    stream_url: str
    location: Optional[str] = ""
    metadata: Optional[dict] = {}


class CameraUpdate(BaseModel):
    name: Optional[str] = None
    stream_url: Optional[str] = None
    location: Optional[str] = None


class WatchlistEntry(BaseModel):
    person_name: str
    threat_level: str = "medium"
    description: Optional[str] = ""
    metadata: Optional[dict] = {}


class AlertAcknowledge(BaseModel):
    alert_id: int


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to websocket: {e}")


manager = ConnectionManager()


# ==================== API Endpoints ====================

@app.get("/")
async def root():
    """Root endpoint - serves the web interface"""
    with open("templates/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


@app.get("/camera")
async def camera_direct():
    """Direct camera access page"""
    with open("templates/camera_direct.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


@app.post("/api/detect-frame")
async def detect_frame(
    frame: UploadFile = File(...),
    device_id: str = Form(...),
    device_type: str = Form(...)
):
    """Process a frame from device camera for face detection"""
    try:
        # Read image from upload
        contents = await frame.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image")
        
        # Resize for faster processing
        small = cv2.resize(img, (0, 0), fx=config.FACE_DETECTION_SCALE, 
                          fy=config.FACE_DETECTION_SCALE)
        rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(rgb_small, 
                                                        model=config.FACE_DETECTION_MODEL)
        
        if not face_locations:
            return {"detections": [], "message": "No faces detected"}
        
        # Get face encodings
        face_encodings = face_recognition.face_encodings(rgb_small, face_locations)
        
        # Load known encodings
        known_encodings = detection_engine.known_encodings
        known_names = detection_engine.known_names
        
        detections = []
        
        for face_encoding in face_encodings:
            name = "Unknown"
            confidence = 0.0
            
            if len(known_encodings) > 0:
                matches = face_recognition.compare_faces(
                    known_encodings, 
                    face_encoding, 
                    config.FACE_RECOGNITION_TOLERANCE
                )
                
                face_distances = face_recognition.face_distance(
                    known_encodings, 
                    face_encoding
                )
                
                if len(face_distances) > 0:
                    best_match_index = np.argmin(face_distances)
                    
                    if matches[best_match_index]:
                        name = known_names[best_match_index]
                        confidence = 1.0 - face_distances[best_match_index]
            
            if name != "Unknown":
                detections.append({
                    'name': name,
                    'confidence': float(confidence),
                    'device_id': device_id,
                    'device_type': device_type
                })
                
                # Log to database (create a virtual camera for device)
                camera = db.get_camera_by_name(f"Device_{device_id}")
                if not camera:
                    camera_id = db.add_camera(
                        name=f"Device_{device_id}",
                        stream_url=f"device://{device_id}",
                        location=device_type
                    )
                else:
                    camera_id = camera['id']
                
                # Add detection
                db.add_detection(camera_id, name, confidence)
                
                # Check watchlist
                watchlist_entry = db.is_on_watchlist(name)
                if watchlist_entry:
                    db.add_alert(
                        camera_id, 
                        name, 
                        watchlist_entry['threat_level'],
                        notes=f"Detected on {device_type}"
                    )
        
        return {
            "detections": detections,
            "face_locations": face_locations,
            "total_faces": len(face_locations),
            "message": f"Detected {len(detections)} known faces"
        }
        
    except Exception as e:
        logger.error(f"Error processing frame: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "detection_engine_running": detection_engine.is_running,
        "active_cameras": len([c for c in camera_manager.get_all_cameras().values() if c.is_running])
    }


# ==================== Camera Endpoints ====================

@app.post("/api/cameras")
async def create_camera(camera: CameraCreate):
    """Add a new camera"""
    try:
        # Check if camera with same name exists
        existing = db.get_camera_by_name(camera.name)
        if existing:
            raise HTTPException(status_code=400, detail="Camera with this name already exists")
        
        # Add to database
        camera_id = db.add_camera(
            name=camera.name,
            stream_url=camera.stream_url,
            location=camera.location,
            metadata=camera.metadata
        )
        
        # Add to camera manager
        camera_manager.add_camera(camera_id, camera.name, camera.stream_url)
        
        return {
            "success": True,
            "camera_id": camera_id,
            "message": f"Camera '{camera.name}' added successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating camera: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cameras")
async def get_cameras():
    """Get all cameras"""
    try:
        cameras = db.get_all_cameras()
        statuses = camera_manager.get_all_statuses()
        
        # Merge database info with runtime status
        status_dict = {s['camera_id']: s for s in statuses}
        
        for camera in cameras:
            camera_id = camera['id']
            if camera_id in status_dict:
                camera['runtime_status'] = status_dict[camera_id]
            else:
                camera['runtime_status'] = None
        
        return {"cameras": cameras}
    except Exception as e:
        logger.error(f"Error getting cameras: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cameras/{camera_id}")
async def get_camera(camera_id: int):
    """Get specific camera details"""
    try:
        camera = db.get_camera(camera_id)
        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found")
        
        # Add runtime status
        cam_obj = camera_manager.get_camera(camera_id)
        if cam_obj:
            camera['runtime_status'] = cam_obj.get_status()
        
        return camera
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting camera: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/cameras/{camera_id}")
async def delete_camera(camera_id: int):
    """Delete a camera"""
    try:
        camera = db.get_camera(camera_id)
        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found")
        
        # Remove from camera manager
        camera_manager.remove_camera(camera_id)
        
        # Delete from database
        db.delete_camera(camera_id)
        
        return {"success": True, "message": "Camera deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting camera: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cameras/{camera_id}/start")
async def start_camera(camera_id: int):
    """Start a camera stream"""
    try:
        success = camera_manager.start_camera(camera_id)
        if not success:
            raise HTTPException(status_code=404, detail="Camera not found")
        
        return {"success": True, "message": "Camera started"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting camera: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cameras/{camera_id}/stop")
async def stop_camera(camera_id: int):
    """Stop a camera stream"""
    try:
        success = camera_manager.stop_camera(camera_id)
        if not success:
            raise HTTPException(status_code=404, detail="Camera not found")
        
        return {"success": True, "message": "Camera stopped"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping camera: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cameras/start-all")
async def start_all_cameras():
    """Start all cameras"""
    try:
        camera_manager.start_all_cameras()
        return {"success": True, "message": "All cameras started"}
    except Exception as e:
        logger.error(f"Error starting all cameras: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cameras/stop-all")
async def stop_all_cameras():
    """Stop all cameras"""
    try:
        camera_manager.stop_all_cameras()
        return {"success": True, "message": "All cameras stopped"}
    except Exception as e:
        logger.error(f"Error stopping all cameras: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Video Stream Endpoints ====================

def generate_frames(camera_id: int):
    """Generate video frames for streaming"""
    while True:
        try:
            frame = camera_manager.get_frame(camera_id)
            
            if frame is None:
                # Send a blank frame if no frame available
                blank = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(blank, "No Signal", (200, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                frame = blank
            
            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ret:
                continue
            
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
        except Exception as e:
            logger.error(f"Error generating frame: {e}")
            break


@app.get("/api/cameras/{camera_id}/stream")
async def video_stream(camera_id: int):
    """Stream video from a specific camera"""
    camera = db.get_camera(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    return StreamingResponse(
        generate_frames(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ==================== Detection Endpoints ====================

@app.get("/api/detections")
async def get_detections(limit: int = 100):
    """Get recent detections"""
    try:
        detections = db.get_recent_detections(limit)
        return {"detections": detections}
    except Exception as e:
        logger.error(f"Error getting detections: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/detections/camera/{camera_id}")
async def get_camera_detections(camera_id: int, limit: int = 50):
    """Get detections for a specific camera"""
    try:
        detections = db.get_detections_by_camera(camera_id, limit)
        return {"detections": detections}
    except Exception as e:
        logger.error(f"Error getting camera detections: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Alert Endpoints ====================

@app.get("/api/alerts")
async def get_alerts(limit: int = 50, unacknowledged_only: bool = False):
    """Get recent alerts"""
    try:
        alerts = db.get_recent_alerts(limit, unacknowledged_only)
        return {"alerts": alerts}
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/alerts/acknowledge")
async def acknowledge_alert(data: AlertAcknowledge):
    """Acknowledge an alert"""
    try:
        db.acknowledge_alert(data.alert_id)
        return {"success": True, "message": "Alert acknowledged"}
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Watchlist Endpoints ====================

@app.post("/api/watchlist")
async def add_to_watchlist(entry: WatchlistEntry):
    """Add person to watchlist"""
    try:
        entry_id = db.add_to_watchlist(
            person_name=entry.person_name,
            threat_level=entry.threat_level,
            description=entry.description,
            metadata=entry.metadata
        )
        return {
            "success": True,
            "entry_id": entry_id,
            "message": f"'{entry.person_name}' added to watchlist"
        }
    except Exception as e:
        logger.error(f"Error adding to watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/watchlist")
async def get_watchlist():
    """Get watchlist"""
    try:
        watchlist = db.get_watchlist()
        return {"watchlist": watchlist}
    except Exception as e:
        logger.error(f"Error getting watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/watchlist/{person_name}")
async def remove_from_watchlist(person_name: str):
    """Remove person from watchlist"""
    try:
        db.remove_from_watchlist(person_name)
        return {"success": True, "message": f"'{person_name}' removed from watchlist"}
    except Exception as e:
        logger.error(f"Error removing from watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== System Endpoints ====================

@app.get("/api/statistics")
async def get_statistics():
    """Get system statistics"""
    try:
        db_stats = db.get_statistics()
        engine_stats = detection_engine.get_statistics()
        camera_stats = camera_manager.get_all_statuses()
        
        return {
            "database": db_stats,
            "detection_engine": engine_stats,
            "cameras": camera_stats
        }
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/detection-engine/start")
async def start_detection_engine():
    """Start detection engine"""
    try:
        detection_engine.start()
        return {"success": True, "message": "Detection engine started"}
    except Exception as e:
        logger.error(f"Error starting detection engine: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/detection-engine/stop")
async def stop_detection_engine():
    """Stop detection engine"""
    try:
        detection_engine.stop()
        return {"success": True, "message": "Detection engine stopped"}
    except Exception as e:
        logger.error(f"Error stopping detection engine: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/detection-engine/reload")
async def reload_known_faces():
    """Reload known faces"""
    try:
        detection_engine.reload_known_faces()
        return {"success": True, "message": "Known faces reloaded"}
    except Exception as e:
        logger.error(f"Error reloading known faces: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== WebSocket Endpoints ====================

@app.websocket("/ws/updates")
async def websocket_updates(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Send periodic updates
            stats = {
                "type": "statistics",
                "data": {
                    "database": db.get_statistics(),
                    "detection_engine": detection_engine.get_statistics(),
                    "cameras": camera_manager.get_all_statuses()
                },
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send_json(stats)
            
            # Check for new alerts
            alerts = db.get_recent_alerts(limit=5, unacknowledged_only=True)
            if alerts:
                await websocket.send_json({
                    "type": "alerts",
                    "data": alerts,
                    "timestamp": datetime.now().isoformat()
                })
            
            await asyncio.sleep(2)  # Update every 2 seconds
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# ==================== Startup/Shutdown Events ====================

@app.on_event("startup")
async def startup_event():
    """Initialize system on startup"""
    logger.info("Starting Multi-Camera CCTV System...")
    
    # Load cameras from database
    camera_manager.load_cameras_from_db()
    
    # Start detection engine
    detection_engine.start()
    
    logger.info("System started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Multi-Camera CCTV System...")
    
    # Stop all cameras
    camera_manager.stop_all_cameras()
    
    # Stop detection engine
    detection_engine.stop()
    
    logger.info("System shutdown complete")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=config.SERVER_HOST,
        port=config.SERVER_PORT,
        log_level="info"
    )
