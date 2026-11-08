"""
REMINDERS MODULE
Modul untuk pemeriksaan deadline, status overdue, dan pengurutan urgensi.

Modul ini tidak membuat tampilan Tkinter dan tidak menyimpan file.
Tampilan popup serta penyimpanan penanda reminder tetap dilakukan oleh main.py
melalui messagebox dan storage.py.

Format deadline tugas:
    YYYY-MM-DD HH:MM

Fungsi yang digunakan main.py:
    is_overdue(task, now=None)
    get_overdue_tasks(tasks, now=None)
    sort_by_urgency(tasks, now=None)
    get_upcoming_reminders(tasks, now=None, within_minutes=15)
"""

from datetime import datetime
from task_manager import parse_deadline


PRIORITY_ORDER = {
    "Tinggi": 0,
    "Sedang": 1,
    "Rendah": 2,
}


def is_overdue(task, now=None):
    """
    Mengembalikan True jika deadline tugas sudah lewat dan tugas belum selesai.
    Tugas tanpa deadline valid dianggap tidak overdue.
    """
    if not isinstance(task, dict):
        return False

    if task.get("status") == "Selesai":
        return False

    now = now or datetime.now()

    try:
        deadline = parse_deadline(task.get("deadline", ""))
    except (TypeError, ValueError):
        return False

    return deadline < now


def get_overdue_tasks(tasks, now=None):
    """Mengembalikan semua tugas yang sudah melewati deadline."""
    now = now or datetime.now()
    return [
        task for task in tasks
        if is_overdue(task, now)
    ]


def urgency_sort_key(task, now=None):
    """
    Kunci pengurutan:
    1. Tugas aktif lebih dahulu daripada tugas selesai.
    2. Tugas aktif yang overdue didahulukan.
    3. Prioritas tertinggi ke prioritas terendah (Tinggi > Sedang > Rendah).
    4. Deadline yang lebih dekat didahulukan.
    5. Judul tugas secara alfabetis.
    """
    now = now or datetime.now()

    completed = task.get("status") == "Selesai"

    try:
        deadline = parse_deadline(task.get("deadline", ""))
    except (TypeError, ValueError):
        deadline = datetime.max

    completed_rank = 1 if completed else 0
    overdue_rank = 0 if (not completed and deadline < now) else 1
    priority_rank = PRIORITY_ORDER.get(task.get("priority", "Rendah"), 3)

    return (
        completed_rank,
        overdue_rank,
        priority_rank,
        deadline,
        str(task.get("title", "")).lower(),
    )


def sort_by_urgency(tasks, now=None):
    """
    Mengembalikan salinan daftar tugas yang sudah diurutkan.
    Daftar asli tidak diubah.
    """
    if not isinstance(tasks, list):
        raise TypeError("tasks harus berupa list.")
    now = now or datetime.now()
    return sorted(tasks, key=lambda task: urgency_sort_key(task, now))


def get_upcoming_reminders(tasks, now=None, within_minutes=15):
    """
    Mengambil tugas yang deadline-nya akan tiba dalam rentang waktu tertentu.

    Tugas yang diambil:
    - Belum berstatus Selesai.
    - Belum pernah ditandai reminded=True.
    - Deadline berada dari sekarang sampai `within_minutes` ke depan.

    Return:
        List berisi tuple (task, minutes_left).
        minutes_left adalah sisa menit dibulatkan ke bawah, minimum 0.

    main.py bertugas menampilkan popup dan mengubah task["reminded"] menjadi True.
    """
    if not isinstance(tasks, list):
        raise TypeError("tasks harus berupa list.")

    if within_minutes < 0:
        raise ValueError("within_minutes tidak boleh bernilai negatif.")

    now = now or datetime.now()
    reminders = []

    for task in tasks:
        if not isinstance(task, dict):
            continue

        if task.get("status") == "Selesai":
            continue

        if task.get("reminded", False):
            continue

        try:
            deadline = parse_deadline(task.get("deadline", ""))
        except (TypeError, ValueError):
            continue

        minutes_left = (deadline - now).total_seconds() / 60

        if 0 <= minutes_left <= within_minutes:
            reminders.append((task, max(0, int(minutes_left)), deadline))

    # Reminder dengan deadline paling dekat ditampilkan lebih dahulu.
    reminders.sort(key=lambda item: item[2])
    return [(task, minutes) for task, minutes, _deadline in reminders]
