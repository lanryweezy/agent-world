"""
State management system for autonomous AI agents.

This module handles the creation, persistence, and management of agent states
including emotional states, relationships, goals, and status tracking.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict

from .interfaces import AgentState, AgentStatus
from .logger import get_agent_logger, log_agent_event
from ..utils.validators import validate_emotional_state
from ..utils.generators import generate_emotional_state


class StateManager:
    """
    Manages agent states including emotional states, relationships, goals, and persistence.
    """
    
    def __init__(self, data_directory: str = "./data"):
        self.data_directory = Path(data_directory)
        self.db_path = self.data_directory / "agents" / "states.db"
        self.logger = get_agent_logger("SYSTEM", "state_manager")
        
        # Ensure directories exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._initialize_database()
        
        # State change tracking
        self.state_history: Dict[str, List[Dict]] = {}
        self.relationship_cache: Dict[str, Dict[str, float]] = {}
    
    def _initialize_database(self) -> None:
        """Initialize the state database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS agent_states (
                        agent_id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        emotional_state TEXT NOT NULL,
                        status_level INTEGER NOT NULL DEFAULT 0,
                        relationships TEXT NOT NULL DEFAULT '{}',
                        current_goals TEXT NOT NULL DEFAULT '[]',
                        last_activity REAL,
                        resource_usage TEXT NOT NULL DEFAULT '{}',
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS state_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        agent_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        emotional_state TEXT NOT NULL,
                        status_level INTEGER NOT NULL,
                        timestamp REAL NOT NULL,
                        change_reason TEXT,
                        FOREIGN KEY (agent_id) REFERENCES agent_states(agent_id)
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS relationships (
                        agent1_id TEXT NOT NULL,
                        agent2_id TEXT NOT NULL,
                        relationship_strength REAL NOT NULL,
                        relationship_type TEXT,
                        interaction_count INTEGER NOT NULL DEFAULT 0,
                        last_interaction REAL,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL,
                        PRIMARY KEY (agent1_id, agent2_id)
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS goals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        agent_id TEXT NOT NULL,
                        goal_description TEXT NOT NULL,
                        priority INTEGER NOT NULL DEFAULT 5,
                        status TEXT NOT NULL DEFAULT 'active',
                        progress REAL NOT NULL DEFAULT 0.0,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL,
                        deadline REAL,
                        FOREIGN KEY (agent_id) REFERENCES agent_states(agent_id)
                    )
                """)
                
                # Create indexes
                conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_status ON agent_states(status)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_state_history_agent ON state_history(agent_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_state_history_timestamp ON state_history(timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_relationships_agent1 ON relationships(agent1_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_goals_agent ON goals(agent_id)")
                
                conn.commit()
                
            self.logger.info("State database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize state database: {e}")
            raise
    
    def create_state(self, agent_id: str, initial_emotional_state: Optional[Dict[str, float]] = None) -> AgentState:
        """
        Create a new agent state with default values.
        
        Args:
            agent_id: Agent identifier
            initial_emotional_state: Optional initial emotional state
            
        Returns:
            Created AgentState
            
        Raises:
            ValueError: If validation fails
        """
        try:
            # Generate initial emotional state if not provided
            if initial_emotional_state is None:
                initial_emotional_state = generate_emotional_state()
            
            # Validate emotional state
            validation_errors = validate_emotional_state(initial_emotional_state)
            if validation_errors:
                raise ValueError(f"Emotional state validation failed: {validation_errors}")
            
            # Create state
            state = AgentState(
                agent_id=agent_id,
                status=AgentStatus.ACTIVE,
                emotional_state=initial_emotional_state,
                status_level=0,
                relationships={},
                current_goals=[],
                last_activity=datetime.now(),
                resource_usage={}
            )
            
            # Store in database
            self._store_state(state)
            
            # Log state creation
            log_agent_event(
                agent_id,
                "state_created",
                {
                    "initial_status": state.status.value,
                    "emotional_state": state.emotional_state
                }
            )
            
            self.logger.info(f"Created state for agent {agent_id}")
            
            return state
            
        except Exception as e:
            self.logger.error(f"Failed to create state for {agent_id}: {e}")
            raise
    
    def get_state(self, agent_id: str) -> Optional[AgentState]:
        """
        Retrieve an agent state by ID.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            AgentState if found, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM agent_states WHERE agent_id = ?",
                    (agent_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_state(row)
                
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve state for {agent_id}: {e}")
            return None
    
    def update_state(self, state: AgentState, change_reason: Optional[str] = None) -> bool:
        """
        Update an existing agent state.
        
        Args:
            state: Updated AgentState
            change_reason: Optional reason for the change
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate emotional state
            validation_errors = validate_emotional_state(state.emotional_state)
            if validation_errors:
                self.logger.error(f"Emotional state validation failed: {validation_errors}")
                return False
            
            # Get current state for history tracking
            current_state = self.get_state(state.agent_id)
            
            # Update database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE agent_states 
                    SET status = ?, emotional_state = ?, status_level = ?, 
                        relationships = ?, current_goals = ?, last_activity = ?,
                        resource_usage = ?, updated_at = ?
                    WHERE agent_id = ?
                """, (
                    state.status.value,
                    json.dumps(state.emotional_state),
                    state.status_level,
                    json.dumps(state.relationships),
                    json.dumps(state.current_goals),
                    state.last_activity.timestamp() if state.last_activity else None,
                    json.dumps(state.resource_usage),
                    datetime.now().timestamp(),
                    state.agent_id
                ))
                
                # Add to history if status changed
                if current_state and current_state.status != state.status:
                    conn.execute("""
                        INSERT INTO state_history 
                        (agent_id, status, emotional_state, status_level, timestamp, change_reason)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        state.agent_id,
                        state.status.value,
                        json.dumps(state.emotional_state),
                        state.status_level,
                        datetime.now().timestamp(),
                        change_reason
                    ))
                
                conn.commit()
            
            # Log state change
            if current_state and current_state.status != state.status:
                log_agent_event(
                    state.agent_id,
                    "status_change",
                    {
                        "old_status": current_state.status.value,
                        "new_status": state.status.value,
                        "reason": change_reason
                    }
                )
            
            self.logger.debug(f"Updated state for agent {state.agent_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update state for {state.agent_id}: {e}")
            return False
    
    def update_emotional_state(
        self, 
        agent_id: str, 
        emotion_changes: Dict[str, float],
        reason: Optional[str] = None
    ) -> bool:
        """
        Update specific emotions in an agent's emotional state.
        
        Args:
            agent_id: Agent identifier
            emotion_changes: Dictionary of emotion changes (emotion -> delta)
            reason: Optional reason for the change
            
        Returns:
            True if successful, False otherwise
        """
        try:
            state = self.get_state(agent_id)
            if not state:
                self.logger.error(f"Agent {agent_id} state not found")
                return False
            
            # Apply emotion changes
            for emotion, delta in emotion_changes.items():
                if emotion in state.emotional_state:
                    new_value = state.emotional_state[emotion] + delta
                    state.emotional_state[emotion] = max(0.0, min(1.0, new_value))
            
            # Update last activity
            state.last_activity = datetime.now()
            
            # Save updated state
            success = self.update_state(state, f"emotion_update: {reason}")
            
            if success:
                log_agent_event(
                    agent_id,
                    "emotion_change",
                    {
                        "changes": emotion_changes,
                        "new_state": state.emotional_state,
                        "reason": reason
                    }
                )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to update emotions for {agent_id}: {e}")
            return False
    
    def update_relationship(
        self, 
        agent1_id: str, 
        agent2_id: str, 
        strength_change: float,
        relationship_type: Optional[str] = None
    ) -> bool:
        """
        Update relationship between two agents.
        
        Args:
            agent1_id: First agent ID
            agent2_id: Second agent ID
            strength_change: Change in relationship strength (-1.0 to 1.0)
            relationship_type: Optional relationship type
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                now = datetime.now().timestamp()
                
                # Check if relationship exists
                cursor = conn.execute("""
                    SELECT relationship_strength, interaction_count 
                    FROM relationships 
                    WHERE agent1_id = ? AND agent2_id = ?
                """, (agent1_id, agent2_id))
                
                row = cursor.fetchone()
                
                if row:
                    # Update existing relationship
                    current_strength, interaction_count = row
                    new_strength = max(-1.0, min(1.0, current_strength + strength_change))
                    
                    conn.execute("""
                        UPDATE relationships 
                        SET relationship_strength = ?, interaction_count = ?, 
                            last_interaction = ?, updated_at = ?,
                            relationship_type = COALESCE(?, relationship_type)
                        WHERE agent1_id = ? AND agent2_id = ?
                    """, (
                        new_strength, interaction_count + 1, now, now,
                        relationship_type, agent1_id, agent2_id
                    ))
                else:
                    # Create new relationship
                    initial_strength = max(-1.0, min(1.0, strength_change))
                    conn.execute("""
                        INSERT INTO relationships 
                        (agent1_id, agent2_id, relationship_strength, relationship_type,
                         interaction_count, last_interaction, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        agent1_id, agent2_id, initial_strength, relationship_type,
                        1, now, now, now
                    ))
                
                # Also update the reverse relationship
                cursor = conn.execute("""
                    SELECT relationship_strength, interaction_count 
                    FROM relationships 
                    WHERE agent1_id = ? AND agent2_id = ?
                """, (agent2_id, agent1_id))
                
                row = cursor.fetchone()
                
                if row:
                    current_strength, interaction_count = row
                    new_strength = max(-1.0, min(1.0, current_strength + strength_change))
                    
                    conn.execute("""
                        UPDATE relationships 
                        SET relationship_strength = ?, interaction_count = ?, 
                            last_interaction = ?, updated_at = ?,
                            relationship_type = COALESCE(?, relationship_type)
                        WHERE agent1_id = ? AND agent2_id = ?
                    """, (
                        new_strength, interaction_count + 1, now, now,
                        relationship_type, agent2_id, agent1_id
                    ))
                else:
                    initial_strength = max(-1.0, min(1.0, strength_change))
                    conn.execute("""
                        INSERT INTO relationships 
                        (agent1_id, agent2_id, relationship_strength, relationship_type,
                         interaction_count, last_interaction, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        agent2_id, agent1_id, initial_strength, relationship_type,
                        1, now, now, now
                    ))
                
                conn.commit()
            
            # Update agent states with new relationship info
            self._update_agent_relationships(agent1_id)
            self._update_agent_relationships(agent2_id)
            
            log_agent_event(
                agent1_id,
                "relationship_update",
                {
                    "other_agent": agent2_id,
                    "strength_change": strength_change,
                    "relationship_type": relationship_type
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update relationship {agent1_id}-{agent2_id}: {e}")
            return False
    
    def add_goal(
        self, 
        agent_id: str, 
        goal_description: str, 
        priority: int = 5,
        deadline: Optional[datetime] = None
    ) -> bool:
        """
        Add a goal to an agent's goal list.
        
        Args:
            agent_id: Agent identifier
            goal_description: Description of the goal
            priority: Goal priority (1-10)
            deadline: Optional deadline
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                now = datetime.now().timestamp()
                deadline_timestamp = deadline.timestamp() if deadline else None
                
                conn.execute("""
                    INSERT INTO goals 
                    (agent_id, goal_description, priority, status, progress, 
                     created_at, updated_at, deadline)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    agent_id, goal_description, priority, 'active', 0.0,
                    now, now, deadline_timestamp
                ))
                
                conn.commit()
            
            # Update agent state with new goals
            self._update_agent_goals(agent_id)
            
            log_agent_event(
                agent_id,
                "goal_added",
                {
                    "goal": goal_description,
                    "priority": priority,
                    "deadline": deadline.isoformat() if deadline else None
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add goal for {agent_id}: {e}")
            return False
    
    def update_goal_progress(self, agent_id: str, goal_description: str, progress: float) -> bool:
        """
        Update progress on a specific goal.
        
        Args:
            agent_id: Agent identifier
            goal_description: Goal description to match
            progress: Progress value (0.0 to 1.0)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            progress = max(0.0, min(1.0, progress))
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    UPDATE goals 
                    SET progress = ?, updated_at = ?, 
                        status = CASE WHEN ? >= 1.0 THEN 'completed' ELSE status END
                    WHERE agent_id = ? AND goal_description = ? AND status = 'active'
                """, (progress, datetime.now().timestamp(), progress, agent_id, goal_description))
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    # Update agent state
                    self._update_agent_goals(agent_id)
                    
                    log_agent_event(
                        agent_id,
                        "goal_progress",
                        {
                            "goal": goal_description,
                            "progress": progress,
                            "completed": progress >= 1.0
                        }
                    )
                    
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to update goal progress for {agent_id}: {e}")
            return False
    
    def get_state_history(self, agent_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get state change history for an agent.
        
        Args:
            agent_id: Agent identifier
            limit: Maximum number of history entries
            
        Returns:
            List of state history entries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM state_history 
                    WHERE agent_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (agent_id, limit))
                
                rows = cursor.fetchall()
                
                history = []
                for row in rows:
                    history.append({
                        'timestamp': datetime.fromtimestamp(row['timestamp']),
                        'status': row['status'],
                        'emotional_state': json.loads(row['emotional_state']),
                        'status_level': row['status_level'],
                        'change_reason': row['change_reason']
                    })
                
                return history
                
        except Exception as e:
            self.logger.error(f"Failed to get state history for {agent_id}: {e}")
            return []
    
    def get_relationships(self, agent_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all relationships for an agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Dictionary of relationships {other_agent_id: relationship_info}
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM relationships 
                    WHERE agent1_id = ?
                    ORDER BY relationship_strength DESC
                """, (agent_id,))
                
                rows = cursor.fetchall()
                
                relationships = {}
                for row in rows:
                    relationships[row['agent2_id']] = {
                        'strength': row['relationship_strength'],
                        'type': row['relationship_type'],
                        'interaction_count': row['interaction_count'],
                        'last_interaction': datetime.fromtimestamp(row['last_interaction']) if row['last_interaction'] else None
                    }
                
                return relationships
                
        except Exception as e:
            self.logger.error(f"Failed to get relationships for {agent_id}: {e}")
            return {}
    
    def cleanup_old_history(self, days_to_keep: int = 30) -> int:
        """
        Clean up old state history entries.
        
        Args:
            days_to_keep: Number of days of history to keep
            
        Returns:
            Number of entries deleted
        """
        try:
            cutoff_time = (datetime.now() - timedelta(days=days_to_keep)).timestamp()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM state_history WHERE timestamp < ?",
                    (cutoff_time,)
                )
                deleted_count = cursor.rowcount
                conn.commit()
            
            self.logger.info(f"Cleaned up {deleted_count} old state history entries")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old history: {e}")
            return 0
    
    # Private helper methods
    
    def _store_state(self, state: AgentState) -> None:
        """Store state in database."""
        with sqlite3.connect(self.db_path) as conn:
            now = datetime.now().timestamp()
            
            conn.execute("""
                INSERT OR REPLACE INTO agent_states 
                (agent_id, status, emotional_state, status_level, relationships,
                 current_goals, last_activity, resource_usage, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                state.agent_id,
                state.status.value,
                json.dumps(state.emotional_state),
                state.status_level,
                json.dumps(state.relationships),
                json.dumps(state.current_goals),
                state.last_activity.timestamp() if state.last_activity else None,
                json.dumps(state.resource_usage),
                now,
                now
            ))
            
            conn.commit()
    
    def _row_to_state(self, row: sqlite3.Row) -> AgentState:
        """Convert database row to AgentState."""
        return AgentState(
            agent_id=row['agent_id'],
            status=AgentStatus(row['status']),
            emotional_state=json.loads(row['emotional_state']),
            status_level=row['status_level'],
            relationships=json.loads(row['relationships']),
            current_goals=json.loads(row['current_goals']),
            last_activity=datetime.fromtimestamp(row['last_activity']) if row['last_activity'] else None,
            resource_usage=json.loads(row['resource_usage'])
        )
    
    def _update_agent_relationships(self, agent_id: str) -> None:
        """Update agent state with current relationships."""
        relationships = self.get_relationships(agent_id)
        state = self.get_state(agent_id)
        
        if state:
            # Convert to simple strength mapping for state
            state.relationships = {
                other_id: info['strength'] 
                for other_id, info in relationships.items()
            }
            self.update_state(state, "relationship_sync")
    
    def _update_agent_goals(self, agent_id: str) -> None:
        """Update agent state with current goals."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT goal_description FROM goals 
                    WHERE agent_id = ? AND status = 'active'
                    ORDER BY priority DESC, created_at ASC
                """, (agent_id,))
                
                goals = [row['goal_description'] for row in cursor.fetchall()]
                
                state = self.get_state(agent_id)
                if state:
                    state.current_goals = goals
                    self.update_state(state, "goals_sync")
                    
        except Exception as e:
            self.logger.error(f"Failed to update goals for {agent_id}: {e}")