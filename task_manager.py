"""
TASK MANAGER MODULE
Modul untuk mengelola data tugas Smart To-Do.

Modul ini tidak mengurus tampilan Tkinter dan tidak menyimpan file JSON.
Tugas penyimpanan tetap menjadi tanggung jawab storage.py.
main.py memanggil fungsi-fungsi di modul ini, lalu menyimpan perubahan
menggunakan save_tasks().

Format data tugas:
{
    "id": 1,
    "title": "Mengerjakan tugas Python",
    "description": "Menyelesaikan aplikasi",
    "deadline": "2026-11-10 20:00",
    "priority": "Tinggi",
    "status": "Belum Selesai",
    "reminded": false
}
"""

from datetime import datetime


DATE_FORMAT = "%Y-%m-%d %H:%M"
VALID_PRIORITIES = ("Tinggi", "Sedang", "Rendah")
STATUS_ACTIVE = "Belum Selesai"
STATUS_COMPLETED = "Selesai"


def parse_deadline(value):
    """
    Memvalidasi dan mengubah deadline menjadi datetime.

    Format yang diterima: YYYY-MM-DD HH:MM
    Contoh: 2026-11-10 20:00

    Raises:
        ValueError: jika format atau tanggal tidak valid.
    """
    if not isinstance(value, str):
        raise ValueError("Deadline harus berupa teks.")
    try:
        return datetime.strptime(value.strip(), DATE_FORMAT)
    except ValueError as error:
        raise ValueError(
            "Deadline harus menggunakan format YYYY-MM-DD HH:MM "
            "(contoh: 2026-11-10 20:00)."
        ) from error


def _validate_task_fields(title, description, deadline, priority):
    """Validasi data sebelum tugas ditambahkan atau diperbarui."""
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Nama tugas wajib diisi.")

    if description is None:
        description = ""
    elif not isinstance(description, str):
        description = str(description)

    # Pastikan tanggal benar-benar valid.
    parse_deadline(deadline)

    if priority not in VALID_PRIORITIES:
        raise ValueError("Prioritas harus Tinggi, Sedang, atau Rendah.")

    return title.strip(), description.strip(), deadline.strip(), priority


def get_next_id(tasks):
    """
    Menghasilkan ID integer berikutnya.
    ID dibuat dari angka terbesar + 1 agar tidak bentrok dengan data lama.
    """
    if not isinstance(tasks, list):
        raise TypeError("tasks harus berupa list.")

    existing_ids = []
    for task in tasks:
        if not isinstance(task, dict):
            continue
        try:
            existing_ids.append(int(task.get("id", 0)))
        except (TypeError, ValueError):
            continue

    return max(existing_ids, default=0) + 1


def find_task(tasks, task_id):
    """Mencari satu tugas berdasarkan ID; mengembalikan None jika tidak ada."""
    if not isinstance(tasks, list):
        raise TypeError("tasks harus berupa list.")

    for task in tasks:
        if isinstance(task, dict) and str(task.get("id")) == str(task_id):
            return task
    return None


def add_task(tasks, title, description, deadline, priority):
    """
    Menambahkan tugas baru ke list dan mengembalikan dictionary tugas.

    Perubahan belum ditulis ke file. Pemanggil perlu memanggil save_tasks()
    dari storage.py setelah fungsi ini berhasil.
    """
    if not isinstance(tasks, list):
        raise TypeError("tasks harus berupa list.")

    title, description, deadline, priority = _validate_task_fields(
        title, description, deadline, priority
    )

    task = {
        "id": get_next_id(tasks),
        "title": title,
        "description": description,
        "deadline": deadline,
        "priority": priority,
        "status": STATUS_ACTIVE,
        "reminded": False,
    }
    tasks.append(task)
    return task


def update_task(tasks, task_id, title, description, deadline, priority):
    """
    Memperbarui tugas berdasarkan ID.

    Return:
        True  -> tugas ditemukan dan diperbarui.
        False -> ID tugas tidak ditemukan.
    """
    task = find_task(tasks, task_id)
    if task is None:
        return False

    title, description, deadline, priority = _validate_task_fields(
        title, description, deadline, priority
    )

    deadline_changed = task.get("deadline") != deadline

    task.update({
        "title": title,
        "description": description,
        "deadline": deadline,
        "priority": priority,
    })

    # Jika deadline berubah, pengingat lama tidak lagi berlaku.
    if deadline_changed:
        task["reminded"] = False

    # Jika task lama berasal dari file JSON versi berbeda, pastikan key ada.
    task.setdefault("status", STATUS_ACTIVE)
    task.setdefault("reminded", False)
    return True


def delete_task(tasks, task_id):
    """
    Menghapus tugas berdasarkan ID.

    Return:
        True  -> tugas berhasil dihapus.
        False -> ID tugas tidak ditemukan.
    """
    task = find_task(tasks, task_id)
    if task is None:
        return False

    tasks.remove(task)
    return True


def toggle_complete(tasks, task_id):
    """
    Mengubah status tugas:
    Belum Selesai <-> Selesai.

    Jika tugas diaktifkan kembali, penanda reminder di-reset.
    Return False jika ID tidak ditemukan.
    """
    task = find_task(tasks, task_id)
    if task is None:
        return False

    if task.get("status") == STATUS_COMPLETED:
        task["status"] = STATUS_ACTIVE
        task["reminded"] = False
    else:
        task["status"] = STATUS_COMPLETED

    return True


def set_task_status(tasks, task_id, status):
    """
    Mengatur status tugas secara eksplisit menjadi 'Belum Selesai' atau 'Selesai'.
    Jika diaktifkan kembali, penanda reminder di-reset.
    Return False jika ID tidak ditemukan.
    """
    task = find_task(tasks, task_id)
    if task is None:
        return False

    if status not in (STATUS_ACTIVE, STATUS_COMPLETED):
        raise ValueError(
            f"Status harus berupa '{STATUS_ACTIVE}' atau '{STATUS_COMPLETED}'."
        )

    task["status"] = status
    if status == STATUS_ACTIVE:
        task["reminded"] = False
    return True
