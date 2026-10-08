"""PawPal+ core system: owners, pets, care tasks, and the daily scheduler."""

from __future__ import annotations

from dataclasses import dataclass, field, fields, replace
from datetime import date, datetime, time, timedelta
from typing import Optional

# Lower rank = more important. Used for sorting instead of comparing strings.
PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}
FREQUENCY_DAYS = {"daily": 1, "weekly": 7}


@dataclass
class Task:
    """A single pet care activity (walk, feeding, meds, etc.)."""

    title: str
    category: str
    duration_minutes: int
    priority: str = "medium"
    frequency: str = "daily"
    preferred_time: Optional[time] = None
    last_completed: Optional[date] = None
    due_date: Optional[date] = None  # None = due now
    # The instance spawned when this one was completed; lets an undo remove it.
    _next: Optional[Task] = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Validate fields right after the dataclass is constructed."""
        self._validate()

    def _validate(self) -> None:
        """Raise ValueError if any field holds an invalid value."""
        if self.duration_minutes <= 0:
            raise ValueError(f"duration_minutes must be positive, got {self.duration_minutes}")
        if self.priority not in PRIORITY_RANK:
            raise ValueError(f"priority must be one of {list(PRIORITY_RANK)}, got {self.priority!r}")
        if self.frequency not in FREQUENCY_DAYS:
            raise ValueError(f"frequency must be one of {list(FREQUENCY_DAYS)}, got {self.frequency!r}")

    @property
    def priority_rank(self) -> int:
        """Numeric priority (0 = high) for sorting."""
        return PRIORITY_RANK[self.priority]

    def mark_complete(self, on: Optional[date] = None) -> None:
        """Mark this task as done on the given date (defaults to today)."""
        self.last_completed = on or date.today()

    def is_completed(self, on: Optional[date] = None) -> bool:
        """Return True if this task was completed on the given date (defaults to today)."""
        return self.last_completed == (on or date.today())

    def next_occurrence(self) -> Task:
        """Return a fresh copy of this task, due one frequency period after it was completed."""
        if self.last_completed is None:
            raise ValueError(f"{self.title!r} hasn't been completed yet")
        next_due = self.last_completed + timedelta(days=FREQUENCY_DAYS[self.frequency])
        return replace(self, last_completed=None, due_date=next_due)

    def is_due_today(self, today: Optional[date] = None) -> bool:
        """Return True if this task should be scheduled on the given date (defaults to today)."""
        if self.last_completed is not None:
            return False  # completed instances are history; the next instance carries the recurrence
        return self.due_date is None or self.due_date <= (today or date.today())

    def edit(self, **changes) -> None:
        """Update one or more fields on this task, rejecting unknown field names."""
        valid = {f.name for f in fields(self) if f.init}
        unknown = set(changes) - valid
        if unknown:
            raise AttributeError(f"Task has no field(s): {', '.join(sorted(unknown))}")
        replace(self, **changes)  # validates on a copy, so a bad edit leaves this task untouched
        for name, value in changes.items():
            setattr(self, name, value)


@dataclass
class Pet:
    """A pet and its list of care tasks."""

    name: str
    species: str
    age: int
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a care task for this pet."""
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove this exact task object (not just an equal-looking one) from this pet."""
        for i, existing in enumerate(self.tasks):
            if existing is task:
                del self.tasks[i]
                return
        raise ValueError(f"{task.title!r} is not a task for {self.name}")

    def complete_task(self, task: Task, on: Optional[date] = None) -> Task:
        """Mark a task done and add its next occurrence (tomorrow or next week); return the new task."""
        if task.last_completed is not None:
            raise ValueError(f"{task.title!r} is already completed; complete its next occurrence instead")
        task.mark_complete(on)
        task._next = task.next_occurrence()
        self.add_task(task._next)
        return task._next

    def undo_complete(self, task: Task) -> None:
        """Reverse complete_task: clear the completion and remove the occurrence it spawned."""
        if task._next is not None and any(t is task._next for t in self.tasks):
            self.remove_task(task._next)
        task._next = None
        task.last_completed = None

    def get_tasks(self) -> list[Task]:
        """Return all tasks for this pet."""
        return list(self.tasks)


@dataclass
class Owner:
    """A pet owner with daily time constraints and preferences."""

    name: str
    available_minutes: int
    day_start: time = time(8, 0)
    preferences: dict = field(default_factory=dict)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner."""
        self.pets.append(pet)

    def get_pets(self) -> list[Pet]:
        """Return all pets belonging to this owner."""
        return list(self.pets)

    def set_availability(self, minutes: int) -> None:
        """Set how many minutes the owner has available today."""
        if minutes < 0:
            raise ValueError(f"available minutes cannot be negative, got {minutes}")
        self.available_minutes = minutes


@dataclass
class ScheduledTask:
    """One entry in the daily plan: which pet, which task, when, and why."""

    pet: Pet
    task: Task
    start: datetime
    end: datetime
    reason: str


