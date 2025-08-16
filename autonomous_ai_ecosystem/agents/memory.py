"""
Memory system for autonomous AI agents.

This module implements a multi-layered memory system with short-term, long-term,
and episodic memory storage, retrieval, and consolidation mechanisms.
"""

import sqlite3
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict
from enum import Enum

from ..core.interfaces import Memory, MemoryInterface, AgentModule
from ..core.logger import get_agent_logger, log_agent_event
from ..utils.generators import generate_knowledge_id


class MemoryType(Enum):
    """Types of memory storage."""
    EPISODIC = "episodic"      # Specific events and experiences
    SEMANTIC = "semantic"      # Facts and knowledge
    PROCEDURAL = "procedural"  # Skills and procedures
    WORKING = "working"        # Temporary working memory


class MemoryImportance(Enum):
    """Memory importance levels."""
    CRITICAL = 1.0
    HIGH = 0.8
    MEDIUM = 0.6
    LOW = 0.4
    TRIVIAL = 0.2


class MemorySystem(AgentModule, MemoryInterface):
    """
    Multi-layered memory system for AI agents with storage, retrieval, and consolidation.
    """
    
    def __init__(self, agent_id: str, data_directory: str = "./data"):
        super().__init__(agent_id)
        self.data_directory = Path(data_directory)
        self.db_path = self.data_directory / "agents" / f"{agent_id}_memory.db"
        self.logger = get_agent_logger(agent_id, "memory_system")
        
        # Memory configuration
        self.max_working_memory = 50  # Maximum items in working memory
        self.consolidation_threshold = 0.7  # Importance threshold for consolidation
        self.forgetting_threshold = 0.3  # Importance threshold for forgetting
        self.decay_rate = 0.1  # Daily importance decay rate
        
        # Memory caches for performance
        self.working_memory: List[Memory] = []
        self.memory_cache: Dict[str, Memory] = {}
        self.retrieval_cache: Dict[str, List[Memory]] = {}
        
        # Statistics
        self.memory_stats = {
            "total_memories": 0,
            "episodic_memories": 0,
            "semantic_memories": 0,
            "procedural_memories": 0,
            "working_memories": 0,
            "retrievals_performed": 0,
            "consolidations_performed": 0,
            "memories_forgotten": 0
        }
        
        # Ensure directories exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Memory system initialized for {agent_id}")
    
    async def initialize(self) -> None:
        """Initialize the memory system and database."""
        try:
            self._initialize_database()
            await self._load_working_memory()
            await self._update_memory_stats()
            
            self.logger.info("Memory system initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize memory system: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the memory system gracefully."""
        try:
            # Save working memory to database
            await self._save_working_memory()
            
            # Clear caches
            self.working_memory.clear()
            self.memory_cache.clear()
            self.retrieval_cache.clear()
            
            self.logger.info("Memory system shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during memory system shutdown: {e}")
    
    async def store_memory(self, memory: Memory) -> None:
        """
        Store a new memory in the appropriate memory layer.
        
        Args:
            memory: Memory object to store
        """
        try:
            # Validate memory
            if not memory.memory_id or not memory.content:
                raise ValueError("Memory must have ID and content")
            
            # Add to working memory first
            self.working_memory.append(memory)
            self.memory_cache[memory.memory_id] = memory
            
            # Clear retrieval cache as it may be outdated
            self.retrieval_cache.clear()
            
            # Manage working memory size
            if len(self.working_memory) > self.max_working_memory:
                await self._consolidate_oldest_working_memory()
            
            # Store in database
            await self._store_memory_in_db(memory)
            
            # Update statistics
            self.memory_stats["total_memories"] += 1
            self.memory_stats[f"{memory.memory_type}_memories"] += 1
            
            log_agent_event(
                self.agent_id,
                "memory_stored",
                {
                    "memory_id": memory.memory_id,
                    "type": memory.memory_type,
                    "importance": memory.importance,
                    "tags": memory.tags
                }
            )
            
            self.logger.debug(f"Stored memory {memory.memory_id} ({memory.memory_type})")
            
        except Exception as e:
            self.logger.error(f"Failed to store memory {memory.memory_id}: {e}")
            raise
    
    async def retrieve_memories(self, query: str, limit: int = 10) -> List[Memory]:
        """
        Retrieve relevant memories based on a query.
        
        Args:
            query: Search query string
            limit: Maximum number of memories to return
            
        Returns:
            List of relevant Memory objects
        """
        try:
            # Check cache first
            cache_key = f"{query}:{limit}"
            if cache_key in self.retrieval_cache:
                self.memory_stats["retrievals_performed"] += 1
                return self.retrieval_cache[cache_key]
            
            # Search working memory first (most recent)
            working_results = self._search_working_memory(query, limit)
            
            # Search database for additional results
            db_results = await self._search_database_memories(query, limit - len(working_results))
            
            # Combine and rank results
            all_results = working_results + db_results
            ranked_results = self._rank_memories_by_relevance(all_results, query)
            
            # Limit results
            final_results = ranked_results[:limit]
            
            # Cache results
            self.retrieval_cache[cache_key] = final_results
            
            # Update statistics
            self.memory_stats["retrievals_performed"] += 1
            
            log_agent_event(
                self.agent_id,
                "memories_retrieved",
                {
                    "query": query,
                    "results_count": len(final_results),
                    "from_working_memory": len(working_results),
                    "from_database": len(db_results)
                }
            )
            
            self.logger.debug(f"Retrieved {len(final_results)} memories for query: {query}")
            
            return final_results
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve memories for query '{query}': {e}")
            return []
    
    async def consolidate_memories(self) -> None:
        """
        Consolidate short-term memories to long-term storage.
        """
        try:
            consolidation_count = 0
            
            # Process working memory for consolidation
            memories_to_consolidate = []
            
            for memory in self.working_memory[:]:
                # Check if memory should be consolidated
                if self._should_consolidate_memory(memory):
                    memories_to_consolidate.append(memory)
            
            # Consolidate selected memories
            for memory in memories_to_consolidate:
                await self._consolidate_memory(memory)
                consolidation_count += 1
            
            # Update statistics
            self.memory_stats["consolidations_performed"] += consolidation_count
            
            if consolidation_count > 0:
                log_agent_event(
                    self.agent_id,
                    "memories_consolidated",
                    {"count": consolidation_count}
                )
                
                self.logger.info(f"Consolidated {consolidation_count} memories")
            
        except Exception as e:
            self.logger.error(f"Failed to consolidate memories: {e}")
    
    async def forget_memories(self, max_age_days: int = 30) -> int:
        """
        Forget old, low-importance memories.
        
        Args:
            max_age_days: Maximum age for memories in days
            
        Returns:
            Number of memories forgotten
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            forgotten_count = 0
            
            # Remove from working memory
            working_to_remove = []
            for memory in self.working_memory:
                if (memory.timestamp < cutoff_date and 
                    memory.importance < self.forgetting_threshold):
                    working_to_remove.append(memory)
            
            for memory in working_to_remove:
                self.working_memory.remove(memory)
                if memory.memory_id in self.memory_cache:
                    del self.memory_cache[memory.memory_id]
                forgotten_count += 1
            
            # Remove from database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM memories 
                    WHERE timestamp < ? AND importance < ?
                """, (cutoff_date.timestamp(), self.forgetting_threshold))
                
                db_forgotten = cursor.rowcount
                forgotten_count += db_forgotten
                conn.commit()
            
            # Clear caches
            self.retrieval_cache.clear()
            
            # Update statistics
            self.memory_stats["memories_forgotten"] += forgotten_count
            await self._update_memory_stats()
            
            if forgotten_count > 0:
                log_agent_event(
                    self.agent_id,
                    "memories_forgotten",
                    {"count": forgotten_count, "max_age_days": max_age_days}
                )
                
                self.logger.info(f"Forgot {forgotten_count} old memories")
            
            return forgotten_count
            
        except Exception as e:
            self.logger.error(f"Failed to forget memories: {e}")
            return 0
    
    def create_memory(
        self,
        content: str,
        memory_type: str = MemoryType.EPISODIC.value,
        importance: float = 0.5,
        tags: Optional[List[str]] = None
    ) -> Memory:
        """
        Create a new memory object.
        
        Args:
            content: Memory content
            memory_type: Type of memory
            importance: Importance score (0.0 to 1.0)
            tags: Optional tags for categorization
            
        Returns:
            Created Memory object
        """
        return Memory(
            memory_id=generate_knowledge_id(),
            content=content,
            memory_type=memory_type,
            importance=max(0.0, min(1.0, importance)),
            timestamp=datetime.now(),
            agent_id=self.agent_id,
            tags=tags or []
        )
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get memory system statistics.
        
        Returns:
            Dictionary with memory statistics
        """
        return {
            **self.memory_stats,
            "working_memory_size": len(self.working_memory),
            "cache_size": len(self.memory_cache),
            "retrieval_cache_size": len(self.retrieval_cache)
        }

    # --- "In-House Tool" Methods for Knowledge Base ---

    async def add_to_knowledge_base(self, source: str, content: str, tags: Optional[List[str]] = None) -> str:
        """
        Adds raw external knowledge to the persistent knowledge base.
        This acts as the agent's "In-House Tool" for storing raw data.

        Args:
            source: The origin of the knowledge (e.g., URL, tool name).
            content: The raw content to store (e.g., HTML, API response).
            tags: Optional list of tags for categorization.

        Returns:
            The generated ID for the stored knowledge.
        """
        try:
            knowledge_id = generate_knowledge_id()
            timestamp = datetime.now().timestamp()
            tag_string = json.dumps(tags or [])

            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO knowledge_base (knowledge_id, source, content, tags, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (knowledge_id, source, content, tag_string, timestamp))
                conn.commit()

            self.logger.debug(f"Added knowledge {knowledge_id} from source '{source}' to knowledge base.")
            return knowledge_id
        except Exception as e:
            self.logger.error(f"Failed to add to knowledge base: {e}")
            raise

    async def query_knowledge_base(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Queries the knowledge base using full-text search.

        Args:
            query: The search query.
            limit: The maximum number of results to return.

        Returns:
            A list of dictionaries representing the search results.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT knowledge_id, source, snippet(knowledge_base, 2, '<b>', '</b>', '...', 20) as snippet, rank, timestamp
                    FROM knowledge_base
                    WHERE knowledge_base MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """, (query, limit))

                results = [dict(row) for row in cursor.fetchall()]

            self.logger.debug(f"Queried knowledge base for '{query}', found {len(results)} results.")
            return results
        except Exception as e:
            self.logger.error(f"Failed to query knowledge base: {e}")
            return []

    async def get_knowledge_by_id(self, knowledge_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a full knowledge entry by its ID.

        Args:
            knowledge_id: The ID of the knowledge to retrieve.

        Returns:
            A dictionary with the full knowledge content, or None if not found.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM knowledge_base WHERE knowledge_id = ?
                """, (knowledge_id,))
                row = cursor.fetchone()

                if row:
                    return dict(row)
            return None
        except Exception as e:
            self.logger.error(f"Failed to get knowledge by ID {knowledge_id}: {e}")
            return None

    async def get_memories_by_type(self, memory_type: str, limit: int = 50) -> List[Memory]:
        """
        Get memories of a specific type.
        
        Args:
            memory_type: Type of memory to retrieve
            limit: Maximum number of memories
            
        Returns:
            List of Memory objects
        """
        try:
            # Search working memory
            working_results = [
                memory for memory in self.working_memory
                if memory.memory_type == memory_type
            ][:limit]
            
            # Search database if needed
            remaining_limit = limit - len(working_results)
            if remaining_limit > 0:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute("""
                        SELECT * FROM memories 
                        WHERE memory_type = ? 
                        ORDER BY importance DESC, timestamp DESC 
                        LIMIT ?
                    """, (memory_type, remaining_limit))
                    
                    db_results = [self._row_to_memory(row) for row in cursor.fetchall()]
            else:
                db_results = []
            
            return working_results + db_results
            
        except Exception as e:
            self.logger.error(f"Failed to get memories by type {memory_type}: {e}")
            return []
    
    async def get_recent_memories(self, hours: int = 24, limit: int = 50) -> List[Memory]:
        """
        Get recent memories within specified time window.
        
        Args:
            hours: Time window in hours
            limit: Maximum number of memories
            
        Returns:
            List of recent Memory objects
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # Search working memory
            working_results = [
                memory for memory in self.working_memory
                if memory.timestamp >= cutoff_time
            ]
            
            # Sort by timestamp (most recent first)
            working_results.sort(key=lambda m: m.timestamp, reverse=True)
            working_results = working_results[:limit]
            
            # Search database if needed
            remaining_limit = limit - len(working_results)
            if remaining_limit > 0:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute("""
                        SELECT * FROM memories 
                        WHERE timestamp >= ? 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    """, (cutoff_time.timestamp(), remaining_limit))
                    
                    db_results = [self._row_to_memory(row) for row in cursor.fetchall()]
            else:
                db_results = []
            
            return working_results + db_results
            
        except Exception as e:
            self.logger.error(f"Failed to get recent memories: {e}")
            return []
    
    # Private helper methods
    
    def _initialize_database(self) -> None:
        """Initialize the memory database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS memories (
                        memory_id TEXT PRIMARY KEY,
                        content TEXT NOT NULL,
                        memory_type TEXT NOT NULL,
                        importance REAL NOT NULL,
                        timestamp REAL NOT NULL,
                        agent_id TEXT NOT NULL,
                        tags TEXT NOT NULL DEFAULT '[]',
                        created_at REAL NOT NULL,
                        last_accessed REAL,
                        access_count INTEGER DEFAULT 0
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS memory_associations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        memory1_id TEXT NOT NULL,
                        memory2_id TEXT NOT NULL,
                        association_strength REAL NOT NULL,
                        association_type TEXT,
                        created_at REAL NOT NULL,
                        FOREIGN KEY (memory1_id) REFERENCES memories(memory_id),
                        FOREIGN KEY (memory2_id) REFERENCES memories(memory_id)
                    )
                """)
                
                # Create indexes for performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_type ON memories(memory_type)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_timestamp ON memories(timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_importance ON memories(importance)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_agent ON memories(agent_id)")

                # Create knowledge_base table for the "In-House Tool"
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_base USING fts5(
                        knowledge_id,
                        source,
                        content,
                        tags,
                        timestamp
                    )
                """)
                
                conn.commit()
                
            self.logger.debug("Memory database initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize memory database: {e}")
            raise
    
    async def _load_working_memory(self) -> None:
        """Load recent high-importance memories into working memory."""
        try:
            # Load recent memories from database
            recent_cutoff = datetime.now() - timedelta(hours=24)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM memories 
                    WHERE timestamp >= ? OR importance >= ?
                    ORDER BY importance DESC, timestamp DESC 
                    LIMIT ?
                """, (recent_cutoff.timestamp(), 0.7, self.max_working_memory))
                
                rows = cursor.fetchall()
                
                for row in rows:
                    memory = self._row_to_memory(row)
                    self.working_memory.append(memory)
                    self.memory_cache[memory.memory_id] = memory
            
            self.logger.debug(f"Loaded {len(self.working_memory)} memories into working memory")
            
        except Exception as e:
            self.logger.error(f"Failed to load working memory: {e}")
    
    async def _save_working_memory(self) -> None:
        """Save working memory to database."""
        try:
            for memory in self.working_memory:
                await self._store_memory_in_db(memory)
            
            self.logger.debug("Saved working memory to database")
            
        except Exception as e:
            self.logger.error(f"Failed to save working memory: {e}")
    
    async def _store_memory_in_db(self, memory: Memory) -> None:
        """Store a memory in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                now = datetime.now().timestamp()
                
                conn.execute("""
                    INSERT OR REPLACE INTO memories 
                    (memory_id, content, memory_type, importance, timestamp, 
                     agent_id, tags, created_at, last_accessed, access_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    memory.memory_id,
                    memory.content,
                    memory.memory_type,
                    memory.importance,
                    memory.timestamp.timestamp(),
                    memory.agent_id,
                    json.dumps(memory.tags),
                    now,
                    now,
                    0
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to store memory in database: {e}")
            raise
    
    def _search_working_memory(self, query: str, limit: int) -> List[Memory]:
        """Search working memory for relevant memories."""
        try:
            query_lower = query.lower()
            results = []
            
            for memory in self.working_memory:
                # Simple text matching (can be enhanced with more sophisticated algorithms)
                if (query_lower in memory.content.lower() or 
                    any(query_lower in tag.lower() for tag in memory.tags)):
                    results.append(memory)
            
            # Sort by importance and recency
            results.sort(key=lambda m: (m.importance, m.timestamp.timestamp()), reverse=True)
            
            return results[:limit]
            
        except Exception as e:
            self.logger.error(f"Failed to search working memory: {e}")
            return []
    
    async def _search_database_memories(self, query: str, limit: int) -> List[Memory]:
        """Search database for relevant memories."""
        try:
            if limit <= 0:
                return []
            
            query_lower = query.lower()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Simple text search (can be enhanced with FTS)
                cursor = conn.execute("""
                    SELECT * FROM memories 
                    WHERE LOWER(content) LIKE ? OR LOWER(tags) LIKE ?
                    ORDER BY importance DESC, timestamp DESC 
                    LIMIT ?
                """, (f"%{query_lower}%", f"%{query_lower}%", limit))
                
                rows = cursor.fetchall()
                
                # Update access statistics
                memory_ids = [row['memory_id'] for row in rows]
                if memory_ids:
                    placeholders = ','.join('?' * len(memory_ids))
                    conn.execute(f"""
                        UPDATE memories 
                        SET last_accessed = ?, access_count = access_count + 1
                        WHERE memory_id IN ({placeholders})
                    """, [datetime.now().timestamp()] + memory_ids)
                    conn.commit()
                
                return [self._row_to_memory(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Failed to search database memories: {e}")
            return []
    
    def _rank_memories_by_relevance(self, memories: List[Memory], query: str) -> List[Memory]:
        """Rank memories by relevance to query."""
        try:
            query_lower = query.lower()
            
            def calculate_relevance(memory: Memory) -> float:
                score = 0.0
                
                # Content relevance
                content_lower = memory.content.lower()
                if query_lower in content_lower:
                    score += 0.5
                
                # Tag relevance
                for tag in memory.tags:
                    if query_lower in tag.lower():
                        score += 0.3
                
                # Importance boost
                score += memory.importance * 0.3
                
                # Recency boost (more recent = higher score)
                days_old = (datetime.now() - memory.timestamp).days
                recency_score = max(0, 1.0 - (days_old / 30.0))  # Decay over 30 days
                score += recency_score * 0.2
                
                return score
            
            # Sort by relevance score
            memories.sort(key=calculate_relevance, reverse=True)
            
            return memories
            
        except Exception as e:
            self.logger.error(f"Failed to rank memories: {e}")
            return memories
    
    def _should_consolidate_memory(self, memory: Memory) -> bool:
        """Check if a memory should be consolidated to long-term storage."""
        # Consolidate if importance is high or memory is old enough
        age_hours = (datetime.now() - memory.timestamp).total_seconds() / 3600
        
        return (memory.importance >= self.consolidation_threshold or 
                age_hours >= 24)  # Consolidate after 24 hours
    
    async def _consolidate_memory(self, memory: Memory) -> None:
        """Consolidate a memory from working to long-term storage."""
        try:
            # Remove from working memory
            if memory in self.working_memory:
                self.working_memory.remove(memory)
            
            # Ensure it's stored in database
            await self._store_memory_in_db(memory)
            
            self.logger.debug(f"Consolidated memory {memory.memory_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to consolidate memory {memory.memory_id}: {e}")
    
    async def _consolidate_oldest_working_memory(self) -> None:
        """Consolidate the oldest memory from working memory."""
        if not self.working_memory:
            return
        
        # Find oldest memory
        oldest_memory = min(self.working_memory, key=lambda m: m.timestamp)
        await self._consolidate_memory(oldest_memory)
    
    def _row_to_memory(self, row: sqlite3.Row) -> Memory:
        """Convert database row to Memory object."""
        return Memory(
            memory_id=row['memory_id'],
            content=row['content'],
            memory_type=row['memory_type'],
            importance=row['importance'],
            timestamp=datetime.fromtimestamp(row['timestamp']),
            agent_id=row['agent_id'],
            tags=json.loads(row['tags'])
        )
    
    async def _update_memory_stats(self) -> None:
        """Update memory statistics from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Total memories
                cursor = conn.execute("SELECT COUNT(*) FROM memories")
                self.memory_stats["total_memories"] = cursor.fetchone()[0]
                
                # Memories by type
                cursor = conn.execute("""
                    SELECT memory_type, COUNT(*) FROM memories GROUP BY memory_type
                """)
                
                type_counts = dict(cursor.fetchall())
                for memory_type in MemoryType:
                    key = f"{memory_type.value}_memories"
                    self.memory_stats[key] = type_counts.get(memory_type.value, 0)
                
                # Working memory count
                self.memory_stats["working_memories"] = len(self.working_memory)
                
        except Exception as e:
            self.logger.error(f"Failed to update memory stats: {e}")