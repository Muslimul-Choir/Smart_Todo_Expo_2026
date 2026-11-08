"""
TEST FOCUS MODE
Pengujian untuk modul Focus Mode pada proyek Smart To-Do with Reminders.

Cara menjalankan:
    python test_focus.py

Pengujian ini menggunakan unittest (library bawaan Python), tanpa
SQLite/MySQL dan tanpa membuka jendela aplikasi Tkinter.

Yang diuji:
1. Rekomendasi tugas paling mendesak.
2. Tugas selesai tidak direkomendasikan.
3. Tugas overdue didahulukan.
4. Deadline dan prioritas menjadi dasar urutan.
5. Alasan rekomendasi.
6. Daftar kosong dan batas jumlah rekomendasi.
7. Integrasi task_manager.py + storage.py + reminders.py + focus_mode.py.
8. Koneksi fungsi Focus Mode yang diimpor oleh main.py.
"""

import sys
import unittest
import tempfile
import importlib
from pathlib import Path
from datetime import datetime

# Pastikan modul proyek dapat ditemukan saat test_focus.py dijalankan
# dari folder proyek yang sama.
PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import task_manager
import storage
import reminders
import focus_mode


class TestFocusMode(unittest.TestCase):
    def setUp(self):
        # Waktu tetap membuat hasil tes konsisten setiap kali dijalankan.
        self.now = datetime(2026, 11, 8, 10, 0)

        self.tasks = [
            {
                "id": 1,
                "title": "Membaca materi",
                "description": "Materi kuliah",
                "deadline": "2026-11-12 10:00",
                "priority": "Rendah",
                "status": "Belum Selesai",
                "reminded": False,
            },
            {
                "id": 2,
                "title": "Mengerjakan laporan terlambat",
                "description": "Laporan praktikum",
                "deadline": "2026-11-07 10:00",
                "priority": "Rendah",
                "status": "Belum Selesai",
                "reminded": False,
            },
            {
                "id": 3,
                "title": "Membuat presentasi",
                "description": "Slide presentasi",
                "deadline": "2026-11-08 18:00",
                "priority": "Tinggi",
                "status": "Belum Selesai",
                "reminded": False,
            },
            {
                "id": 4,
                "title": "Tugas yang sudah selesai",
                "description": "Tidak boleh masuk rekomendasi",
                "deadline": "2026-11-08 10:05",
                "priority": "Tinggi",
                "status": "Selesai",
                "reminded": False,
            },
            {
                "id": 5,
                "title": "Tugas prioritas sedang",
                "description": "Tugas tambahan",
                "deadline": "2026-11-09 10:00",
                "priority": "Sedang",
                "status": "Belum Selesai",
                "reminded": False,
            },
        ]

    def test_overdue_task_is_first_recommendation(self):
        recommendations = focus_mode.get_focus_recommendations(
            self.tasks, limit=3, now=self.now
        )
        self.assertEqual(recommendations[0]["task"]["id"], 2)

    def test_completed_task_is_not_recommended(self):
        recommendations = focus_mode.get_focus_recommendations(
            self.tasks, limit=10, now=self.now
        )
        recommended_ids = [item["task"]["id"] for item in recommendations]
        self.assertNotIn(4, recommended_ids)

    def test_nearest_deadline_is_ranked_before_later_deadline(self):
        recommendations = focus_mode.get_focus_recommendations(
            self.tasks, limit=10, now=self.now
        )
        recommended_ids = [item["task"]["id"] for item in recommendations]
        self.assertLess(recommended_ids.index(3), recommended_ids.index(1))

    def test_suggest_next_task_returns_one_task(self):
        task = focus_mode.suggest_next_task(self.tasks, now=self.now)
        self.assertIsNotNone(task)
        self.assertEqual(task["id"], 2)

    def test_suggest_next_task_returns_none_when_all_completed(self):
        completed_tasks = [
            dict(self.tasks[3])
        ]
        self.assertIsNone(
            focus_mode.suggest_next_task(completed_tasks, now=self.now)
        )

    def test_empty_list_returns_empty_recommendations(self):
        self.assertEqual(
            focus_mode.get_focus_recommendations([], now=self.now),
            []
        )

    def test_limit_controls_number_of_recommendations(self):
        recommendations = focus_mode.get_focus_recommendations(
            self.tasks, limit=2, now=self.now
        )
        self.assertEqual(len(recommendations), 2)

    def test_recommendation_contains_task_and_reason(self):
        recommendations = focus_mode.get_focus_recommendations(
            self.tasks, limit=1, now=self.now
        )
        self.assertIn("task", recommendations[0])
        self.assertIn("reason", recommendations[0])
        self.assertTrue(recommendations[0]["reason"])

    def test_overdue_reason_is_explained(self):
        reason = focus_mode.get_focus_reason(self.tasks[1], now=self.now)
        self.assertIn("terlewat", reason.lower())

    def test_completed_task_reason(self):
        reason = focus_mode.get_focus_reason(self.tasks[3], now=self.now)
        self.assertIn("selesai", reason.lower())

    def test_invalid_tasks_argument_raises_type_error(self):
        with self.assertRaises(TypeError):
            focus_mode.get_focus_recommendations("bukan list", now=self.now)

    def test_invalid_limit_raises_value_error(self):
        with self.assertRaises(ValueError):
            focus_mode.get_focus_recommendations(
                self.tasks, limit=-1, now=self.now
            )


