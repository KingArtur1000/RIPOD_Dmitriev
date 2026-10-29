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


class ListSchedulingApp:
    def __init__(self, root):
        self.root = root
        root.title("Лабораторная 3: Списковое планирование (List Scheduling)")
        self._center(1450, 900)
        root.minsize(1100, 700)
        root.configure(bg=BG_MAIN)

        self.G = nx.DiGraph()
        self.default_edges = "1-4, 1-5, 2-5, 2-6, 3-6, 4-7, 5-8, 6-8, 7-9, 8-9"
        
        self.processors = tk.IntVar(value=2)
        
        self._build_style()
        self._build_ui()
        self.update_schedule()

    def _center(self, w, h):
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _build_style(self):
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        
        s.configure(".", background=BG_PANEL, foreground=FG_MAIN, fieldbackground=BG_MAIN)
        s.configure("TFrame", background=BG_PANEL)
        s.configure("Main.TFrame", background=BG_MAIN)
        s.configure("TLabel", background=BG_PANEL, foreground=FG_MAIN, font=("Segoe UI", 10))
        s.configure("Title.TLabel", font=("Segoe UI", 14, "bold"), foreground=ACCENT)
        s.configure("Sub.TLabel", font=("Segoe UI", 9), foreground=FG_MUTED)
        
        s.configure("TButton", font=("Segoe UI", 10, "bold"), background=ACCENT, foreground="white", borderwidth=0, padding=6)
        s.map("TButton", background=[("active", "#0b5ed7")])
        
        s.configure("Treeview", background=BG_PANEL, foreground=FG_MAIN, fieldbackground=BG_PANEL, rowheight=28, font=("Segoe UI", 10))
        s.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background=BG_MAIN, foreground=FG_MAIN, padding=4)
        
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

        self._build_controls(left)
        
        graph_frame = ttk.LabelFrame(right, text=" Граф зависимостей ", padding=5)
        graph_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        self._build_graph_area(graph_frame)
        
        gantt_frame = ttk.LabelFrame(right, text=" Диаграмма Ганта (Распределение по процессорам) ", padding=5)
        gantt_frame.grid(row=1, column=0, sticky="nsew")
        self._build_gantt_area(gantt_frame)

    def _build_controls(self, parent):
        ttk.Label(parent, text="Списковое планирование", style="Title.TLabel").pack(anchor="w")
        ttk.Label(parent, text="List Scheduling Strategy", style="Sub.TLabel").pack(anchor="w", pady=(0, 10))

        cfg_frame = ttk.LabelFrame(parent, text=" Параметры системы ", padding=10)
        cfg_frame.pack(fill="x", pady=5)
        
        ttk.Label(cfg_frame, text="Количество процессоров (p):").pack(anchor="w")
        proc_frame = ttk.Frame(cfg_frame)
        proc_frame.pack(fill="x", pady=5)
        
        spin = ttk.Spinbox(proc_frame, from_=1, to=8, textvariable=self.processors, width=5, font=("Segoe UI", 11))
        spin.pack(side="left")
        spin.bind("<Return>", lambda e: self.update_schedule())
        spin.bind("<<Increment>>", lambda e: self.update_schedule())
        spin.bind("<<Decrement>>", lambda e: self.update_schedule())
        
        ttk.Button(proc_frame, text="Применить", command=self.update_schedule).pack(side="left", padx=10)

        input_frame = ttk.LabelFrame(parent, text=" Входные данные (Граф) ", padding=10)
        input_frame.pack(fill="x", pady=10)
        
        ttk.Label(input_frame, text="Зависимости (A-B, где A→B):").pack(anchor="w", pady=(0, 5))
        self.edges_entry = tk.Text(input_frame, height=5, width=30, font=("Consolas", 10), 
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
        
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        
        # --- НОВАЯ КНОПКА ГЕНЕРАЦИИ ---
        ttk.Button(btn_frame, text="🎲 Сгенерировать", command=self.generate_random_graph).pack(side="left", padx=(0, 5))
        # ------------------------------
        
        ttk.Button(btn_frame, text="Построить план", command=self.update_schedule).pack(side="left", fill="x", expand=True)

        info_frame = ttk.LabelFrame(parent, text=" Результаты планирования ", padding=10)
        info_frame.pack(fill="both", expand=True, pady=(5, 0))
        
        self.info_text = tk.Text(info_frame, height=10, bg=BG_MAIN, fg=FG_MAIN, bd=1, 
                                 relief="solid", font=("Consolas", 9), wrap="word", 
                                 padx=8, pady=8, highlightthickness=1, highlightbackground=BORDER)
        self.info_text.pack(fill="both", expand=True)
        self.info_text.configure(state="disabled")

    def generate_random_graph(self):
        """Генерация случайного DAG (направленного ациклического графа)"""
        n = random.randint(7, 12) # Случайное количество вершин
        nodes = [str(i) for i in range(1, n + 1)]
        edges = []
        
        # Генерируем ребра только от узлов с меньшим индексом к большему.
        # Это гарантирует, что граф будет ациклическим.
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                # Вероятность связи ~35%
                if random.random() < 0.35:
                    edges.append((nodes[i], nodes[j]))
        
        # Проверка на связность: если получился граф без ребер, добавим пару
        if not edges:
            edges.append((nodes[0], nodes[1]))
            edges.append((nodes[1], nodes[-1]))

        # Преобразуем в строку формата "1-2, 2-3"
        edge_str = ", ".join([f"{u}-{v}" for u, v in edges])
        
        self.edges_entry.delete("1.0", "end")
        self.edges_entry.insert("1.0", edge_str)
        self.update_schedule()

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
        for pair in text.split(","):
            if not pair: continue
            try:
                u, v = pair.split("-")
                edges.append((u.strip(), v.strip()))
            except ValueError:
                pass
        return edges

    def update_schedule(self):
        self.G.clear()
        edges = self.parse_edges()
        if not edges: return

        self.G.add_edges_from(edges)
        if not nx.is_directed_acyclic_graph(self.G):
            return

        p = self.processors.get()

        # 1. Вычисление приоритетов (Bottom Level - критический путь до конца)
        priorities = {}
        for node in reversed(list(nx.topological_sort(self.G))):
            succs = list(self.G.successors(node))
            if not succs:
                priorities[node] = 1
            else:
                priorities[node] = 1 + max(priorities[s] for s in succs)

        # 2. Симуляция List Scheduling
        proc_free_time = [0] * p
        assigned_proc = {}
        start_time = {}
        end_time = {}
        scheduled_tasks = set()
        
        while len(scheduled_tasks) < len(self.G.nodes()):
            ready_tasks = []
            for node in self.G.nodes():
                if node in scheduled_tasks: continue
                preds = list(self.G.predecessors(node))
                if all(pr in scheduled_tasks for pr in preds):
                    ready_tasks.append(node)
            
            if not ready_tasks:
                break 
                
            ready_tasks.sort(key=lambda x: (-priorities[x], str(x)))
            min_free = min(proc_free_time)
            
            for i in range(p):
                if proc_free_time[i] <= min_free:
                    if not ready_tasks: break
                    
                    task = ready_tasks.pop(0)
                    preds = list(self.G.predecessors(task))
                    dep_time = max([end_time[pr] for pr in preds]) if preds else 0
                    
                    st = max(proc_free_time[i], dep_time)
                    et = st + 1
                    
                    proc_free_time[i] = et
                    assigned_proc[task] = i
                    start_time[task] = st
                    end_time[task] = et
                    scheduled_tasks.add(task)

        self.draw_graph(assigned_proc, p)
        self.draw_gantt(assigned_proc, start_time, end_time, p)
        self.update_info(priorities, start_time, end_time, assigned_proc, p)

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
        nx.draw_networkx_labels(self.G, pos, ax=self.ax_graph, font_size=12, font_color="white", font_weight="bold")

        self.ax_graph.set_axis_off()
        self.ax_graph.margins(0.1)
        self.fig_graph.tight_layout()
        self.canvas_graph.draw_idle()

    def draw_gantt(self, assigned_proc, start_time, end_time, p):
        self.ax_gantt.clear()
        
        cmap = matplotlib.colormaps["tab10"]
        
        for task, proc in assigned_proc.items():
            st = start_time[task]
            dur = end_time[task] - st
            color = cmap(proc % 10)
            self.ax_gantt.barh(proc, dur, left=st, height=0.6, color=color, edgecolor="#212529", linewidth=1)
            self.ax_gantt.text(st + dur/2, proc, str(task), ha="center", va="center", color="white", fontweight="bold")

        self.ax_gantt.set_yticks(range(p))
        self.ax_gantt.set_yticklabels([f"Процессор {i}" for i in range(p)])
        self.ax_gantt.set_xlabel("Время")
        
        self.ax_gantt.spines['top'].set_visible(False)
        self.ax_gantt.spines['right'].set_visible(False)
        
        max_time = max(end_time.values()) if end_time else 1
        self.ax_gantt.set_xlim(0, max_time + 1)
        self.ax_gantt.set_xticks(range(int(max_time) + 2))
        
        self.fig_gantt.tight_layout()
        self.canvas_gantt.draw_idle()

    def update_info(self, priorities, start_time, end_time, assigned_proc, p):
        total_time = max(end_time.values()) if end_time else 0
        
        info = f"Процессоров: {p}\n"
        info += f"Общее время выполнения (makespan): {total_time}\n"
        info += f"Всего операций: {len(self.G.nodes())}\n\n"
        
        info += f"{'Опер.':<5} | {'Приор.':<6} | {'Проц.':<5} | {'Старт':<5} | {'Конец':<5}\n"
        info += "-" * 38 + "\n"
        
        try:
            sorted_nodes = sorted(self.G.nodes(), key=lambda x: int(x) if str(x).isdigit() else str(x))
        except:
            sorted_nodes = sorted(self.G.nodes())
            
        for node in sorted_nodes:
            info += f"{str(node):<5} | {priorities[node]:<6} | P{assigned_proc[node]:<4} | {start_time[node]:<5} | {end_time[node]:<5}\n"
            
        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", "end")
        self.info_text.insert("1.0", info)
        self.info_text.configure(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = ListSchedulingApp(root)
    root.mainloop()