"""
Web-based dashboard for ecosystem monitoring and management.

This module implements a web-based dashboard for real-time monitoring
of agent activities, system status, and human intervention controls.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event


@dataclass
class DashboardConfig:
    """Configuration for the dashboard."""
    host: str = "localhost"
    port: int = 8080
    title: str = "Autonomous AI Ecosystem Dashboard"
    
    # Features
    enable_real_time_updates: bool = True
    enable_agent_controls: bool = True
    enable_system_controls: bool = True
    enable_emergency_controls: bool = True
    
    # Update intervals (seconds)
    status_update_interval: int = 5
    metrics_update_interval: int = 10
    log_update_interval: int = 2
    
    # Security
    enable_authentication: bool = False
    api_key: Optional[str] = None
    
    # UI settings
    theme: str = "dark"  # dark, light
    max_log_entries: int = 1000
    max_chart_points: int = 100


class EcosystemDashboard(AgentModule):
    """
    Web-based dashboard for ecosystem monitoring and management.
    
    Provides real-time visualization of agent activities, system status,
    and controls for human intervention and system management.
    """
    
    def __init__(self, orchestrator, config: Optional[DashboardConfig] = None):
        super().__init__("ecosystem_dashboard")
        self.logger = get_agent_logger("ecosystem_dashboard", "dashboard")
        
        if not FASTAPI_AVAILABLE:
            raise ImportError("FastAPI is required for the dashboard. Install with: pip install fastapi uvicorn")
        
        self.orchestrator = orchestrator
        self.config = config or DashboardConfig()
        
        # FastAPI app
        self.app = FastAPI(title=self.config.title)
        self._setup_middleware()
        self._setup_routes()
        
        # WebSocket connections
        self.websocket_connections: Set[WebSocket] = set()
        
        # Background tasks
        self.update_task: Optional[asyncio.Task] = None
        self.server_task: Optional[asyncio.Task] = None
        
        # Dashboard state
        self.dashboard_data = {
            "system_status": {},
            "agent_status": [],
            "metrics": {
                "timestamps": [],
                "cpu_usage": [],
                "memory_usage": [],
                "agent_count": [],
                "active_tasks": []
            },
            "logs": [],
            "alerts": []
        }
        
        self.logger.info("Ecosystem dashboard initialized")
    
    async def initialize(self) -> None:
        """Initialize the dashboard."""
        try:
            # Start background update task
            self.update_task = asyncio.create_task(self._update_loop())
            
            # Start web server
            self.server_task = asyncio.create_task(self._start_server())
            
            self.logger.info(f"Dashboard starting on http://{self.config.host}:{self.config.port}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize dashboard: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the dashboard."""
        try:
            # Cancel background tasks
            if self.update_task:
                self.update_task.cancel()
            if self.server_task:
                self.server_task.cancel()
            
            # Close WebSocket connections
            for websocket in self.websocket_connections.copy():
                try:
                    await websocket.close()
                except:
                    pass
            
            self.logger.info("Dashboard shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during dashboard shutdown: {e}")
    
    def _setup_middleware(self) -> None:
        """Setup FastAPI middleware."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self) -> None:
        """Setup FastAPI routes."""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard_home():
            """Serve the main dashboard page."""
            return self._get_dashboard_html()
        
        @self.app.get("/api/status")
        async def get_system_status():
            """Get current system status."""
            try:
                status = await self.orchestrator.get_system_status()
                return JSONResponse(content=status)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/agents")
        async def get_agents():
            """Get all agent statuses."""
            try:
                if self.orchestrator.agent_manager:
                    agents = await self.orchestrator.agent_manager.get_all_agents_status()
                    return JSONResponse(content=agents)
                return JSONResponse(content=[])
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/agents/{agent_id}/stop")
        async def stop_agent(agent_id: str):
            """Stop a specific agent."""
            if not self.config.enable_agent_controls:
                raise HTTPException(status_code=403, detail="Agent controls disabled")
            
            try:
                success = await self.orchestrator.stop_agent(agent_id)
                return JSONResponse(content={"success": success})
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/agents/{agent_id}/restart")
        async def restart_agent(agent_id: str):
            """Restart a specific agent."""
            if not self.config.enable_agent_controls:
                raise HTTPException(status_code=403, detail="Agent controls disabled")
            
            try:
                if self.orchestrator.agent_manager:
                    success = await self.orchestrator.agent_manager.restart_agent(agent_id)
                    return JSONResponse(content={"success": success})
                return JSONResponse(content={"success": False})
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/system/{system_name}/restart")
        async def restart_system(system_name: str):
            """Restart a specific system."""
            if not self.config.enable_system_controls:
                raise HTTPException(status_code=403, detail="System controls disabled")
            
            try:
                success = await self.orchestrator.restart_system(system_name)
                return JSONResponse(content={"success": success})
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/emergency/shutdown")
        async def emergency_shutdown():
            """Trigger emergency shutdown."""
            if not self.config.enable_emergency_controls:
                raise HTTPException(status_code=403, detail="Emergency controls disabled")
            
            try:
                if self.orchestrator.emergency_response:
                    incident_id = await self.orchestrator.emergency_response.trigger_emergency_shutdown(
                        reason="manual_shutdown",
                        description="Emergency shutdown triggered from dashboard"
                    )
                    return JSONResponse(content={"success": True, "incident_id": incident_id})
                return JSONResponse(content={"success": False})
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates."""
            await websocket.accept()
            self.websocket_connections.add(websocket)
            
            try:
                while True:
                    # Send current dashboard data
                    await websocket.send_json(self.dashboard_data)
                    await asyncio.sleep(self.config.status_update_interval)
                    
            except WebSocketDisconnect:
                self.websocket_connections.discard(websocket)
            except Exception as e:
                self.logger.error(f"WebSocket error: {e}")
                self.websocket_connections.discard(websocket)
    
    def _get_dashboard_html(self) -> str:
        """Generate the dashboard HTML."""
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{self.config.title}</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: {'#1a1a1a' if self.config.theme == 'dark' else '#f5f5f5'};
                    color: {'#ffffff' if self.config.theme == 'dark' else '#333333'};
                }}
                .header {{
                    background: {'#2d2d2d' if self.config.theme == 'dark' else '#ffffff'};
                    padding: 1rem 2rem;
                    border-bottom: 1px solid {'#444' if self.config.theme == 'dark' else '#ddd'};
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .container {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 2rem;
                    padding: 2rem;
                    max-width: 1400px;
                    margin: 0 auto;
                }}
                .card {{
                    background: {'#2d2d2d' if self.config.theme == 'dark' else '#ffffff'};
                    border-radius: 8px;
                    padding: 1.5rem;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    border: 1px solid {'#444' if self.config.theme == 'dark' else '#ddd'};
                }}
                .status-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 1rem;
                    margin-top: 1rem;
                }}
                .status-item {{
                    padding: 1rem;
                    border-radius: 6px;
                    background: {'#3d3d3d' if self.config.theme == 'dark' else '#f8f9fa'};
                    border: 1px solid {'#555' if self.config.theme == 'dark' else '#e9ecef'};
                }}
                .status-running {{ border-left: 4px solid #28a745; }}
                .status-failed {{ border-left: 4px solid #dc3545; }}
                .status-stopped {{ border-left: 4px solid #6c757d; }}
                .metrics-chart {{
                    height: 200px;
                    background: {'#3d3d3d' if self.config.theme == 'dark' else '#f8f9fa'};
                    border-radius: 4px;
                    margin-top: 1rem;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: #666;
                }}
                .controls {{
                    display: flex;
                    gap: 1rem;
                    margin-top: 1rem;
                }}
                .btn {{
                    padding: 0.5rem 1rem;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 0.9rem;
                }}
                .btn-primary {{ background: #007bff; color: white; }}
                .btn-warning {{ background: #ffc107; color: black; }}
                .btn-danger {{ background: #dc3545; color: white; }}
                .btn:hover {{ opacity: 0.8; }}
                .log-container {{
                    height: 300px;
                    overflow-y: auto;
                    background: {'#1e1e1e' if self.config.theme == 'dark' else '#f8f9fa'};
                    border: 1px solid {'#444' if self.config.theme == 'dark' else '#ddd'};
                    border-radius: 4px;
                    padding: 1rem;
                    font-family: 'Courier New', monospace;
                    font-size: 0.85rem;
                    margin-top: 1rem;
                }}
                .log-entry {{
                    margin-bottom: 0.5rem;
                    padding: 0.25rem;
                    border-radius: 2px;
                }}
                .log-error {{ background: rgba(220, 53, 69, 0.1); }}
                .log-warning {{ background: rgba(255, 193, 7, 0.1); }}
                .log-info {{ background: rgba(23, 162, 184, 0.1); }}
                .connection-status {{
                    position: fixed;
                    top: 1rem;
                    right: 1rem;
                    padding: 0.5rem 1rem;
                    border-radius: 4px;
                    font-size: 0.8rem;
                }}
                .connected {{ background: #28a745; color: white; }}
                .disconnected {{ background: #dc3545; color: white; }}
            </style>
        </head>
        <body>
            <div class="connection-status" id="connectionStatus">Connecting...</div>
            
            <div class="header">
                <h1>{self.config.title}</h1>
                <p>Real-time monitoring and control interface</p>
            </div>
            
            <div class="container">
                <div class="card">
                    <h2>System Status</h2>
                    <div id="systemStatus">Loading...</div>
                    <div class="controls">
                        <button class="btn btn-warning" onclick="refreshData()">Refresh</button>
                        {'<button class="btn btn-danger" onclick="emergencyShutdown()">Emergency Shutdown</button>' if self.config.enable_emergency_controls else ''}
                    </div>
                </div>
                
                <div class="card">
                    <h2>Agent Status</h2>
                    <div id="agentStatus">Loading...</div>
                </div>
                
                <div class="card">
                    <h2>System Metrics</h2>
                    <div class="metrics-chart" id="metricsChart">
                        Real-time metrics chart will appear here
                    </div>
                </div>
                
                <div class="card">
                    <h2>System Logs</h2>
                    <div class="log-container" id="systemLogs">
                        <div class="log-entry">Dashboard initialized...</div>
                    </div>
                </div>
            </div>
            
            <script>
                let ws = null;
                let reconnectInterval = null;
                
                function connectWebSocket() {{
                    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    const wsUrl = `${{protocol}}//${{window.location.host}}/ws`;
                    
                    ws = new WebSocket(wsUrl);
                    
                    ws.onopen = function() {{
                        console.log('WebSocket connected');
                        document.getElementById('connectionStatus').textContent = 'Connected';
                        document.getElementById('connectionStatus').className = 'connection-status connected';
                        if (reconnectInterval) {{
                            clearInterval(reconnectInterval);
                            reconnectInterval = null;
                        }}
                    }};
                    
                    ws.onmessage = function(event) {{
                        const data = JSON.parse(event.data);
                        updateDashboard(data);
                    }};
                    
                    ws.onclose = function() {{
                        console.log('WebSocket disconnected');
                        document.getElementById('connectionStatus').textContent = 'Disconnected';
                        document.getElementById('connectionStatus').className = 'connection-status disconnected';
                        
                        if (!reconnectInterval) {{
                            reconnectInterval = setInterval(connectWebSocket, 5000);
                        }}
                    }};
                    
                    ws.onerror = function(error) {{
                        console.error('WebSocket error:', error);
                    }};
                }}
                
                function updateDashboard(data) {{
                    // Update system status
                    if (data.system_status) {{
                        updateSystemStatus(data.system_status);
                    }}
                    
                    // Update agent status
                    if (data.agent_status) {{
                        updateAgentStatus(data.agent_status);
                    }}
                    
                    // Update logs
                    if (data.logs) {{
                        updateLogs(data.logs);
                    }}
                }}
                
                function updateSystemStatus(status) {{
                    const container = document.getElementById('systemStatus');
                    let html = '<div class="status-grid">';
                    
                    if (status.systems) {{
                        for (const [name, systemStatus] of Object.entries(status.systems)) {{
                            const statusClass = `status-${{systemStatus.status}}`;
                            html += `
                                <div class="status-item ${{statusClass}}">
                                    <strong>${{name}}</strong><br>
                                    Status: ${{systemStatus.status}}<br>
                                    ${{systemStatus.initialized_at ? `Started: ${{new Date(systemStatus.initialized_at).toLocaleTimeString()}}` : ''}}
                                </div>
                            `;
                        }}
                    }}
                    
                    html += '</div>';
                    container.innerHTML = html;
                }}
                
                function updateAgentStatus(agents) {{
                    const container = document.getElementById('agentStatus');
                    let html = '<div class="status-grid">';
                    
                    agents.forEach(agent => {{
                        const statusClass = `status-${{agent.status}}`;
                        html += `
                            <div class="status-item ${{statusClass}}">
                                <strong>${{agent.agent_id}}</strong><br>
                                Status: ${{agent.status}}<br>
                                Uptime: ${{Math.round(agent.uptime_seconds || 0)}}s<br>
                                {'<button class="btn btn-warning" onclick="restartAgent(\'' + agent.agent_id + '\')">Restart</button>' if self.config.enable_agent_controls else ''}
                            </div>
                        `;
                    }});
                    
                    html += '</div>';
                    container.innerHTML = html;
                }}
                
                function updateLogs(logs) {{
                    const container = document.getElementById('systemLogs');
                    let html = '';
                    
                    logs.slice(-20).forEach(log => {{
                        const logClass = log.level ? `log-${{log.level.toLowerCase()}}` : '';
                        html += `<div class="log-entry ${{logClass}}">${{log.timestamp}} [${{log.level}}] ${{log.message}}</div>`;
                    }});
                    
                    container.innerHTML = html;
                    container.scrollTop = container.scrollHeight;
                }}
                
                async function refreshData() {{
                    try {{
                        const response = await fetch('/api/status');
                        const data = await response.json();
                        updateSystemStatus(data);
                    }} catch (error) {{
                        console.error('Failed to refresh data:', error);
                    }}
                }}
                
                async function restartAgent(agentId) {{
                    if (!confirm(`Are you sure you want to restart agent ${{agentId}}?`)) return;
                    
                    try {{
                        const response = await fetch(`/api/agents/${{agentId}}/restart`, {{
                            method: 'POST'
                        }});
                        const result = await response.json();
                        
                        if (result.success) {{
                            alert('Agent restart initiated');
                        }} else {{
                            alert('Failed to restart agent');
                        }}
                    }} catch (error) {{
                        alert('Error restarting agent: ' + error.message);
                    }}
                }}
                
                async function emergencyShutdown() {{
                    if (!confirm('Are you sure you want to trigger an emergency shutdown? This will stop the entire ecosystem.')) return;
                    
                    try {{
                        const response = await fetch('/api/emergency/shutdown', {{
                            method: 'POST'
                        }});
                        const result = await response.json();
                        
                        if (result.success) {{
                            alert('Emergency shutdown initiated');
                        }} else {{
                            alert('Failed to trigger emergency shutdown');
                        }}
                    }} catch (error) {{
                        alert('Error triggering emergency shutdown: ' + error.message);
                    }}
                }}
                
                // Initialize WebSocket connection
                connectWebSocket();
                
                // Initial data load
                refreshData();
            </script>
        </body>
        </html>
        """
    
    async def _update_loop(self) -> None:
        """Background loop to update dashboard data."""
        while True:
            try:
                await asyncio.sleep(self.config.status_update_interval)
                
                # Update system status
                if self.orchestrator:
                    self.dashboard_data["system_status"] = await self.orchestrator.get_system_status()
                    
                    # Update agent status
                    if self.orchestrator.agent_manager:
                        self.dashboard_data["agent_status"] = await self.orchestrator.agent_manager.get_all_agents_status()
                
                # Update metrics (simplified for now)
                current_time = datetime.now()
                self.dashboard_data["metrics"]["timestamps"].append(current_time.isoformat())
                
                # Keep only recent data points
                max_points = self.config.max_chart_points
                for key in self.dashboard_data["metrics"]:
                    if len(self.dashboard_data["metrics"][key]) > max_points:
                        self.dashboard_data["metrics"][key] = self.dashboard_data["metrics"][key][-max_points:]
                
                # Add sample log entry
                self.dashboard_data["logs"].append({
                    "timestamp": current_time.strftime("%H:%M:%S"),
                    "level": "INFO",
                    "message": f"Dashboard update at {current_time.strftime('%H:%M:%S')}"
                })
                
                # Keep only recent log entries
                if len(self.dashboard_data["logs"]) > self.config.max_log_entries:
                    self.dashboard_data["logs"] = self.dashboard_data["logs"][-self.config.max_log_entries:]
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in dashboard update loop: {e}")
    
    async def _start_server(self) -> None:
        """Start the FastAPI server."""
        try:
            config = uvicorn.Config(
                self.app,
                host=self.config.host,
                port=self.config.port,
                log_level="info"
            )
            server = uvicorn.Server(config)
            await server.serve()
            
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Error starting dashboard server: {e}")
    
    async def broadcast_update(self, data: Dict[str, Any]) -> None:
        """Broadcast update to all connected WebSocket clients."""
        if not self.websocket_connections:
            return
        
        disconnected = set()
        
        for websocket in self.websocket_connections:
            try:
                await websocket.send_json(data)
            except:
                disconnected.add(websocket)
        
        # Remove disconnected clients
        self.websocket_connections -= disconnected