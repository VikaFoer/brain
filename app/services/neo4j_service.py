"""
Service for working with Neo4j graph database
"""
from typing import Dict, List, Any, Optional
from app.core.neo4j_db import get_neo4j_session
import logging

logger = logging.getLogger(__name__)


class Neo4jService:
    """Service for Neo4j graph operations"""
    
    def create_category_node(self, category_id: int, name: str, element_count: int = 0):
        """Create or update category node"""
        try:
            session = get_neo4j_session()
        except RuntimeError as e:
            # Neo4j not configured, skip
            return None
        
        with session:
            query = """
            MERGE (c:Category {id: $category_id})
            SET c.name = $name,
                c.element_count = $element_count,
                c.type = 'Category'
            RETURN c
            """
            result = session.run(query, category_id=category_id, name=name, element_count=element_count)
            return result.single()
    
    def create_subset_node(self, subset_id: int, name: str, category_id: int):
        """Create or update subset node"""
        with get_neo4j_session() as session:
            query = """
            MERGE (s:Subset {id: $subset_id})
            SET s.name = $name,
                s.type = 'Subset'
            WITH s
            MATCH (c:Category {id: $category_id})
            MERGE (s)-[:BELONGS_TO]->(c)
            RETURN s
            """
            result = session.run(query, subset_id=subset_id, name=name, category_id=category_id)
            return result.single()
    
    def create_legal_act_node(
        self,
        act_id: int,
        nreg: str,
        title: str,
        subset_id: Optional[int] = None
    ):
        """Create or update legal act node"""
        try:
            session = get_neo4j_session()
        except RuntimeError:
            return None
        with session:
            query = """
            MERGE (a:LegalAct {id: $act_id})
            SET a.nreg = $nreg,
                a.title = $title,
                a.type = 'LegalAct'
            """
            
            if subset_id:
                query += """
            WITH a
            MATCH (s:Subset {id: $subset_id})
            MERGE (a)-[:BELONGS_TO]->(s)
            """
            
            query += " RETURN a"
            
            result = session.run(
                query,
                act_id=act_id,
                nreg=nreg,
                title=title,
                subset_id=subset_id
            )
            return result.single()
    
    def create_relation(
        self,
        source_act_id: int,
        target_act_id: int,
        relation_type: str,
        description: Optional[str] = None,
        confidence: int = 100
    ):
        """Create relation between two legal acts"""
        try:
            session = get_neo4j_session()
        except RuntimeError:
            return None
        with session:
            # Map relation types to Neo4j relationship types
            rel_type_map = {
                "посилається": "REFERENCES",
                "змінює": "MODIFIES",
                "скасовує": "CANCELS",
                "доповнює": "SUPPLEMENTS",
                "реалізує": "IMPLEMENTS",
                "замінює": "REPLACES"
            }
            
            neo4j_rel_type = rel_type_map.get(relation_type, "RELATED_TO")
            
            query = f"""
            MATCH (source:LegalAct {{id: $source_id}})
            MATCH (target:LegalAct {{id: $target_id}})
            MERGE (source)-[r:{neo4j_rel_type}]->(target)
            SET r.description = $description,
                r.confidence = $confidence,
                r.relation_type = $relation_type
            RETURN r
            """
            
            result = session.run(
                query,
                source_id=source_act_id,
                target_id=target_act_id,
                description=description,
                confidence=confidence,
                relation_type=relation_type
            )
            return result.single()
    
    def link_act_to_category(self, act_id: int, category_id: int):
        """Link legal act to category"""
        try:
            session = get_neo4j_session()
        except RuntimeError:
            return None
        with session:
            query = """
            MATCH (a:LegalAct {id: $act_id})
            MATCH (c:Category {id: $category_id})
            MERGE (a)-[:IN_CATEGORY]->(c)
            RETURN a, c
            """
            result = session.run(query, act_id=act_id, category_id=category_id)
            return result.single()
    
    def get_category_graph(self, category_ids: List[int], depth: int = 2) -> Dict[str, Any]:
        """Get graph for selected categories"""
        try:
            session = get_neo4j_session()
        except RuntimeError:
            return {"nodes": [], "edges": []}
        with session:
            query = """
            MATCH path = (c:Category)-[*1..%d]-(connected)
            WHERE c.id IN $category_ids
            RETURN path
            LIMIT 1000
            """ % depth
            
            result = session.run(query, category_ids=category_ids)
            
            nodes = set()
            edges = []
            
            for record in result:
                path = record["path"]
                for node in path.nodes:
                    nodes.add((node.id, node.labels[0], dict(node)))
                
                for rel in path.relationships:
                    edges.append({
                        "source": rel.start_node.id,
                        "target": rel.end_node.id,
                        "type": rel.type,
                        "properties": dict(rel)
                    })
            
            return {
                "nodes": [{"id": n[0], "label": n[1], "properties": n[2]} for n in nodes],
                "edges": edges
            }
    
    def get_relations_between_categories(
        self,
        category1_id: int,
        category2_id: int
    ) -> List[Dict[str, Any]]:
        """Get relations between two categories"""
        try:
            session = get_neo4j_session()
        except RuntimeError:
            return []
        with session:
            query = """
            MATCH (c1:Category {id: $cat1_id})<-[:IN_CATEGORY]-(a1:LegalAct)
            MATCH (a1)-[r]->(a2:LegalAct)-[:IN_CATEGORY]->(c2:Category {id: $cat2_id})
            RETURN a1, r, a2
            LIMIT 100
            """
            
            result = session.run(query, cat1_id=category1_id, cat2_id=category2_id)
            
            relations = []
            for record in result:
                relations.append({
                    "source_act": {
                        "id": record["a1"].id,
                        "nreg": record["a1"]["nreg"],
                        "title": record["a1"]["title"]
                    },
                    "relation": {
                        "type": record["r"].type,
                        "properties": dict(record["r"])
                    },
                    "target_act": {
                        "id": record["a2"].id,
                        "nreg": record["a2"]["nreg"],
                        "title": record["a2"]["title"]
                    }
                })
            
            return relations
    
    def get_category_statistics(self) -> List[Dict[str, Any]]:
        """Get statistics for all categories"""
        try:
            session = get_neo4j_session()
        except RuntimeError:
            return []
        with session:
            query = """
            MATCH (c:Category)
            OPTIONAL MATCH (c)<-[:BELONGS_TO]-(s:Subset)
            OPTIONAL MATCH (s)<-[:BELONGS_TO]-(a:LegalAct)
            RETURN c.id as id,
                   c.name as name,
                   c.element_count as element_count,
                   count(DISTINCT s) as subset_count,
                   count(DISTINCT a) as act_count
            ORDER BY act_count DESC
            """
            
            result = session.run(query)
            
            stats = []
            for record in result:
                stats.append({
                    "id": record["id"],
                    "name": record["name"],
                    "element_count": record["element_count"],
                    "subset_count": record["subset_count"],
                    "act_count": record["act_count"]
                })
            
            return stats


# Singleton instance
neo4j_service = Neo4jService()

