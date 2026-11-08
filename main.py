"""
SMART TO-DO WITH REMINDERS
Aplikasi desktop sederhana menggunakan Tkinter + JSON (tanpa database).

Cara menjalankan:
    python main.py

Data otomatis disimpan di:
    data/tasks.json

Format deadline:
    YYYY-MM-DD HH:MM
Contoh:
    2026-11-10 20:00

Modul pendukung:
- storage.py      : penyimpanan lokal file JSON.
- task_manager.py : CRUD dan manipulasi data tugas.
- reminders.py    : pengingat waktu, overdue, dan pengurutan urgensi.
- focus_mode.py   : rekomendasi tugas fokus dan alasannya.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from datetime import datetime, timedelta

# Integrasi dengan modul-modul pendukung
import storage
from storage import ensure_data_file, load_tasks, save_tasks, StorageError

import task_manager
from task_manager import (
    DATE_FORMAT,
    VALID_PRIORITIES,
    STATUS_ACTIVE,
    STATUS_COMPLETED,
    parse_deadline,
    get_next_id,
    find_task,
    add_task,
    update_task,
    delete_task,
    toggle_complete,
    set_task_status,
)

import reminders
from reminders import (
    PRIORITY_ORDER,
    is_overdue,
    get_overdue_tasks,
    urgency_sort_key,
    sort_by_urgency,
    get_upcoming_reminders,
)

import focus_mode
from focus_mode import (
    get_focus_recommendations,
    suggest_next_task,
    get_focus_reason,
)


# ============================================================
# KONFIGURASI APLIKASI
# ============================================================

APP_TITLE = "Smart To-Do with Reminders"
REMINDER_MINUTES = 15
CHECK_REMINDER_EVERY_MS = 30_000

BASE_DIR = storage.BASE_DIR
DATA_DIR = storage.DATA_DIR
DATA_FILE = storage.DATA_FILE


def get_focus_task(tasks):
    """Fungsi pembantu kompatibilitas untuk mendapatkan tugas fokus berikutnya."""
    return suggest_next_task(tasks)


# ============================================================
# DIALOG TAMBAH / EDIT TUGAS
# ============================================================

class TaskDialog(tk.Toplevel):
    def __init__(self, parent, title="Tambah Tugas", task=None):
        super().__init__(parent)
        self.parent = parent
        self.result = None
        self.action = None  # "save", "delete", "toggle_complete"
        self.task = task
        self.is_edit = task is not None

        self.title(title)
        self.configure(bg="#F4F7FB")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.title_var = tk.StringVar(value=task.get("title", "") if task else "")
        self.deadline_var = tk.StringVar(
            value=task.get("deadline", datetime.now().strftime(DATE_FORMAT))
            if task else (datetime.now() + timedelta(hours=1)).strftime(DATE_FORMAT)
        )
        self.priority_var = tk.StringVar(
            value=task.get("priority", "Sedang") if task else "Sedang"
        )
        if self.is_edit:
            self.status_var = tk.StringVar(
                value=task.get("status", STATUS_ACTIVE)
            )

        self._build_form()
        self._center_window()

        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<Control-Return>", lambda _event: self._save())

    def _build_form(self):
        container = ttk.Frame(self, padding=20)
        container.pack(fill="both", expand=True)

        header_text = "Edit Detail Tugas" if self.is_edit else "Tambah Tugas Baru"
        ttk.Label(
            container,
            text=header_text,
            style="DialogTitle.TLabel"
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))

        # 1. Judul
        ttk.Label(container, text="Nama tugas *").grid(
            row=1, column=0, sticky="w", pady=5
        )
        title_entry = ttk.Entry(
            container, textvariable=self.title_var, width=42
        )
        title_entry.grid(row=1, column=1, sticky="ew", pady=5)
        title_entry.focus_set()

        # 2. Deskripsi
        ttk.Label(container, text="Deskripsi").grid(
            row=2, column=0, sticky="nw", pady=5
        )
        self.description_text = tk.Text(
            container, width=32, height=4, wrap="word",
            font=("Segoe UI", 9), relief="solid", bd=1
        )
        self.description_text.grid(row=2, column=1, sticky="ew", pady=5)
        if self.task:
            self.description_text.insert("1.0", self.task.get("description", ""))

        # 3. Deadline
        ttk.Label(container, text="Deadline *").grid(
            row=3, column=0, sticky="w", pady=5
        )
        deadline_entry = ttk.Entry(
            container, textvariable=self.deadline_var, width=42
        )
        deadline_entry.grid(row=3, column=1, sticky="ew", pady=5)

        ttk.Label(
            container,
            text="Format: YYYY-MM-DD HH:MM",
            style="Hint.TLabel"
        ).grid(row=4, column=1, sticky="w", pady=(0, 5))

        # 4. Prioritas
        ttk.Label(container, text="Prioritas *").grid(
            row=5, column=0, sticky="w", pady=5
        )
        priority_box = ttk.Combobox(
            container,
            textvariable=self.priority_var,
            values=["Tinggi", "Sedang", "Rendah"],
            state="readonly",
            width=39
        )
        priority_box.grid(row=5, column=1, sticky="ew", pady=5)

        current_row = 6

        # 5. Status (Khusus Edit)
        if self.is_edit:
            ttk.Label(container, text="Status").grid(
                row=current_row, column=0, sticky="w", pady=5
            )
            status_box = ttk.Combobox(
                container,
                textvariable=self.status_var,
                values=[STATUS_ACTIVE, STATUS_COMPLETED],
                state="readonly",
                width=39
            )
            status_box.grid(row=current_row, column=1, sticky="ew", pady=5)
            current_row += 1

        # Action Buttons
        button_row = ttk.Frame(container)
        button_row.grid(row=current_row, column=0, columnspan=2, sticky="ew", pady=(20, 0))

        if self.is_edit:
            # Tombol aksi sebelah kiri khusus pop up edit: Hapus & Tugas Selesai
            left_buttons = ttk.Frame(button_row)
            left_buttons.pack(side="left")

            ttk.Button(
                left_buttons,
                text="Hapus",
                style="Danger.TButton",
                command=self._confirm_delete
            ).pack(side="left", padx=(0, 8))

            complete_button_text = (
                "Batal Selesai"
                if self.task.get("status") == STATUS_COMPLETED
                else "✓ Tugas Selesai"
            )
            ttk.Button(
                left_buttons,
                text=complete_button_text,
                style="Success.TButton",
                command=self._toggle_complete_action
            ).pack(side="left")

        # Tombol aksi sebelah kanan: Simpan dan Batal
        right_buttons = ttk.Frame(button_row)
        right_buttons.pack(side="right")

        ttk.Button(
            right_buttons, text="Batal", style="Secondary.TButton",
            command=self.destroy
        ).pack(side="right", padx=(8, 0))

        ttk.Button(
            right_buttons, text="Simpan", style="Accent.TButton",
            command=self._save
        ).pack(side="right")

        container.columnconfigure(1, weight=1)

    def _center_window(self):
        self.update_idletasks()
        width = max(self.winfo_reqwidth(), 540)
        height = self.winfo_reqheight()
        x = self.parent.winfo_rootx() + (self.parent.winfo_width() - width) // 2
        y = self.parent.winfo_rooty() + (self.parent.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")

    def _validate_inputs(self):
        title = self.title_var.get().strip()
        description = self.description_text.get("1.0", "end").strip()
        deadline = self.deadline_var.get().strip()
        priority = self.priority_var.get().strip()

        if not title:
            messagebox.showerror("Input belum lengkap", "Nama tugas wajib diisi.", parent=self)
            return None

        try:
            parse_deadline(deadline)
        except ValueError:
            messagebox.showerror(
                "Format deadline salah",
                "Gunakan format YYYY-MM-DD HH:MM.\nContoh: 2026-11-10 20:00",
                parent=self
            )
            return None

        if priority not in VALID_PRIORITIES:
            messagebox.showerror("Prioritas tidak valid", "Pilih prioritas yang tersedia.", parent=self)
            return None

        status = self.status_var.get().strip() if self.is_edit else STATUS_ACTIVE

        return {
            "title": title,
            "description": description,
            "deadline": deadline,
            "priority": priority,
            "status": status,
        }

    def _save(self):
        validated = self._validate_inputs()
        if not validated:
            return

        self.result = validated
        self.action = "save"
        self.destroy()

    def _confirm_delete(self):
        """Fitur hapus di dalam pop up mengedit tugas."""
        task_title = self.task.get("title", "") if self.task else ""
        confirm = messagebox.askyesno(
            "Konfirmasi Hapus Tugas",
            f'Yakin ingin menghapus tugas "{task_title}"?',
            parent=self
        )
        if confirm:
            self.action = "delete"
            self.destroy()

    def _toggle_complete_action(self):
        """Fitur tugas selesai di dalam pop up mengedit tugas."""
        validated = self._validate_inputs()
        if not validated:
            return

        # Balik status tugas
        current_status = self.task.get("status", STATUS_ACTIVE)
        new_status = (
            STATUS_ACTIVE
            if current_status == STATUS_COMPLETED
            else STATUS_COMPLETED
        )
        validated["status"] = new_status

        self.result = validated
        self.action = "toggle_complete"
        self.destroy()


# ============================================================
# APLIKASI UTAMA
# ============================================================

class SmartTodoApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1120x720")
        self.root.minsize(900, 600)
        self.root.configure(bg="#F4F7FB")

        try:
            self.tasks = load_tasks()
        except StorageError as error:
            messagebox.showwarning(
                "Data tidak dapat dibaca",
                f"File tasks.json tidak dapat dibaca:\n{error}\n\n"
                "Aplikasi akan dibuka dengan daftar tugas kosong.",
                parent=self.root
            )
            self.tasks = []

        self.search_var = tk.StringVar()
        self.filter_var = tk.StringVar(value="Semua")
        self.status_var = tk.StringVar(value="Siap digunakan")
        self._reminder_popup_open = False

        self._configure_styles()
        self._build_layout()
        self.refresh_tasks()
        self.root.after(1500, self.check_reminders)

    def _configure_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "TFrame", background="#F4F7FB"
        )
        style.configure(
            "TLabel", background="#F4F7FB", foreground="#243247",
            font=("Segoe UI", 9)
        )
        style.configure(
            "Title.TLabel", background="#F4F7FB", foreground="#14243A",
            font=("Segoe UI", 23, "bold")
        )
        style.configure(
            "Subtitle.TLabel", background="#F4F7FB", foreground="#66758A",
            font=("Segoe UI", 9)
        )
        style.configure(
            "Section.TLabel", background="#F4F7FB", foreground="#14243A",
            font=("Segoe UI", 12, "bold")
        )
        style.configure(
            "DialogTitle.TLabel", background="#F4F7FB", foreground="#14243A",
            font=("Segoe UI", 15, "bold")
        )
        style.configure(
            "Hint.TLabel", background="#F4F7FB", foreground="#738197",
            font=("Segoe UI", 8)
        )
        style.configure(
            "Accent.TButton", background="#2563A6", foreground="white",
            font=("Segoe UI", 9, "bold"), padding=(13, 8), borderwidth=0
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#1D4F86"), ("pressed", "#173E6B")]
        )
        style.configure(
            "Secondary.TButton", background="#E5ECF4", foreground="#243247",
            font=("Segoe UI", 9, "bold"), padding=(11, 8), borderwidth=0
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#D5E0EC")]
        )
        style.configure(
            "Danger.TButton", background="#C44747", foreground="white",
            font=("Segoe UI", 9, "bold"), padding=(11, 8), borderwidth=0
        )
        style.map(
            "Danger.TButton",
            background=[("active", "#A63535"), ("pressed", "#8B2626")]
        )
        style.configure(
            "Success.TButton", background="#27845B", foreground="white",
            font=("Segoe UI", 9, "bold"), padding=(11, 8), borderwidth=0
        )
        style.map(
            "Success.TButton",
            background=[("active", "#1E6847"), ("pressed", "#165036")]
        )
        style.configure(
            "Treeview",
            background="white",
            fieldbackground="white",
            foreground="#243247",
            rowheight=34,
            font=("Segoe UI", 9),
            borderwidth=0
        )
        style.configure(
            "Treeview.Heading",
            background="#EAF0F7",
            foreground="#243247",
            font=("Segoe UI", 9, "bold"),
            padding=(8, 9),
            relief="flat"
        )
        style.map(
            "Treeview",
            background=[("selected", "#DCEBFA")],
            foreground=[("selected", "#14243A")]
        )
        style.configure(
            "TCombobox", padding=6, fieldbackground="white"
        )

    def _build_layout(self):
        # Header
        header = tk.Frame(self.root, bg="#14243A", height=116)
        header.pack(fill="x")
        header.pack_propagate(False)

        header_inner = tk.Frame(header, bg="#14243A")
        header_inner.pack(fill="both", expand=True, padx=30, pady=20)

        left_header = tk.Frame(header_inner, bg="#14243A")
        left_header.pack(side="left", fill="y")

        tk.Label(
            left_header, text="PERSONAL PRODUCTIVITY  /  PYTHON PROJECT",
            bg="#14243A", fg="#F2B84B",
            font=("Segoe UI", 8, "bold")
        ).pack(anchor="w")
        tk.Label(
            left_header, text="Smart To-Do",
            bg="#14243A", fg="white",
            font=("Segoe UI", 24, "bold")
        ).pack(anchor="w", pady=(3, 0))
        tk.Label(
            left_header, text="Atur tugas. Jaga deadline. Fokus pada hal penting.",
            bg="#14243A", fg="#D5E0EC",
            font=("Segoe UI", 9)
        ).pack(anchor="w")

        tk.Label(
            header_inner,
            text=datetime.now().strftime("%A, %d %B %Y"),
            bg="#14243A", fg="#D5E0EC",
            font=("Segoe UI", 9)
        ).pack(side="right", anchor="s", pady=8)

        # Main content
        content = ttk.Frame(self.root, padding=(28, 22, 28, 12))
        content.pack(fill="both", expand=True)

        # Summary cards
        cards = ttk.Frame(content)
        cards.pack(fill="x", pady=(0, 18))

        self.total_value = self._create_stat_card(cards, "TOTAL TUGAS", "0", "#2563A6")
        self.active_value = self._create_stat_card(cards, "BELUM SELESAI", "0", "#C18419")
        self.overdue_value = self._create_stat_card(cards, "TERLAMBAT", "0", "#C44747")
        self.completed_value = self._create_stat_card(cards, "SELESAI", "0", "#27845B")

        # Section heading and action buttons
        top_row = ttk.Frame(content)
        top_row.pack(fill="x", pady=(0, 10))

        ttk.Label(top_row, text="Daftar Tugas", style="Section.TLabel").pack(side="left")
        ttk.Button(
            top_row, text="+ Tambah Tugas", style="Accent.TButton",
            command=self.add_task
        ).pack(side="right")

        # Search and filter
        tools = ttk.Frame(content)
        tools.pack(fill="x", pady=(0, 10))

        search_entry = ttk.Entry(tools, textvariable=self.search_var, width=34)
        search_entry.pack(side="left", ipady=5)
        search_entry.insert(0, "")
        search_entry.bind("<KeyRelease>", lambda _event: self.refresh_tasks())

        ttk.Label(tools, text="  Filter:").pack(side="left", padx=(10, 4))
        filter_box = ttk.Combobox(
            tools, textvariable=self.filter_var,
            values=["Semua", "Belum Selesai", "Selesai", "Terlambat"],
            state="readonly", width=17
        )
        filter_box.pack(side="left", ipady=3)
        filter_box.bind("<<ComboboxSelected>>", lambda _event: self.refresh_tasks())

        # Tombol Urutkan Urgensi (Menyortir prioritas tertinggi ke prioritas terendah)
        ttk.Button(
            tools, text="Urutkan Urgensi", style="Secondary.TButton",
            command=self.sort_tasks_by_urgency
        ).pack(side="right")

        # Table
        table_frame = ttk.Frame(content)
        table_frame.pack(fill="both", expand=True)

        columns = ("title", "deadline", "priority", "status")
        self.tree = ttk.Treeview(
            table_frame, columns=columns, show="headings",
            selectmode="browse"
        )
        self.tree.heading("title", text="NAMA TUGAS")
        self.tree.heading("deadline", text="DEADLINE")
        self.tree.heading(
            "priority",
            text="PRIORITAS",
            command=self.sort_tasks_by_urgency
        )
        self.tree.heading("status", text="STATUS")

        self.tree.column("title", width=420, minwidth=220, anchor="w")
        self.tree.column("deadline", width=180, minwidth=150, anchor="center")
        self.tree.column("priority", width=120, minwidth=100, anchor="center")
        self.tree.column("status", width=150, minwidth=120, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.tag_configure("overdue", foreground="#B42318", background="#FFF1F0")
        self.tree.tag_configure("soon", foreground="#9A6700", background="#FFF8E6")
        self.tree.tag_configure("completed", foreground="#66758A")
        self.tree.tag_configure("normal", foreground="#243247", background="white")

        self.tree.bind("<Double-1>", lambda _event: self.edit_task())
        self.tree.bind("<Return>", lambda _event: self.edit_task())

        # Bottom action bar
        actions = ttk.Frame(content)
        actions.pack(fill="x", pady=(12, 0))

        ttk.Button(
            actions, text="Edit", style="Secondary.TButton",
            command=self.edit_task
        ).pack(side="left", padx=(0, 7))
        ttk.Button(
            actions, text="Hapus", style="Secondary.TButton",
            command=self.remove_task
        ).pack(side="left", padx=(0, 7))
        ttk.Button(
            actions, text="Tandai Selesai / Aktif", style="Secondary.TButton",
            command=self.mark_complete
        ).pack(side="left")

        ttk.Button(
            actions, text="✦ Focus Mode", style="Accent.TButton",
            command=self.show_focus_mode
        ).pack(side="right")

        # Footer status
        footer = tk.Frame(self.root, bg="#EAF0F7", height=30)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        tk.Label(
            footer, textvariable=self.status_var,
            bg="#EAF0F7", fg="#66758A",
            font=("Segoe UI", 8)
        ).pack(side="left", padx=28, pady=6)
        tk.Label(
            footer, text="LOCAL JSON STORAGE  •  NO DATABASE SERVER",
            bg="#EAF0F7", fg="#66758A",
            font=("Segoe UI", 8, "bold")
        ).pack(side="right", padx=28, pady=6)

    def _create_stat_card(self, parent, label, value, accent):
        card = tk.Frame(parent, bg="white", highlightbackground="#E1E8F0", highlightthickness=1)
        card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        tk.Frame(card, bg=accent, height=4).pack(fill="x")
        body = tk.Frame(card, bg="white")
        body.pack(fill="both", expand=True, padx=14, pady=10)
        tk.Label(
            body, text=label, bg="white", fg="#738197",
            font=("Segoe UI", 8, "bold")
        ).pack(anchor="w")
        value_label = tk.Label(
            body, text=value, bg="white", fg="#14243A",
            font=("Segoe UI", 21, "bold")
        )
        value_label.pack(anchor="w", pady=(2, 0))
        return value_label

    def _save_and_refresh(self, status_message="Perubahan berhasil disimpan."):
        try:
            save_tasks(self.tasks)
        except (StorageError, OSError, TypeError) as error:
            messagebox.showerror(
                "Gagal menyimpan",
                f"Data tidak dapat disimpan.\nDetail: {error}",
                parent=self.root
            )
            return
        self.refresh_tasks()
        self.status_var.set(status_message)

    def _selected_task(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo(
                "Pilih tugas",
                "Pilih salah satu tugas terlebih dahulu.",
                parent=self.root
            )
            return None
        task_id = selection[0]
        return find_task(self.tasks, task_id)

    def add_task(self):
        dialog = TaskDialog(self.root, title="Tambah Tugas")
        self.root.wait_window(dialog)
        if dialog.action == "save" and dialog.result:
            add_task(
                self.tasks,
                dialog.result["title"],
                dialog.result["description"],
                dialog.result["deadline"],
                dialog.result["priority"],
            )
            self._save_and_refresh("Tugas baru berhasil ditambahkan.")

    def edit_task(self):
        task = self._selected_task()
        if task is None:
            return

        dialog = TaskDialog(self.root, title="Edit Tugas", task=task)
        self.root.wait_window(dialog)

        # 1. Fitur hapus dari dalam pop up edit tugas
        if dialog.action == "delete":
            delete_task(self.tasks, task["id"])
            self._save_and_refresh(f'Tugas "{task.get("title", "")}" berhasil dihapus.')

        # 2. Fitur tugas selesai / toggle selesai dari dalam pop up edit tugas
        elif dialog.action == "toggle_complete" and dialog.result:
            update_task(
                self.tasks,
                task["id"],
                dialog.result["title"],
                dialog.result["description"],
                dialog.result["deadline"],
                dialog.result["priority"],
            )
            task["status"] = dialog.result["status"]
            if task["status"] == STATUS_ACTIVE:
                task["reminded"] = False
            status_text = "selesai" if task["status"] == STATUS_COMPLETED else "belum selesai"
            self._save_and_refresh(f"Tugas berhasil ditandai {status_text}.")

        # 3. Simpan perubahan biasa
        elif dialog.action == "save" and dialog.result:
            update_task(
                self.tasks,
                task["id"],
                dialog.result["title"],
                dialog.result["description"],
                dialog.result["deadline"],
                dialog.result["priority"],
            )
            if "status" in dialog.result and dialog.result["status"] != task.get("status"):
                task["status"] = dialog.result["status"]
                if task["status"] == STATUS_ACTIVE:
                    task["reminded"] = False
            self._save_and_refresh("Tugas berhasil diperbarui.")

    def remove_task(self):
        task = self._selected_task()
        if task is None:
            return
        confirm = messagebox.askyesno(
            "Hapus tugas",
            f'Yakin ingin menghapus tugas "{task.get("title", "")}"?',
            parent=self.root
        )
        if confirm:
            delete_task(self.tasks, task["id"])
            self._save_and_refresh("Tugas berhasil dihapus.")

    def mark_complete(self):
        task = self._selected_task()
        if task is None:
            return
        toggle_complete(self.tasks, task["id"])
        status_text = "selesai" if task.get("status") == STATUS_COMPLETED else "belum selesai"
        self._save_and_refresh(f"Status tugas diubah menjadi {status_text}.")

    def sort_tasks_by_urgency(self):
        """Fitur urut urgensi yang menyortir prioritas tertinggi ke terendah."""
        self.tasks = sort_by_urgency(self.tasks)
        self._save_and_refresh("Tugas berhasil diurutkan berdasarkan prioritas tertinggi ke terendah.")

    def show_focus_mode(self):
        task = suggest_next_task(self.tasks)
        if task is None:
            messagebox.showinfo(
                "Focus Mode",
                "Belum ada tugas aktif. Semua tugas sudah selesai atau daftar masih kosong.",
                parent=self.root
            )
            return

        reason = get_focus_reason(task)
        overdue_text = "\nSTATUS   : TERLAMBAT" if is_overdue(task) else ""
        messagebox.showinfo(
            "✦ Focus Mode — Rekomendasi Tugas",
            f"Tugas yang paling direkomendasikan:\n\n"
            f"• {task.get('title', '-')}\n\n"
            f"Alasan   : {reason}\n"
            f"Prioritas: {task.get('priority', '-')}\n"
            f"Deadline : {task.get('deadline', '-')}"
            f"{overdue_text}\n\n"
            f"Deskripsi: {task.get('description') or '-'}",
            parent=self.root
        )

    def refresh_tasks(self):
        # Bersihkan tabel.
        for item in self.tree.get_children():
            self.tree.delete(item)

        now = datetime.now()
        query = self.search_var.get().strip().lower()
        selected_filter = self.filter_var.get()

        visible_tasks = sort_by_urgency(self.tasks)

        for task in visible_tasks:
            title = str(task.get("title", "Tanpa judul"))
            description = str(task.get("description", ""))
            searchable = f"{title} {description}".lower()
            if query and query not in searchable:
                continue

            completed = task.get("status") == STATUS_COMPLETED
            overdue = is_overdue(task, now)

            if selected_filter == "Belum Selesai" and completed:
                continue
            if selected_filter == "Selesai" and not completed:
                continue
            if selected_filter == "Terlambat" and not overdue:
                continue

            try:
                deadline_dt = parse_deadline(task.get("deadline", ""))
                deadline_text = deadline_dt.strftime("%d-%m-%Y %H:%M")
                minutes_left = (deadline_dt - now).total_seconds() / 60
            except (TypeError, ValueError):
                deadline_text = "Deadline tidak valid"
                minutes_left = None

            if completed:
                status_text = "Selesai"
                tag = "completed"
            elif overdue:
                status_text = "Terlambat"
                tag = "overdue"
            elif minutes_left is not None and 0 <= minutes_left <= REMINDER_MINUTES:
                status_text = "Segera Deadline"
                tag = "soon"
            else:
                status_text = "Belum Selesai"
                tag = "normal"

            priority = task.get("priority", "Rendah")
            self.tree.insert(
                "", "end",
                iid=str(task.get("id")),
                values=(title, deadline_text, priority, status_text),
                tags=(tag,)
            )

        total = len(self.tasks)
        completed_count = sum(1 for task in self.tasks if task.get("status") == STATUS_COMPLETED)
        active_count = total - completed_count
        overdue_count = sum(1 for task in self.tasks if is_overdue(task, now))

        self.total_value.config(text=str(total))
        self.active_value.config(text=str(active_count))
        self.overdue_value.config(text=str(overdue_count))
        self.completed_value.config(text=str(completed_count))

    def check_reminders(self):
        """Cek deadline secara berkala dan tampilkan popup satu kali per tugas."""
        if not self._reminder_popup_open:
            now = datetime.now()
            upcoming = get_upcoming_reminders(
                self.tasks, now=now, within_minutes=REMINDER_MINUTES
            )

            if upcoming:
                # Tandai reminder yang akan ditampilkan agar tidak berulang.
                for task, _minutes in upcoming:
                    task["reminded"] = True
                try:
                    save_tasks(self.tasks)
                except (StorageError, OSError):
                    pass

                self._reminder_popup_open = True
                self.refresh_tasks()

                reminder_lines = []
                for task, minutes in upcoming:
                    reminder_lines.append(
                        f"• {task.get('title', 'Tanpa judul')} "
                        f"(deadline {task.get('deadline', '-')}, sekitar {minutes} menit lagi)"
                    )

                messagebox.showwarning(
                    "Pengingat Deadline",
                    "Ada tugas yang deadline-nya segera tiba:\n\n"
                    + "\n".join(reminder_lines),
                    parent=self.root
                )
                self._reminder_popup_open = False

        self.root.after(CHECK_REMINDER_EVERY_MS, self.check_reminders)


def main():
    root = tk.Tk()
    app = SmartTodoApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
