import json
import logging
import os
from typing import Optional

import kuzu

logger = logging.getLogger(__name__)

_DEFAULT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "graph.db")
)


class GraphStore:
    """
    Embedded property-graph store backed by KuzuDB.

    Schema
    ------
    Entity(name, type)  — a named node; type is a free-form label such as
                          'person', 'animal', 'place', 'object', 'topic'.
    Relation            — directed edge between two entities with a rel_type
                          string and an optional JSON properties blob.

    Typical usage
    -------------
    g = GraphStore()
    g.upsert_entity("Kabir", "person")
    g.upsert_entity("Jetty", "animal")
    g.upsert_relation("Kabir", "has_pet", "Jetty")
    g.upsert_relation("Kabir", "likes", "dinosaurs", props={"intensity": "high"})

    neighbors = g.get_neighbors("Kabir")
    # [{"name": "Jetty", "type": "animal", "rel_type": "has_pet", "props": {}}, ...]
    """

    def __init__(self, path: str = _DEFAULT_PATH):
        self._path = os.path.abspath(path)
        self._db = kuzu.Database(self._path)
        self._conn = kuzu.Connection(self._db)
        self._init_schema()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def upsert_entity(self, name: str, type: str) -> None:
        """Create or update an entity node."""
        self._conn.execute(
            "MERGE (e:Entity {name: $name}) SET e.type = $type",
            {"name": name, "type": type},
        )
        logger.debug(f"[Graph] Upserted entity: {name} ({type})")

    def upsert_relation(
        self,
        from_name: str,
        rel_type: str,
        to_name: str,
        props: Optional[dict] = None,
    ) -> None:
        """Create or update a directed relation between two entities.

        Both entities must exist; call upsert_entity first if needed.
        """
        props_str = json.dumps(props or {})
        self._conn.execute(
            """
            MATCH (a:Entity {name: $from_name}), (b:Entity {name: $to_name})
            MERGE (a)-[r:Relation {rel_type: $rel_type}]->(b)
            SET r.props = $props
            """,
            {
                "from_name": from_name,
                "to_name": to_name,
                "rel_type": rel_type,
                "props": props_str,
            },
        )
        logger.debug(f"[Graph] Upserted relation: {from_name} -{rel_type}-> {to_name}")

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_entity(self, name: str) -> Optional[dict]:
        """Return {"name": ..., "type": ...} or None if not found."""
        result = self._conn.execute(
            "MATCH (e:Entity {name: $name}) RETURN e.name, e.type",
            {"name": name},
        )
        if result.has_next():
            row = result.get_next()
            return {"name": row[0], "type": row[1]}
        return None

    def get_neighbors(
        self,
        name: str,
        rel_type: Optional[str] = None,
        direction: str = "out",
    ) -> list:
        """Return entities connected to name, with edge metadata.

        direction: 'out' (default), 'in', or 'both'
        rel_type:  filter to a specific relation type, or None for all
        """
        if direction == "out":
            pattern = "(a:Entity {name: $name})-[r:Relation]->(b:Entity)"
            return_clause = "b.name, b.type, r.rel_type, r.props"
        elif direction == "in":
            pattern = "(a:Entity)-[r:Relation]->(b:Entity {name: $name})"
            return_clause = "a.name, a.type, r.rel_type, r.props"
        else:  # both
            pattern = "(a:Entity {name: $name})-[r:Relation]-(b:Entity)"
            return_clause = "b.name, b.type, r.rel_type, r.props"

        cypher = f"MATCH {pattern}"
        if rel_type:
            cypher += " WHERE r.rel_type = $rel_type"
        cypher += f" RETURN {return_clause}"

        params = {"name": name}
        if rel_type:
            params["rel_type"] = rel_type

        return self._collect(self._conn.execute(cypher, params))

    def all_entities(self) -> list:
        """Return all entity nodes as [{"name": ..., "type": ...}, ...]."""
        result = self._conn.execute("MATCH (e:Entity) RETURN e.name, e.type ORDER BY e.name")
        rows = []
        while result.has_next():
            row = result.get_next()
            rows.append({"name": row[0], "type": row[1]})
        return rows

    def all_relations(self) -> list:
        """Return all edges as [{"from": ..., "rel_type": ..., "to": ..., "props": {...}}, ...]."""
        result = self._conn.execute(
            "MATCH (a:Entity)-[r:Relation]->(b:Entity) "
            "RETURN a.name, r.rel_type, b.name, r.props "
            "ORDER BY a.name, r.rel_type"
        )
        rows = []
        while result.has_next():
            row = result.get_next()
            rows.append({
                "from": row[0],
                "rel_type": row[1],
                "to": row[2],
                "props": json.loads(row[3]) if row[3] else {},
            })
        return rows

    def query(self, cypher: str, params: Optional[dict] = None) -> list:
        """Execute a raw Cypher query and return rows as lists."""
        return self._collect(self._conn.execute(cypher, params or {}))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _init_schema(self) -> None:
        self._conn.execute(
            "CREATE NODE TABLE IF NOT EXISTS Entity(name STRING, type STRING, PRIMARY KEY(name))"
        )
        self._conn.execute(
            "CREATE REL TABLE IF NOT EXISTS Relation(FROM Entity TO Entity, rel_type STRING, props STRING)"
        )

    @staticmethod
    def _collect(result) -> list:
        rows = []
        while result.has_next():
            row = result.get_next()
            rows.append(row)
        return rows