class TestProjectIntegration(unittest.TestCase):
    def test_focus_module_uses_reminder_sorting(self):
        # Pastikan Focus Mode memakai fungsi urgensi dari reminders.py.
        self.assertIs(focus_mode.sort_by_urgency, reminders.sort_by_urgency)
        self.assertIs(focus_mode.is_overdue, reminders.is_overdue)

    def test_task_manager_storage_and_focus_mode_work_together(self):
        # Gunakan direktori sementara agar data asli pengguna tidak disentuh.
        original_data_dir = storage.DATA_DIR
        original_data_file = storage.DATA_FILE

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                storage.DATA_DIR = temp_path / "data"
                storage.DATA_FILE = storage.DATA_DIR / "tasks.json"

                # 1. Storage menyiapkan file JSON.
                tasks = storage.load_tasks()

                # 2. Task manager membuat tugas.
                created_task = task_manager.add_task(
                    tasks,
                    "Tes integrasi Focus Mode",
                    "Tugas dibuat melalui task_manager",
                    "2026-11-10 20:00",
                    "Tinggi",
                )

                # 3. Storage menyimpan data.
                storage.save_tasks(tasks)

                # 4. Data dibaca kembali dari file JSON.
                loaded_tasks = storage.load_tasks()
                self.assertEqual(len(loaded_tasks), 1)
                self.assertEqual(
                    loaded_tasks[0]["title"],
                    "Tes integrasi Focus Mode",
                )

                # 5. Focus Mode merekomendasikan tugas hasil pembacaan JSON.
                suggested = focus_mode.suggest_next_task(
                    loaded_tasks,
                    now=datetime(2026, 11, 8, 10, 0),
                )
                self.assertIsNotNone(suggested)
                self.assertEqual(suggested["id"], created_task["id"])

        finally:
            # Kembalikan lokasi penyimpanan asli setelah tes selesai.
            storage.DATA_DIR = original_data_dir
            storage.DATA_FILE = original_data_file

    def test_main_imports_focus_mode_functions(self):
        # Import main.py tidak menjalankan root.mainloop karena dilindungi
        # oleh if __name__ == "__main__".
        main_module = importlib.import_module("main")
        self.assertIs(
            main_module.get_focus_recommendations,
            focus_mode.get_focus_recommendations,
        )
        self.assertIs(
            main_module.get_focus_reason,
            focus_mode.get_focus_reason,
        )


if __name__ == "__main__":
    print("=" * 60)
    print("SMART TO-DO WITH REMINDERS - FOCUS MODE TEST")
    print("=" * 60)
    unittest.main(verbosity=2)
