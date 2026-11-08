SMART TO-DO WITH REMINDERS

Isi proyek:
- main.py          : tampilan aplikasi dan penghubung seluruh modul.
- task_manager.py  : tambah, edit, hapus, cari, dan ubah status tugas.
- storage.py       : penyimpanan lokal menggunakan JSON.
- reminders.py     : reminder, deteksi overdue, dan pengurutan urgensi.
- focus_mode.py    : rekomendasi tugas dan alasan rekomendasi.
- test_focus.py    : pengujian Focus Mode dan integrasi modul.

Cara menjalankan aplikasi:
    python main.py

Cara menjalankan pengujian Focus Mode:
    python test_focus.py

Pengujian memakai unittest bawaan Python dan tidak membuka jendela Tkinter.
Folder data/tasks.json dibuat otomatis saat aplikasi pertama kali dijalankan.
Format deadline: YYYY-MM-DD HH:MM.
Tidak menggunakan SQLite, MySQL, atau database server.
