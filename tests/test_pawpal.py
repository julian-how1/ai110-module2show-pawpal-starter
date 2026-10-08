"""Basic tests for PawPal+ core classes."""

from datetime import date, time

from pawpal_system import Owner, Pet, Scheduler, Task


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


def test_completing_daily_task_creates_next_instance_due_tomorrow():
    pet = Pet(name="Buddy", species="dog", age=4)
    walk = Task("Morning walk", "exercise", 30, frequency="daily")
    pet.add_task(walk)

    nxt = pet.complete_task(walk, on=date(2026, 10, 7))

    assert len(pet.get_tasks()) == 2
    assert nxt is not walk
    assert nxt.title == "Morning walk"
    assert nxt.last_completed is None
    assert nxt.due_date == date(2026, 10, 8)
    assert walk.last_completed == date(2026, 10, 7)


def test_completing_weekly_task_creates_next_instance_due_next_week():
    pet = Pet(name="Whiskers", species="cat", age=7)
    brushing = Task("Brushing", "grooming", 20, frequency="weekly")
    pet.add_task(brushing)

    nxt = pet.complete_task(brushing, on=date(2026, 10, 7))

    assert nxt.due_date == date(2026, 10, 14)
    assert not nxt.is_due_today(date(2026, 10, 13))
    assert nxt.is_due_today(date(2026, 10, 14))


def test_completed_task_is_not_scheduled_but_next_instance_is_when_due():
    owner = Owner(name="Jordan", available_minutes=120)
    pet = Pet(name="Buddy", species="dog", age=4)
    owner.add_pet(pet)
    walk = Task("Morning walk", "exercise", 30)
    pet.add_task(walk)
    pet.complete_task(walk, on=date(2026, 10, 7))

    assert Scheduler(owner, day=date(2026, 10, 7)).generate_plan() == []
    tomorrow = Scheduler(owner, day=date(2026, 10, 8)).generate_plan()
    assert [e.task.title for e in tomorrow] == ["Morning walk"]
    assert tomorrow[0].task is not walk


def test_undo_complete_removes_spawned_instance():
    pet = Pet(name="Buddy", species="dog", age=4)
    walk = Task("Morning walk", "exercise", 30)
    pet.add_task(walk)
    pet.complete_task(walk, on=date(2026, 10, 7))

    pet.undo_complete(walk)

    assert pet.get_tasks() == [walk]
    assert walk.last_completed is None
    assert walk.is_due_today(date(2026, 10, 7))


def test_conflict_warnings_flag_tasks_at_same_time():
    owner = Owner(name="Jordan", available_minutes=120)
    buddy = Pet(name="Buddy", species="dog", age=4)
    whiskers = Pet(name="Whiskers", species="cat", age=7)
    owner.add_pet(buddy)
    owner.add_pet(whiskers)
    buddy.add_task(Task("Ear drops", "medication", 5, preferred_time=time(17, 30)))
    whiskers.add_task(Task("Dinner", "feeding", 10, preferred_time=time(17, 30)))

    scheduler = Scheduler(owner, day=date(2026, 10, 7))
    scheduler.generate_plan()
    warnings = scheduler.conflict_warnings()

    assert len(warnings) == 1
    assert "Ear drops" in warnings[0] and "Dinner" in warnings[0]
    assert "both start at 17:30" in warnings[0]


def test_conflict_warnings_empty_when_no_overlap():
    owner = Owner(name="Jordan", available_minutes=120)
    buddy = Pet(name="Buddy", species="dog", age=4)
    owner.add_pet(buddy)
    buddy.add_task(Task("Walk", "exercise", 30, preferred_time=time(7, 0)))
    buddy.add_task(Task("Breakfast", "feeding", 10, preferred_time=time(7, 30)))

    scheduler = Scheduler(owner, day=date(2026, 10, 7))
    scheduler.generate_plan()

    assert scheduler.conflict_warnings() == []
