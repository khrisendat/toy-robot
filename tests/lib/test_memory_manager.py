import pytest

from src.lib.robot_memory import RobotMemory, strip_annotations


def test_strip_annotations_removes_profile_tag():
    text = 'I will call you Whoopsie! [MEMORY profile called="Whoopsie"]'
    assert strip_annotations(text) == "I will call you Whoopsie!"


def test_strip_annotations_removes_preference_tag():
    text = 'Dinosaurs are the best! [MEMORY preference likes="dinosaurs"]'
    assert strip_annotations(text) == "Dinosaurs are the best!"


def test_strip_annotations_leaves_plain_text():
    assert strip_annotations("Hello there!") == "Hello there!"


def test_strip_annotations_removes_multiple_tags():
    text = 'Got it! [MEMORY profile called="Whoopsie"] [MEMORY preference likes="trucks"]'
    assert strip_annotations(text) == "Got it!"


def test_strip_annotations_removes_multi_kv_tag():
    text = 'Cool fish! [MEMORY preference pet="fish" pet_name="Jetty" pet_species="zebra loach"]'
    assert strip_annotations(text) == "Cool fish!"


class TestRobotMemory:
    @pytest.fixture
    def memory(self, tmp_path):
        return RobotMemory(base_dir=str(tmp_path), user_name="Kabir")

    def test_process_annotations_profile(self, memory):
        clean = memory.process_annotations('Call me Whoopsie! [MEMORY profile called="Whoopsie"]')
        assert clean == "Call me Whoopsie!"
        rows = memory.graph.get_neighbors("Kabir", rel_type="called")
        assert rows[0][0] == "Whoopsie"

    def test_process_annotations_preference(self, memory):
        clean = memory.process_annotations('I love trucks! [MEMORY preference likes="trucks"]')
        assert clean == "I love trucks!"
        rows = memory.graph.get_neighbors("Kabir", rel_type="likes")
        assert rows[0][0] == "trucks"

    def test_process_annotations_robot_name(self, memory):
        memory.process_annotations('You can call me Beep! [MEMORY profile robot_name="Beep"]')
        assert memory.get_robot_name() == "Beep"

    def test_process_annotations_pet_group(self, memory):
        text = 'Cool fish! [MEMORY preference pet="fish" pet_name="Jetty" pet_species="zebra loach"]'
        memory.process_annotations(text)
        pet_rows = memory.graph.get_neighbors("Kabir", rel_type="has_pet")
        assert pet_rows[0][0] == "Jetty"
        type_rows = memory.graph.get_neighbors("Jetty", rel_type="pet_type")
        assert type_rows[0][0] == "fish"
        species_rows = memory.graph.get_neighbors("Jetty", rel_type="species")
        assert species_rows[0][0] == "zebra loach"

    def test_build_context_empty(self, memory):
        assert memory.build_context() == ""

    def test_build_context_includes_fact(self, memory):
        memory.process_annotations('[MEMORY profile called="Whoopsie"]')
        ctx = memory.build_context()
        assert "Facts about Kabir" in ctx
        assert "called: Whoopsie" in ctx

    def test_build_context_excludes_robot_name(self, memory):
        memory.process_annotations('[MEMORY profile robot_name="Beep"]')
        ctx = memory.build_context()
        assert "robot_name" not in ctx

    def test_build_context_parent(self, memory):
        memory.process_annotations('[MEMORY profile dada="yes"]')
        ctx = memory.build_context()
        assert "dada: yes" in ctx

    def test_build_context_pet_rendering(self, memory):
        memory.process_annotations('[MEMORY preference pet="fish" pet_name="Jetty"]')
        ctx = memory.build_context()
        assert "pet_name: Jetty" in ctx
        assert "pet: fish" in ctx

    def test_get_robot_name_none_by_default(self, memory):
        assert memory.get_robot_name() is None

    def test_record_turn_stores_episodic_entry(self, memory):
        memory.record_turn("hello", "hi there")
        assert len(memory.episodic) == 1

    def test_record_turn_stores_speaker_metadata(self, memory, tmp_path):
        import json
        memory.record_turn("hello", "hi there", speaker_name="Kabir")
        path = tmp_path / "episodic.jsonl"
        entry = json.loads(path.read_text().strip())
        assert entry["metadata"]["speaker"] == "Kabir"

    def test_record_turn_asserts_last_seen_for_non_primary_speaker(self, memory):
        memory.record_turn("hey", "hello!", speaker_name="Dada")
        rows = memory.graph.get_neighbors("Dada", rel_type="last_seen")
        assert len(rows) == 1

    def test_record_turn_does_not_assert_last_seen_for_primary_user(self, memory):
        memory.record_turn("hey", "hello!", speaker_name="Kabir")
        rows = memory.graph.get_neighbors("Kabir", rel_type="last_seen")
        assert len(rows) == 0

    def test_record_turn_no_speaker_no_graph_change(self, memory):
        before = len(memory.graph.all_relations())
        memory.record_turn("hey", "hello!", speaker_name=None)
        assert len(memory.graph.all_relations()) == before
