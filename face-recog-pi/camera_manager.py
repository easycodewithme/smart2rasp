"""
Camera Manager - Handles multiple camera streams with RTSP support
"""
import cv2
import threading
import time
import queue
import numpy as np
from typing import Dict, Optional
from datetime import datetime
import logging
import config
from database import db

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)


class CameraStream:
    """Handles individual camera stream"""
    
    def __init__(self, camera_id: int, name: str, stream_url: str):
        self.camera_id = camera_id
        self.name = name
        self.stream_url = stream_url
        self.cap = None
        self.is_running = False
        self.thread = None
        self.frame_queue = queue.Queue(maxsize=config.MAX_QUEUE_SIZE)
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.fps = 0
        self.frame_count = 0
        self.last_frame_time = time.time()
        self.error_count = 0
        self.last_error = None
        
    def start(self):
        """Start camera stream"""
        if self.is_running:
            logger.warning(f"Camera {self.name} is already running")
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        logger.info(f"Started camera stream: {self.name}")
    
    def stop(self):
        """Stop camera stream"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)
        if self.cap:
            self.cap.release()
        logger.info(f"Stopped camera stream: {self.name}")
        db.update_camera_status(self.camera_id, "inactive")
    
    def _capture_loop(self):
        """Main capture loop"""
        while self.is_running:
            try:
                # Open camera if not already open
                if self.cap is None or not self.cap.isOpened():
                    self._connect()
                    if self.cap is None:
                        time.sleep(config.CAMERA_RECONNECT_DELAY)
                        continue
                
                ret, frame = self.cap.read()
                
                if not ret:
                    logger.warning(f"Failed to read frame from {self.name}")
                    self.error_count += 1
                    self.last_error = "Failed to read frame"
                    
                    if self.error_count > 10:
                        logger.error(f"Too many errors for {self.name}, reconnecting...")
                        self._reconnect()
                    time.sleep(0.1)
                    continue
                
                # Reset error count on successful read
                self.error_count = 0
                self.frame_count += 1
                
                # Calculate FPS
                current_time = time.time()
                if current_time - self.last_frame_time >= 1.0:
                    self.fps = self.frame_count / (current_time - self.last_frame_time)
                    self.frame_count = 0
                    self.last_frame_time = current_time
                
                # Store latest frame
                with self.frame_lock:
                    self.latest_frame = frame.copy()
                
                # Add to processing queue (non-blocking)
                try:
                    self.frame_queue.put_nowait({
                        'frame': frame,
                        'timestamp': datetime.now(),
                        'camera_id': self.camera_id,
                        'camera_name': self.name
                    })
                except queue.Full:
                    # Skip frame if queue is full
                    pass
                
                # Update camera status
                db.update_camera_status(self.camera_id, "active")
                
            except Exception as e:
                logger.error(f"Error in capture loop for {self.name}: {e}")
                self.last_error = str(e)
                self.error_count += 1
                time.sleep(1)
    
    def _connect(self):
        """Connect to camera stream"""
        try:
            logger.info(f"Connecting to {self.name} at {self.stream_url}")
            
            # Try to parse stream URL as integer for webcam index
            try:
                source = int(self.stream_url)
            except ValueError:
                source = self.stream_url
            
            self.cap = cv2.VideoCapture(source)
            
            # Set buffer size to reduce latency
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            if self.cap.isOpened():
                logger.info(f"Successfully connected to {self.name}")
                db.update_camera_status(self.camera_id, "active")
                self.error_count = 0
            else:
                logger.error(f"Failed to open camera {self.name}")
                self.cap = None
                db.update_camera_status(self.camera_id, "error")
                
        except Exception as e:
            logger.error(f"Error connecting to {self.name}: {e}")
            self.cap = None
            self.last_error = str(e)
            db.update_camera_status(self.camera_id, "error")
    
    def _reconnect(self):
        """Reconnect to camera"""
        if self.cap:
            self.cap.release()
        self.cap = None
        self.error_count = 0
        time.sleep(config.CAMERA_RECONNECT_DELAY)
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Get the latest frame"""
        with self.frame_lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None
    
    def get_status(self) -> Dict:
        """Get camera status"""
        return {
            'camera_id': self.camera_id,
            'name': self.name,
            'stream_url': self.stream_url,
            'is_running': self.is_running,
            'fps': round(self.fps, 2),
            'queue_size': self.frame_queue.qsize(),
            'error_count': self.error_count,
            'last_error': self.last_error
        }


class CameraManager:
    """Manages multiple camera streams"""
    
    def __init__(self):
        self.cameras: Dict[int, CameraStream] = {}
        self.lock = threading.Lock()
        logger.info("Camera Manager initialized")
    
    def add_camera(self, camera_id: int, name: str, stream_url: str) -> bool:
        """Add a new camera"""
        with self.lock:
            if camera_id in self.cameras:
                logger.warning(f"Camera {camera_id} already exists")
                return False
            
            camera = CameraStream(camera_id, name, stream_url)
            self.cameras[camera_id] = camera
            logger.info(f"Added camera: {name} (ID: {camera_id})")
            return True
    
    def remove_camera(self, camera_id: int) -> bool:
        """Remove a camera"""
        with self.lock:
            if camera_id not in self.cameras:
                logger.warning(f"Camera {camera_id} not found")
                return False
            
            camera = self.cameras[camera_id]
            camera.stop()
            del self.cameras[camera_id]
            logger.info(f"Removed camera: {camera.name} (ID: {camera_id})")
            return True
    
    def start_camera(self, camera_id: int) -> bool:
        """Start a specific camera"""
        with self.lock:
            if camera_id not in self.cameras:
                logger.warning(f"Camera {camera_id} not found")
                return False
            
            self.cameras[camera_id].start()
            return True
    
    def stop_camera(self, camera_id: int) -> bool:
        """Stop a specific camera"""
        with self.lock:
            if camera_id not in self.cameras:
                logger.warning(f"Camera {camera_id} not found")
                return False
            
            self.cameras[camera_id].stop()
            return True
    
    def start_all_cameras(self):
        """Start all cameras"""
        with self.lock:
            for camera in self.cameras.values():
                if not camera.is_running:
                    camera.start()
        logger.info("Started all cameras")
    
    def stop_all_cameras(self):
        """Stop all cameras"""
        with self.lock:
            for camera in self.cameras.values():
                camera.stop()
        logger.info("Stopped all cameras")
    
    def get_camera(self, camera_id: int) -> Optional[CameraStream]:
        """Get a specific camera"""
        return self.cameras.get(camera_id)
    
    def get_all_cameras(self) -> Dict[int, CameraStream]:
        """Get all cameras"""
        return self.cameras.copy()
    
    def get_frame(self, camera_id: int) -> Optional[np.ndarray]:
        """Get latest frame from a camera"""
        camera = self.cameras.get(camera_id)
        if camera:
            return camera.get_latest_frame()
        return None
    
    def get_all_statuses(self) -> list:
        """Get status of all cameras"""
        return [camera.get_status() for camera in self.cameras.values()]
    
    def load_cameras_from_db(self):
        """Load all cameras from database"""
        cameras = db.get_all_cameras()
        for cam in cameras:
            self.add_camera(cam['id'], cam['name'], cam['stream_url'])
        logger.info(f"Loaded {len(cameras)} cameras from database")


# Global camera manager instance
camera_manager = CameraManager()
