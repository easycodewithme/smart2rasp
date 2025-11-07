"""
Detection Engine - Multi-threaded face detection and recognition
"""
import cv2
import numpy as np
import face_recognition
import threading
import queue
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import config
from database import db
from camera_manager import camera_manager

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)


class DetectionEngine:
    """Multi-threaded face detection and recognition engine"""
    
    def __init__(self):
        self.known_encodings = []
        self.known_names = []
        self.is_running = False
        self.worker_threads = []
        self.num_workers = 4  # Number of processing threads
        self.processing_queue = queue.Queue(maxsize=500)
        self.results_queue = queue.Queue()
        self.alert_cooldown = {}  # Track last alert time per person per camera
        self.detection_count = 0
        self.alert_count = 0
        self.load_known_faces()
        logger.info("Detection Engine initialized")
    
    def load_known_faces(self):
        """Load known face encodings from file"""
        try:
            if not os.path.exists(config.KNOWN_ENCODINGS_FILE):
                logger.warning(f"Encodings file not found: {config.KNOWN_ENCODINGS_FILE}")
                return
            
            data = np.load(config.KNOWN_ENCODINGS_FILE, allow_pickle=True).item()
            
            self.known_names = []
            self.known_encodings = []
            
            for name, val in data.items():
                if val is None:
                    continue
                arr = np.array(val)
                
                if arr.ndim == 1 and arr.size == 128:
                    self.known_names.append(name)
                    self.known_encodings.append(arr)
                elif arr.ndim == 2 and arr.shape[1] == 128:
                    for row in arr:
                        self.known_names.append(name)
                        self.known_encodings.append(row)
            
            logger.info(f"Loaded {len(set(self.known_names))} people, {len(self.known_encodings)} encodings")
            
        except Exception as e:
            logger.error(f"Error loading known faces: {e}")
    
    def reload_known_faces(self):
        """Reload known faces (useful after adding new people)"""
        logger.info("Reloading known faces...")
        self.load_known_faces()
    
    def start(self):
        """Start detection engine"""
        if self.is_running:
            logger.warning("Detection engine already running")
            return
        
        self.is_running = True
        
        # Start worker threads
        for i in range(self.num_workers):
            thread = threading.Thread(target=self._worker_loop, args=(i,), daemon=True)
            thread.start()
            self.worker_threads.append(thread)
        
        # Start frame collector thread
        collector_thread = threading.Thread(target=self._collect_frames, daemon=True)
        collector_thread.start()
        
        # Start results processor thread
        results_thread = threading.Thread(target=self._process_results, daemon=True)
        results_thread.start()
        
        logger.info(f"Detection engine started with {self.num_workers} workers")
    
    def stop(self):
        """Stop detection engine"""
        self.is_running = False
        for thread in self.worker_threads:
            thread.join(timeout=2)
        self.worker_threads.clear()
        logger.info("Detection engine stopped")
    
    def _collect_frames(self):
        """Collect frames from all cameras and add to processing queue"""
        frame_counter = 0
        
        while self.is_running:
            try:
                cameras = camera_manager.get_all_cameras()
                
                for camera_id, camera in cameras.items():
                    if not camera.is_running:
                        continue
                    
                    try:
                        # Get frame from camera queue (non-blocking)
                        frame_data = camera.frame_queue.get_nowait()
                        
                        # Process every Nth frame
                        frame_counter += 1
                        if frame_counter % config.PROCESS_EVERY_N_FRAMES != 0:
                            continue
                        
                        # Add to processing queue
                        try:
                            self.processing_queue.put_nowait(frame_data)
                        except queue.Full:
                            pass  # Skip if queue is full
                            
                    except queue.Empty:
                        pass
                
                time.sleep(0.01)  # Small delay to prevent CPU spinning
                
            except Exception as e:
                logger.error(f"Error in frame collector: {e}")
                time.sleep(0.1)
    
    def _worker_loop(self, worker_id: int):
        """Worker thread for processing frames"""
        logger.info(f"Worker {worker_id} started")
        
        while self.is_running:
            try:
                # Get frame from queue
                frame_data = self.processing_queue.get(timeout=1)
                
                # Process frame
                result = self._process_frame(frame_data)
                
                if result:
                    self.results_queue.put(result)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in worker {worker_id}: {e}")
    
    def _process_frame(self, frame_data: Dict) -> Optional[Dict]:
        """Process a single frame for face detection and recognition"""
        try:
            frame = frame_data['frame']
            camera_id = frame_data['camera_id']
            camera_name = frame_data['camera_name']
            timestamp = frame_data['timestamp']
            
            # Resize frame for faster processing
            small_frame = cv2.resize(frame, (0, 0), fx=config.FACE_DETECTION_SCALE, 
                                    fy=config.FACE_DETECTION_SCALE)
            rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            # Detect faces
            face_locations = face_recognition.face_locations(rgb_small, 
                                                            model=config.FACE_DETECTION_MODEL)
            
            if not face_locations:
                return None
            
            # Get face encodings
            face_encodings = face_recognition.face_encodings(rgb_small, face_locations)
            
            detections = []
            
            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                # Scale back to original frame size
                top = int(top / config.FACE_DETECTION_SCALE)
                right = int(right / config.FACE_DETECTION_SCALE)
                bottom = int(bottom / config.FACE_DETECTION_SCALE)
                left = int(left / config.FACE_DETECTION_SCALE)
                
                # Match face to known faces
                name = "Unknown"
                confidence = 0.0
                
                if len(self.known_encodings) > 0:
                    matches = face_recognition.compare_faces(
                        self.known_encodings, 
                        face_encoding, 
                        config.FACE_RECOGNITION_TOLERANCE
                    )
                    
                    face_distances = face_recognition.face_distance(
                        self.known_encodings, 
                        face_encoding
                    )
                    
                    if len(face_distances) > 0:
                        best_match_index = np.argmin(face_distances)
                        
                        if matches[best_match_index]:
                            name = self.known_names[best_match_index]
                            confidence = 1.0 - face_distances[best_match_index]
                
                detections.append({
                    'name': name,
                    'confidence': confidence,
                    'bbox': (top, right, bottom, left),
                    'encoding': face_encoding
                })
            
            if detections:
                return {
                    'camera_id': camera_id,
                    'camera_name': camera_name,
                    'timestamp': timestamp,
                    'frame': frame,
                    'detections': detections
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            return None
    
    def _process_results(self):
        """Process detection results and generate alerts"""
        while self.is_running:
            try:
                result = self.results_queue.get(timeout=1)
                
                camera_id = result['camera_id']
                camera_name = result['camera_name']
                timestamp = result['timestamp']
                frame = result['frame']
                detections = result['detections']
                
                for detection in detections:
                    name = detection['name']
                    confidence = detection['confidence']
                    bbox = detection['bbox']
                    
                    # Skip unknown faces
                    if name == "Unknown":
                        continue
                    
                    self.detection_count += 1
                    
                    # Save detection to database
                    snapshot_path = self._save_snapshot(frame, bbox, camera_name, name, timestamp)
                    db.add_detection(camera_id, name, confidence, snapshot_path, bbox)
                    
                    # Check if person is on watchlist
                    watchlist_entry = db.is_on_watchlist(name)
                    
                    if watchlist_entry:
                        # Check alert cooldown
                        cooldown_key = f"{camera_id}_{name}"
                        current_time = datetime.now()
                        
                        if cooldown_key in self.alert_cooldown:
                            last_alert_time = self.alert_cooldown[cooldown_key]
                            if (current_time - last_alert_time).seconds < config.ALERT_COOLDOWN:
                                continue  # Skip alert due to cooldown
                        
                        # Generate alert
                        self.alert_count += 1
                        self.alert_cooldown[cooldown_key] = current_time
                        
                        alert_level = watchlist_entry['threat_level']
                        notes = f"Detected on {camera_name} with {confidence:.2%} confidence"
                        
                        db.add_alert(camera_id, name, alert_level, snapshot_path, notes)
                        
                        logger.warning(f"ALERT: {name} detected on {camera_name} "
                                     f"(Threat Level: {alert_level})")
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing results: {e}")
    
    def _save_snapshot(self, frame: np.ndarray, bbox: tuple, camera_name: str, 
                      person_name: str, timestamp: datetime) -> str:
        """Save detection snapshot"""
        try:
            if not config.SAVE_ALERT_SNAPSHOTS:
                return None
            
            top, right, bottom, left = bbox
            
            # Add some padding
            padding = 20
            top = max(0, top - padding)
            left = max(0, left - padding)
            bottom = min(frame.shape[0], bottom + padding)
            right = min(frame.shape[1], right + padding)
            
            # Crop face region
            face_img = frame[top:bottom, left:right]
            
            # Generate filename
            timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"{camera_name}_{person_name}_{timestamp_str}.jpg"
            filepath = os.path.join(config.ALERT_SNAPSHOT_DIR, filename)
            
            # Save image
            cv2.imwrite(filepath, face_img)
            
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving snapshot: {e}")
            return None
    
    def get_statistics(self) -> Dict:
        """Get detection engine statistics"""
        return {
            'is_running': self.is_running,
            'num_workers': self.num_workers,
            'processing_queue_size': self.processing_queue.qsize(),
            'results_queue_size': self.results_queue.qsize(),
            'known_people': len(set(self.known_names)),
            'total_encodings': len(self.known_encodings),
            'detection_count': self.detection_count,
            'alert_count': self.alert_count
        }


# Global detection engine instance
detection_engine = DetectionEngine()
