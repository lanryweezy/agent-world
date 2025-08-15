"""
Unit tests for emergency response and shutdown systems.
"""

import pytest
import pytest_asyncio
import asyncio
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from autonomous_ai_ecosystem.safety.emergency_response import (
    EmergencyResponseSystem,
    EmergencyLevel,
    ShutdownReason,
    RecoveryStrategy,
    EmergencyIncident,
    SystemBackup
)


@pytest_asyncio.fixture
async def emergency_system():
    """Create emergency response system for testing."""
    system = EmergencyResponseSystem("test_emergency")
    
    # Use temporary directory for backups
    temp_dir = tempfile.mkdtemp()
    system.config["backup_directory"] = temp_dir
    system.config["incident_log_file"] = os.path.join(temp_dir, "incidents.log")
    
    await system.initialize()
    
    yield system
    
    await system.shutdown()
    
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_emergency_system_initialization(emergency_system):
    """Test emergency system initialization."""
    assert emergency_system.agent_id == "test_emergency"
    assert emergency_system.monitoring_active
    assert not emergency_system.emergency_active
    assert not emergency_system.shutdown_in_progress
    assert os.path.exists(emergency_system.config["backup_directory"])


@pytest.mark.asyncio
async def test_incident_reporting(emergency_system):
    """Test incident reporting functionality."""
    # Report an incident
    incident_id = await emergency_system.report_incident(
        level=EmergencyLevel.HIGH,
        reason=ShutdownReason.MEMORY_LEAK,
        description="High memory usage detected",
        component="memory_monitor",
        error_message="Memory usage exceeded threshold"
    )
    
    assert incident_id
    assert incident_id in emergency_system.incidents
    
    incident = emergency_system.incidents[incident_id]
    assert incident.level == EmergencyLevel.HIGH
    assert incident.reason == ShutdownReason.MEMORY_LEAK
    assert incident.description == "High memory usage detected"
    assert incident.component == "memory_monitor"
    assert incident.error_message == "Memory usage exceeded threshold"
    assert not incident.resolved
    
    # Check statistics
    assert emergency_system.stats["total_incidents"] == 1
    assert emergency_system.stats["incidents_by_level"][EmergencyLevel.HIGH.value] == 1
    assert emergency_system.stats["incidents_by_reason"][ShutdownReason.MEMORY_LEAK.value] == 1


@pytest.mark.asyncio
async def test_incident_report_retrieval(emergency_system):
    """Test incident report retrieval."""
    # Report an incident
    incident_id = await emergency_system.report_incident(
        level=EmergencyLevel.MEDIUM,
        reason=ShutdownReason.RESOURCE_EXHAUSTION,
        description="CPU usage high"
    )
    
    # Get incident report
    report = await emergency_system.get_incident_report(incident_id)
    
    assert report is not None
    assert report["incident_id"] == incident_id
    assert report["level"] == EmergencyLevel.MEDIUM.value
    assert report["reason"] == ShutdownReason.RESOURCE_EXHAUSTION.value
    assert report["description"] == "CPU usage high"
    assert not report["resolved"]
    assert report["detected_at"]
    
    # Test non-existent incident
    non_existent_report = await emergency_system.get_incident_report("non_existent")
    assert non_existent_report is None


@pytest.mark.asyncio
async def test_system_backup_creation(emergency_system):
    """Test system backup creation."""
    # Create test files to backup
    test_config = os.path.join(os.getcwd(), "config.json")
    with open(test_config, "w") as f:
        f.write('{"test": "config"}')
    
    try:
        # Create backup
        backup_id = await emergency_system.create_system_backup("test", "full")
        
        assert backup_id
        assert backup_id in emergency_system.backups
        
        backup = emergency_system.backups[backup_id]
        assert backup.backup_type == "test"
        assert backup.components_backed_up
        assert backup.size_bytes > 0
        assert backup.checksum
        assert os.path.exists(backup.backup_path)
        
        # Check statistics
        assert emergency_system.stats["total_backups"] == 2  # Initial + test backup
        
    finally:
        # Cleanup test file
        if os.path.exists(test_config):
            os.remove(test_config)


@pytest.mark.asyncio
async def test_backup_verification(emergency_system):
    """Test backup verification."""
    # Create backup
    backup_id = await emergency_system.create_system_backup("verification_test", "config")
    
    assert backup_id
    backup = emergency_system.backups[backup_id]
    
    # Verify backup
    is_valid = await emergency_system._verify_backup(backup)
    assert is_valid
    assert backup.verified
    assert backup.verification_date
    
    # Test corrupted backup
    # Modify backup directory to simulate corruption
    test_file = os.path.join(backup.backup_path, "corrupted.txt")
    with open(test_file, "w") as f:
        f.write("corruption")
    
    is_valid_after_corruption = await emergency_system._verify_backup(backup)
    assert not is_valid_after_corruption


