from datetime import date, time

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

with st.expander("Scenario", expanded=False):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.
"""
    )

# The Owner object (and its pets/tasks) lives in session_state so it survives reruns.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan", available_minutes=120)
owner: Owner = st.session_state.owner

st.subheader("Owner")
col1, col2, col3 = st.columns(3)
with col1:
    owner.name = st.text_input("Owner name", value="Jordan")
with col2:
    owner.set_availability(int(st.number_input("Minutes available today", min_value=0, max_value=1440, value=120)))
with col3:
    owner.day_start = st.time_input("Day starts at", value=time(8, 0))

st.divider()

st.subheader("Pets")
with st.form("add_pet", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        pet_name = st.text_input("Pet name", value="Mochi")
    with col2:
        species = st.selectbox("Species", ["dog", "cat", "other"])
    with col3:
        age = st.number_input("Age", min_value=0, max_value=40, value=3)
    if st.form_submit_button("Add pet"):
        if not pet_name.strip():
            st.error("Pet name can't be empty.")
        elif any(p.name == pet_name.strip() for p in owner.get_pets()):
            st.error(f"{owner.name} already has a pet named {pet_name.strip()}.")
        else:
            owner.add_pet(Pet(name=pet_name.strip(), species=species, age=int(age)))

if owner.get_pets():
    st.table([{"Name": p.name, "Species": p.species, "Age": p.age, "Tasks": len(p.tasks)} for p in owner.get_pets()])
else:
    st.info("No pets yet. Add one above.")

st.divider()

CATEGORIES = ["exercise", "feeding", "medication", "grooming", "play", "other"]
PRIORITIES = ["high", "medium", "low"]
FREQUENCIES = ["daily", "weekly"]


def task_status(task: Task) -> str:
    """Short label: when this task was done, or when it's next due."""
    if task.last_completed:
        return f"✅ done {task.last_completed:%b %d}"
    if task.due_date and task.due_date > date.today():
        return f"due {task.due_date:%b %d}"
    return "due now"


st.subheader("Tasks")
if not owner.get_pets():
    st.caption("Add a pet first, then you can give it tasks.")
else:
    with st.form("add_task", clear_on_submit=True):
        pet_choice = st.selectbox("For pet", [p.name for p in owner.get_pets()])
        col1, col2 = st.columns(2)
        with col1:
            task_title = st.text_input("Task title", value="Morning walk")
            category = st.selectbox("Category", CATEGORIES)
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        with col2:
            priority = st.selectbox("Priority", PRIORITIES)
            frequency = st.selectbox("Frequency", FREQUENCIES)
            pin_time = st.checkbox("Set a preferred time")
            preferred = st.time_input("Preferred time", value=time(8, 0))
        if st.form_submit_button("Add task"):
            if not task_title.strip():
                st.error("Task title can't be empty.")
            else:
                pet = next(p for p in owner.get_pets() if p.name == pet_choice)
                pet.add_task(
                    Task(
                        title=task_title.strip(),
                        category=category,
                        duration_minutes=int(duration),
                        priority=priority,
                        frequency=frequency,
                        preferred_time=preferred if pin_time else None,
                    )
                )
                st.rerun()  # refresh the pet table's task count above

    all_tasks = [(pet, task) for pet in owner.get_pets() for task in pet.get_tasks()]
    if all_tasks:
        st.table(
            [
                {
                    "Pet": pet.name,
                    "Task": task.title,
                    "Category": task.category,
                    "Minutes": task.duration_minutes,
                    "Priority": task.priority,
                    "Frequency": task.frequency,
                    "Preferred time": task.preferred_time.strftime("%I:%M %p") if task.preferred_time else "flexible",
                    "Due": task_status(task),
                }
                for pet, task in all_tasks
            ]
        )
    else:
        st.info("No tasks yet. Add one above.")

    if all_tasks:
        st.markdown("#### Manage a task")
        idx = st.selectbox(
            "Task",
            range(len(all_tasks)),
            format_func=lambda i: f"{all_tasks[i][0].name}: {all_tasks[i][1].title} ({task_status(all_tasks[i][1])})",
        )
        sel_pet, sel_task = all_tasks[idx]

        col1, col2 = st.columns(2)
        with col1:
            if sel_task.last_completed is not None:
                if st.button("Mark not done", use_container_width=True):
                    sel_pet.undo_complete(sel_task)
                    st.rerun()
            elif st.button("Mark done today", use_container_width=True):
                sel_pet.complete_task(sel_task)  # also schedules the next daily/weekly occurrence
                st.rerun()
        with col2:
            if st.button("Remove task", use_container_width=True):
                sel_pet.remove_task(sel_task)
                st.rerun()

        # Keys use the task object's id so the form refills with the right values when the selection changes.
        tid = id(sel_task)
        with st.form(f"edit_task_{tid}"):
            st.caption("Edit task")
            col1, col2 = st.columns(2)
            with col1:
                new_title = st.text_input("Title", value=sel_task.title, key=f"edit_title_{tid}")
                new_category = st.selectbox(
                    "Category", CATEGORIES, index=CATEGORIES.index(sel_task.category), key=f"edit_cat_{tid}"
                )
                new_duration = st.number_input(
                    "Duration (minutes)", min_value=1, max_value=240,
                    value=sel_task.duration_minutes, key=f"edit_dur_{tid}",
                )
            with col2:
                new_priority = st.selectbox(
                    "Priority", PRIORITIES, index=PRIORITIES.index(sel_task.priority), key=f"edit_pri_{tid}"
                )
                new_frequency = st.selectbox(
                    "Frequency", FREQUENCIES, index=FREQUENCIES.index(sel_task.frequency), key=f"edit_freq_{tid}"
                )
                new_pin = st.checkbox(
                    "Set a preferred time", value=sel_task.preferred_time is not None, key=f"edit_pin_{tid}"
                )
                new_time = st.time_input(
                    "Preferred time", value=sel_task.preferred_time or time(8, 0), key=f"edit_time_{tid}"
                )
            if st.form_submit_button("Save changes"):
                if not new_title.strip():
                    st.error("Task title can't be empty.")
                else:
                    sel_task.edit(
                        title=new_title.strip(),
                        category=new_category,
                        duration_minutes=int(new_duration),
                        priority=new_priority,
                        frequency=new_frequency,
                        preferred_time=new_time if new_pin else None,
                    )
                    st.rerun()

st.divider()

st.subheader("Today's Schedule")
if st.button("Generate schedule", type="primary"):
    scheduler = Scheduler(owner)
    plan = scheduler.generate_plan()

    if not plan and not scheduler.skipped:
        st.info("No tasks are due today.")
    else:
        used = sum(e.task.duration_minutes for e in plan)
        st.caption(f"{scheduler.day:%A, %B %d, %Y} · {used}/{owner.available_minutes} minutes used")

    if plan:
        st.table(
            [
                {
                    "Time": f"{e.start:%I:%M %p} - {e.end:%I:%M %p}",
                    "Pet": e.pet.name,
                    "Task": e.task.title,
                    "Priority": e.task.priority,
                    "Why": e.reason,
                }
                for e in plan
            ]
        )

    for pet, task, reason in scheduler.skipped:
        st.warning(f"Skipped **{task.title}** for {pet.name} ({task.priority}): {reason}")

    for warning in scheduler.conflict_warnings():
        st.warning(warning)

    with st.expander("Plan explanation"):
        st.text(scheduler.explain_plan())
