import pytest

from src.lib.memory_manager import KVStore, MemoryManager, strip_annotations


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


class TestKVStore:
    def test_set_and_get(self, tmp_path):
        store = KVStore(str(tmp_path / "test.json"))
        store.set("name", "Whoopsie")
        assert store.get("name") == "Whoopsie"

    def test_get_missing_returns_default(self, tmp_path):
        store = KVStore(str(tmp_path / "test.json"))
        assert store.get("missing") is None
        assert store.get("missing", "fallback") == "fallback"

    def test_persists_to_disk(self, tmp_path):
        path = str(tmp_path / "test.json")
        KVStore(path).set("name", "Whoopsie")
        assert KVStore(path).get("name") == "Whoopsie"

    def test_items_returns_all(self, tmp_path):
        store = KVStore(str(tmp_path / "test.json"))
        store.set("a", "1")
        store.set("b", "2")
        assert dict(store.items()) == {"a": "1", "b": "2"}

    def test_overwrite_existing_key(self, tmp_path):
        store = KVStore(str(tmp_path / "test.json"))
        store.set("name", "first")
        store.set("name", "second")
        assert store.get("name") == "second"


class TestMemoryManager:
    @pytest.fixture
    def manager(self, tmp_path):
        return MemoryManager(base_dir=str(tmp_path))

    def test_process_annotations_updates_profile(self, manager):
        clean = manager.process_annotations('Call me Whoopsie! [MEMORY profile called="Whoopsie"]')
        assert clean == "Call me Whoopsie!"
        assert manager.profile.get("called") == "Whoopsie"

    def test_process_annotations_updates_preference(self, manager):
        clean = manager.process_annotations('I love trucks! [MEMORY preference likes="trucks"]')
        assert clean == "I love trucks!"
        assert manager.preferences.get("likes") == "trucks"

    def test_process_annotations_handles_multi_kv_tag(self, manager):
        text = 'Cool fish! [MEMORY preference pet="fish" pet_name="Jetty" pet_species="zebra loach"]'
        clean = manager.process_annotations(text)
        assert clean == "Cool fish!"
        assert manager.preferences.get("pet") == "fish"
        assert manager.preferences.get("pet_name") == "Jetty"
        assert manager.preferences.get("pet_species") == "zebra loach"

    def test_process_annotations_handles_robot_name(self, manager):
        manager.process_annotations('You can call me Beep! [MEMORY profile robot_name="Beep"]')
        assert manager.profile.get("robot_name") == "Beep"

    def test_build_context_empty(self, manager):
        assert manager.build_context("hello") == ""

    def test_build_context_includes_profile(self, manager):
        manager.profile.set("called", "Whoopsie")
        context = manager.build_context("what is my name")
        assert "Profile:" in context
        assert "called: Whoopsie" in context

    def test_build_context_excludes_robot_name_from_profile_block(self, manager):
        manager.profile.set("robot_name", "Beep")
        manager.profile.set("called", "Whoopsie")
        context = manager.build_context("hello")
        assert "robot_name" not in context
        assert "called: Whoopsie" in context

    def test_build_context_includes_preferences(self, manager):
        manager.preferences.set("likes", "dinosaurs")
        context = manager.build_context("hello")
        assert "Preferences:" in context
        assert "likes: dinosaurs" in context

    def test_store_delegates_to_episodic(self, manager):
        manager.store("hello", "hi there", "Child", "Robot")
        assert len(manager.episodic._entries) == 1
