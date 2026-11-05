import tkinter as tk
from tkinter import ttk, messagebox
import networkx as nx
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import random

# ---------- Светлая цветовая схема ----------
BG_MAIN   = "#f4f6f9"
BG_PANEL  = "#ffffff"
FG_MAIN   = "#212529"
FG_MUTED  = "#6c757d"
ACCENT    = "#0d6efd"
BORDER    = "#dee2e6"
GRAPH_BG  = "#ffffff"

class EdgeZeroingApp:
    def __init__(self, root):
        self.root = root
        root.title("Лабораторная 6: Стратегия «Зануление дуг» (Edge Zeroing)")
        self._center(1500, 950)
        root.minsize(1150, 750)
        root.configure(bg=BG_MAIN)

        self.G = nx.DiGraph()
        self.durations = {}
        self.default_edges = "1:2, 2:2, 1-3:3, 2-4:3, 3-5:3, 4-5:3, 5-6:3, 6-7:3, 7-8:3, 8-9:3"
        
        self.processors = tk.IntVar(value=3)
        self.comm_cost = tk.IntVar(value=2)
        
        self.gen_nodes = tk.IntVar(value=9)
        self.gen_density = tk.DoubleVar(value=0.25)
        
        # Переменные для анимации EZ
        self.ez_history = []
        self.ez_anim_index = 0
        self.ez_anim_job = None

        self._build_style()
        self._build_ui()
        self.update_schedule()

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
        main.columnconfigure(0, weight=0, minsize=420)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        left = ttk.Frame(main, padding=15)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        
        right = ttk.Frame(main, style="Main.TFrame")
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        self._build_controls(left)
        
        graph_frame = ttk.LabelFrame(right, text=" Граф задач (с весами дуг и длительностями) ", padding=5)
        graph_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        self._build_graph_area(graph_frame)
        
        gantt_frame = ttk.LabelFrame(right, text=" Временная диаграмма ", padding=5)
        gantt_frame.grid(row=1, column=0, sticky="nsew")
        self._build_gantt_area(gantt_frame)

    def _build_controls(self, parent):
        ttk.Label(parent, text="Асинхронное планирование", style="Title.TLabel").pack(anchor="w")
        ttk.Label(parent, text="Стратегия Edge Zeroing", style="Sub.TLabel").pack(anchor="w", pady=(0, 10))

        cfg_frame = ttk.LabelFrame(parent, text=" Параметры системы ", padding=10)
        cfg_frame.pack(fill="x", pady=5)
        
        ttk.Label(cfg_frame, text="Количество процессоров (p):").pack(anchor="w")
        proc_frame = ttk.Frame(cfg_frame)
        proc_frame.pack(fill="x", pady=5)
        spin = ttk.Spinbox(proc_frame, from_=1, to=8, textvariable=self.processors, width=5, font=("Segoe UI", 11))
        spin.pack(side="left")
        spin.bind("<<Increment>>", lambda e: self.update_schedule())
        spin.bind("<<Decrement>>", lambda e: self.update_schedule())
        ttk.Button(proc_frame, text="Применить", command=self.update_schedule).pack(side="left", padx=10)

        input_frame = ttk.LabelFrame(parent, text=" Входные данные (A-B:вес или A:длит) ", padding=10)
        input_frame.pack(fill="x", pady=10)
        
        self.edges_entry = tk.Text(input_frame, height=4, width=30, font=("Consolas", 10), 
                                   bg=BG_MAIN, fg=FG_MAIN, relief="solid", bd=1, 
                                   highlightthickness=1, highlightbackground=BORDER)
        self.edges_entry.pack(fill="x")
        self.edges_entry.insert("1.0", self.default_edges)
        
        self.context_menu = tk.Menu(self.edges_entry, tearoff=0)
        self.context_menu.add_command(label="Вставить", command=lambda: self.edges_entry.event_generate("<<Paste>>"))
        self.context_menu.add_command(label="Очистить", command=lambda: self.edges_entry.delete("1.0", "end"))
        
        def show_ctx(event):
            self.context_menu.post(event.x_root, event.y_root)
        self.edges_entry.bind("<Button-3>", show_ctx)
        self.edges_entry.bind("<Control-v>", lambda e: self.edges_entry.event_generate("<<Paste>>"))
        self.edges_entry.bind("<Command-v>", lambda e: self.edges_entry.event_generate("<<Paste>>"))

        gen_frame = ttk.LabelFrame(parent, text=" Генератор случайного графа ", padding=10)
        gen_frame.pack(fill="x", pady=5)
        
        g_row1 = ttk.Frame(gen_frame)
        g_row1.pack(fill="x", pady=2)
        ttk.Label(g_row1, text="Кол-во операций (N):").pack(side="left")
        ttk.Spinbox(g_row1, from_=5, to=15, textvariable=self.gen_nodes, width=5).pack(side="right")
        
        g_row2 = ttk.Frame(gen_frame)
        g_row2.pack(fill="x", pady=2)
        ttk.Label(g_row2, text="Плотность связей:").pack(side="left")
        ttk.Spinbox(g_row2, from_=0.1, to=0.6, increment=0.05, textvariable=self.gen_density, width=5).pack(side="right")

        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        ttk.Button(btn_frame, text="📋 Вставить", command=self.paste_from_clipboard).pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="🎲 Сгенерировать", command=self.generate_random_graph).pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="Построить (List Scheduling)", command=self.update_schedule).pack(side="left", fill="x", expand=True)
        
        # --- Блок EZ и Анимации ---
        ez_frame = ttk.LabelFrame(parent, text=" Оптимизация (Edge Zeroing) ", padding=10)
        ez_frame.pack(fill="x", pady=5)
        
        self.btn_ez = ttk.Button(ez_frame, text="⚡ Рассчитать EZ", command=self.apply_ez)
        self.btn_ez.pack(fill="x", pady=2)
        
        ez_anim_frame = ttk.Frame(ez_frame)
        ez_anim_frame.pack(fill="x", pady=2)
        
        self.btn_ez_play = ttk.Button(ez_anim_frame, text="▶ Анимация EZ", command=self.toggle_ez_animation, state="disabled")
        self.btn_ez_play.pack(fill="x", pady=2)
        
        step_frame = ttk.Frame(ez_anim_frame)
        step_frame.pack(fill="x", pady=2)
        
        self.btn_ez_prev = ttk.Button(step_frame, text="⏮ Назад", command=self.prev_ez_step, state="disabled")
        self.btn_ez_prev.pack(side="left", fill="x", expand=True, padx=(0, 2))
        
        self.btn_ez_step = ttk.Button(step_frame, text="⏭ Шаг", command=self.next_ez_step, state="disabled")
        self.btn_ez_step.pack(side="right", fill="x", expand=True, padx=(2, 0))
        
        self.lbl_ez_step = ttk.Label(ez_frame, text="Шаг: 0 / 0", font=("Consolas", 9))
        self.lbl_ez_step.pack(anchor="e", pady=(2, 0))

        # Инфо
        info_frame = ttk.LabelFrame(parent, text=" Анализ EZ ", padding=10)
        info_frame.pack(fill="both", expand=True, pady=(5, 0))
        
        self.info_text = tk.Text(info_frame, height=6, bg=BG_MAIN, fg=FG_MAIN, bd=1, 
                                 relief="solid", font=("Consolas", 9), wrap="word", 
                                 padx=8, pady=8, highlightthickness=1, highlightbackground=BORDER)
        self.info_text.pack(fill="both", expand=True)
        self.info_text.configure(state="disabled")

    def generate_random_graph(self):
        n = self.gen_nodes.get()
        density = self.gen_density.get()
        
        nodes = [str(i) for i in range(1, n + 1)]
        edges = set()
        durations = {}
        
        for node in nodes:
            if random.random() < 0.25:
                durations[node] = random.randint(2, 3)
            else:
                durations[node] = 1
        
        for i in range(n):
            for j in range(i + 1, n):
                if random.random() < density:
                    edges.add((nodes[i], nodes[j]))
                    
        for i in range(1, n):
            if not any(v == nodes[i] for u, v in edges) and not any(u == nodes[i] for u, v in edges):
                parent = nodes[random.randint(0, i-1)]
                edges.add((parent, nodes[i]))

        edge_strs = []
        for node, dur in durations.items():
            if dur > 1:
                edge_strs.append(f"{node}:{dur}")
                
        for u, v in edges:
            w = random.randint(1, 4)
            edge_strs.append(f"{u}-{v}:{w}")
                
        text = ", ".join(edge_strs)
        self.edges_entry.delete("1.0", "end")
        self.edges_entry.insert("1.0", text)
        self.update_schedule()

    def paste_from_clipboard(self):
        try:
            text = self.root.clipboard_get()
            self.edges_entry.delete("1.0", "end")
            self.edges_entry.insert("1.0", text)
            self.update_schedule()
        except tk.TclError:
            messagebox.showwarning("Буфер обмена", "Пусто!")

    def _build_graph_area(self, parent):
        self.fig_graph = Figure(figsize=(6, 3), dpi=100, facecolor=GRAPH_BG)
        self.ax_graph = self.fig_graph.add_subplot(111)
        self.ax_graph.set_facecolor(GRAPH_BG)
        self.canvas_graph = FigureCanvasTkAgg(self.fig_graph, master=parent)
        self.canvas_graph.get_tk_widget().pack(fill="both", expand=True)

    def _build_gantt_area(self, parent):
        self.fig_gantt = Figure(figsize=(6, 2.5), dpi=100, facecolor=GRAPH_BG)
        self.ax_gantt = self.fig_gantt.add_subplot(111)
        self.ax_gantt.set_facecolor(GRAPH_BG)
        self.canvas_gantt = FigureCanvasTkAgg(self.fig_gantt, master=parent)
        self.canvas_gantt.get_tk_widget().pack(fill="both", expand=True)

    def parse_edges(self):
        text = self.edges_entry.get("1.0", "end-1c")
        text = text.replace("\n", ",").replace(" ", "")
        self.G.clear()
        self.durations = {}
        
        for pair in text.split(","):
            if not pair: continue
            try:
                if "-" in pair:
                    if ":" in pair:
                        edge_part, comm = pair.split(":")
                        u, v = edge_part.split("-")
                        self.G.add_edge(u.strip(), v.strip(), comm=int(comm))
                    else:
                        u, v = pair.split("-")
                        self.G.add_edge(u.strip(), v.strip(), comm=self.comm_cost.get())
                elif ":" in pair:
                    u, dur = pair.split(":")
                    self.durations[u.strip()] = int(dur)
            except ValueError:
                pass
                
        for n in self.G.nodes():
            if n not in self.durations:
                self.durations[n] = 1
                
        return list(self.G.edges())

    def update_schedule(self):
        # Сброс анимации при построении нового графа
        self.ez_history = []
        self.ez_anim_index = 0
        if self.ez_anim_job:
            self.root.after_cancel(self.ez_anim_job)
            self.ez_anim_job = None
        
        self.btn_ez_play.configure(text="▶ Анимация EZ", state="disabled")
        self.btn_ez_step.configure(state="disabled")
        self.btn_ez_prev.configure(state="disabled")
        self.lbl_ez_step.configure(text="Шаг: 0 / 0")

        if not self.parse_edges(): return
        
        if not nx.is_directed_acyclic_graph(self.G):
            messagebox.showerror("Ошибка", "Граф содержит циклы!")
            return

        p = self.processors.get()
        self.assignment = self.list_scheduling(p)
        self.calculate_and_draw(p, "Исходный план (List Scheduling)")

    def list_scheduling(self, p):
        priorities = {}
        for node in reversed(list(nx.topological_sort(self.G))):
            succs = list(self.G.successors(node))
            w = self.durations.get(node, 1)
            priorities[node] = w if not succs else w + max(priorities[s] for s in succs)
            
        assignment = {}
        proc_free = [0] * p
        scheduled = set()
        
        while len(scheduled) < len(self.G.nodes()):
            ready = [n for n in self.G.nodes() if n not in scheduled and all(pr in scheduled for pr in self.G.predecessors(n))]
            if not ready: break
            ready.sort(key=lambda x: (-priorities[x], str(x)))
            
            free_procs = [i for i in range(p) if proc_free[i] <= min(proc_free)]
            for proc in free_procs:
                if not ready: break
                task = ready.pop(0)
                assignment[task] = proc
                
                preds = list(self.G.predecessors(task))
                max_end = 0
                for pr in preds:
                    c = 0 if assignment.get(pr) == proc else self.G[pr][task]['comm']
                    end = proc_free[assignment.get(pr, 0)] + c
                    max_end = max(max_end, end)
                
                st = max(proc_free[proc], max_end)
                proc_free[proc] = st + self.durations.get(task, 1)
                scheduled.add(task)
        return assignment

    def calculate_schedule(self, assignment):
        start_time = {}
        end_time = {}
        proc_free = {i: 0 for i in range(self.processors.get())}
        
        for node in nx.topological_sort(self.G):
            proc = assignment[node]
            preds = list(self.G.predecessors(node))
            
            ready_time = proc_free[proc]
            for pr in preds:
                comm_delay = 0 if assignment[pr] == proc else self.G[pr][node]['comm']
                ready_time = max(ready_time, end_time[pr] + comm_delay)
                
            st = ready_time
            dur = self.durations.get(node, 1)
            end_time[node] = st + dur
            start_time[node] = st
            proc_free[proc] = end_time[node]
            
        makespan = max(end_time.values()) if end_time else 0
        return start_time, end_time, makespan

    def apply_ez(self):
        """Запуск алгоритма EZ с сохранением истории шагов"""
        p = self.processors.get()
        improved = True
        
        current_assignment = self.assignment.copy()
        _, _, current_makespan = self.calculate_schedule(current_assignment)
        
        self.ez_history = []
        log_messages = []
        
        self.ez_history.append({
            "assignment": current_assignment.copy(),
            "makespan": current_makespan,
            "log": "Начальное состояние (до оптимизации)."
        })

        while improved:
            improved = False
            start_t, end_t, _ = self.calculate_schedule(current_assignment)
            
            sorted_tasks = sorted(end_t.keys(), key=lambda x: end_t[x], reverse=True)
            
            for task in sorted_tasks:
                preds = list(self.G.predecessors(task))
                
                for pred in preds:
                    pred_proc = current_assignment[pred]
                    task_proc = current_assignment[task]
                    
                    if pred_proc != task_proc:
                        old_proc = current_assignment[task]
                        current_assignment[task] = pred_proc
                        
                        _, _, new_makespan = self.calculate_schedule(current_assignment)
                        
                        if new_makespan < current_makespan:
                            log_messages.append(f"Задача {task} -> P{pred_proc} (занулена дуга {pred}->{task}). Время: {current_makespan} -> {new_makespan}")
                            current_makespan = new_makespan
                            
                            self.ez_history.append({
                                "assignment": current_assignment.copy(),
                                "makespan": current_makespan,
                                "log": "\n".join(log_messages)
                            })
                            
                            improved = True
                            break
                        else:
                            current_assignment[task] = old_proc
                            
                if improved:
                    break
                    
        if len(self.ez_history) > 1:
            self.ez_anim_index = 0
            self.btn_ez_play.configure(state="normal")
            self.show_ez_step()
        else:
            self.btn_ez_play.configure(state="disabled")
            self.btn_ez_step.configure(state="disabled")
            self.btn_ez_prev.configure(state="disabled")
            self.calculate_and_draw(p, "После Edge Zeroing", "Улучшений не найдено. Граф уже оптимален.")
            self.lbl_ez_step.configure(text="Шаг: 0 / 0")

    def show_ez_step(self):
        if not self.ez_history: return
        step_data = self.ez_history[self.ez_anim_index]
        self.assignment = step_data["assignment"]
        self.calculate_and_draw(self.processors.get(), f"Edge Zeroing (Шаг {self.ez_anim_index})", step_data["log"])
        self.lbl_ez_step.configure(text=f"Шаг: {self.ez_anim_index} / {len(self.ez_history)-1}")

        # Управление доступностью кнопок
        if self.ez_anim_index > 0:
            self.btn_ez_prev.configure(state="normal")
        else:
            self.btn_ez_prev.configure(state="disabled")

        if self.ez_anim_index < len(self.ez_history) - 1:
            self.btn_ez_step.configure(state="normal")
        else:
            self.btn_ez_step.configure(state="disabled")

    def stop_ez_animation(self):
        if self.ez_anim_job:
            self.root.after_cancel(self.ez_anim_job)
            self.ez_anim_job = None
            self.btn_ez_play.configure(text="▶ Анимация EZ")

    def next_ez_step(self):
        self.stop_ez_animation()
        if self.ez_anim_index < len(self.ez_history) - 1:
            self.ez_anim_index += 1
            self.show_ez_step()

    def prev_ez_step(self):
        self.stop_ez_animation()
        if self.ez_anim_index > 0:
            self.ez_anim_index -= 1
            self.show_ez_step()

    def toggle_ez_animation(self):
        if self.ez_anim_job:
            self.stop_ez_animation()
        else:
            if self.ez_anim_index >= len(self.ez_history) - 1:
                self.ez_anim_index = 0
                self.show_ez_step()
            
            self.btn_ez_play.configure(text="⏸ Пауза")
            self.animate_ez()

    def animate_ez(self):
        if self.ez_anim_index < len(self.ez_history) - 1:
            self.ez_anim_index += 1
            self.show_ez_step()
            self.ez_anim_job = self.root.after(1500, self.animate_ez)
        else:
            self.ez_anim_job = None
            self.btn_ez_play.configure(text="▶ Анимация EZ")

    def calculate_and_draw(self, p, mode_text, log_text=""):
        st, et, makespan = self.calculate_schedule(self.assignment)
        self.draw_graph()
        self.draw_gantt(st, et, p)
        self.update_info(p, makespan, mode_text, log_text)

    def draw_graph(self):
        self.ax_graph.clear()
        levels = {}
        for node in nx.topological_sort(self.G):
            preds = list(self.G.predecessors(node))
            levels[node] = max([levels[pr] for pr in preds]) + 1 if preds else 0
            
        pos = {}
        nodes_by_level = {}
        for node, lvl in levels.items():
            nodes_by_level.setdefault(lvl, []).append(node)
        for lvl, nodes in nodes_by_level.items():
            try: nodes.sort(key=lambda x: int(x) if str(x).isdigit() else str(x))
            except: nodes.sort()
            count = len(nodes)
            for i, node in enumerate(nodes):
                pos[node] = (lvl, (i - (count - 1) / 2.0) * -1.5)

        cmap = matplotlib.colormaps["tab10"]
        colors = [cmap(self.assignment[n] % 10) for n in self.G.nodes()]
        
        nx.draw_networkx_edges(self.G, pos, ax=self.ax_graph, edge_color="#adb5bd", width=2, arrowsize=15, connectionstyle="arc3,rad=0.1")
        edge_labels = {(u, v): self.G[u][v]['comm'] for u, v in self.G.edges()}
        nx.draw_networkx_edge_labels(self.G, pos, edge_labels=edge_labels, ax=self.ax_graph, font_size=9, font_color="#d63384")
        
        nx.draw_networkx_nodes(self.G, pos, ax=self.ax_graph, node_size=700, node_color=colors, edgecolors="#212529", linewidths=1.5)
        
        labels = {}
        for n in self.G.nodes():
            dur = self.durations.get(n, 1)
            labels[n] = f"{n}\n({dur})" if dur > 1 else str(n)
            
        nx.draw_networkx_labels(self.G, pos, ax=self.ax_graph, labels=labels, font_size=9, font_color="white", font_weight="bold")

        self.ax_graph.set_axis_off()
        self.ax_graph.margins(0.1)
        self.fig_graph.tight_layout()
        self.canvas_graph.draw_idle()

    def draw_gantt(self, st, et, p):
        self.ax_gantt.clear()
        cmap = matplotlib.colormaps["tab10"]
        
        for task, proc in self.assignment.items():
            start = st[task]
            dur = et[task] - start
            color = cmap(proc % 10)
            
            self.ax_gantt.barh(proc, dur, left=start, height=0.6, color=color, edgecolor="#212529", linewidth=1, zorder=2)
            self.ax_gantt.text(start + dur/2, proc, str(task), ha="center", va="center", color="white", fontweight="bold", zorder=3)
            
            for pr in self.G.predecessors(task):
                if self.assignment[pr] != proc:
                    self.ax_gantt.plot([et[pr], st[task]], [self.assignment[pr], proc], 
                                       color="#d63384", linestyle="--", linewidth=1.5, alpha=0.7, zorder=1)

        self.ax_gantt.set_yticks(range(p))
        self.ax_gantt.set_yticklabels([f"Процессор {i}" for i in range(p)])
        
        self.ax_gantt.spines['top'].set_visible(False)
        self.ax_gantt.spines['right'].set_visible(False)
        
        max_time = max(et.values()) if et else 1
        self.ax_gantt.set_xlim(0, max_time + 1)
        self.ax_gantt.set_xticks(range(int(max_time) + 2))
        self.ax_gantt.grid(True, axis='x', linestyle="--", alpha=0.5, zorder=1)
                
        self.fig_gantt.tight_layout()
        self.canvas_gantt.draw_idle()

    def update_info(self, p, makespan, mode_text, log_text):
        info = f"Режим: {mode_text}\n"
        info += f"Процессоров: {p}\n"
        info += f"Время выполнения (makespan): {makespan}\n\n"
        
        if log_text:
            info += "--- Журнал EZ ---\n"
            info += log_text + "\n\n"
            
        info += "Суть метода:\n"
        info += "Мы ищем дуги, передающие данные между разными\n"
        info += "процессорами, и пытаемся перенести задачу на\n"
        info += "процессор предшественника. Это зануляет задержку."
        
        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", "end")
        self.info_text.insert("1.0", info)
        self.info_text.configure(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    app = EdgeZeroingApp(root)
    root.mainloop()