"""Demo script: build an owner with pets and tasks, then print today's schedule."""

from datetime import time

from pawpal_system import Owner, Pet, Scheduler, Task


def main() -> None:
    owner = Owner(name="Jordan", available_minutes=120, day_start=time(7, 0))

    buddy = Pet(name="Buddy", species="dog", age=4)
    whiskers = Pet(name="Whiskers", species="cat", age=7)
    owner.add_pet(buddy)
    owner.add_pet(whiskers)

    buddy.add_task(Task("Morning walk", "exercise", 30, priority="high", preferred_time=time(7, 30)))
    buddy.add_task(Task("Breakfast", "feeding", 10, priority="high", preferred_time=time(8, 15)))
    buddy.add_task(Task("Evening walk", "exercise", 30, priority="medium", preferred_time=time(18, 0)))
    whiskers.add_task(Task("Thyroid meds", "medication", 5, priority="high", preferred_time=time(9, 0)))
    whiskers.add_task(Task("Litter box cleanup", "grooming", 15, priority="medium"))
    whiskers.add_task(Task("Brushing", "grooming", 20, priority="low", frequency="weekly"))

    scheduler = Scheduler(owner)
    plan = scheduler.generate_plan()

    print("=" * 50)
    print(f"Today's Schedule - {scheduler.day:%A, %B %d, %Y}")
    print(f"Owner: {owner.name}  |  Pets: {', '.join(p.name for p in owner.get_pets())}")
    print("=" * 50)

    if not plan:
        print("Nothing scheduled today.")
    for entry in plan:
        print(
            f"{entry.start:%I:%M %p} - {entry.end:%I:%M %p}  "
            f"{entry.pet.name:<9} {entry.task.title:<20} [{entry.task.priority}]"
        )

    print("-" * 50)
    print(scheduler.explain_plan())


if __name__ == "__main__":
    main()
