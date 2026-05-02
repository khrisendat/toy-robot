import json
import logging
from typing import Optional

import kuzu

logger = logging.getLogger(__name__)


class GraphStore:
    """
    Embedded property-graph store backed by KuzuDB.

    Schema
    ------
    Entity(name, type)  — a named node with a free-form type label.
    Relation            — directed edge with a rel_type string and optional JSON props.
    """

    def __init__(self, path: str):
        import os
        self._path = os.path.abspath(path)
        self._db = kuzu.Database(self._path)
        self._conn = kuzu.Connection(self._db)
        self._init_schema()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def upsert_entity(self, name: str, type: str) -> None:
        self._conn.execute(
            "MERGE (e:Entity {name: $name}) SET e.type = $type",
            {"name": name, "type": type},
        )

    def upsert_relation(
        self,
        from_name: str,
        rel_type: str,
        to_name: str,
        props: Optional[dict] = None,
    ) -> None:
        props_str = json.dumps(props or {})
        self._conn.execute(
            """
            MATCH (a:Entity {name: $from_name}), (b:Entity {name: $to_name})
            MERGE (a)-[r:Relation {rel_type: $rel_type}]->(b)
            SET r.props = $props
            """,
            {"from_name": from_name, "to_name": to_name, "rel_type": rel_type, "props": props_str},
        )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_entity(self, name: str) -> Optional[dict]:
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
        """Return entities connected to name with edge metadata.

        Each row: [neighbor_name, neighbor_type, rel_type, props_dict]
        direction: 'out' (default), 'in', or 'both'
        """
        if direction == "out":
            pattern = "(a:Entity {name: $name})-[r:Relation]->(b:Entity)"
            return_clause = "b.name, b.type, r.rel_type, r.props"
        elif direction == "in":
            pattern = "(a:Entity)-[r:Relation]->(b:Entity {name: $name})"
            return_clause = "a.name, a.type, r.rel_type, r.props"
        else:
            pattern = "(a:Entity {name: $name})-[r:Relation]-(b:Entity)"
            return_clause = "b.name, b.type, r.rel_type, r.props"

        cypher = f"MATCH {pattern}"
        if rel_type:
            cypher += " WHERE r.rel_type = $rel_type"
        cypher += f" RETURN {return_clause}"

        params: dict = {"name": name}
        if rel_type:
            params["rel_type"] = rel_type

        return self._collect(self._conn.execute(cypher, params))

    def all_entities(self) -> list:
        result = self._conn.execute("MATCH (e:Entity) RETURN e.name, e.type ORDER BY e.name")
        rows = []
        while result.has_next():
            row = result.get_next()
            rows.append({"name": row[0], "type": row[1]})
        return rows

    def all_relations(self) -> list:
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
            rows.append(result.get_next())
        return rows