class Scheduler:
    """Builds a daily care plan from an owner's pets, tasks, and constraints."""

    def __init__(self, owner: Owner, day: Optional[date] = None) -> None:
        """Create a scheduler for the owner on the given day (defaults to today)."""
        self.owner = owner
        self.day = day or date.today()
        self.plan: list[ScheduledTask] = []
        self.skipped: list[tuple[Pet, Task, str]] = []

    def generate_plan(self) -> list[ScheduledTask]:
        """Build and return today's schedule, ordered by start time."""
        self.plan = []
        self.skipped = []

        due = [
            (pet, task)
            for pet in self.owner.pets
            for task in pet.tasks
            if task.is_due_today(self.day)
        ]
        fitted = self.filter_by_time(self.sort_by_priority(due))

        # Tasks with a preferred time are pinned there; the rest fill the earliest open gaps.
        fixed = sorted((p for p in fitted if p[1].preferred_time), key=lambda p: p[1].preferred_time)
        flexible = [p for p in fitted if not p[1].preferred_time]

        for pet, task in fixed:
            start = datetime.combine(self.day, task.preferred_time)
            self._add_entry(pet, task, start, f"{task.priority} priority, pinned to preferred time")

        day_start = datetime.combine(self.day, self.owner.day_start)
        midnight = datetime.combine(self.day + timedelta(days=1), time.min)
        for pet, task in flexible:
            start = self._next_free_slot(day_start, task.duration_minutes)
            if start + timedelta(minutes=task.duration_minutes) > midnight:
                self.skipped.append((pet, task, "no open slot left before midnight"))
                continue
            self._add_entry(pet, task, start, f"{task.priority} priority, placed in next open slot")

        self.plan.sort(key=lambda entry: entry.start)
        return self.plan

    def sort_by_priority(self, tasks: list[tuple[Pet, Task]]) -> list[tuple[Pet, Task]]:
        """Return (pet, task) pairs ordered by priority, then shortest duration first."""
        return sorted(tasks, key=lambda p: (p[1].priority_rank, p[1].duration_minutes))

    def sort_by_time(self, tasks: list[tuple[Pet, Task]]) -> list[tuple[Pet, Task]]:
        """Return (pet, task) pairs ordered by preferred time; flexible (no time) tasks go last."""
        return sorted(tasks, key=lambda p: (p[1].preferred_time is None, p[1].preferred_time or time.min))

    def filter_tasks(
        self, pet_name: Optional[str] = None, completed: Optional[bool] = None
    ) -> list[tuple[Pet, Task]]:
        """Return (pet, task) pairs matching the given pet name and/or completion status.

        completed=True means done on this day; completed=False means still open. Instances
        completed on earlier days are history and match neither.
        """
        def matches(task: Task) -> bool:
            if completed is None:
                return True
            if completed:
                return task.is_completed(self.day)
            return task.last_completed is None

        return [
            (pet, task)
            for pet in self.owner.pets
            if pet_name is None or pet.name == pet_name
            for task in pet.tasks
            if matches(task)
        ]

    def filter_by_time(self, tasks: list[tuple[Pet, Task]]) -> list[tuple[Pet, Task]]:
        """Keep tasks that fit in the owner's available time, in order; record the rest as skipped."""
        remaining = self.owner.available_minutes
        kept = []
        for pet, task in tasks:
            if task.duration_minutes <= remaining:
                kept.append((pet, task))
                remaining -= task.duration_minutes
            else:
                self.skipped.append(
                    (pet, task, f"needs {task.duration_minutes} min, only {remaining} min left")
                )
        return kept

    def detect_conflicts(self) -> list[tuple[ScheduledTask, ScheduledTask]]:
        """Return pairs of scheduled tasks whose time slots overlap."""
        entries = sorted(self.plan, key=lambda e: e.start)
        conflicts = []
        for i, a in enumerate(entries):
            for b in entries[i + 1:]:
                if b.start >= a.end:
                    break
                conflicts.append((a, b))
        return conflicts

    def explain_plan(self) -> str:
        """Return a human-readable explanation of why the plan was built this way."""
        if not self.plan and not self.skipped:
            return "No tasks are due today."

        used = sum(e.task.duration_minutes for e in self.plan)
        lines = [
            f"Daily plan for {self.owner.name} ({used}/{self.owner.available_minutes} min used):"
        ]
        for e in self.plan:
            lines.append(
                f"  {e.start:%H:%M}-{e.end:%H:%M}  {e.task.title} for {e.pet.name} "
                f"({e.task.duration_minutes} min) - {e.reason}"
            )
        if self.skipped:
            lines.append("Skipped:")
            for pet, task, reason in self.skipped:
                lines.append(f"  {task.title} for {pet.name} [{task.priority}] - {reason}")
        lines.extend(self.conflict_warnings())
        return "\n".join(lines)

    def conflict_warnings(self) -> list[str]:
        """Return a readable warning for each pair of overlapping tasks (empty list if none)."""
        warnings = []
        for a, b in self.detect_conflicts():
            if a.start == b.start:
                clash = f"both start at {a.start:%H:%M}"
            else:
                clash = f"overlap {b.start:%H:%M}-{min(a.end, b.end):%H:%M}"
            warnings.append(
                f"Warning: {a.task.title} ({a.pet.name}) and {b.task.title} ({b.pet.name}) {clash}"
            )
        return warnings

    def _add_entry(self, pet: Pet, task: Task, start: datetime, reason: str) -> None:
        """Append a ScheduledTask to the plan, computing its end from the task duration."""
        end = start + timedelta(minutes=task.duration_minutes)
        self.plan.append(ScheduledTask(pet, task, start, end, reason))

    def _next_free_slot(self, earliest: datetime, duration_minutes: int) -> datetime:
        """Return the earliest start >= `earliest` that doesn't overlap anything already planned."""
        start = earliest
        length = timedelta(minutes=duration_minutes)
        for entry in sorted(self.plan, key=lambda e: e.start):
            if start + length <= entry.start:
                break
            if start < entry.end:
                start = entry.end
        return start
