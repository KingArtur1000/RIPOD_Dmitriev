import tkinter as tk
from tkinter import ttk, messagebox
import networkx as nx
import threading
import time
import random
import queue

# ---------- Светлая цветовая схема ----------
BG_MAIN   = "#f4f6f9"
BG_PANEL  = "#ffffff"
FG_MAIN   = "#212529"
FG_MUTED  = "#6c757d"
ACCENT    = "#0d6efd"
BORDER    = "#dee2e6"
COLORS    = ["#0d6efd", "#198754", "#dc3545", "#ffc107", "#0dcaf0", "#6f42c1", "#d63384", "#fd7e14"]

class Lab7App:
    def __init__(self, root):
        self.root = root
        root.title("Лабораторная 7: Многопоточное выполнение планов")
        self._center(1450, 850)
        root.minsize(1100, 700)
        root.configure(bg=BG_MAIN)

        self.G = nx.DiGraph()
        self.default_edges = "1-2, 1-3, 2-4, 3-4, 4-5"
        
        self.is_running = False
        self.t_start = 0
        self.start_times = {}
        self.end_times = {}
        self.task_procs = {}
        
        # Очередь для безопасного логирования из потоков
        self.log_queue = queue.Queue()
        
        self._build_style()
        self._build_ui()
        
        # Запускаем цикл обработки очереди логов
        self.root.after(100, self.process_log_queue)

    def _center(self, w, h):
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _build_style(self):
        s = ttk.Style()
        try: s.theme_use("clam")
        except tk.TclError: pass
        
        s.configure(".", background=BG_PANEL, foreground=FG_MAIN, fieldbackground=BG_MAIN)
        s.configure("TFrame", background=BG_PANEL)
        s.configure("Main.TFrame", background=BG_MAIN)
        s.configure("TLabel", background=BG_PANEL, foreground=FG_MAIN, font=("Segoe UI", 10))
        s.configure("Title.TLabel", font=("Segoe UI", 14, "bold"), foreground=ACCENT)
        s.configure("Sub.TLabel", font=("Segoe UI", 9), foreground=FG_MUTED)
        
        s.configure("TButton", font=("Segoe UI", 10, "bold"), background=ACCENT, foreground="white", borderwidth=0, padding=6)
        s.map("TButton", background=[("active", "#0b5ed7")])
        
        s.configure("TLabelframe", background=BG_PANEL, foreground=FG_MAIN, bordercolor=BORDER)
        s.configure("TLabelframe.Label", background=BG_PANEL, foreground=FG_MAIN, font=("Segoe UI", 10, "bold"))

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=15, style="Main.TFrame")
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=0, minsize=350)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        left = ttk.Frame(main, padding=15)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        
        right = ttk.Frame(main, style="Main.TFrame")
        right.grid(row=0, column=1, sticky="nsew")
        
        self._build_controls(left)
        self._build_visualizer(right)

    def _build_controls(self, parent):
        ttk.Label(parent, text="Многопоточность", style="Title.TLabel").pack(anchor="w")
        ttk.Label(parent, text="Синхронный и Асинхронный планы", style="Sub.TLabel").pack(anchor="w", pady=(0, 10))

        input_frame = ttk.LabelFrame(parent, text=" Входные данные (A-B) ", padding=10)
        input_frame.pack(fill="x", pady=5)
        
        self.edges_entry = tk.Text(input_frame, height=4, width=30, font=("Consolas", 10), 
                                   bg=BG_MAIN, fg=FG_MAIN, relief="solid", bd=1, 
                                   highlightthickness=1, highlightbackground=BORDER)
        self.edges_entry.pack(fill="x")
        self.edges_entry.insert("1.0", self.default_edges)
        
        self.context_menu = tk.Menu(self.edges_entry, tearoff=0)
        self.context_menu.add_command(label="Вставить", command=lambda: self.edges_entry.event_generate("<<Paste>>"))
        def show_ctx(event): self.context_menu.post(event.x_root, event.y_root)
        self.edges_entry.bind("<Button-3>", show_ctx)
        self.edges_entry.bind("<Control-v>", lambda e: self.edges_entry.event_generate("<<Paste>>"))

        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        ttk.Button(btn_frame, text="📋 Вставить", command=self.paste_from_clipboard).pack(side="left", padx=(0, 5))
        
        run_frame = ttk.Frame(parent)
        run_frame.pack(fill="x", pady=10)
        
        self.btn_sync = ttk.Button(run_frame, text="▶ Синхронный (ASAP)", command=lambda: self.run_plan("SYNC"))
        self.btn_sync.pack(fill="x", pady=2)
        
        self.btn_async = ttk.Button(run_frame, text="▶ Асинхронный (Граф)", command=lambda: self.run_plan("ASYNC"))
        self.btn_async.pack(fill="x", pady=2)

        log_frame = ttk.LabelFrame(parent, text=" Журнал выполнения ", padding=10)
        log_frame.pack(fill="both", expand=True, pady=(10, 0))
        
        self.log_text = tk.Text(log_frame, height=10, bg=BG_MAIN, fg=FG_MAIN, bd=1, 
                                 relief="solid", font=("Consolas", 9), wrap="word", 
                                 padx=8, pady=8, highlightthickness=1, highlightbackground=BORDER)
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")

    def _build_visualizer(self, parent):
        viz_frame = ttk.LabelFrame(parent, text=" Временная диаграмма (Реальное время) ", padding=5)
        viz_frame.pack(fill="both", expand=True)
        
        self.canvas = tk.Canvas(viz_frame, bg="#ffffff", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

    def paste_from_clipboard(self):
        try:
            text = self.root.clipboard_get()
            self.edges_entry.delete("1.0", "end")
            self.edges_entry.insert("1.0", text)
        except tk.TclError:
            pass

    # --- БЕЗОПАСНОЕ ЛОГИРОВАНИЕ ---
    def log(self, msg):
        """Кладет сообщение в очередь (можно вызывать из любого потока)"""
        self.log_queue.put(msg)

    def process_log_queue(self):
        """Забирает сообщения из очереди и обновляет GUI (только главный поток)"""
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.configure(state="normal")
                self.log_text.insert("end", msg + "\n")
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(100, self.process_log_queue)

    def run_plan(self, mode):
        if self.is_running:
            messagebox.showwarning("Внимание", "Планировщик уже запущен!")
            return

        self.G.clear()
        text = self.edges_entry.get("1.0", "end-1c").replace("\n", ",").replace(" ", "")
        edges = []
        for pair in text.split(","):
            if not pair: continue
            try:
                u, v = pair.split("-")
                edges.append((u.strip(), v.strip()))
            except ValueError:
                pass
        
        if not edges:
            return

        self.G.add_edges_from(edges)
        if not nx.is_directed_acyclic_graph(self.G):
            messagebox.showerror("Ошибка", "Граф содержит циклы!")
            return

        self.is_running = True
        self.t_start = time.time()
        self.start_times.clear()
        self.end_times.clear()
        
        # Очистка лога
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        
        self.log(f"--- Запуск {mode} плана ---")

        # Назначаем условные процессоры для визуализации (0..3)
        for i, node in enumerate(self.G.nodes()):
            self.task_procs[node] = i % 4 

        if mode == "SYNC":
            threading.Thread(target=self.execute_sync, daemon=True).start()
        else:
            threading.Thread(target=self.execute_async, daemon=True).start()

        self.update_ui()

    def execute_sync(self):
        levels = {}
        for node in nx.topological_sort(self.G):
            preds = list(self.G.predecessors(node))
            levels[node] = max([levels[pr] for pr in preds]) + 1 if preds else 0

        grouped = {}
        for n, lvl in levels.items():
            grouped.setdefault(lvl, []).append(n)

        for lvl in sorted(grouped.keys()):
            tasks = grouped[lvl]
            barrier = threading.Barrier(len(tasks))
            threads = []

            def worker(task):
                time.sleep(random.uniform(0.5, 1.5))
                self.end_times[task] = time.time() - self.t_start
                self.log(f"[SYNC] Задача {task} (Шаг {lvl}) завершена.")
                barrier.wait()

            for task in tasks:
                self.start_times[task] = time.time() - self.t_start
                t = threading.Thread(target=worker, args=(task,), daemon=True)
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

        self.is_running = False
        self.log(f"--- SYNC План завершен. Время: {time.time() - self.t_start:.2f}с ---")

    def execute_async(self):
        self.events = {n: threading.Event() for n in self.G.nodes()}
        threads = []

        def worker(task):
            for pred in self.G.predecessors(task):
                self.events[pred].wait()
            
            self.start_times[task] = time.time() - self.t_start
            time.sleep(random.uniform(0.5, 1.5))
            self.end_times[task] = time.time() - self.t_start
            self.log(f"[ASYNC] Задача {task} завершена.")
            self.events[task].set()

        for node in self.G.nodes():
            t = threading.Thread(target=worker, args=(node,), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.is_running = False
        self.log(f"--- ASYNC План завершен. Время: {time.time() - self.t_start:.2f}с ---")

    def update_ui(self):
        self.canvas.delete("all")
        
        # Безопасное вычисление времени
        if self.is_running:
            elapsed = time.time() - self.t_start
            max_time = max([elapsed] + list(self.end_times.values()) if self.end_times else [elapsed])
        else:
            max_time = max(self.end_times.values()) if self.end_times else 1
            
        max_time = max(max_time, 1.0)

        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        
        # Если окно еще не отрисовано, просто ждем
        if w > 50 and h > 50:
            time_scale = (w - 150) / max_time

            for i in range(int(max_time) + 2):
                x = 100 + i * time_scale
                self.canvas.create_line(x, 30, x, h-30, fill="#dee2e6", dash=(4, 4))
                self.canvas.create_text(x, 15, text=f"{i}s", fill=FG_MUTED, font=("Segoe UI", 9))

            y_offset = 50
            line_height = 50
            
            for task in self.G.nodes():
                if task not in self.start_times: continue
                
                st = self.start_times[task]
                # Если задача завершена, берем её точное время, иначе — текущее
                et = self.end_times.get(task, time.time() - self.t_start if self.is_running else st)
                dur = max(0.1, et - st)
                
                proc = self.task_procs[task]
                y = y_offset + proc * line_height
                
                x1 = 100 + st * time_scale
                x2 = 100 + et * time_scale
                
                color = COLORS[proc % len(COLORS)]
                
                self.canvas.create_rectangle(x1+2, y+2, x2+2, y+30, fill="#e9ecef", outline="")
                self.canvas.create_rectangle(x1, y, x2, y+30, fill=color, outline="white", width=2)
                self.canvas.create_text((x1+x2)/2, y+15, text=f"Оп. {task}", fill="white", font=("Segoe UI", 9, "bold"))
                
            for i in range(4):
                self.canvas.create_text(50, 50 + i * line_height + 15, text=f"Поток {i}", fill=FG_MAIN, font=("Segoe UI", 9))

        self.root.after(50, self.update_ui)

if __name__ == "__main__":
    root = tk.Tk()
    app = Lab7App(root)
    root.mainloop()