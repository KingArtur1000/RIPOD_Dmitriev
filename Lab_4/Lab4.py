import tkinter as tk
from tkinter import ttk, messagebox
import networkx as nx
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ---------- Светлая цветовая схема ----------
BG_MAIN   = "#f4f6f9"
BG_PANEL  = "#ffffff"
FG_MAIN   = "#212529"
FG_MUTED  = "#6c757d"
ACCENT    = "#0d6efd"
BORDER    = "#dee2e6"
GRAPH_BG  = "#ffffff"

class MultiStepSchedulingApp:
    def __init__(self, root):
        self.root = root
        root.title("Лабораторная 4: Многошаговое планирование")
        self._center(1450, 900)
        root.minsize(1100, 700)
        root.configure(bg=BG_MAIN)

        self.G = nx.DiGraph()
        self.durations = {}
        # Дефолтный граф с разными длительностями (формат A-B:duration)
        self.default_edges = "1-4, 1-5, 2-5, 2-6, 3-6:2, 4-7, 5-8:3, 6-8, 7-9, 8-9"
        
        self.processors = tk.IntVar(value=3)
        self.strategy = tk.StringVar(value="ASAP")
        
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
        
        s.configure("TRadiobutton", background=BG_PANEL, foreground=FG_MAIN, font=("Segoe UI", 10))
        s.map("TRadiobutton", background=[("active", BG_MAIN)])
        
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
        
        graph_frame = ttk.LabelFrame(right, text=" Граф зависимостей ", padding=5)
        graph_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        self._build_graph_area(graph_frame)
        
        gantt_frame = ttk.LabelFrame(right, text=" Диаграмма Ганта ", padding=5)
        gantt_frame.grid(row=1, column=0, sticky="nsew")
        self._build_gantt_area(gantt_frame)

    def _build_controls(self, parent):
        ttk.Label(parent, text="Многошаговое планирование", style="Title.TLabel").pack(anchor="w")
        ttk.Label(parent, text="Синхронное (ASAP) vs Асинхронное (List)", style="Sub.TLabel").pack(anchor="w", pady=(0, 10))

        strat_frame = ttk.LabelFrame(parent, text=" Стратегия планирования ", padding=8)
        strat_frame.pack(fill="x", pady=5)
        ttk.Radiobutton(strat_frame, text="Многошаговое ASAP (Синхронное)", value="ASAP", 
                        variable=self.strategy, command=self.update_schedule).pack(anchor="w", pady=2)
        ttk.Radiobutton(strat_frame, text="Многошаговое List Scheduling (Асинхронное)", value="LIST", 
                        variable=self.strategy, command=self.update_schedule).pack(anchor="w", pady=2)

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

        input_frame = ttk.LabelFrame(parent, text=" Входные данные (A-B или A-B:время) ", padding=10)
        input_frame.pack(fill="x", pady=10)
        
        self.edges_entry = tk.Text(input_frame, height=4, width=30, font=("Consolas", 10), 
                                   bg=BG_MAIN, fg=FG_MAIN, relief="solid", bd=1, 
                                   highlightthickness=1, highlightbackground=BORDER)
        self.edges_entry.pack(fill="x")
        self.edges_entry.insert("1.0", self.default_edges)
        
        # --- ИСПРАВЛЕНИЕ ДЛЯ ВСТАВКИ ТЕКСТА ---
        self.context_menu = tk.Menu(self.edges_entry, tearoff=0)
        self.context_menu.add_command(label="Вырезать", command=lambda: self.edges_entry.event_generate("<<Cut>>"))
        self.context_menu.add_command(label="Копировать", command=lambda: self.edges_entry.event_generate("<<Copy>>"))
        self.context_menu.add_command(label="Вставить", command=lambda: self.edges_entry.event_generate("<<Paste>>"))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Выделить все", command=lambda: self.edges_entry.tag_add("sel", "1.0", "end"))

        def show_context_menu(event):
            self.context_menu.post(event.x_root, event.y_root)

        self.edges_entry.bind("<Button-3>", show_context_menu) # ПКМ Windows/Linux
        self.edges_entry.bind("<Button-2>", show_context_menu) # ПКМ Mac
        
        self.edges_entry.bind("<Control-v>", lambda e: self.edges_entry.event_generate("<<Paste>>"))
        self.edges_entry.bind("<Command-v>", lambda e: self.edges_entry.event_generate("<<Paste>>"))
        # -------------------------------------

        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        
        # Кнопка вставки
        ttk.Button(btn_frame, text="📋 Вставить", command=self.paste_from_clipboard).pack(side="left", padx=(0, 5))
        # Кнопка построения
        ttk.Button(btn_frame, text="Построить план", command=self.update_schedule).pack(side="left", fill="x", expand=True)

        info_frame = ttk.LabelFrame(parent, text=" Результаты ", padding=10)
        info_frame.pack(fill="both", expand=True, pady=(5, 0))
        
        self.info_text = tk.Text(info_frame, height=8, bg=BG_MAIN, fg=FG_MAIN, bd=1, 
                                 relief="solid", font=("Consolas", 9), wrap="word", 
                                 padx=8, pady=8, highlightthickness=1, highlightbackground=BORDER)
        self.info_text.pack(fill="both", expand=True)
        self.info_text.configure(state="disabled")

    def paste_from_clipboard(self):
        """Вставка текста из буфера обмена с последующим пересчетом"""
        try:
            clipboard_text = self.root.clipboard_get()
            self.edges_entry.delete("1.0", "end")
            self.edges_entry.insert("1.0", clipboard_text)
            self.update_schedule()
        except tk.TclError:
            messagebox.showwarning("Буфер обмена", "Буфер обмена пуст или не содержит текста.")

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
        edges = []
        durations = {}
        for pair in text.split(","):
            if not pair: continue
            try:
                if ":" in pair:
                    edge_part, dur_part = pair.split(":")
                    u, v = edge_part.split("-")
                    durations[u.strip()] = int(dur_part)
                else:
                    u, v = pair.split("-")
                edges.append((u.strip(), v.strip()))
            except ValueError:
                pass
        return edges, durations

    def update_schedule(self):
        self.G.clear()
        edges, self.durations = self.parse_edges()
        if not edges: return

        self.G.add_edges_from(edges)
        if not nx.is_directed_acyclic_graph(self.G):
            messagebox.showerror("Ошибка", "Граф содержит циклы!")
            return

        p = self.processors.get()
        current_strat = self.strategy.get()

        # 1. Приоритеты (Bottom Level)
        priorities = {}
        for node in reversed(list(nx.topological_sort(self.G))):
            succs = list(self.G.successors(node))
            w = self.durations.get(node, 1)
            if not succs:
                priorities[node] = w
            else:
                priorities[node] = w + max(priorities[s] for s in succs)

        assigned_proc = {}
        start_time = {}
        end_time = {}

        if current_strat == "ASAP":
            # --- МНОГОШАГОВЫЙ ASAP ---
            step = 0
            scheduled = set()
            proc_free_time = [0] * p
            
            while len(scheduled) < len(self.G.nodes()):
                ready = [n for n in self.G.nodes() if n not in scheduled and all(pr in scheduled for pr in self.G.predecessors(n))]
                ready.sort(key=lambda x: (-priorities[x], str(x)))
                
                free_procs = [i for i in range(p) if proc_free_time[i] <= step]
                
                for proc in free_procs:
                    if not ready: break
                    task = ready.pop(0)
                    assigned_proc[task] = proc
                    start_time[task] = step
                    dur = self.durations.get(task, 1)
                    end_time[task] = step + dur
                    proc_free_time[proc] = step + dur
                    scheduled.add(task)
                
                step += 1
                
        else:
            # --- LIST SCHEDULING ---
            proc_free_time = [0] * p
            scheduled = set()
            
            while len(scheduled) < len(self.G.nodes()):
                ready = [n for n in self.G.nodes() if n not in scheduled and all(pr in scheduled for pr in self.G.predecessors(n))]
                if not ready: break
                
                ready.sort(key=lambda x: (-priorities[x], str(x)))
                
                min_time = min(proc_free_time)
                free_procs = [i for i in range(p) if proc_free_time[i] == min_time]
                
                for proc in free_procs:
                    if not ready: break
                    task = ready.pop(0)
                    
                    preds = list(self.G.predecessors(task))
                    dep_time = max([end_time[pr] for pr in preds]) if preds else 0
                    
                    st = max(proc_free_time[proc], dep_time)
                    dur = self.durations.get(task, 1)
                    et = st + dur
                    
                    proc_free_time[proc] = et
                    assigned_proc[task] = proc
                    start_time[task] = st
                    end_time[task] = et
                    scheduled.add(task)

        self.draw_graph(assigned_proc, p)
        self.draw_gantt(assigned_proc, start_time, end_time, p, current_strat)
        self.update_info(priorities, start_time, end_time, assigned_proc, p, current_strat)

    def draw_graph(self, assigned_proc, p):
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
        colors = [cmap(assigned_proc[n] % 10) for n in self.G.nodes()]
        
        nx.draw_networkx_edges(self.G, pos, ax=self.ax_graph, edge_color="#adb5bd", width=2, arrowsize=20)
        nx.draw_networkx_nodes(self.G, pos, ax=self.ax_graph, node_size=700, node_color=colors, edgecolors="#212529", linewidths=1.5)
        
        labels = {n: f"{n}\n({self.durations.get(n, 1)})" for n in self.G.nodes()}
        nx.draw_networkx_labels(self.G, pos, ax=self.ax_graph, labels=labels, font_size=9, font_color="white", font_weight="bold")

        self.ax_graph.set_axis_off()
        self.ax_graph.margins(0.1)
        self.fig_graph.tight_layout()
        self.canvas_graph.draw_idle()

    def draw_gantt(self, assigned_proc, start_time, end_time, p, strategy):
        self.ax_gantt.clear()
        cmap = matplotlib.colormaps["tab10"]
        
        for task, proc in assigned_proc.items():
            st = start_time[task]
            dur = end_time[task] - st
            color = cmap(proc % 10)
            
            self.ax_gantt.barh(proc, dur, left=st, height=0.7, color=color, 
                               edgecolor="#212529", linewidth=1, zorder=2)
            
            self.ax_gantt.text(st + dur/2, proc, str(task), ha="center", va="center", 
                               color="white", fontweight="bold", fontsize=9, zorder=3)

        self.ax_gantt.set_yticks(range(p))
        self.ax_gantt.set_yticklabels([f"Процессор {i}" for i in range(p)])
        self.ax_gantt.set_xlabel("Время (шаги)")
        
        self.ax_gantt.spines['top'].set_visible(False)
        self.ax_gantt.spines['right'].set_visible(False)
        
        max_time = max(end_time.values()) if end_time else 1
        self.ax_gantt.set_xlim(0, max_time + 1)
        self.ax_gantt.set_xticks(range(int(max_time) + 2))
        
        self.ax_gantt.grid(True, axis='x', linestyle="--", alpha=0.6, zorder=1)
                
        self.fig_gantt.tight_layout()
        self.canvas_gantt.draw_idle()

    def update_info(self, priorities, start_time, end_time, assigned_proc, p, strategy):
        total_time = max(end_time.values()) if end_time else 0
        active_strategy = "Многошаговое ASAP (Синхронное)" if strategy == "ASAP" else "List Scheduling (Асинхронное)"
        
        info = f"Стратегия: {active_strategy}\n"
        info += f"Процессоров: {p}\n"
        info += f"Время выполнения (makespan): {total_time}\n\n"
        
        info += f"{'Опер.':<5} | {'Приор.':<6} | {'Длит.':<5} | {'Проц.':<5} | {'Старт':<5} | {'Конец':<5}\n"
        info += "-" * 42 + "\n"
        
        try: sorted_nodes = sorted(self.G.nodes(), key=lambda x: int(x) if str(x).isdigit() else str(x))
        except: sorted_nodes = sorted(self.G.nodes())
            
        for node in sorted_nodes:
            dur = self.durations.get(node, 1)
            info += f"{str(node):<5} | {priorities[node]:<6} | {dur:<5} | P{assigned_proc[node]:<4} | {start_time[node]:<5} | {end_time[node]:<5}\n"
            
        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", "end")
        self.info_text.insert("1.0", info)
        self.info_text.configure(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = MultiStepSchedulingApp(root)
    root.mainloop()