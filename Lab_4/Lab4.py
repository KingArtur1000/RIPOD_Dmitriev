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

class MultiStepSchedulingApp:
    def __init__(self, root):
        self.root = root
        root.title("Лабораторная 4: Планирование (8 алгоритмов + Анимация)")
        self._center(1500, 950)
        root.minsize(1150, 750)
        root.configure(bg=BG_MAIN)

        self.G = nx.DiGraph()
        self.durations = {}
        self.default_edges = "1-4, 1-5, 2-5, 2-6, 3-6:2, 4-7, 5-8:3, 6-8, 7-9, 8-9"
        
        self.processors = tk.IntVar(value=3)
        self.strategy = tk.StringVar(value="MS-ASAP")
        
        self.gen_nodes = tk.IntVar(value=10)
        self.gen_density = tk.DoubleVar(value=0.25)
        
        self.current_time = 0.0
        self.max_time = 1.0
        self.anim_running = False
        self.anim_job = None
        
        self.assigned_proc = {}
        self.start_time = {}
        self.end_time = {}

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
        right.rowconfigure(0, weight=2)
        right.rowconfigure(1, weight=3)

        self._build_controls(left)
        
        graph_frame = ttk.LabelFrame(right, text=" Граф зависимостей ", padding=5)
        graph_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        self._build_graph_area(graph_frame)
        
        gantt_main_frame = ttk.LabelFrame(right, text=" Диаграмма Ганта ", padding=5)
        gantt_main_frame.grid(row=1, column=0, sticky="nsew")
        gantt_main_frame.rowconfigure(0, weight=1)
        gantt_main_frame.columnconfigure(0, weight=1)
        
        self._build_gantt_area(gantt_main_frame)
        self._build_animation_controls(gantt_main_frame)

    def _build_controls(self, parent):
        ttk.Label(parent, text="Многошаговое планирование", style="Title.TLabel").pack(anchor="w")
        ttk.Label(parent, text="8 стратегий (ASAP, ALAP, C-ASAP...)", style="Sub.TLabel").pack(anchor="w", pady=(0, 10))

        strat_frame = ttk.LabelFrame(parent, text=" Стратегия планирования ", padding=8)
        strat_frame.pack(fill="x", pady=5)
        
        strategies = [
            "ASAP (Обычный)", "ALAP (Обычный)", 
            "C-ASAP (Цепочечный)", "C-ALAP (Цепочечный)",
            "MS-ASAP (Синхронный)", "MS-ALAP (Синхронный)",
            "LS (Асинхронный)", "MS-LS (Многошаговый)"
        ]
        combo = ttk.Combobox(strat_frame, textvariable=self.strategy, values=strategies, state="readonly", font=("Segoe UI", 10))
        combo.pack(fill="x", pady=2)
        combo.bind("<<ComboboxSelected>>", lambda e: self.update_schedule())

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
        
        self.context_menu = tk.Menu(self.edges_entry, tearoff=0)
        self.context_menu.add_command(label="Вставить", command=lambda: self.edges_entry.event_generate("<<Paste>>"))
        self.context_menu.add_command(label="Очистить", command=lambda: self.edges_entry.delete("1.0", "end"))
        
        def show_context_menu(event):
            self.context_menu.post(event.x_root, event.y_root)

        self.edges_entry.bind("<Button-3>", show_context_menu) 
        self.edges_entry.bind("<Button-2>", show_context_menu)
        self.edges_entry.bind("<Control-v>", lambda e: self.edges_entry.event_generate("<<Paste>>"))
        self.edges_entry.bind("<Command-v>", lambda e: self.edges_entry.event_generate("<<Paste>>"))

        gen_frame = ttk.LabelFrame(parent, text=" Генератор ", padding=10)
        gen_frame.pack(fill="x", pady=5)
        
        g_row1 = ttk.Frame(gen_frame)
        g_row1.pack(fill="x", pady=2)
        ttk.Label(g_row1, text="Кол-во операций (N):").pack(side="left")
        ttk.Spinbox(g_row1, from_=5, to=20, textvariable=self.gen_nodes, width=5).pack(side="right")
        
        g_row2 = ttk.Frame(gen_frame)
        g_row2.pack(fill="x", pady=2)
        ttk.Label(g_row2, text="Плотность связей:").pack(side="left")
        ttk.Spinbox(g_row2, from_=0.1, to=0.8, increment=0.05, textvariable=self.gen_density, width=5).pack(side="right")

        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(btn_frame, text="📋 Вставить", command=self.paste_from_clipboard).pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="🎲 Сгенерировать", command=self.generate_random_graph).pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="Построить план", command=self.update_schedule).pack(side="left", fill="x", expand=True)

        info_frame = ttk.LabelFrame(parent, text=" Результаты ", padding=10)
        info_frame.pack(fill="both", expand=True, pady=(5, 0))
        
        self.info_text = tk.Text(info_frame, height=6, bg=BG_MAIN, fg=FG_MAIN, bd=1, 
                                 relief="solid", font=("Consolas", 9), wrap="word", 
                                 padx=8, pady=8, highlightthickness=1, highlightbackground=BORDER)
        self.info_text.pack(fill="both", expand=True)
        self.info_text.configure(state="disabled")

    def _build_graph_area(self, parent):
        self.fig_graph = Figure(figsize=(6, 2.5), dpi=100, facecolor=GRAPH_BG)
        self.ax_graph = self.fig_graph.add_subplot(111)
        self.ax_graph.set_facecolor(GRAPH_BG)
        self.canvas_graph = FigureCanvasTkAgg(self.fig_graph, master=parent)
        self.canvas_graph.get_tk_widget().pack(fill="both", expand=True)

    def _build_gantt_area(self, parent):
        self.fig_gantt = Figure(figsize=(6, 2.5), dpi=100, facecolor=GRAPH_BG)
        self.ax_gantt = self.fig_gantt.add_subplot(111)
        self.ax_gantt.set_facecolor(GRAPH_BG)
        self.canvas_gantt = FigureCanvasTkAgg(self.fig_gantt, master=parent)
        self.canvas_gantt.get_tk_widget().grid(row=0, column=0, sticky="nsew")

    def _build_animation_controls(self, parent):
        anim_frame = ttk.Frame(parent)
        anim_frame.grid(row=1, column=0, sticky="ew", pady=5, padx=10)
        
        self.btn_play = ttk.Button(anim_frame, text="▶ Play", width=10, command=self.toggle_animation)
        self.btn_play.pack(side="left", padx=5)
        
        self.time_slider = ttk.Scale(anim_frame, from_=0, to=10, orient="horizontal", command=self.on_slider_move)
        self.time_slider.pack(side="left", fill="x", expand=True, padx=5)
        
        self.lbl_time = ttk.Label(anim_frame, text="0.0", font=("Consolas", 10, "bold"))
        self.lbl_time.pack(side="right", padx=5)

    def toggle_animation(self):
        if self.anim_running:
            self.anim_running = False
            self.btn_play.configure(text="▶ Play")
            if self.anim_job:
                self.root.after_cancel(self.anim_job)
        else:
            self.anim_running = True
            self.btn_play.configure(text="⏸ Pause")
            self.current_time = 0
            self.time_slider.set(0)
            self.animate()

    def animate(self):
        if not self.anim_running: return
        self.current_time += 0.15
        if self.current_time > self.max_time + 1:
            self.current_time = 0
        self.time_slider.set(self.current_time)
        self.lbl_time.configure(text=f"{self.current_time:.1f}")
        self.draw_gantt()
        self.anim_job = self.root.after(50, self.animate)

    def on_slider_move(self, val):
        self.current_time = float(val)
        self.lbl_time.configure(text=f"{self.current_time:.1f}")
        self.draw_gantt()

    def generate_random_graph(self):
        n = self.gen_nodes.get()
        density = self.gen_density.get()
        
        nodes = [str(i) for i in range(1, n + 1)]
        edges = set()
        durations = {}
        
        for node in nodes:
            if random.random() < 0.3:
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
        for u, v in edges:
            if durations[u] > 1:
                edge_strs.append(f"{u}-{v}:{durations[u]}")
            else:
                edge_strs.append(f"{u}-{v}")
                
        edge_strs.sort(key=lambda x: (int(x.split('-')[0]), int(x.split('-')[1].split(':')[0])))
        
        text = ", ".join(edge_strs)
        self.edges_entry.delete("1.0", "end")
        self.edges_entry.insert("1.0", text)
        self.update_schedule()

    def paste_from_clipboard(self):
        try:
            clipboard_text = self.root.clipboard_get()
            self.edges_entry.delete("1.0", "end")
            self.edges_entry.insert("1.0", clipboard_text)
            self.update_schedule()
        except tk.TclError:
            pass

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

    # =========================================================
    # АЛГОРИТМЫ ПЛАНИРОВАНИЯ
    # =========================================================
    
    def get_priorities(self):
        priorities = {}
        for node in reversed(list(nx.topological_sort(self.G))):
            succs = list(self.G.successors(node))
            w = self.durations.get(node, 1)
            priorities[node] = w if not succs else w + max(priorities[s] for s in succs)
        return priorities

    def algo_regular_asap(self):
        self.assigned_proc, self.start_time, self.end_time = {}, {}, {}
        p = self.processors.get()
        proc_free = [0] * p
        
        for node in nx.topological_sort(self.G):
            preds = list(self.G.predecessors(node))
            st = max([self.end_time[pr] for pr in preds]) if preds else 0
            dur = self.durations.get(node, 1)
            
            best_p = proc_free.index(min(proc_free))
            st = max(st, proc_free[best_p])
            
            self.assigned_proc[node] = best_p
            self.start_time[node] = st
            self.end_time[node] = st + dur
            proc_free[best_p] = st + dur

    def algo_regular_alap(self):
        T_max = max(self.get_priorities().values()) if self.G.nodes() else 0
        
        self.assigned_proc, self.start_time, self.end_time = {}, {}, {}
        G_rev = self.G.reverse()
        p = self.processors.get()
        proc_free = [T_max] * p
        
        for node in nx.topological_sort(G_rev):
            succs = list(G_rev.predecessors(node))
            et = min([self.start_time[s] for s in succs]) if succs else T_max
            dur = self.durations.get(node, 1)
            
            best_p = proc_free.index(max(proc_free))
            et = min(et, proc_free[best_p])
            
            self.assigned_proc[node] = best_p
            self.end_time[node] = et
            self.start_time[node] = et - dur
            proc_free[best_p] = et - dur

    def form_chains(self):
        G_copy = self.G.copy()
        chains = []
        while G_copy.nodes():
            start_nodes = [n for n in G_copy.nodes() if G_copy.in_degree(n) == 0]
            if not start_nodes: start_nodes = [list(G_copy.nodes())[0]]
            
            current = start_nodes[0]
            chain = [current]
            
            while True:
                succs = list(G_copy.successors(current))
                next_node = None
                for s in succs:
                    if G_copy.in_degree(s) == 1:
                        next_node = s
                        break
                if next_node:
                    chain.append(next_node)
                    current = next_node
                else:
                    break
            G_copy.remove_nodes_from(chain)
            chains.append(chain)
        return chains

    def algo_chain_scheduling(self, alap=False):
        chains = self.form_chains()
        CG = nx.DiGraph()
        chain_durs = {}
        
        node_to_chain = {}
        for i, ch in enumerate(chains):
            c_name = f"C{i}"
            CG.add_node(c_name)
            chain_durs[c_name] = sum(self.durations.get(n, 1) for n in ch)
            for n in ch:
                node_to_chain[n] = c_name
                
        for u, v in self.G.edges():
            cu, cv = node_to_chain[u], node_to_chain[v]
            if cu != cv:
                CG.add_edge(cu, cv)
                
        p = self.processors.get()
        
        if not alap:
            c_assigned, c_start, c_end = {}, {}, {}
            proc_free = [0] * p
            for node in nx.topological_sort(CG):
                preds = list(CG.predecessors(node))
                st = max([c_end[pr] for pr in preds]) if preds else 0
                dur = chain_durs[node]
                best_p = proc_free.index(min(proc_free))
                st = max(st, proc_free[best_p])
                
                c_assigned[node] = best_p
                c_start[node] = st
                c_end[node] = st + dur
                proc_free[best_p] = st + dur
        else:
            c_priorities = {}
            for node in reversed(list(nx.topological_sort(CG))):
                succs = list(CG.successors(node))
                w = chain_durs[node]
                c_priorities[node] = w if not succs else w + max(c_priorities[s] for s in succs)
                
            T_max = max(c_priorities.values()) if c_priorities else 0
            
            c_assigned, c_start, c_end = {}, {}, {}
            CG_rev = CG.reverse()
            proc_free = [T_max] * p
            
            for node in nx.topological_sort(CG_rev):
                succs = list(CG_rev.predecessors(node))
                et = min([c_start[s] for s in succs]) if succs else T_max
                dur = chain_durs[node]
                
                best_p = proc_free.index(max(proc_free))
                et = min(et, proc_free[best_p])
                
                c_assigned[node] = best_p
                c_end[node] = et
                c_start[node] = et - dur
                proc_free[best_p] = et - dur

        self.assigned_proc, self.start_time, self.end_time = {}, {}, {}
        for i, ch in enumerate(chains):
            c_name = f"C{i}"
            curr_t = c_start[c_name]
            for n in ch:
                self.assigned_proc[n] = c_assigned[c_name]
                self.start_time[n] = curr_t
                dur = self.durations.get(n, 1)
                self.end_time[n] = curr_t + dur
                curr_t += dur

    # --- ИСПРАВЛЕННЫЕ МНОГОШАГОВЫЕ АЛГОРИТМЫ ---

    def algo_ms_asap(self):
        # Синхронный барьерный алгоритм (все ждут самого долгого)
        self.assigned_proc, self.start_time, self.end_time = {}, {}, {}
        p = self.processors.get()
        step_time = 0
        scheduled = set()
        priorities = self.get_priorities()

        while len(scheduled) < len(self.G.nodes()):
            ready = []
            for n in self.G.nodes():
                if n in scheduled: continue
                preds = list(self.G.predecessors(n))
                # Проверяем, что все предшественники ЗАВЕРШИЛИСЬ до текущего шага
                if all(self.end_time.get(pr, 0) <= step_time for pr in preds):
                    ready.append(n)

            if not ready:
                step_time += 1
                continue

            ready.sort(key=lambda x: (-priorities[x], str(x)))
            batch = ready[:p] # Берем не более p задач на шаг
            max_dur = 0
            
            for i, task in enumerate(batch):
                proc = i % p
                self.assigned_proc[task] = proc
                self.start_time[task] = step_time
                dur = self.durations.get(task, 1)
                self.end_time[task] = step_time + dur
                max_dur = max(max_dur, dur)
                scheduled.add(task)

            step_time += max_dur if max_dur > 0 else 1

    def algo_ms_alap(self):
        # Синхронный ALAP (через реверс графа и барьер)
        G_rev = self.G.reverse()
        priorities_rev = {}
        for node in reversed(list(nx.topological_sort(G_rev))):
            succs = list(G_rev.successors(node))
            w = self.durations.get(node, 1)
            priorities_rev[node] = w if not succs else w + max(priorities_rev[s] for s in succs)

        self.assigned_proc, self.start_time, self.end_time = {}, {}, {}
        p = self.processors.get()
        step_time = 0
        scheduled = set()
        st_rev, et_rev = {}, {}

        while len(scheduled) < len(G_rev.nodes()):
            ready = []
            for n in G_rev.nodes():
                if n in scheduled: continue
                preds = list(G_rev.predecessors(n))
                if all(et_rev.get(pr, 0) <= step_time for pr in preds):
                    ready.append(n)

            if not ready:
                step_time += 1
                continue

            ready.sort(key=lambda x: (-priorities_rev[x], str(x)))
            batch = ready[:p]
            max_dur = 0
            
            for i, task in enumerate(batch):
                proc = i % p
                self.assigned_proc[task] = proc
                st_rev[task] = step_time
                dur = self.durations.get(task, 1)
                et_rev[task] = step_time + dur
                max_dur = max(max_dur, dur)
                scheduled.add(task)

            step_time += max_dur if max_dur > 0 else 1

        T_max = max(et_rev.values()) if et_rev else 0
        for task in self.G.nodes():
            self.start_time[task] = T_max - et_rev[task]
            self.end_time[task] = T_max - st_rev[task]

    def algo_ms_ls(self):
        # Многошаговый List Scheduling (без барьера, тик за тиком)
        self.assigned_proc, self.start_time, self.end_time = {}, {}, {}
        p = self.processors.get()
        step = 0
        scheduled = set()
        proc_free_time = [0] * p
        priorities = self.get_priorities()

        while len(scheduled) < len(self.G.nodes()):
            ready = []
            for n in self.G.nodes():
                if n in scheduled: continue
                preds = list(self.G.predecessors(n))
                # Проверяем зависимости
                if all(self.end_time.get(pr, 0) <= step for pr in preds):
                    ready.append(n)

            ready.sort(key=lambda x: (-priorities[x], str(x)))
            # Берем только те процессоры, которые УЖЕ СВОБОДНЫ
            free_procs = [i for i in range(p) if proc_free_time[i] <= step]

            for proc in free_procs:
                if not ready: break
                task = ready.pop(0)
                self.assigned_proc[task] = proc
                self.start_time[task] = step
                dur = self.durations.get(task, 1)
                self.end_time[task] = step + dur
                proc_free_time[proc] = step + dur # Обновляем время освобождения
                scheduled.add(task)

            step += 1

    def algo_list_scheduling(self):
        self.assigned_proc, self.start_time, self.end_time = {}, {}, {}
        p = self.processors.get()
        proc_free_time = [0] * p
        scheduled = set()
        priorities = self.get_priorities()
        
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
                dep_time = max([self.end_time[pr] for pr in preds]) if preds else 0
                
                st = max(proc_free_time[proc], dep_time)
                dur = self.durations.get(task, 1)
                et = st + dur
                
                proc_free_time[proc] = et
                self.assigned_proc[task] = proc
                self.start_time[task] = st
                self.end_time[task] = et
                scheduled.add(task)

    # =========================================================

    def update_schedule(self):
        self.G.clear()
        edges, self.durations = self.parse_edges()
        if not edges: return
        self.G.add_edges_from(edges)
        
        if not nx.is_directed_acyclic_graph(self.G):
            messagebox.showerror("Ошибка", "Граф содержит циклы!")
            return

        strat_raw = self.strategy.get().split()[0]
        
        if strat_raw == "ASAP": self.algo_regular_asap()
        elif strat_raw == "ALAP": self.algo_regular_alap()
        elif strat_raw == "C-ASAP": self.algo_chain_scheduling(alap=False)
        elif strat_raw == "C-ALAP": self.algo_chain_scheduling(alap=True)
        elif strat_raw == "MS-ASAP": self.algo_ms_asap()
        elif strat_raw == "MS-ALAP": self.algo_ms_alap()
        elif strat_raw == "LS": self.algo_list_scheduling()
        elif strat_raw == "MS-LS": self.algo_ms_ls()

        # Защита от отрицательных времен
        if self.start_time:
            min_st = min(self.start_time.values())
            if min_st < 0:
                for k in self.start_time: self.start_time[k] -= min_st
                for k in self.end_time: self.end_time[k] -= min_st

        self.max_time = max(self.end_time.values()) if self.end_time else 10.0
        
        self.time_slider.configure(to=self.max_time)
        self.current_time = self.max_time
        self.time_slider.set(self.current_time)
        self.lbl_time.configure(text=f"{self.current_time:.1f}")

        self.draw_graph()
        self.draw_gantt()
        self.update_info()

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
        colors = [cmap(self.assigned_proc.get(n, 0) % 10) for n in self.G.nodes()]
        
        nx.draw_networkx_edges(self.G, pos, ax=self.ax_graph, edge_color="#adb5bd", width=2, arrowsize=20)
        nx.draw_networkx_nodes(self.G, pos, ax=self.ax_graph, node_size=700, node_color=colors, edgecolors="#212529", linewidths=1.5)
        
        labels = {n: f"{n}\n({self.durations.get(n, 1)})" for n in self.G.nodes()}
        nx.draw_networkx_labels(self.G, pos, ax=self.ax_graph, labels=labels, font_size=9, font_color="white", font_weight="bold")

        self.ax_graph.set_axis_off()
        self.ax_graph.margins(0.1)
        self.fig_graph.tight_layout()
        self.canvas_graph.draw_idle()

    def draw_gantt(self):
        self.ax_gantt.clear()
        cmap = matplotlib.colormaps["tab10"]
        p = self.processors.get()
        
        for task, proc in self.assigned_proc.items():
            st = self.start_time[task]
            et = self.end_time[task]
            dur = et - st
            color = cmap(proc % 10)
            
            alpha = 1.0 if st <= self.current_time else 0.15
            edge_alpha = 1.0 if st <= self.current_time else 0.3
            
            edge_color = "#dc3545" if st <= self.current_time < et else "#212529"
            linewidth = 2.5 if st <= self.current_time < et else 1.0

            self.ax_gantt.barh(proc, dur, left=st, height=0.7, color=color, alpha=alpha,
                               edgecolor=edge_color, linewidth=linewidth, zorder=2)
            
            text_color = "white" if alpha > 0.5 else "#6c757d"
            self.ax_gantt.text(st + dur/2, proc, str(task), ha="center", va="center", 
                               color=text_color, fontweight="bold", fontsize=9, zorder=3)

        self.ax_gantt.axvline(x=self.current_time, color="#dc3545", linestyle="-", linewidth=2, alpha=0.8, zorder=4)

        self.ax_gantt.set_yticks(range(p))
        self.ax_gantt.set_yticklabels([f"Процессор {i}" for i in range(p)])
        self.ax_gantt.set_xlabel("Время (шаги)")
        
        self.ax_gantt.spines['top'].set_visible(False)
        self.ax_gantt.spines['right'].set_visible(False)
        
        self.ax_gantt.set_xlim(0, self.max_time + 1)
        self.ax_gantt.set_xticks(range(int(self.max_time) + 2))
        
        self.ax_gantt.grid(True, axis='x', linestyle="--", alpha=0.6, zorder=1)
                
        self.fig_gantt.tight_layout()
        self.canvas_gantt.draw_idle()

    def update_info(self):
        total_time = self.max_time
        strat_name = self.strategy.get()
        
        info = f"Стратегия: {strat_name}\n"
        info += f"Процессоров: {self.processors.get()}\n"
        info += f"Время выполнения (makespan): {total_time:.1f}\n\n"
        
        info += f"{'Опер.':<5} | {'Длит.':<5} | {'Проц.':<5} | {'Старт':<5} | {'Конец':<5}\n"
        info += "-" * 40 + "\n"
        
        try: sorted_nodes = sorted(self.G.nodes(), key=lambda x: int(x) if str(x).isdigit() else str(x))
        except: sorted_nodes = sorted(self.G.nodes())
            
        for node in sorted_nodes:
            if node in self.assigned_proc:
                dur = self.durations.get(node, 1)
                info += f"{str(node):<5} | {dur:<5} | P{self.assigned_proc[node]:<4} | {self.start_time[node]:<5.1f} | {self.end_time[node]:<5.1f}\n"
            
        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", "end")
        self.info_text.insert("1.0", info)
        self.info_text.configure(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = MultiStepSchedulingApp(root)
    root.mainloop()