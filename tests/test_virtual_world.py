"""
Tests for the virtual world environment system.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from autonomous_ai_ecosystem.world.virtual_world import (
    VirtualWorld,
    Location,
    LocationType,
    Resource,
    ResourceType,
    ActivityType,
    Coordinates,
    AgentPosition,
    WorldEvent
)


class TestCoordinates:
    """Test the Coordinates class."""
    
    def test_distance_calculation(self):
        """Test distance calculation between coordinates."""
        coord1 = Coordinates(0, 0, 0)
        coord2 = Coordinates(3, 4, 0)
        
        distance = coord1.distance_to(coord2)
        assert distance == 5.0  # 3-4-5 triangle
    
    def test_3d_distance_calculation(self):
        """Test 3D distance calculation."""
        coord1 = Coordinates(0, 0, 0)
        coord2 = Coordinates(1, 1, 1)
        
        distance = coord1.distance_to(coord2)
        assert abs(distance - 1.732) < 0.01  # sqrt(3)


class TestVirtualWorld:
    """Test the VirtualWorld class."""
    
    @pytest.fixture
    async def world(self):
        """Create a test virtual world."""
        world = VirtualWorld("test_agent", (100, 100, 10))
        await world.initialize()
        return world
    
    @pytest.mark.asyncio
    async def test_world_initialization(self):
        """Test virtual world initialization."""
        world = VirtualWorld("test_agent", (200, 200, 20))
        await world.initialize()
        
        assert world.world_size == (200, 200, 20)
        assert len(world.locations) > 0
        assert "central_hub" in world.locations
        assert world.world_stats["total_locations"] > 0
    
    @pytest.mark.asyncio
    async def test_add_agent_to_world(self, world):
        """Test adding an agent to the world."""
        result = await world.add_agent_to_world("agent_1")
        
        assert result is True
        assert "agent_1" in world.agent_positions
        assert world.world_stats["total_agents"] == 1
        
        # Check agent is in a location
        position = world.agent_positions["agent_1"]
        location = world.locations[position.current_location_id]
        assert "agent_1" in location.current_occupants
    
    @pytest.mark.asyncio
    async def test_add_duplicate_agent(self, world):
        """Test adding the same agent twice."""
        await world.add_agent_to_world("agent_1")
        result = await world.add_agent_to_world("agent_1")
        
        assert result is True  # Should handle gracefully
        assert world.world_stats["total_agents"] == 1
    
    @pytest.mark.asyncio
    async def test_move_agent(self, world):
        """Test moving an agent between locations."""
        await world.add_agent_to_world("agent_1")
        
        # Find two different locations
        locations = list(world.locations.keys())
        current_location = world.agent_positions["agent_1"].current_location_id
        target_location = None
        
        for loc_id in locations:
            if loc_id != current_location:
                target_location = loc_id
                break
        
        assert target_location is not None
        
        result = await world.move_agent("agent_1", target_location)
        
        assert result["success"] is True
        assert world.agent_positions["agent_1"].current_location_id == target_location
        assert world.world_stats["agent_movements"] == 1
    
    @pytest.mark.asyncio
    async def test_move_nonexistent_agent(self, world):
        """Test moving an agent that doesn't exist."""
        result = await world.move_agent("nonexistent", "central_hub")
        
        assert result["success"] is False
        assert "not in world" in result["error"]
    
    @pytest.mark.asyncio
    async def test_move_to_nonexistent_location(self, world):
        """Test moving to a location that doesn't exist."""
        await world.add_agent_to_world("agent_1")
        
        result = await world.move_agent("agent_1", "nonexistent_location")
        
        assert result["success"] is False
        assert "not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_start_activity(self, world):
        """Test starting an activity."""
        await world.add_agent_to_world("agent_1")
        
        # Find a location with available activities
        position = world.agent_positions["agent_1"]
        location = world.locations[position.current_location_id]
        
        if location.available_activities:
            activity = location.available_activities[0]
            result = await world.start_activity("agent_1", activity, 2.0)
            
            assert result["success"] is True
            assert world.agent_positions["agent_1"].current_activity == activity
            assert world.world_stats["activities_performed"] == 1
    
    @pytest.mark.asyncio
    async def test_start_unavailable_activity(self, world):
        """Test starting an activity not available at location."""
        await world.add_agent_to_world("agent_1")
        
        # Try to start an activity that's not available
        result = await world.start_activity("agent_1", ActivityType.RESEARCH, 1.0)
        
        # This might succeed if the location has research, so we check the logic
        if not result["success"]:
            assert "not available" in result["error"]
    
    @pytest.mark.asyncio
    async def test_complete_activity(self, world):
        """Test completing an activity."""
        await world.add_agent_to_world("agent_1")
        
        # Start an activity first
        position = world.agent_positions["agent_1"]
        location = world.locations[position.current_location_id]
        
        if location.available_activities:
            activity = location.available_activities[0]
            await world.start_activity("agent_1", activity, 1.0)
            
            # Complete the activity
            result = await world.complete_activity("agent_1")
            
            assert result["success"] is True
            assert world.agent_positions["agent_1"].current_activity is None
            assert "effects" in result
    
    @pytest.mark.asyncio
    async def test_complete_no_activity(self, world):
        """Test completing activity when none is active."""
        await world.add_agent_to_world("agent_1")
        
        result = await world.complete_activity("agent_1")
        
        assert result["success"] is False
        assert "not performing" in result["error"]
    
    @pytest.mark.asyncio
    async def test_gather_resources(self, world):
        """Test gathering resources from a location."""
        await world.add_agent_to_world("agent_1")
        
        # Find a location with resources
        for location in world.locations.values():
            if location.resources:
                # Move agent to this location
                await world.move_agent("agent_1", location.location_id)
                
                # Try to gather a resource
                resource = list(location.resources.values())[0]
                result = await world.gather_resources("agent_1", resource.resource_type, 10.0)
                
                if result["success"]:
                    assert result["quantity_gathered"] > 0
                    assert world.world_stats["resource_transactions"] == 1
                break
    
    def test_get_agent_location_info(self, world):
        """Test getting agent location information."""
        # This test needs to be run after world initialization
        asyncio.run(self._test_get_agent_location_info_async(world))
    
    async def _test_get_agent_location_info_async(self, world):
        """Async helper for location info test."""
        await world.add_agent_to_world("agent_1")
        
        info = world.get_agent_location_info("agent_1")
        
        assert "location" in info
        assert "agent_position" in info
        assert "available_activities" in info
        assert "available_resources" in info
        assert "connected_locations" in info
    
    def test_get_agent_location_info_nonexistent(self, world):
        """Test getting location info for nonexistent agent."""
        asyncio.run(self._test_get_agent_location_info_nonexistent_async(world))
    
    async def _test_get_agent_location_info_nonexistent_async(self, world):
        """Async helper for nonexistent agent test."""
        info = world.get_agent_location_info("nonexistent")
        
        assert "error" in info
    
    def test_get_world_overview(self, world):
        """Test getting world overview."""
        asyncio.run(self._test_get_world_overview_async(world))
    
    async def _test_get_world_overview_async(self, world):
        """Async helper for world overview test."""
        overview = world.get_world_overview()
        
        assert "world_size" in overview
        assert "statistics" in overview
        assert "location_statistics" in overview
        assert "resource_statistics" in overview
        assert "activity_statistics" in overview
    
    def test_find_locations_by_type(self, world):
        """Test finding locations by type."""
        asyncio.run(self._test_find_locations_by_type_async(world))
    
    async def _test_find_locations_by_type_async(self, world):
        """Async helper for find locations test."""
        residential_locations = world.find_locations_by_type(LocationType.RESIDENTIAL)
        
        assert len(residential_locations) > 0
        for location in residential_locations:
            assert "id" in location
            assert "name" in location
            assert "coordinates" in location
    
    def test_find_locations_with_distance_filter(self, world):
        """Test finding locations with distance filtering."""
        asyncio.run(self._test_find_locations_with_distance_filter_async(world))
    
    async def _test_find_locations_with_distance_filter_async(self, world):
        """Async helper for distance filter test."""
        center = Coordinates(50, 50, 0)
        nearby_locations = world.find_locations_by_type(
            LocationType.RESIDENTIAL,
            max_distance=100.0,
            from_coordinates=center
        )
        
        # All returned locations should be within distance
        for location in nearby_locations:
            if location["distance"] is not None:
                assert location["distance"] <= 100.0
    
    def test_get_world_events(self, world):
        """Test getting world events."""
        asyncio.run(self._test_get_world_events_async(world))
    
    async def _test_get_world_events_async(self, world):
        """Async helper for world events test."""
        # Add an agent to generate some events
        await world.add_agent_to_world("agent_1")
        
        events = world.get_world_events(hours_back=1.0)
        
        assert isinstance(events, list)
        # Should have at least the agent addition event
        assert len(events) > 0
    
    @pytest.mark.asyncio
    async def test_world_shutdown(self, world):
        """Test world shutdown."""
        await world.shutdown()
        # Should complete without errors


