"""Basic tests for PawPal+ core classes."""

from datetime import date, datetime, time

import pytest

from pawpal_system import Owner, Pet, Scheduler, Task

DAY = date(2026, 10, 7)


def make_owner(available_minutes=120, day_start=time(8, 0), pets=("Buddy",)):
    """Return an owner plus their pets (by name) for compact test setup."""
    owner = Owner(name="Jordan", available_minutes=available_minutes, day_start=day_start)
    for name in pets:
        owner.add_pet(Pet(name=name, species="dog", age=4))
    return owner, {p.name: p for p in owner.pets}


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


# --- Chronological ordering ---------------------------------------------------


def test_plan_is_returned_in_chronological_order():
    owner, pets = make_owner(day_start=time(7, 0))
    buddy = pets["Buddy"]
    # Added out of order, mixing pinned and flexible tasks.
    buddy.add_task(Task("Evening walk", "exercise", 30, preferred_time=time(18, 0)))
    buddy.add_task(Task("Play", "enrichment", 20, priority="low"))
    buddy.add_task(Task("Breakfast", "feeding", 10, priority="high", preferred_time=time(8, 15)))
    buddy.add_task(Task("Morning walk", "exercise", 30, priority="high", preferred_time=time(7, 30)))

    plan = Scheduler(owner, day=DAY).generate_plan()

    starts = [e.start for e in plan]
    assert starts == sorted(starts)
    assert [e.task.title for e in plan] == ["Play", "Morning walk", "Breakfast", "Evening walk"]


def test_sort_by_time_orders_pinned_tasks_and_puts_flexible_last():
    owner, pets = make_owner()
    buddy = pets["Buddy"]
    buddy.add_task(Task("Flexible", "misc", 10))
    buddy.add_task(Task("Dinner", "feeding", 10, preferred_time=time(17, 30)))
    buddy.add_task(Task("Breakfast", "feeding", 10, preferred_time=time(8, 0)))
    scheduler = Scheduler(owner, day=DAY)

    ordered = scheduler.sort_by_time(scheduler.filter_tasks())

    assert [t.title for _, t in ordered] == ["Breakfast", "Dinner", "Flexible"]


def test_flexible_task_fills_gap_between_pinned_tasks_only_if_it_fits():
    owner, pets = make_owner(day_start=time(8, 0))
    buddy = pets["Buddy"]
    buddy.add_task(Task("Meds", "medication", 5, priority="high", preferred_time=time(8, 0)))
    buddy.add_task(Task("Walk", "exercise", 30, priority="high", preferred_time=time(8, 20)))
    buddy.add_task(Task("Brush", "grooming", 15))  # fits the 8:05-8:20 gap exactly
    buddy.add_task(Task("Bath", "grooming", 20, priority="low"))  # too long for any gap before 8:50

    plan = {e.task.title: e for e in Scheduler(owner, day=DAY).generate_plan()}

    assert plan["Brush"].start == datetime(2026, 10, 7, 8, 5)
    assert plan["Bath"].start == datetime(2026, 10, 7, 8, 50)


def test_equal_priority_and_duration_keep_insertion_order():
    owner, pets = make_owner()
    scheduler = Scheduler(owner, day=DAY)
    a = Task("A", "misc", 10)
    b = Task("B", "misc", 10)
    pairs = [(pets["Buddy"], a), (pets["Buddy"], b)]

    assert [t for _, t in scheduler.sort_by_priority(pairs)] == [a, b]


# --- Recurrence ----------------------------------------------------------------


def test_completing_daily_task_creates_following_task_that_is_scheduled_tomorrow():
    owner, pets = make_owner()
    buddy = pets["Buddy"]
    walk = Task("Walk", "exercise", 30, priority="high", frequency="daily", preferred_time=time(7, 0))
    buddy.add_task(walk)

    nxt = buddy.complete_task(walk, on=DAY)

    assert nxt.due_date == date(2026, 10, 8)
    assert (nxt.preferred_time, nxt.priority, nxt.frequency) == (time(7, 0), "high", "daily")
    assert nxt.last_completed is None
    assert [e.task for e in Scheduler(owner, day=date(2026, 10, 8)).generate_plan()] == [nxt]


def test_completing_same_task_twice_is_rejected():
    pet = Pet(name="Buddy", species="dog", age=4)
    walk = Task("Walk", "exercise", 30)
    pet.add_task(walk)
    pet.complete_task(walk, on=DAY)

    with pytest.raises(ValueError):
        pet.complete_task(walk, on=DAY)

    assert len(pet.get_tasks()) == 2
    pet.undo_complete(walk)
    assert pet.get_tasks() == [walk]


def test_overdue_task_is_still_scheduled():
    owner, pets = make_owner()
    pets["Buddy"].add_task(Task("Walk", "exercise", 30, due_date=date(2026, 10, 4)))

    assert len(Scheduler(owner, day=DAY).generate_plan()) == 1


def test_daily_recurrence_crosses_year_boundary():
    pet = Pet(name="Buddy", species="dog", age=4)
    walk = Task("Walk", "exercise", 30)
    pet.add_task(walk)

    assert pet.complete_task(walk, on=date(2026, 12, 31)).due_date == date(2027, 1, 1)


