let ws = null;
let currentTab = 'cameras';

document.addEventListener('DOMContentLoaded', function() {
    loadCameras();
    loadAlerts();
    loadDetections();
    loadWatchlist();
    loadStatistics();
    connectWebSocket();
    
    setInterval(loadCameras, 5000);
    setInterval(loadAlerts, 10000);
    setInterval(loadDetections, 15000);
});

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/updates`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        
        if (data.type === 'statistics') {
            updateStatusBar(data.data);
        } else if (data.type === 'alerts') {
            if (currentTab === 'alerts') {
                loadAlerts();
            }
        }
    };
    
    ws.onclose = function() {
        console.log('WebSocket closed, reconnecting...');
        setTimeout(connectWebSocket, 5000);
    };
}

function switchTab(tabName) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    
    event.target.classList.add('active');
    document.getElementById(tabName).classList.add('active');
    currentTab = tabName;
    
    if (tabName === 'system') {
        loadStatistics();
    }
}

function updateStatusBar(data) {
    if (data.database) {
        document.getElementById('activeCameras').textContent = data.database.active_cameras || 0;
        document.getElementById('totalDetections').textContent = data.database.total_detections || 0;
        document.getElementById('totalAlerts').textContent = data.database.unacknowledged_alerts || 0;
        document.getElementById('watchlistCount').textContent = data.database.watchlist_count || 0;
    }
}

async function loadCameras() {
    try {
        const response = await fetch('/api/cameras');
        const data = await response.json();
        
        const grid = document.getElementById('cameraGrid');
        
        if (data.cameras.length === 0) {
            grid.innerHTML = '<div class="no-data">No cameras added yet. Click "Add Camera" to get started.</div>';
            return;
        }
        
        grid.innerHTML = data.cameras.map(camera => {
            const status = camera.runtime_status;
            const isActive = status && status.is_running;
            const statusClass = isActive ? 'status-active' : 'status-inactive';
            const statusText = isActive ? 'Active' : 'Inactive';
            
            return `
                <div class="camera-card">
                    <div class="camera-header">
                        <div>
                            <div class="camera-name">${camera.name}</div>
                            <div style="font-size: 0.85em; opacity: 0.8; margin-top: 5px;">
                                ${camera.location || 'No location'}
                            </div>
                        </div>
                        <div class="camera-status ${statusClass}">${statusText}</div>
                    </div>
                    <div class="camera-video">
                        ${isActive ? 
                            `<img src="/api/cameras/${camera.id}/stream" alt="${camera.name}">` :
                            '<div style="color: #888;">Camera Offline</div>'
                        }
                    </div>
                    <div class="camera-controls">
                        ${isActive ?
                            `<button class="btn btn-danger" onclick="stopCamera(${camera.id})">⏹️ Stop</button>` :
                            `<button class="btn btn-primary" onclick="startCamera(${camera.id})">▶️ Start</button>`
                        }
                        <button class="btn btn-danger" onclick="deleteCamera(${camera.id}, '${camera.name}')">🗑️ Delete</button>
                        ${status ? `<div style="flex: 1; text-align: right; font-size: 0.85em;">FPS: ${status.fps || 0}</div>` : ''}
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading cameras:', error);
    }
}