class TestLocation:
    """Test the Location class."""
    
    def test_location_creation(self):
        """Test creating a location."""
        coords = Coordinates(10, 20, 0)
        location = Location(
            location_id="test_loc",
            name="Test Location",
            description="A test location",
            location_type=LocationType.WORKSPACE,
            coordinates=coords,
            capacity=10
        )
        
        assert location.location_id == "test_loc"
        assert location.name == "Test Location"
        assert location.location_type == LocationType.WORKSPACE
        assert location.capacity == 10
        assert len(location.current_occupants) == 0


class TestResource:
    """Test the Resource class."""
    
    def test_resource_creation(self):
        """Test creating a resource."""
        resource = Resource(
            resource_id="test_resource",
            resource_type=ResourceType.COMPUTATIONAL_POWER,
            quantity=100.0,
            quality=0.8,
            location_id="test_location"
        )
        
        assert resource.resource_id == "test_resource"
        assert resource.resource_type == ResourceType.COMPUTATIONAL_POWER
        assert resource.quantity == 100.0
        assert resource.quality == 0.8


class TestWorldEvent:
    """Test the WorldEvent class."""
    
    def test_world_event_creation(self):
        """Test creating a world event."""
        event = WorldEvent(
            event_id="test_event",
            event_type="test_type",
            location_id="test_location",
            description="Test event description",
            participants=["agent_1", "agent_2"]
        )
        
        assert event.event_id == "test_event"
        assert event.event_type == "test_type"
        assert event.location_id == "test_location"
        assert len(event.participants) == 2


if __name__ == "__main__":
    pytest.main([__file__])