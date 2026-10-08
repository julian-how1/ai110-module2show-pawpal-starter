"""Demo script: build an owner with pets and tasks, then print today's schedule."""

from datetime import time

from pawpal_system import Owner, Pet, Scheduler, Task


def print_tasks(heading: str, pairs) -> None:
    """Print a heading followed by one line per (pet, task) pair."""
    print(f"\n{heading}")
    if not pairs:
        print("  (none)")
    for pet, task in pairs:
        when = task.preferred_time.strftime("%H:%M") if task.preferred_time else "flexible"
        if task.last_completed:
            done = f"done {task.last_completed}"
        elif task.due_date:
            done = f"due {task.due_date}"
        else:
            done = ""
        print(f"  {when:<9} {pet.name:<9} {task.title:<20} [{task.priority}] {done}")


def main() -> None:
    owner = Owner(name="Jordan", available_minutes=120, day_start=time(7, 0))

    buddy = Pet(name="Buddy", species="dog", age=4)
    whiskers = Pet(name="Whiskers", species="cat", age=7)
    owner.add_pet(buddy)
    owner.add_pet(whiskers)

    # Added deliberately out of time order to exercise sort_by_time.
    buddy.add_task(Task("Evening walk", "exercise", 30, priority="medium", preferred_time=time(18, 0)))
    whiskers.add_task(Task("Litter box cleanup", "grooming", 15, priority="medium"))
    buddy.add_task(Task("Breakfast", "feeding", 10, priority="high", preferred_time=time(8, 15)))
    whiskers.add_task(Task("Thyroid meds", "medication", 5, priority="high", preferred_time=time(9, 0)))
    buddy.add_task(Task("Morning walk", "exercise", 30, priority="high", preferred_time=time(7, 30)))
    whiskers.add_task(Task("Brushing", "grooming", 20, priority="low", frequency="weekly"))
    whiskers.add_task(Task("Dinner", "feeding", 10, priority="high", preferred_time=time(17, 30)))
    # Pinned to the same time as Whiskers' dinner to trigger a conflict warning.
    buddy.add_task(Task("Ear drops", "medication", 5, priority="high", preferred_time=time(17, 30)))

    scheduler = Scheduler(owner)

    # Complete two recurring tasks: each spawns its next occurrence on the pet.
    meds, brushing = whiskers.tasks[1], whiskers.tasks[2]
    next_meds = whiskers.complete_task(meds)
    next_brushing = whiskers.complete_task(brushing)
    print(f"Completed {meds.title} ({meds.frequency}) -> next one due {next_meds.due_date}")
    print(f"Completed {brushing.title} ({brushing.frequency}) -> next one due {next_brushing.due_date}")

    all_tasks = scheduler.filter_tasks()
    print("=" * 60)
    print("Sorting & filtering demo")
    print("=" * 60)
    print_tasks("All tasks (insertion order):", all_tasks)
    print_tasks("Sorted by preferred time:", scheduler.sort_by_time(all_tasks))
    print_tasks("Only Buddy's tasks:", scheduler.filter_tasks(pet_name="Buddy"))
    print_tasks("Completed today:", scheduler.filter_tasks(completed=True))
    print_tasks(
        "Whiskers' unfinished tasks, sorted by time:",
        scheduler.sort_by_time(scheduler.filter_tasks(pet_name="Whiskers", completed=False)),
    )

    plan = scheduler.generate_plan()

    print("\n" + "=" * 60)
    print(f"Today's Schedule - {scheduler.day:%A, %B %d, %Y}")
    print(f"Owner: {owner.name}  |  Pets: {', '.join(p.name for p in owner.get_pets())}")
    print("=" * 60)

    if not plan:
        print("Nothing scheduled today.")
    for entry in plan:
        print(
            f"{entry.start:%I:%M %p} - {entry.end:%I:%M %p}  "
            f"{entry.pet.name:<9} {entry.task.title:<20} [{entry.task.priority}]"
        )

    print("-" * 60)
    print(scheduler.explain_plan())

    print("\n" + "=" * 60)
    print("Conflict check")
    print("=" * 60)
    warnings = scheduler.conflict_warnings()
    for warning in warnings:
        print(warning)
    if not warnings:
        print("No conflicts found.")


if __name__ == "__main__":
    main()