@pytest.mark.asyncio
async def test_system_metrics_collection(emergency_system):
    """Test system metrics collection."""
    metrics = await emergency_system._collect_system_metrics()
    
    assert "timestamp" in metrics
    assert "cpu_percent" in metrics
    assert "memory_percent" in metrics
    assert "memory_available_mb" in metrics
    assert "disk_percent" in metrics
    assert "disk_free_mb" in metrics
    assert "process" in metrics
    
    process_info = metrics["process"]
    assert "cpu_percent" in process_info
    assert "memory_mb" in process_info
    assert "open_files" in process_info
    assert "threads" in process_info


@pytest.mark.asyncio
async def test_emergency_condition_detection(emergency_system):
    """Test emergency condition detection."""
    # Create metrics that exceed thresholds
    high_cpu_metrics = {
        "cpu_percent": 98.0,
        "memory_percent": 50.0,
        "disk_percent": 50.0,
        "process": {"open_files": 100}
    }
    
    initial_incidents = len(emergency_system.incidents)
    
    # Check emergency conditions
    await emergency_system._check_emergency_conditions(high_cpu_metrics)
    
    # Should have created an incident for high CPU
    assert len(emergency_system.incidents) > initial_incidents
    
    # Find the CPU incident
    cpu_incident = None
    for incident in emergency_system.incidents.values():
        if "High CPU usage" in incident.description:
            cpu_incident = incident
            break
    
    assert cpu_incident is not None
    assert cpu_incident.level == EmergencyLevel.HIGH
    assert cpu_incident.reason == ShutdownReason.RESOURCE_EXHAUSTION


@pytest.mark.asyncio
async def test_recovery_strategy_determination(emergency_system):
    """Test recovery strategy determination."""
    # Test different incident scenarios
    
    # Critical security breach
    security_incident = EmergencyIncident(
        incident_id="test_security",
        level=EmergencyLevel.CRITICAL,
        reason=ShutdownReason.SECURITY_BREACH,
        description="Security breach detected"
    )
    
    strategy = emergency_system._determine_recovery_strategy(security_incident)
    assert strategy == RecoveryStrategy.RESTORE_BACKUP
    
    # High memory leak
    memory_incident = EmergencyIncident(
        incident_id="test_memory",
        level=EmergencyLevel.HIGH,
        reason=ShutdownReason.MEMORY_LEAK,
        description="Memory leak detected"
    )
    
    strategy = emergency_system._determine_recovery_strategy(memory_incident)
    assert strategy == RecoveryStrategy.RESTART_COMPONENT
    
    # Catastrophic incident
    catastrophic_incident = EmergencyIncident(
        incident_id="test_catastrophic",
        level=EmergencyLevel.CATASTROPHIC,
        reason=ShutdownReason.SYSTEM_CORRUPTION,
        description="System corruption detected"
    )
    
    strategy = emergency_system._determine_recovery_strategy(catastrophic_incident)
    assert strategy == RecoveryStrategy.MANUAL_INTERVENTION


@pytest.mark.asyncio
async def test_shutdown_handler_registration(emergency_system):
    """Test shutdown handler registration."""
    # Create mock handler
    mock_handler = Mock()
    
    # Register handler
    emergency_system.register_shutdown_handler("test_handler", mock_handler)
    
    assert "test_handler" in emergency_system.shutdown_handlers
    assert emergency_system.shutdown_handlers["test_handler"] == mock_handler


@pytest.mark.asyncio
async def test_system_status_retrieval(emergency_system):
    """Test system status retrieval."""
    status = await emergency_system.get_system_status()
    
    assert "emergency_active" in status
    assert "shutdown_in_progress" in status
    assert "safe_mode" in status
    assert "monitoring_active" in status
    assert "system_uptime_seconds" in status
    assert "current_metrics" in status
    assert "recent_incidents" in status
    assert "total_backups" in status
    assert "statistics" in status
    assert "resource_thresholds" in status
    
    assert not status["emergency_active"]
    assert not status["shutdown_in_progress"]
    assert not status["safe_mode"]
    assert status["monitoring_active"]


@pytest.mark.asyncio
async def test_monitoring_start_stop(emergency_system):
    """Test monitoring start and stop."""
    # Stop monitoring
    await emergency_system.stop_monitoring()
    assert not emergency_system.monitoring_active
    assert emergency_system.monitoring_task is None
    
    # Start monitoring
    await emergency_system.start_monitoring()
    assert emergency_system.monitoring_active
    assert emergency_system.monitoring_task is not None
    
    # Stop again
    await emergency_system.stop_monitoring()
    assert not emergency_system.monitoring_active


