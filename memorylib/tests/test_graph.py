import pytest

from memorylib import GraphStore


@pytest.fixture
def graph(tmp_path):
    return GraphStore(path=str(tmp_path / "test.db"))


class TestEntity:
    def test_upsert_and_get(self, graph):
        graph.upsert_entity("Kabir", "person")
        assert graph.get_entity("Kabir") == {"name": "Kabir", "type": "person"}

    def test_get_missing_returns_none(self, graph):
        assert graph.get_entity("Nobody") is None

    def test_upsert_updates_type(self, graph):
        graph.upsert_entity("Jetty", "unknown")
        graph.upsert_entity("Jetty", "animal")
        assert graph.get_entity("Jetty")["type"] == "animal"

    def test_all_entities_empty(self, graph):
        assert graph.all_entities() == []

    def test_all_entities_returns_all(self, graph):
        graph.upsert_entity("Kabir", "person")
        graph.upsert_entity("Jetty", "animal")
        names = {e["name"] for e in graph.all_entities()}
        assert names == {"Kabir", "Jetty"}

    def test_persists_across_connections(self, tmp_path):
        path = str(tmp_path / "test.db")
        GraphStore(path=path).upsert_entity("Kabir", "person")
        assert GraphStore(path=path).get_entity("Kabir") == {"name": "Kabir", "type": "person"}


class TestRelation:
    def test_upsert_relation(self, graph):
        graph.upsert_entity("Kabir", "person")
        graph.upsert_entity("Jetty", "animal")
        graph.upsert_relation("Kabir", "has_pet", "Jetty")
        relations = graph.all_relations()
        assert len(relations) == 1
        assert relations[0]["from"] == "Kabir"
        assert relations[0]["rel_type"] == "has_pet"
        assert relations[0]["to"] == "Jetty"

    def test_relation_with_props(self, graph):
        graph.upsert_entity("Kabir", "person")
        graph.upsert_entity("dinosaurs", "topic")
        graph.upsert_relation("Kabir", "likes", "dinosaurs", props={"intensity": "high"})
        assert graph.all_relations()[0]["props"] == {"intensity": "high"}

    def test_upsert_relation_updates_props(self, graph):
        graph.upsert_entity("Kabir", "person")
        graph.upsert_entity("dinosaurs", "topic")
        graph.upsert_relation("Kabir", "likes", "dinosaurs", props={"intensity": "low"})
        graph.upsert_relation("Kabir", "likes", "dinosaurs", props={"intensity": "high"})
        assert len(graph.all_relations()) == 1
        assert graph.all_relations()[0]["props"]["intensity"] == "high"

    def test_multiple_relations_from_same_entity(self, graph):
        graph.upsert_entity("Kabir", "person")
        graph.upsert_entity("Jetty", "animal")
        graph.upsert_entity("dinosaurs", "topic")
        graph.upsert_relation("Kabir", "has_pet", "Jetty")
        graph.upsert_relation("Kabir", "likes", "dinosaurs")
        assert len(graph.all_relations()) == 2


class TestGetNeighbors:
    @pytest.fixture(autouse=True)
    def _setup(self, graph):
        self.graph = graph
        graph.upsert_entity("Kabir", "person")
        graph.upsert_entity("Dada", "person")
        graph.upsert_entity("Jetty", "animal")
        graph.upsert_entity("dinosaurs", "topic")
        graph.upsert_relation("Kabir", "has_pet", "Jetty")
        graph.upsert_relation("Kabir", "likes", "dinosaurs")
        graph.upsert_relation("Dada", "family_of", "Kabir")

    def test_outbound_neighbors(self):
        names = {row[0] for row in self.graph.get_neighbors("Kabir")}
        assert names == {"Jetty", "dinosaurs"}

    def test_inbound_neighbors(self):
        names = {row[0] for row in self.graph.get_neighbors("Kabir", direction="in")}
        assert names == {"Dada"}

    def test_filter_by_rel_type(self):
        neighbors = self.graph.get_neighbors("Kabir", rel_type="has_pet")
        assert len(neighbors) == 1
        assert neighbors[0][0] == "Jetty"

    def test_no_neighbors_returns_empty(self):
        self.graph.upsert_entity("Isolated", "person")
        assert self.graph.get_neighbors("Isolated") == []


class TestQuery:
    def test_raw_cypher_query(self, graph):
        graph.upsert_entity("Kabir", "person")
        graph.upsert_entity("Dada", "person")
        result = graph.query("MATCH (e:Entity {type: $type}) RETURN e.name ORDER BY e.name", {"type": "person"})
        assert [row[0] for row in result] == ["Dada", "Kabir"]
