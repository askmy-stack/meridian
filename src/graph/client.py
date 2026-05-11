"""Neo4j graph database client for Meridian.

Provides connection management and CRUD operations for the knowledge graph.
Uses neo4j Python driver with connection pooling.
"""

import os
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import structlog
from neo4j import GraphDatabase, Driver, Session, Transaction
from neo4j.exceptions import Neo4jError, ServiceUnavailable

logger = structlog.get_logger(__name__)


class Neo4jClient:
    """Neo4j client with connection pooling and retry logic.
    
    Usage:
        client = Neo4jClient()
        with client.session() as session:
            result = session.run("MATCH (n) RETURN count(n)")
    """
    
    def __init__(
        self,
        uri: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        max_connection_pool_size: int = 10,
        connection_timeout: int = 30
    ):
        """Initialize Neo4j client.
        
        Args:
            uri: Neo4j bolt URI (default from NEO4J_URI env var)
            username: Neo4j username (default from NEO4J_USER env var)
            password: Neo4j password (default from NEO4J_PASSWORD env var)
            max_connection_pool_size: Connection pool size
            connection_timeout: Connection timeout in seconds
        """
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.username = username or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        self.max_pool_size = max_connection_pool_size
        self.connection_timeout = connection_timeout
        
        self._driver: Optional[Driver] = None
        
        self.logger = logger.bind(
            uri=self.uri,
            user=self.username,
            pool_size=max_connection_pool_size
        )
    
    def connect(self) -> None:
        """Initialize connection to Neo4j."""
        if self._driver is not None:
            return
        
        try:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password),
                max_connection_pool_size=self.max_pool_size,
                connection_timeout=self.connection_timeout
            )
            
            # Verify connectivity
            self._driver.verify_connectivity()
            
            self.logger.info("neo4j_connected")
        except ServiceUnavailable as e:
            self.logger.error("neo4j_connection_failed", error=str(e))
            raise
        except Neo4jError as e:
            self.logger.error("neo4j_auth_failed", error=str(e))
            raise
    
    def close(self) -> None:
        """Close all connections."""
        if self._driver:
            self._driver.close()
            self._driver = None
            self.logger.info("neo4j_disconnected")
    
    @contextmanager
    def session(self, database: Optional[str] = None):
        """Get a Neo4j session context manager.
        
        Args:
            database: Database name (default: neo4j)
            
        Yields:
            Neo4j Session object
        """
        if self._driver is None:
            self.connect()
        
        session = self._driver.session(database=database or "neo4j")
        try:
            yield session
        finally:
            session.close()
    
    def health_check(self) -> bool:
        """Check if Neo4j is reachable.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            if self._driver is None:
                self.connect()
            self._driver.verify_connectivity()
            return True
        except Exception as e:
            self.logger.warning("neo4j_health_check_failed", error=str(e))
            return False
    
    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return results.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Database name
            
        Returns:
            List of records as dictionaries
        """
        with self.session(database) as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    
    def execute_write(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Execute a write transaction.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Database name
            
        Returns:
            List of records as dictionaries
        """
        def _tx_func(tx: Transaction, query: str, params: Dict[str, Any]):
            result = tx.run(query, params)
            return [record.data() for record in result]
        
        with self.session(database) as session:
            return session.execute_write(_tx_func, query, parameters or {})
    
    def execute_read(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Execute a read transaction.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Database name
            
        Returns:
            List of records as dictionaries
        """
        def _tx_func(tx: Transaction, query: str, params: Dict[str, Any]):
            result = tx.run(query, params)
            return [record.data() for record in result]
        
        with self.session(database) as session:
            return session.execute_read(_tx_func, query, parameters or {})


# Singleton instance for application use
_client: Optional[Neo4jClient] = None


def get_neo4j_client() -> Neo4jClient:
    """Get or create singleton Neo4j client instance.
    
    Returns:
        Neo4jClient singleton
    """
    global _client
    if _client is None:
        _client = Neo4jClient()
    return _client


def reset_client() -> None:
    """Reset singleton (useful for testing)."""
    global _client
    if _client:
        _client.close()
    _client = None