@pytest.mark.asyncio
async def test_automatic_response_trigger(emergency_system):
    """Test automatic response triggering."""
    # Create high-level incident
    incident = EmergencyIncident(
        incident_id="test_auto_response",
        level=EmergencyLevel.HIGH,
        reason=ShutdownReason.MEMORY_LEAK,
        description="Memory leak for auto response test"
    )
    
    # Trigger automatic response
    await emergency_system._trigger_automatic_response(incident)
    
    # Check that recovery strategy was set
    assert incident.recovery_strategy is not None
    assert len(incident.actions_taken) > 0
    
    # Check that appropriate action was logged
    strategy_action = None
    for action in incident.actions_taken:
        if "Recovery strategy determined" in action:
            strategy_action = action
            break
    
    assert strategy_action is not None


@pytest.mark.asyncio
async def test_incident_resolution(emergency_system):
    """Test incident resolution."""
    # Create incident
    incident = EmergencyIncident(
        incident_id="test_resolution",
        level=EmergencyLevel.MEDIUM,
        reason=ShutdownReason.RESOURCE_EXHAUSTION,
        description="Test incident for resolution"
    )
    
    assert not incident.resolved
    assert incident.resolved_at is None
    assert incident.response_time_seconds is None
    
    # Mark as resolved
    incident.mark_resolved()
    
    assert incident.resolved
    assert incident.resolved_at is not None
    assert incident.response_time_seconds is not None
    assert incident.response_time_seconds >= 0


@pytest.mark.asyncio
async def test_backup_expiration_cleanup(emergency_system):
    """Test backup expiration and cleanup."""
    # Create backup with short expiration
    backup_id = await emergency_system.create_system_backup("expiration_test", "config")
    backup = emergency_system.backups[backup_id]
    
    # Set expiration to past
    backup.expires_at = datetime.now() - timedelta(days=1)
    backup.auto_delete = True
    
    # Run cleanup
    await emergency_system._cleanup_old_data()
    
    # Backup should be removed
    assert backup_id not in emergency_system.backups
    assert not os.path.exists(backup.backup_path)


@pytest.mark.asyncio
async def test_directory_size_calculation(emergency_system):
    """Test directory size calculation."""
    # Create test directory with files
    test_dir = os.path.join(emergency_system.config["backup_directory"], "size_test")
    os.makedirs(test_dir, exist_ok=True)
    
    # Create test files
    test_file1 = os.path.join(test_dir, "file1.txt")
    test_file2 = os.path.join(test_dir, "file2.txt")
    
    with open(test_file1, "w") as f:
        f.write("test content 1")
    
    with open(test_file2, "w") as f:
        f.write("test content 2")
    
    # Calculate size
    size = await emergency_system._calculate_directory_size(test_dir)
    
    assert size > 0
    assert size == len("test content 1") + len("test content 2")


@pytest.mark.asyncio
async def test_directory_checksum_calculation(emergency_system):
    """Test directory checksum calculation."""
    # Create test directory with files
    test_dir = os.path.join(emergency_system.config["backup_directory"], "checksum_test")
    os.makedirs(test_dir, exist_ok=True)
    
    # Create test file
    test_file = os.path.join(test_dir, "checksum_file.txt")
    with open(test_file, "w") as f:
        f.write("checksum test content")
    
    # Calculate checksum
    checksum1 = await emergency_system._calculate_directory_checksum(test_dir)
    checksum2 = await emergency_system._calculate_directory_checksum(test_dir)
    
    # Should be consistent
    assert checksum1 == checksum2
    assert len(checksum1) == 32  # MD5 hash length
    
    # Modify file and check checksum changes
    with open(test_file, "a") as f:
        f.write(" modified")
    
    checksum3 = await emergency_system._calculate_directory_checksum(test_dir)
    assert checksum3 != checksum1


@pytest.mark.asyncio
async def test_incident_action_logging(emergency_system):
    """Test incident action logging."""
    incident = EmergencyIncident(
        incident_id="test_actions",
        level=EmergencyLevel.LOW,
        reason=ShutdownReason.RESOURCE_EXHAUSTION,
        description="Test incident for action logging"
    )
    
    # Add actions
    incident.add_action("First action taken")
    incident.add_action("Second action taken")
    
    assert len(incident.actions_taken) == 2
    assert "First action taken" in incident.actions_taken[0]
    assert "Second action taken" in incident.actions_taken[1]
    
    # Check timestamp format
    for action in incident.actions_taken:
        assert "[" in action and "]" in action  # Timestamp format


@pytest.mark.asyncio
async def test_resource_threshold_configuration(emergency_system):
    """Test resource threshold configuration."""
    # Check default thresholds
    assert "cpu_percent" in emergency_system.resource_thresholds
    assert "memory_percent" in emergency_system.resource_thresholds
    assert "disk_percent" in emergency_system.resource_thresholds
    assert "open_files" in emergency_system.resource_thresholds
    
    # Modify thresholds
    emergency_system.resource_thresholds["cpu_percent"] = 80.0
    emergency_system.resource_thresholds["memory_percent"] = 85.0
    
    assert emergency_system.resource_thresholds["cpu_percent"] == 80.0
    assert emergency_system.resource_thresholds["memory_percent"] == 85.0


if __name__ == "__main__":
    pytest.main([__file__])