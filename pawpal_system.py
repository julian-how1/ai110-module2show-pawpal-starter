"""PawPal+ core system: owners, pets, care tasks, and the daily scheduler."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Task:
    """A single pet care activity (walk, feeding, meds, etc.)."""

    title: str
    category: str
    duration_minutes: int
    priority: str = "medium"
    frequency: str = "daily"
    preferred_time: Optional[str] = None
    completed: bool = False

    def mark_complete(self) -> None:
        """Mark this task as done."""
        pass

    def is_due_today(self) -> bool:
        """Return True if this task should be scheduled today."""
        pass

    def edit(self, **changes) -> None:
        """Update one or more fields on this task."""
        pass


@dataclass
class Pet:
    """A pet and its list of care tasks."""

    name: str
    species: str
    age: int
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a care task for this pet."""
        pass

    def remove_task(self, task: Task) -> None:
        """Remove a care task from this pet."""
        pass

    def get_tasks(self) -> list[Task]:
        """Return all tasks for this pet."""
        pass


@dataclass
class Owner:
    """A pet owner with daily time constraints and preferences."""

    name: str
    available_minutes: int
    preferences: dict = field(default_factory=dict)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner."""
        pass

    def get_pets(self) -> list[Pet]:
        """Return all pets belonging to this owner."""
        pass

    def set_availability(self, minutes: int) -> None:
        """Set how many minutes the owner has available today."""
        pass


class Scheduler:
    """Builds a daily care plan from an owner's pets, tasks, and constraints."""

    def __init__(self, owner: Owner) -> None:
        self.owner = owner
        self.plan: list = []
        self.skipped: list[Task] = []

    def generate_plan(self) -> list:
        """Build and return today's schedule as a list of (time, Task) entries."""
        pass

    def sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        """Return tasks ordered from highest to lowest priority."""
        pass

    def filter_by_time(self, tasks: list[Task]) -> list[Task]:
        """Keep only tasks that fit in the owner's available time; record the rest as skipped."""
        pass

    def detect_conflicts(self) -> list:
        """Return pairs of scheduled tasks whose time slots overlap."""
        pass

    def explain_plan(self) -> str:
        """Return a human-readable explanation of why the plan was built this way."""
        pass
