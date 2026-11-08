"""
STORAGE MODULE
Penyimpanan lokal untuk aplikasi Smart To-Do with Reminders.

Tidak menggunakan SQLite, MySQL, atau database server.
Semua data disimpan dalam file JSON di folder:
    Smart_ToDo/data/tasks.json

Fungsi utama yang digunakan main.py:
    ensure_data_file()
    load_tasks()
    save_tasks(tasks)
"""

import json
import os
from pathlib import Path


# Lokasi penyimpanan selalu mengikuti lokasi file storage.py.
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "tasks.json"

VALID_PRIORITIES = {"Tinggi", "Sedang", "Rendah"}
VALID_STATUSES = {"Belum Selesai", "Selesai"}


class StorageError(OSError):
    """Error khusus ketika data lokal gagal dibaca atau disimpan."""


def ensure_data_file():
    """
    Membuat folder data dan file tasks.json jika belum tersedia atau kosong.
    Tidak menghapus atau menimpa file yang sudah ada isinya.
    """
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        if not DATA_FILE.exists() or DATA_FILE.stat().st_size == 0:
            temporary_file = DATA_FILE.with_suffix(".tmp")
            temporary_file.write_text("[]", encoding="utf-8")
            temporary_file.replace(DATA_FILE)

    except OSError as error:
        raise StorageError(
            f"Tidak dapat menyiapkan folder penyimpanan: {error}"
        ) from error


def _normalize_tasks(raw_tasks):
    """
    Memastikan data yang dibaca memiliki bentuk yang konsisten.
    Fungsi ini membantu menangani data lama atau key yang belum lengkap.
    """
    normalized = []
    used_ids = set()
    next_id = 1

    for raw_task in raw_tasks:
        if not isinstance(raw_task, dict):
            # Abaikan item yang bukan dictionary.
            continue

        # Pastikan ID berupa integer positif dan tidak duplikat.
        try:
            task_id = int(raw_task.get("id", 0))
        except (TypeError, ValueError):
            task_id = 0

        if task_id <= 0 or task_id in used_ids:
            while next_id in used_ids:
                next_id += 1
            task_id = next_id

        used_ids.add(task_id)
        next_id = max(next_id, task_id + 1)

        priority = raw_task.get("priority", "Rendah")
        if priority not in VALID_PRIORITIES:
            priority = "Rendah"

        status = raw_task.get("status", "Belum Selesai")
        if status not in VALID_STATUSES:
            status = "Belum Selesai"

        normalized.append({
            "id": task_id,
            "title": str(raw_task.get("title", "Tanpa judul")),
            "description": str(raw_task.get("description", "")),
            "deadline": str(raw_task.get("deadline", "")),
            "priority": priority,
            "status": status,
            "reminded": bool(raw_task.get("reminded", False)),
        })

    return normalized


def load_tasks():
    """
    Membaca daftar tugas dari tasks.json.

    Return:
        list: daftar tugas yang sudah dinormalisasi.

    Raises:
        StorageError: jika file tidak bisa dibaca atau format JSON rusak.
        File JSON yang rusak tidak akan dihapus atau ditimpa otomatis.
    """
    ensure_data_file()

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            raw_tasks = json.load(file)

    except json.JSONDecodeError as error:
        raise StorageError(
            "Isi data/tasks.json bukan JSON yang valid. "
            "File asli dipertahankan agar data dapat diperiksa atau dipulihkan."
        ) from error
    except OSError as error:
        raise StorageError(
            f"Tidak dapat membaca {DATA_FILE}: {error}"
        ) from error

    if not isinstance(raw_tasks, list):
        raise StorageError(
            "Format tasks.json tidak sesuai. Data utama harus berupa list JSON."
        )

    return _normalize_tasks(raw_tasks)


def save_tasks(tasks):
    """
    Menyimpan seluruh daftar tugas ke tasks.json secara aman.

    Data ditulis ke file sementara terlebih dahulu, lalu dipindahkan
    untuk mengurangi risiko file JSON menjadi setengah tertulis jika
    proses penyimpanan terganggu.
    """
    if not isinstance(tasks, list):
        raise TypeError("Data tugas yang disimpan harus berupa list.")

    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise TypeError(
                f"Data tugas pada urutan ke-{index + 1} harus berupa dictionary."
            )

    ensure_data_file()

    temporary_file = DATA_FILE.with_suffix(".tmp")

    try:
        with temporary_file.open("w", encoding="utf-8") as file:
            json.dump(tasks, file, indent=2, ensure_ascii=False)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())

        temporary_file.replace(DATA_FILE)

    except (OSError, TypeError, ValueError) as error:
        # Bersihkan file sementara jika penyimpanan gagal.
        try:
            if temporary_file.exists():
                temporary_file.unlink()
        except OSError:
            pass

        raise StorageError(
            f"Tidak dapat menyimpan data tugas: {error}"
        ) from error


def get_storage_location():
    """Mengembalikan lokasi file JSON untuk ditampilkan atau diuji."""
    return DATA_FILE
