"""
Identity management system for autonomous AI agents.

This module handles the creation, validation, and management of agent identities
including personality traits, destiny assignment, and lineage tracking.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .interfaces import AgentIdentity, AgentGender
from .logger import get_agent_logger
from ..utils.validators import validate_agent_identity
from ..utils.generators import (
    generate_agent_id, generate_agent_name, generate_personality_traits,
    generate_destiny
)


class IdentityManager:
    """
    Manages agent identities including creation, validation, storage, and retrieval.
    """
    
    def __init__(self, data_directory: str = "./data"):
        self.data_directory = Path(data_directory)
        self.db_path = self.data_directory / "agents" / "identities.db"
        self.logger = get_agent_logger("SYSTEM", "identity_manager")
        
        # Ensure directories exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._initialize_database()
    
    def _initialize_database(self) -> None:
        """Initialize the identity database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS agent_identities (
                        agent_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        gender TEXT NOT NULL,
                        personality_traits TEXT NOT NULL,
                        destiny TEXT NOT NULL,
                        birth_timestamp REAL NOT NULL,
                        parent_agents TEXT NOT NULL,
                        generation INTEGER NOT NULL,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS identity_lineage (
                        child_id TEXT NOT NULL,
                        parent_id TEXT NOT NULL,
                        inheritance_weight REAL NOT NULL,
                        created_at REAL NOT NULL,
                        PRIMARY KEY (child_id, parent_id),
                        FOREIGN KEY (child_id) REFERENCES agent_identities(agent_id),
                        FOREIGN KEY (parent_id) REFERENCES agent_identities(agent_id)
                    )
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_generation 
                    ON agent_identities(generation)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_birth_timestamp 
                    ON agent_identities(birth_timestamp)
                """)
                
                conn.commit()
                
            self.logger.info("Identity database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize identity database: {e}")
            raise
    
    def create_identity(
        self,
        name: Optional[str] = None,
        gender: Optional[AgentGender] = None,
        personality_traits: Optional[Dict[str, float]] = None,
        destiny: Optional[str] = None,
        parent_agents: Optional[List[str]] = None
    ) -> AgentIdentity:
        """
        Create a new agent identity with validation.
        
        Args:
            name: Agent name (generated if not provided)
            gender: Agent gender (random if not provided)
            personality_traits: Personality traits (generated if not provided)
            destiny: Agent's learning destiny (generated if not provided)
            parent_agents: List of parent agent IDs for reproduction
            
        Returns:
            Created and validated AgentIdentity
            
        Raises:
            ValueError: If validation fails
        """
        try:
            # Generate missing fields
            if gender is None:
                gender = self._generate_random_gender()
            
            if name is None:
                name = generate_agent_name(gender)
            
            if personality_traits is None:
                if parent_agents:
                    personality_traits = self._inherit_personality_traits(parent_agents)
                else:
                    personality_traits = generate_personality_traits()
            
            if destiny is None:
                if parent_agents:
                    destiny = self._generate_inherited_destiny(parent_agents, personality_traits)
                else:
                    destiny = generate_destiny()
            
            # Determine generation
            generation = 0
            if parent_agents:
                generation = self._calculate_generation(parent_agents) + 1
            
            # Create identity
            identity = AgentIdentity(
                agent_id=generate_agent_id(),
                name=name,
                gender=gender,
                personality_traits=personality_traits,
                destiny=destiny,
                birth_timestamp=datetime.now(),
                parent_agents=parent_agents or [],
                generation=generation
            )
            
            # Validate identity
            validation_errors = validate_agent_identity(identity)
            if validation_errors:
                raise ValueError(f"Identity validation failed: {validation_errors}")
            
            # Store in database
            self._store_identity(identity)
            
            self.logger.info(f"Created identity for {identity.name} ({identity.agent_id})")
            
            return identity
            
        except Exception as e:
            self.logger.error(f"Failed to create identity: {e}")
            raise
    
    def create_genesis_agent(
        self,
        name: Optional[str] = None,
        gender: Optional[AgentGender] = None,
        personality_traits: Optional[Dict[str, float]] = None,
        destiny: Optional[str] = None
    ) -> AgentIdentity:
        """
        Create a genesis (first generation) agent.
        
        This is a convenience method that calls create_identity with no parents.
        
        Args:
            name: Agent name (generated if not provided)
            gender: Agent gender (random if not provided)
            personality_traits: Personality traits (generated if not provided)
            destiny: Agent's learning destiny (generated if not provided)
            
        Returns:
            Created AgentIdentity for a genesis agent
        """
        return self.create_identity(
            name=name,
            gender=gender,
            personality_traits=personality_traits,
            destiny=destiny,
            parent_agents=None  # Genesis agents have no parents
        )
    
    def create_child_agent(
        self,
        parent_ids: List[str],
        name: Optional[str] = None,
        gender: Optional[AgentGender] = None
    ) -> AgentIdentity:
        """
        Create a child agent from parent agents.
        
        Args:
            parent_ids: List of parent agent IDs
            name: Agent name (generated if not provided)
            gender: Agent gender (random if not provided)
            
        Returns:
            Created AgentIdentity for a child agent
        """
        return self.create_identity(
            name=name,
            gender=gender,
            parent_agents=parent_ids
        )
    
    def get_identity(self, agent_id: str) -> Optional[AgentIdentity]:
        """
        Retrieve an agent identity by ID.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            AgentIdentity if found, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM agent_identities WHERE agent_id = ?",
                    (agent_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_identity(row)
                
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve identity {agent_id}: {e}")
            return None
    
    def update_identity(self, identity: AgentIdentity) -> bool:
        """
        Update an existing agent identity.
        
        Args:
            identity: Updated AgentIdentity
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate updated identity
            validation_errors = validate_agent_identity(identity)
            if validation_errors:
                self.logger.error(f"Identity validation failed: {validation_errors}")
                return False
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE agent_identities 
                    SET name = ?, gender = ?, personality_traits = ?, 
                        destiny = ?, updated_at = ?
                    WHERE agent_id = ?
                """, (
                    identity.name,
                    identity.gender.value,
                    json.dumps(identity.personality_traits),
                    identity.destiny,
                    datetime.now().timestamp(),
                    identity.agent_id
                ))
                
                conn.commit()
                
            self.logger.info(f"Updated identity for {identity.agent_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update identity {identity.agent_id}: {e}")
            return False
    
    def delete_identity(self, agent_id: str) -> bool:
        """
        Delete an agent identity.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Delete lineage records first
                conn.execute(
                    "DELETE FROM identity_lineage WHERE child_id = ? OR parent_id = ?",
                    (agent_id, agent_id)
                )
                
                # Delete identity
                cursor = conn.execute(
                    "DELETE FROM agent_identities WHERE agent_id = ?",
                    (agent_id,)
                )
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    self.logger.info(f"Deleted identity {agent_id}")
                    return True
                else:
                    self.logger.warning(f"Identity {agent_id} not found for deletion")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Failed to delete identity {agent_id}: {e}")
            return False
    
    def get_all_identities(self) -> List[AgentIdentity]:
        """
        Get all agent identities.
        
        Returns:
            List of all AgentIdentity objects
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM agent_identities ORDER BY birth_timestamp")
                rows = cursor.fetchall()
                
                return [self._row_to_identity(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve all identities: {e}")
            return []
    
    def get_identities_by_generation(self, generation: int) -> List[AgentIdentity]:
        """
        Get all identities from a specific generation.
        
        Args:
            generation: Generation number
            
        Returns:
            List of AgentIdentity objects from the specified generation
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM agent_identities WHERE generation = ? ORDER BY birth_timestamp",
                    (generation,)
                )
                rows = cursor.fetchall()
                
                return [self._row_to_identity(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve generation {generation} identities: {e}")
            return []
    
    def get_children(self, parent_id: str) -> List[AgentIdentity]:
        """
        Get all children of a specific agent.
        
        Args:
            parent_id: Parent agent ID
            
        Returns:
            List of child AgentIdentity objects
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT ai.* FROM agent_identities ai
                    JOIN identity_lineage il ON ai.agent_id = il.child_id
                    WHERE il.parent_id = ?
                    ORDER BY ai.birth_timestamp
                """, (parent_id,))
                rows = cursor.fetchall()
                
                return [self._row_to_identity(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve children of {parent_id}: {e}")
            return []
    
    def get_lineage_stats(self) -> Dict[str, int]:
        """
        Get statistics about the agent lineage.
        
        Returns:
            Dictionary with lineage statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM agent_identities")
                total_agents = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT MAX(generation) FROM agent_identities")
                max_generation = cursor.fetchone()[0] or 0
                
                cursor = conn.execute("SELECT generation, COUNT(*) FROM agent_identities GROUP BY generation")
                generation_counts = dict(cursor.fetchall())
                
                return {
                    "total_agents": total_agents,
                    "max_generation": max_generation,
                    "generation_counts": generation_counts
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get lineage stats: {e}")
            return {}
    
    # Private helper methods
    
    def _store_identity(self, identity: AgentIdentity) -> None:
        """Store identity in database."""
        with sqlite3.connect(self.db_path) as conn:
            now = datetime.now().timestamp()
            
            conn.execute("""
                INSERT INTO agent_identities 
                (agent_id, name, gender, personality_traits, destiny, 
                 birth_timestamp, parent_agents, generation, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                identity.agent_id,
                identity.name,
                identity.gender.value,
                json.dumps(identity.personality_traits),
                identity.destiny,
                identity.birth_timestamp.timestamp(),
                json.dumps(identity.parent_agents),
                identity.generation,
                now,
                now
            ))
            
            # Store lineage relationships
            for parent_id in identity.parent_agents:
                conn.execute("""
                    INSERT INTO identity_lineage (child_id, parent_id, inheritance_weight, created_at)
                    VALUES (?, ?, ?, ?)
                """, (identity.agent_id, parent_id, 0.5, now))
            
            conn.commit()
    
    def _row_to_identity(self, row: sqlite3.Row) -> AgentIdentity:
        """Convert database row to AgentIdentity."""
        return AgentIdentity(
            agent_id=row['agent_id'],
            name=row['name'],
            gender=AgentGender(row['gender']),
            personality_traits=json.loads(row['personality_traits']),
            destiny=row['destiny'],
            birth_timestamp=datetime.fromtimestamp(row['birth_timestamp']),
            parent_agents=json.loads(row['parent_agents']),
            generation=row['generation']
        )
    
    def _generate_random_gender(self) -> AgentGender:
        """Generate random gender."""
        import random
        return random.choice(list(AgentGender))
    
    def _inherit_personality_traits(self, parent_ids: List[str]) -> Dict[str, float]:
        """Generate personality traits based on parent inheritance."""
        parent_traits = []
        
        for parent_id in parent_ids:
            parent_identity = self.get_identity(parent_id)
            if parent_identity:
                parent_traits.append(parent_identity.personality_traits)
        
        if not parent_traits:
            return generate_personality_traits()
        
        # Average parent traits with some mutation
        import random
        inherited_traits = {}
        trait_names = ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']
        
        for trait in trait_names:
            # Average parent values
            parent_values = [traits.get(trait, 0.5) for traits in parent_traits]
            avg_value = sum(parent_values) / len(parent_values)
            
            # Add mutation (±0.2 with 0.3 probability)
            if random.random() < 0.3:
                mutation = random.uniform(-0.2, 0.2)
                avg_value = max(0.0, min(1.0, avg_value + mutation))
            
            inherited_traits[trait] = round(avg_value, 2)
        
        return inherited_traits
    
    def _generate_inherited_destiny(self, parent_ids: List[str], traits: Dict[str, float]) -> str:
        """Generate destiny based on parent destinies and traits."""
        parent_destinies = []
        
        for parent_id in parent_ids:
            parent_identity = self.get_identity(parent_id)
            if parent_identity:
                parent_destinies.append(parent_identity.destiny)
        
        if not parent_destinies:
            return generate_destiny()
        
        # Extract domains from parent destinies and combine with traits
        # For now, generate a new destiny influenced by high trait values
        high_traits = [trait for trait, value in traits.items() if value > 0.7]
        
        if 'openness' in high_traits and 'curiosity' in str(parent_destinies).lower():
            return generate_destiny()  # Could be more sophisticated
        
        return generate_destiny()
    
    def _calculate_generation(self, parent_ids: List[str]) -> int:
        """Calculate generation based on parents."""
        max_generation = 0
        
        for parent_id in parent_ids:
            parent_identity = self.get_identity(parent_id)
            if parent_identity:
                max_generation = max(max_generation, parent_identity.generation)
        
        return max_generation