def test_unfinished_filter_excludes_tasks_completed_on_earlier_days():
    owner, pets = make_owner()
    buddy = pets["Buddy"]
    walk = Task("Walk", "exercise", 30)
    buddy.add_task(walk)
    nxt = buddy.complete_task(walk, on=date(2026, 10, 1))
    scheduler = Scheduler(owner, day=DAY)

    assert [t for _, t in scheduler.filter_tasks(completed=False)] == [nxt]
    assert scheduler.filter_tasks(completed=True) == []


# --- Conflicts / duplicates ------------------------------------------------------


def test_scheduler_flags_duplicate_task_entries():
    owner, pets = make_owner()
    buddy = pets["Buddy"]
    # The same task accidentally entered twice for the same pet.
    buddy.add_task(Task("Breakfast", "feeding", 10, preferred_time=time(8, 0)))
    buddy.add_task(Task("Breakfast", "feeding", 10, preferred_time=time(8, 0)))
    scheduler = Scheduler(owner, day=DAY)
    scheduler.generate_plan()

    warnings = scheduler.conflict_warnings()

    assert warnings == ["Warning: Breakfast (Buddy) and Breakfast (Buddy) both start at 08:00"]


def test_partial_overlap_is_flagged_but_back_to_back_is_not():
    owner, pets = make_owner()
    buddy = pets["Buddy"]
    buddy.add_task(Task("Long walk", "exercise", 60, preferred_time=time(9, 0)))
    buddy.add_task(Task("Snack", "feeding", 10, preferred_time=time(9, 30)))  # inside the walk
    buddy.add_task(Task("Nap check", "misc", 5, preferred_time=time(10, 0)))  # starts as walk ends
    scheduler = Scheduler(owner, day=DAY)
    scheduler.generate_plan()

    pairs = [(a.task.title, b.task.title) for a, b in scheduler.detect_conflicts()]

    assert pairs == [("Long walk", "Snack")]
    assert "overlap 09:30-09:40" in scheduler.conflict_warnings()[0]


# --- Time budget and day boundaries -----------------------------------------------


def test_task_that_exactly_uses_remaining_time_is_kept():
    owner, pets = make_owner(available_minutes=30)
    pets["Buddy"].add_task(Task("Walk", "exercise", 30))
    scheduler = Scheduler(owner, day=DAY)

    assert len(scheduler.generate_plan()) == 1
    assert scheduler.skipped == []


def test_long_high_priority_task_skipped_but_shorter_low_priority_still_fits():
    owner, pets = make_owner(available_minutes=30)
    pets["Buddy"].add_task(Task("Hike", "exercise", 40, priority="high"))
    pets["Buddy"].add_task(Task("Brush", "grooming", 10, priority="low"))
    scheduler = Scheduler(owner, day=DAY)

    assert [e.task.title for e in scheduler.generate_plan()] == ["Brush"]
    assert [(t.title, reason) for _, t, reason in scheduler.skipped] == [
        ("Hike", "needs 40 min, only 30 min left")
    ]


def test_zero_available_minutes_skips_everything():
    owner, pets = make_owner(available_minutes=0)
    pets["Buddy"].add_task(Task("Walk", "exercise", 30))
    scheduler = Scheduler(owner, day=DAY)

    assert scheduler.generate_plan() == []
    assert len(scheduler.skipped) == 1
    assert "Skipped:" in scheduler.explain_plan()


def test_owner_with_no_pets_has_empty_plan():
    owner, _ = make_owner(pets=())
    scheduler = Scheduler(owner, day=DAY)

    assert scheduler.generate_plan() == []
    assert scheduler.explain_plan() == "No tasks are due today."


def test_flexible_task_that_would_run_past_midnight_is_skipped():
    owner, pets = make_owner(day_start=time(23, 30))
    pets["Buddy"].add_task(Task("Play", "enrichment", 45))
    scheduler = Scheduler(owner, day=DAY)

    assert scheduler.generate_plan() == []
    assert scheduler.skipped[0][2] == "no open slot left before midnight"


def test_generate_plan_twice_gives_same_result():
    owner, pets = make_owner()
    pets["Buddy"].add_task(Task("Walk", "exercise", 30))
    scheduler = Scheduler(owner, day=DAY)

    first = [(e.task.title, e.start) for e in scheduler.generate_plan()]
    second = [(e.task.title, e.start) for e in scheduler.generate_plan()]

    assert first == second and len(second) == 1


# --- Editing and identity ---------------------------------------------------------


def test_invalid_edit_leaves_task_unchanged():
    task = Task("Walk", "exercise", 30, priority="high")

    with pytest.raises(ValueError):
        task.edit(priority="urgent", duration_minutes=45)

    assert (task.priority, task.duration_minutes) == ("high", 30)


def test_remove_task_removes_exact_object_not_an_equal_copy():
    pet = Pet(name="Buddy", species="dog", age=4)
    first = Task("Walk", "exercise", 30)
    second = Task("Walk", "exercise", 30)
    pet.add_task(first)
    pet.add_task(second)

    pet.remove_task(second)

    assert len(pet.tasks) == 1 and pet.tasks[0] is first
