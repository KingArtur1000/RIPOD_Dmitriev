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

class GraphCollapsingApp:
    def __init__(self, root):
        self.root = root
        root.title("Лабораторная 5: Свертывание графа распараллеленности")
        self._center(1450, 950)
        root.minsize(1100, 750)
        root.configure(bg=BG_MAIN)

        self.G = nx.DiGraph()
        self.default_edges = "1-5, 1-6, 2-6, 2-7, 3-7, 3-8, 4-8, 5-9, 6-9, 7-10, 8-10, 9-11, 10-11"
        
        self.processors = tk.IntVar(value=3)
        
        self._build_style()
        self._build_ui()
        self.update_collapse()

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
        main.columnconfigure(0, weight=0, minsize=380)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        left = ttk.Frame(main, padding=15)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        
        right = ttk.Frame(main, style="Main.TFrame")
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        right.rowconfigure(2, weight=1)

        self._build_controls(left)
        
        graph_frame = ttk.LabelFrame(right, text=" Исходный граф (раскраска по процессорам) ", padding=5)
        graph_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 5))
        self._build_graph_area(graph_frame)
        
        collapsed_frame = ttk.LabelFrame(right, text=" Свернутый граф (Узлы = Процессоры) ", padding=5)
        collapsed_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 5))
        self._build_collapsed_area(collapsed_frame)
        
        gantt_frame = ttk.LabelFrame(right, text=" Временная диаграмма ", padding=5)
        gantt_frame.grid(row=2, column=0, sticky="nsew")
        self._build_gantt_area(gantt_frame)

    def _build_controls(self, parent):
        ttk.Label(parent, text="Свертывание графа", style="Title.TLabel").pack(anchor="w")
        ttk.Label(parent, text="Метод collapsing", style="Sub.TLabel").pack(anchor="w", pady=(0, 10))

        cfg_frame = ttk.LabelFrame(parent, text=" Параметры системы ", padding=10)
        cfg_frame.pack(fill="x", pady=5)
        
        ttk.Label(cfg_frame, text="Количество процессоров (p):").pack(anchor="w")
        proc_frame = ttk.Frame(cfg_frame)
        proc_frame.pack(fill="x", pady=5)
        spin = ttk.Spinbox(proc_frame, from_=1, to=8, textvariable=self.processors, width=5, font=("Segoe UI", 11))
        spin.pack(side="left")
        spin.bind("<<Increment>>", lambda e: self.update_collapse())
        spin.bind("<<Decrement>>", lambda e: self.update_collapse())
        ttk.Button(proc_frame, text="Применить", command=self.update_collapse).pack(side="left", padx=10)

        input_frame = ttk.LabelFrame(parent, text=" Входные данные (Граф) ", padding=10)
        input_frame.pack(fill="x", pady=10)
        
        self.edges_entry = tk.Text(input_frame, height=4, width=30, font=("Consolas", 10), 
                                   bg=BG_MAIN, fg=FG_MAIN, relief="solid", bd=1, 
                                   highlightthickness=1, highlightbackground=BORDER)
        self.edges_entry.pack(fill="x")
        self.edges_entry.insert("1.0", self.default_edges)
        
        # Контекстное меню
        self.context_menu = tk.Menu(self.edges_entry, tearoff=0)
        self.context_menu.add_command(label="Вставить", command=lambda: self.edges_entry.event_generate("<<Paste>>"))
        self.context_menu.add_command(label="Очистить", command=lambda: self.edges_entry.delete("1.0", "end"))
        
        def show_ctx(event):
            self.context_menu.post(event.x_root, event.y_root)
        self.edges_entry.bind("<Button-3>", show_ctx)
        self.edges_entry.bind("<Control-v>", lambda e: self.edges_entry.event_generate("<<Paste>>"))
        self.edges_entry.bind("<Command-v>", lambda e: self.edges_entry.event_generate("<<Paste>>"))

        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        ttk.Button(btn_frame, text="📋 Вставить", command=self.paste_from_clipboard).pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="Свернуть граф", command=self.update_collapse).pack(side="left", fill="x", expand=True)

        # Инфо
        info_frame = ttk.LabelFrame(parent, text=" Анализ свертывания ", padding=10)
        info_frame.pack(fill="both", expand=True, pady=(5, 0))
        
        self.info_text = tk.Text(info_frame, height=10, bg=BG_MAIN, fg=FG_MAIN, bd=1, 
                                 relief="solid", font=("Consolas", 9), wrap="word", 
                                 padx=8, pady=8, highlightthickness=1, highlightbackground=BORDER)
        self.info_text.pack(fill="both", expand=True)
        self.info_text.configure(state="disabled")

    def paste_from_clipboard(self):
        try:
            text = self.root.clipboard_get()
            self.edges_entry.delete("1.0", "end")
            self.edges_entry.insert("1.0", text)
            self.update_collapse()
        except tk.TclError:
            messagebox.showwarning("Буфер обмена", "Пусто!")

    def _build_graph_area(self, parent):
        self.fig_graph = Figure(figsize=(6, 2), dpi=100, facecolor=GRAPH_BG)
        self.ax_graph = self.fig_graph.add_subplot(111)
        self.ax_graph.set_facecolor(GRAPH_BG)
        self.canvas_graph = FigureCanvasTkAgg(self.fig_graph, master=parent)
        self.canvas_graph.get_tk_widget().pack(fill="both", expand=True)

    def _build_collapsed_area(self, parent):
        self.fig_col = Figure(figsize=(6, 2), dpi=100, facecolor=GRAPH_BG)
        self.ax_col = self.fig_col.add_subplot(111)
        self.ax_col.set_facecolor(GRAPH_BG)
        self.canvas_col = FigureCanvasTkAgg(self.fig_col, master=parent)
        self.canvas_col.get_tk_widget().pack(fill="both", expand=True)

    def _build_gantt_area(self, parent):
        self.fig_gantt = Figure(figsize=(6, 2), dpi=100, facecolor=GRAPH_BG)
        self.ax_gantt = self.fig_gantt.add_subplot(111)
        self.ax_gantt.set_facecolor(GRAPH_BG)
        self.canvas_gantt = FigureCanvasTkAgg(self.fig_gantt, master=parent)
        self.canvas_gantt.get_tk_widget().pack(fill="both", expand=True)

    def parse_edges(self):
        text = self.edges_entry.get("1.0", "end-1c")
        text = text.replace("\n", ",").replace(" ", "")
        edges = []
        for pair in text.split(","):
            if not pair: continue
            try:
                u, v = pair.split("-")
                edges.append((u.strip(), v.strip()))
            except ValueError:
                pass
        return edges

    def update_collapse(self):
        self.G.clear()
        edges = self.parse_edges()
        if not edges: return

        self.G.add_edges_from(edges)
        if not nx.is_directed_acyclic_graph(self.G):
            messagebox.showerror("Ошибка", "Граф содержит циклы!")
            return

        p = self.processors.get()

        # 1. Приоритеты (Bottom Level)
        priorities = {}
        for node in reversed(list(nx.topological_sort(self.G))):
            succs = list(self.G.successors(node))
            priorities[node] = 1 if not succs else 1 + max(priorities[s] for s in succs)

        # 2. Назначение задач процессорам (многошаговое ASAP)
        assigned_proc = {}
        start_time = {}
        end_time = {}
        step = 0
        scheduled = set()
        proc_free_time = [0] * p
        proc_tasks = {i: [] for i in range(p)}

        while len(scheduled) < len(self.G.nodes()):
            ready = [n for n in self.G.nodes() if n not in scheduled and all(pr in scheduled for pr in self.G.predecessors(n))]
            ready.sort(key=lambda x: (-priorities[x], str(x)))
            
            free_procs = [i for i in range(p) if proc_free_time[i] <= step]
            
            for proc in free_procs:
                if not ready: break
                task = ready.pop(0)
                assigned_proc[task] = proc
                start_time[task] = step
                end_time[task] = step + 1
                proc_free_time[proc] = step + 1
                scheduled.add(task)
                proc_tasks[proc].append(task)
            
            step += 1

        # 3. СВЕРТЫВАНИЕ ГРАФА
        collapsed_G = nx.DiGraph()
        collapsed_labels = {}
        
        for proc_id, tasks in proc_tasks.items():
            if not tasks: continue
            proc_name = f"P{proc_id}"
            collapsed_G.add_node(proc_name)
            tasks.sort(key=lambda x: start_time[x])
            collapsed_labels[proc_name] = " → ".join(str(t) for t in tasks)

        for u, v in self.G.edges():
            pu = f"P{assigned_proc[u]}"
            pv = f"P{assigned_proc[v]}"
            if pu != pv:
                collapsed_G.add_edge(pu, pv)

        # 4. Отрисовка
        self.draw_original(assigned_proc)
        self.draw_collapsed(collapsed_G, collapsed_labels)
        self.draw_gantt(assigned_proc, start_time, end_time, p)
        self.update_info(proc_tasks, collapsed_G)

    def draw_original(self, assigned_proc):
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
        
        nx.draw_networkx_edges(self.G, pos, ax=self.ax_graph, edge_color="#adb5bd", width=1.5, arrowsize=15)
        nx.draw_networkx_nodes(self.G, pos, ax=self.ax_graph, node_size=600, node_color=colors, edgecolors="#212529", linewidths=1)
        nx.draw_networkx_labels(self.G, pos, ax=self.ax_graph, font_size=10, font_color="white", font_weight="bold")

        self.ax_graph.set_axis_off()
        self.ax_graph.margins(0.1)
        self.fig_graph.tight_layout()
        self.canvas_graph.draw_idle()

    def draw_collapsed(self, cG, labels):
        self.ax_col.clear()
        if not cG.nodes(): return
        
        # --- ИСПРАВЛЕНИЕ БАГА ---
        # В свернутом графе могут быть циклы (P1->P2 и P2->P1),
        # поэтому используем круговую раскладку вместо топологической сортировки
        pos = nx.circular_layout(cG)
        
        # Рисуем ребра (со скруглением, чтобы双向 связи не перекрывались)
        nx.draw_networkx_edges(cG, pos, ax=self.ax_col, edge_color="#6c757d", 
                               width=2, arrowsize=20, connectionstyle="arc3,rad=0.1")
        
        # Рисуем узлы
        nx.draw_networkx_nodes(cG, pos, ax=self.ax_col, node_size=3500, 
                               node_color="#e3f2fd", edgecolors=ACCENT, linewidths=2)
        
        # Рисуем подписи
        nx.draw_networkx_labels(cG, pos, ax=self.ax_col, labels=labels, 
                                font_size=10, font_color="#000000", font_weight="bold")

        self.ax_col.set_axis_off()
        self.ax_col.margins(0.2)
        self.fig_col.tight_layout()
        self.canvas_col.draw_idle()

    def draw_gantt(self, assigned_proc, start_time, end_time, p):
        self.ax_gantt.clear()
        cmap = matplotlib.colormaps["tab10"]
        
        for task, proc in assigned_proc.items():
            st = start_time[task]
            dur = end_time[task] - st
            color = cmap(proc % 10)
            
            self.ax_gantt.barh(proc, dur, left=st, height=0.6, color=color, edgecolor="#212529", linewidth=1, zorder=2)
            self.ax_gantt.text(st + dur/2, proc, str(task), ha="center", va="center", color="white", fontweight="bold", zorder=3)

        self.ax_gantt.set_yticks(range(p))
        self.ax_gantt.set_yticklabels([f"Процессор {i}" for i in range(p)])
        
        self.ax_gantt.spines['top'].set_visible(False)
        self.ax_gantt.spines['right'].set_visible(False)
        
        max_time = max(end_time.values()) if end_time else 1
        self.ax_gantt.set_xlim(0, max_time + 1)
        self.ax_gantt.set_xticks(range(int(max_time) + 2))
        self.ax_gantt.grid(True, axis='x', linestyle="--", alpha=0.5, zorder=1)
                
        self.fig_gantt.tight_layout()
        self.canvas_gantt.draw_idle()

    def update_info(self, proc_tasks, cG):
        info = "Свернутый граф:\n"
        info += f"Количество процессоров (узлов): {len(cG.nodes())}\n"
        info += f"Количество связей (ребер): {len(cG.edges())}\n\n"
        
        for proc in sorted(proc_tasks.keys()):
            if not proc_tasks[proc]: continue
            info += f"P{proc}: {len(proc_tasks[proc])} операций\n"
            
        info += "\nСуть метода: мы объединили последовательности операций,\n"
        info += "выполняемых на одном процессоре, в супер-узлы.\n"
        info += "Теперь граф показывает связи между процессорами."
        
        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", "end")
        self.info_text.insert("1.0", info)
        self.info_text.configure(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    app = GraphCollapsingApp(root)
    root.mainloop()