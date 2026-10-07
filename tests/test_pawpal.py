"""Basic tests for PawPal+ core classes."""

from datetime import date

from pawpal_system import Pet, Task


def test_mark_complete_changes_task_status():
    task = Task("Morning walk", "exercise", 30)
    today = date(2026, 10, 7)
    assert not task.is_completed(today)

    task.mark_complete(today)

    assert task.is_completed(today)
    assert task.last_completed == today


def test_add_task_increases_pet_task_count():
    pet = Pet(name="Buddy", species="dog", age=4)
    assert len(pet.get_tasks()) == 0

    pet.add_task(Task("Breakfast", "feeding", 10))

    assert len(pet.get_tasks()) == 1