async function loadAlerts() {
    try {
        const response = await fetch('/api/alerts?limit=20');
        const data = await response.json();
        
        const container = document.getElementById('alertsList');
        
        if (data.alerts.length === 0) {
            container.innerHTML = '<div class="no-data">No alerts yet.</div>';
            return;
        }
        
        container.innerHTML = data.alerts.map(alert => {
            const levelClass = `alert-${alert.alert_level === 'high' ? 'danger' : alert.alert_level === 'medium' ? 'warning' : 'info'}`;
            const time = new Date(alert.timestamp).toLocaleString();
            
            return `
                <div class="alert ${levelClass}">
                    <div class="alert-header">
                        <strong>🚨 ${alert.person_name} detected on ${alert.camera_name}</strong>
                        <span class="alert-time">${time}</span>
                    </div>
                    <div>Threat Level: <span class="badge badge-${alert.alert_level}">${alert.alert_level.toUpperCase()}</span></div>
                    ${alert.notes ? `<div style="margin-top: 10px; opacity: 0.9;">${alert.notes}</div>` : ''}
                    ${!alert.acknowledged ? 
                        `<button class="btn btn-secondary" style="margin-top: 10px;" onclick="acknowledgeAlert(${alert.id})">✓ Acknowledge</button>` :
                        '<div style="margin-top: 10px; color: #4CAF50;">✓ Acknowledged</div>'
                    }
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading alerts:', error);
    }
}

async function loadDetections() {
    try {
        const response = await fetch('/api/detections?limit=50');
        const data = await response.json();
        
        const tbody = document.querySelector('#detectionsTable tbody');
        
        if (data.detections.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="no-data">No detections yet.</td></tr>';
            return;
        }
        
        tbody.innerHTML = data.detections.map(det => {
            const time = new Date(det.timestamp).toLocaleString();
            const confidence = (det.confidence * 100).toFixed(1);
            
            return `
                <tr>
                    <td>${time}</td>
                    <td>${det.camera_name}</td>
                    <td>${det.person_name}</td>
                    <td>${confidence}%</td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading detections:', error);
    }
}

async function loadWatchlist() {
    try {
        const response = await fetch('/api/watchlist');
        const data = await response.json();
        
        const tbody = document.querySelector('#watchlistTable tbody');
        
        if (data.watchlist.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="no-data">Watchlist is empty.</td></tr>';
            return;
        }
        
        tbody.innerHTML = data.watchlist.map(entry => {
            const added = new Date(entry.added_at).toLocaleDateString();
            
            return `
                <tr>
                    <td><strong>${entry.person_name}</strong></td>
                    <td><span class="badge badge-${entry.threat_level}">${entry.threat_level.toUpperCase()}</span></td>
                    <td>${entry.description || '-'}</td>
                    <td>${added}</td>
                    <td>
                        <button class="btn btn-danger" onclick="removeFromWatchlist('${entry.person_name}')">Remove</button>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading watchlist:', error);
    }
}

async function loadStatistics() {
    try {
        const response = await fetch('/api/statistics');
        const data = await response.json();
        
        const container = document.getElementById('systemStats');
        
        container.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-top: 20px;">
                <div style="background: rgba(0,0,0,0.5); padding: 20px; border-radius: 10px;">
                    <h3>Database</h3>
                    <p>Total Cameras: <strong>${data.database.total_cameras}</strong></p>
                    <p>Active Cameras: <strong>${data.database.active_cameras}</strong></p>
                    <p>Total Detections: <strong>${data.database.total_detections}</strong></p>
                    <p>Detections Today: <strong>${data.database.detections_today}</strong></p>
                    <p>Total Alerts: <strong>${data.database.total_alerts}</strong></p>
                    <p>Unacknowledged: <strong>${data.database.unacknowledged_alerts}</strong></p>
                </div>
                <div style="background: rgba(0,0,0,0.5); padding: 20px; border-radius: 10px;">
                    <h3>Detection Engine</h3>
                    <p>Status: <strong>${data.detection_engine.is_running ? '✓ Running' : '✗ Stopped'}</strong></p>
                    <p>Workers: <strong>${data.detection_engine.num_workers}</strong></p>
                    <p>Known People: <strong>${data.detection_engine.known_people}</strong></p>
                    <p>Total Encodings: <strong>${data.detection_engine.total_encodings}</strong></p>
                    <p>Detections: <strong>${data.detection_engine.detection_count}</strong></p>
                    <p>Alerts Generated: <strong>${data.detection_engine.alert_count}</strong></p>
                </div>
            </div>
            <div style="margin-top: 20px;">
                <button class="btn btn-primary" onclick="reloadKnownFaces()">🔄 Reload Known Faces</button>
                ${data.detection_engine.is_running ?
                    '<button class="btn btn-danger" onclick="stopDetectionEngine()">⏹️ Stop Detection Engine</button>' :
                    '<button class="btn btn-primary" onclick="startDetectionEngine()">▶️ Start Detection Engine</button>'
                }
            </div>
        `;
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

async function startCamera(id) {
    try {
        await fetch(`/api/cameras/${id}/start`, { method: 'POST' });
        setTimeout(loadCameras, 1000);
    } catch (error) {
        alert('Error starting camera: ' + error.message);
    }
}

async function stopCamera(id) {
    try {
        await fetch(`/api/cameras/${id}/stop`, { method: 'POST' });
        setTimeout(loadCameras, 1000);
    } catch (error) {
        alert('Error stopping camera: ' + error.message);
    }
}

async function startAllCameras() {
    try {
        await fetch('/api/cameras/start-all', { method: 'POST' });
        setTimeout(loadCameras, 1000);
    } catch (error) {
        alert('Error starting cameras: ' + error.message);
    }
}

async function stopAllCameras() {
    try {
        await fetch('/api/cameras/stop-all', { method: 'POST' });
        setTimeout(loadCameras, 1000);
    } catch (error) {
        alert('Error stopping cameras: ' + error.message);
    }
}

async function deleteCamera(id, name) {
    if (!confirm(`Delete camera "${name}"?`)) return;
    
    try {
        await fetch(`/api/cameras/${id}`, { method: 'DELETE' });
        loadCameras();
    } catch (error) {
        alert('Error deleting camera: ' + error.message);
    }
}

async function addCamera(event) {
    event.preventDefault();
    
    const data = {
        name: document.getElementById('cameraName').value,
        stream_url: document.getElementById('cameraUrl').value,
        location: document.getElementById('cameraLocation').value
    };
    
    try {
        const response = await fetch('/api/cameras', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            closeModal('addCameraModal');
            loadCameras();
            event.target.reset();
        } else {
            const error = await response.json();
            alert('Error: ' + error.detail);
        }
    } catch (error) {
        alert('Error adding camera: ' + error.message);
    }
}

async function addToWatchlist(event) {
    event.preventDefault();
    
    const data = {
        person_name: document.getElementById('watchlistName').value,
        threat_level: document.getElementById('watchlistThreat').value,
        description: document.getElementById('watchlistDesc').value
    };
    
    try {
        const response = await fetch('/api/watchlist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            closeModal('addWatchlistModal');
            loadWatchlist();
            event.target.reset();
        } else {
            const error = await response.json();
            alert('Error: ' + error.detail);
        }
    } catch (error) {
        alert('Error adding to watchlist: ' + error.message);
    }
}

async function removeFromWatchlist(name) {
    if (!confirm(`Remove "${name}" from watchlist?`)) return;
    
    try {
        await fetch(`/api/watchlist/${encodeURIComponent(name)}`, { method: 'DELETE' });
        loadWatchlist();
    } catch (error) {
        alert('Error removing from watchlist: ' + error.message);
    }
}

async function acknowledgeAlert(id) {
    try {
        await fetch('/api/alerts/acknowledge', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ alert_id: id })
        });
        loadAlerts();
    } catch (error) {
        alert('Error acknowledging alert: ' + error.message);
    }
}

async function reloadKnownFaces() {
    try {
        await fetch('/api/detection-engine/reload', { method: 'POST' });
        alert('Known faces reloaded successfully');
        loadStatistics();
    } catch (error) {
        alert('Error reloading known faces: ' + error.message);
    }
}

async function startDetectionEngine() {
    try {
        await fetch('/api/detection-engine/start', { method: 'POST' });
        setTimeout(loadStatistics, 1000);
    } catch (error) {
        alert('Error starting detection engine: ' + error.message);
    }
}

async function stopDetectionEngine() {
    try {
        await fetch('/api/detection-engine/stop', { method: 'POST' });
        setTimeout(loadStatistics, 1000);
    } catch (error) {
        alert('Error stopping detection engine: ' + error.message);
    }
}

function showAddCameraModal() {
    document.getElementById('addCameraModal').classList.add('active');
}

function showAddWatchlistModal() {
    document.getElementById('addWatchlistModal').classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}
