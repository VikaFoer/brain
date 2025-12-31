"""
Neo4j database connection
"""
from neo4j import GraphDatabase
from app.core.config import settings
from typing import Optional


class Neo4jDriver:
    """Neo4j database driver singleton"""
    _instance: Optional['Neo4jDriver'] = None
    _driver = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
    
    def get_driver(self):
        return self._driver
    
    def close(self):
        if self._driver:
            self._driver.close()
    
    def verify_connectivity(self):
        """Verify Neo4j connection"""
        try:
            self._driver.verify_connectivity()
            return True
        except Exception as e:
            print(f"Neo4j connection error: {e}")
            return False


# Global Neo4j driver instance
neo4j_driver = Neo4jDriver()


def get_neo4j_session():
    """Get Neo4j session"""
    return neo4j_driver.get_driver().session()

