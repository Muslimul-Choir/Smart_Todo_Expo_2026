"""
FOCUS MODE MODULE
Modul rekomendasi tugas untuk aplikasi Smart To-Do with Reminders.

Tujuan:
- Memilih tugas yang paling disarankan untuk dikerjakan berikutnya.
- Mengurutkan beberapa rekomendasi tugas.
- Menjelaskan alasan mengapa tugas tersebut direkomendasikan.

Prioritas keputusan:
1. Tugas yang sudah overdue didahulukan.
2. Prioritas tertinggi ke terendah (Tinggi > Sedang > Rendah) didahulukan.
3. Deadline yang paling dekat didahulukan.
4. Tugas selesai tidak pernah direkomendasikan.

Modul ini menggunakan fungsi pengurutan dari reminders.py agar aturan
urgensi tetap konsisten di seluruh aplikasi.
"""

from datetime import datetime, timedelta

from reminders import sort_by_urgency, is_overdue
from task_manager import parse_deadline


def get_focus_recommendations(tasks, limit=3, now=None):
    """
    Mengembalikan daftar rekomendasi tugas yang belum selesai.

    Args:
        tasks (list): daftar tugas dari storage.py.
        limit (int): jumlah rekomendasi maksimum.
        now (datetime): waktu saat ini; opsional untuk pengujian.

    Return:
        list[dict]: setiap item berisi:
            {
                "task": dictionary tugas,
                "reason": alasan rekomendasi
            }

    Daftar tugas asli tidak diubah.
    """
    if not isinstance(tasks, list):
        raise TypeError("tasks harus berupa list.")

    if limit is None:
        limit = len(tasks)
    if not isinstance(limit, int) or limit < 0:
        raise ValueError("limit harus berupa bilangan bulat >= 0.")

    now = now or datetime.now()

    active_tasks = [
        task for task in tasks
        if isinstance(task, dict) and task.get("status") != "Selesai"
    ]

    ordered_tasks = sort_by_urgency(active_tasks, now=now)
    recommendations = []

    for task in ordered_tasks[:limit]:
        recommendations.append({
            "task": task,
            "reason": get_focus_reason(task, now=now),
        })

    return recommendations


def suggest_next_task(tasks, now=None):
    """
    Mengembalikan satu tugas yang paling direkomendasikan.

    Return:
        dictionary tugas jika masih ada tugas aktif.
        None jika semua tugas sudah selesai atau daftar kosong.
    """
    recommendations = get_focus_recommendations(tasks, limit=1, now=now)
    if not recommendations:
        return None
    return recommendations[0]["task"]


def get_focus_reason(task, now=None):
    """
    Menghasilkan alasan singkat untuk rekomendasi sebuah tugas.
    """
    if not isinstance(task, dict):
        return "Tugas ini direkomendasikan untuk dikerjakan."

    now = now or datetime.now()

    if task.get("status") == "Selesai":
        return "Tugas ini sudah selesai."

    if is_overdue(task, now=now):
        return "Deadline sudah terlewat. Selesaikan tugas ini sesegera mungkin."

    try:
        deadline = parse_deadline(task.get("deadline", ""))
        time_left = deadline - now
    except (TypeError, ValueError):
        return "Deadline belum valid. Periksa kembali tanggal dan waktu tugas."

    priority = task.get("priority", "Rendah")

    if time_left <= timedelta(hours=24):
        if priority == "Tinggi":
            return "Deadline kurang dari 24 jam dan prioritas tugas Tinggi."
        return "Deadline kurang dari 24 jam. Sebaiknya segera dikerjakan."

    if priority == "Tinggi":
        return "Tugas memiliki prioritas Tinggi."

    if time_left <= timedelta(days=3):
        return "Deadline tinggal beberapa hari lagi."

    return "Tugas aktif dengan deadline paling dekat dibandingkan tugas lainnya."
