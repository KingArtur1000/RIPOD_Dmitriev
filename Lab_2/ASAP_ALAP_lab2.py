import tkinter as tk
from tkinter import ttk, messagebox
import networkx as nx
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.patches import Patch

# ---------- Светлая цветовая схема ----------
BG_MAIN   = "#f4f6f9"
BG_PANEL  = "#ffffff"
FG_MAIN   = "#212529"
FG_MUTED  = "#6c757d"
ACCENT    = "#0d6efd"
BORDER    = "#dee2e6"
GRAPH_BG  = "#ffffff"


class ASAP_ALAP_App:
    def __init__(self, root):
        self.root = root
        root.title("Лабораторная 2: Планирование ASAP и ALAP")
        self._center(1400, 900)
        root.minsize(1050, 700)
        root.configure(bg=BG_MAIN)

        self.G = nx.DiGraph()
        self.default_edges = "1-7, 2-8, 3-9, 4-10, 5-9, 6-12, 7-10, 8-10, 9-11, 10-13, 11-13, 12-13, 13-14"
        
        self.schedule_mode = tk.StringVar(value="ASAP")
        
        self._build_style()
        self._build_ui()
        self.update_graph()

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
        
        s.configure("TRadiobutton", background=BG_PANEL, foreground=FG_MAIN, font=("Segoe UI", 10))
        s.map("TRadiobutton", background=[("active", BG_MAIN)])
        
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
        # Настраиваем строки для правой части (Граф, Гантт, Таблица)
        right.rowconfigure(0, weight=3) # Граф
        right.rowconfigure(1, weight=2) # Гантт
        right.rowconfigure(2, weight=1) # Таблица

        self._build_controls(left)
        self._build_graph_area(right)
        self._build_gantt_area(right)
        self._build_table_area(right)

    def _build_controls(self, parent):
        ttk.Label(parent, text="Планировщик ASAP / ALAP", style="Title.TLabel").pack(anchor="w")
        ttk.Label(parent, text="Синхронное планирование процессов", style="Sub.TLabel").pack(anchor="w", pady=(0, 10))

        mode_frame = ttk.LabelFrame(parent, text=" Режим отображения ", padding=8)
        mode_frame.pack(fill="x", pady=(0, 10))
        ttk.Radiobutton(mode_frame, text="ASAP (Как можно раньше)", value="ASAP", 
                        variable=self.schedule_mode, command=self.update_graph).pack(anchor="w", pady=2)
        ttk.Radiobutton(mode_frame, text="ALAP (Как можно позже)", value="ALAP", 
                        variable=self.schedule_mode, command=self.update_graph).pack(anchor="w", pady=2)

        input_frame = ttk.LabelFrame(parent, text=" Входные данные (Граф) ", padding=10)
        input_frame.pack(fill="x", pady=5)
        
        ttk.Label(input_frame, text="Зависимости (Формат: A-B, где A→B):").pack(anchor="w", pady=(0, 5))
        
        self.edges_entry = tk.Text(input_frame, height=5, width=30, font=("Consolas", 10), 
                                   bg=BG_MAIN, fg=FG_MAIN, relief="solid", bd=1, 
                                   highlightthickness=1, highlightbackground=BORDER)
        self.edges_entry.pack(fill="x")
        self.edges_entry.insert("1.0", self.default_edges)
        
        # Контекстное меню (ПКМ)
        self.context_menu = tk.Menu(self.edges_entry, tearoff=0)
        self.context_menu.add_command(label="Вставить", command=lambda: self.edges_entry.event_generate("<<Paste>>"))
        self.context_menu.add_command(label="Очистить", command=lambda: self.edges_entry.delete("1.0", "end"))
        
        def show_context_menu(event):
            self.context_menu.post(event.x_root, event.y_root)

        self.edges_entry.bind("<Button-3>", show_context_menu)
        self.edges_entry.bind("<Button-2>", show_context_menu)
        self.edges_entry.bind("<Control-v>", lambda e: self.edges_entry.event_generate("<<Paste>>"))
        self.edges_entry.bind("<Command-v>", lambda e: self.edges_entry.event_generate("<<Paste>>"))
        
        paste_btn = ttk.Button(input_frame, text="📋 Вставить из буфера", command=self.paste_from_clipboard)
        paste_btn.pack(fill="x", pady=(5, 0))

        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        ttk.Button(btn_frame, text="Пересчитать план", command=self.update_graph).pack(side="left", fill="x", expand=True)
        
        info_frame = ttk.LabelFrame(parent, text=" Анализ и резервы времени ", padding=10)
        info_frame.pack(fill="both", expand=True, pady=(10, 0))
        
        self.info_text = tk.Text(info_frame, height=12, bg=BG_MAIN, fg=FG_MAIN, bd=1, 
                                 relief="solid", font=("Consolas", 9), wrap="word", 
                                 padx=8, pady=8, highlightthickness=1, highlightbackground=BORDER)
        self.info_text.pack(fill="both", expand=True)
        self.info_text.configure(state="disabled")

    def paste_from_clipboard(self):
        try:
            clipboard_text = self.root.clipboard_get()
            self.edges_entry.delete("1.0", "end")
            self.edges_entry.insert("1.0", clipboard_text)
            self.update_graph()
        except tk.TclError:
            messagebox.showwarning("Буфер обмена", "Буфер обмена пуст или не содержит текста.")

    def _build_graph_area(self, parent):
        frame = ttk.Frame(parent, padding=5)
        frame.grid(row=0, column=0, sticky="nsew", pady=(0, 5))
        
        self.fig = Figure(figsize=(6, 3), dpi=100, facecolor=GRAPH_BG)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor(GRAPH_BG)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _build_gantt_area(self, parent):
        frame = ttk.LabelFrame(parent, text=" Диаграмма Ганта (с выделением критического пути) ", padding=5)
        frame.grid(row=1, column=0, sticky="nsew", pady=5)
        
        self.fig_gantt = Figure(figsize=(6, 2.5), dpi=100, facecolor=GRAPH_BG)
        self.ax_gantt = self.fig_gantt.add_subplot(111)
        self.ax_gantt.set_facecolor(GRAPH_BG)
        
        self.canvas_gantt = FigureCanvasTkAgg(self.fig_gantt, master=frame)
        self.canvas_gantt.get_tk_widget().pack(fill="both", expand=True)

    def _build_table_area(self, parent):
        frame = ttk.LabelFrame(parent, text=" Последовательно-параллельный план ", padding=5)
        frame.grid(row=2, column=0, sticky="nsew", pady=(5, 0))
        
        columns = ("level", "operations", "count")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=4)
        self.tree.heading("level", text="Временной шаг (Ярус)")
        self.tree.heading("operations", text="Операции (выполняются параллельно)")
        self.tree.heading("count", text="Кол-во")
        
        self.tree.column("level", width=150, anchor="center")
        self.tree.column("operations", width=400, anchor="center")
        self.tree.column("count", width=100, anchor="center")
        
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

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

    def update_graph(self):
        self.G.clear()
        edges = self.parse_edges()
        
        if not edges:
            return

        self.G.add_edges_from(edges)

        if not nx.is_directed_acyclic_graph(self.G):
            return

        # --- 1. РАСЧЕТ ASAP ---
        levels_asap = {}
        for node in nx.topological_sort(self.G):
            preds = list(self.G.predecessors(node))
            if not preds:
                levels_asap[node] = 0
            else:
                levels_asap[node] = max(levels_asap[p] for p in preds) + 1
                
        max_time = max(levels_asap.values()) if levels_asap else 0

        # --- 2. РАСЧЕТ ALAP ---
        levels_alap = {}
        for node in reversed(list(nx.topological_sort(self.G))):
            succs = list(self.G.successors(node))
            if not succs:
                levels_alap[node] = max_time
            else:
                levels_alap[node] = min(levels_alap[s] for s in succs) - 1

        # --- 3. РЕЗЕРВ ---
        slack = {node: levels_alap[node] - levels_asap[node] for node in self.G.nodes()}

        # --- 4. ОТРИСОВКА ---
        current_mode = self.schedule_mode.get()
        active_levels = levels_asap if current_mode == "ASAP" else levels_alap

        schedule = {}
        for node, lvl in active_levels.items():
            schedule.setdefault(lvl, []).append(node)

        self.draw_graph(active_levels)
        self.draw_gantt(levels_asap, levels_alap, slack)
        self.update_table(schedule)
        self.update_info(levels_asap, levels_alap, slack, current_mode)

    def draw_graph(self, levels):
        self.ax.clear()
        
        pos = {}
        max_level = max(levels.values()) if levels else 0
        
        nodes_by_level = {}
        for node, lvl in levels.items():
            nodes_by_level.setdefault(lvl, []).append(node)
            
        for lvl, nodes in nodes_by_level.items():
            try:
                nodes.sort(key=lambda x: int(x) if str(x).isdigit() else str(x))
            except:
                nodes.sort()
                
            count = len(nodes)
            for i, node in enumerate(nodes):
                x = lvl
                y = (i - (count - 1) / 2.0) * -1.5
                pos[node] = (x, y)

        global_max_y = max([y for x, y in pos.values()]) if pos else 0
        label_y = global_max_y + 1.2
        
        for lvl in range(max_level + 1):
            self.ax.axvline(x=lvl, color="#dee2e6", linestyle="--", zorder=0, linewidth=1.5)
            self.ax.text(lvl, label_y, f"Шаг {lvl}", ha="center", va="bottom", 
                         fontsize=10, color=FG_MUTED, fontweight="bold")

        nx.draw_networkx_edges(self.G, pos, ax=self.ax, edge_color="#6c757d", 
                               width=2, arrowsize=20, arrows=True, node_size=700)

        unique_levels = sorted(set(levels.values()))
        cmap = matplotlib.colormaps["Blues"]
        denom = max(1, max(unique_levels))
        colors = [cmap(0.3 + 0.5 * (levels[n] / denom)) for n in self.G.nodes()]

        nx.draw_networkx_nodes(self.G, pos, ax=self.ax, node_size=700, 
                               node_color=colors, edgecolors="#212529", linewidths=1.5)
        
        nx.draw_networkx_labels(self.G, pos, ax=self.ax, font_size=11, 
                                font_color="#000000", font_weight="bold")

        self.ax.set_axis_off()
        self.ax.margins(x=0.05, y=0.15) 
        self.fig.tight_layout()
        self.canvas.draw_idle()

    def draw_gantt(self, levels_asap, levels_alap, slack):
        self.ax_gantt.clear()
        if not levels_asap: return

        try:
            sorted_nodes = sorted(self.G.nodes(), key=lambda x: int(x) if str(x).isdigit() else str(x))
        except:
            sorted_nodes = sorted(self.G.nodes())

        y_positions = range(len(sorted_nodes))

        for i, node in enumerate(sorted_nodes):
            asap_start = levels_asap[node]
            s = slack[node]
            
            # Основная задача (выполнение по ASAP)
            if s == 0:
                # Критический путь — красный
                self.ax_gantt.barh(i, 1, left=asap_start, color="#dc3545", edgecolor="#a71d2a", height=0.6, zorder=3)
            else:
                # Есть резерв — синий
                self.ax_gantt.barh(i, 1, left=asap_start, color="#0d6efd", edgecolor="#0b5ed7", height=0.6, zorder=3)
                
                # Резерв (заштрихованная область от ASAP до ALAP)
                self.ax_gantt.barh(i, s, left=asap_start + 1, color="#e9ecef", edgecolor="#ced4da", 
                                   height=0.6, zorder=2, hatch='//')

        self.ax_gantt.set_yticks(y_positions)
        self.ax_gantt.set_yticklabels(sorted_nodes)
        self.ax_gantt.set_xlabel("Время (шаги)")

        max_time = max(levels_alap.values()) + 1 if levels_alap else 10
        self.ax_gantt.set_xlim(0, max_time + 1)
        self.ax_gantt.set_xticks(range(max_time + 2))

        self.ax_gantt.grid(axis='x', linestyle='--', alpha=0.7, zorder=1)
        self.ax_gantt.spines['top'].set_visible(False)
        self.ax_gantt.spines['right'].set_visible(False)

        # Легенда (теперь в правом нижнем углу)
        legend_elements = [
            Patch(facecolor='#dc3545', edgecolor='#a71d2a', label='Критическая задача (ASAP)'),
            Patch(facecolor='#0d6efd', edgecolor='#0b5ed7', label='Задача с резервом (ASAP)'),
            Patch(facecolor='#e9ecef', edgecolor='#ced4da', hatch='//', label='Резерв до ALAP')
        ]
        self.ax_gantt.legend(handles=legend_elements, loc='lower right', fontsize=8, framealpha=0.9)

        self.fig_gantt.tight_layout()
        self.canvas_gantt.draw_idle()

    def update_table(self, schedule):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for lvl in sorted(schedule.keys()):
            ops = sorted(schedule[lvl], key=lambda x: int(x) if x.isdigit() else x)
            self.tree.insert("", "end", values=(f"Шаг {lvl}", ", ".join(ops), len(ops)))

    def update_info(self, levels_asap, levels_alap, slack, current_mode):
        total_ops = len(self.G.nodes())
        max_time = max(levels_asap.values()) if levels_asap else 0
        
        critical_path = [str(node) for node in self.G.nodes() if slack[node] == 0]
        try:
            critical_path.sort(key=lambda x: int(x) if x.isdigit() else x)
        except:
            critical_path.sort()

        info = f"Текущий режим: {current_mode}\n"
        info += f"Длина критического пути: {max_time + 1} шагов\n"
        info += f"Критические операции: {', '.join(critical_path)}\n\n"
        
        info += f"{'Опер.':<6} | {'ASAP':<5} | {'ALAP':<5} | {'Резерв':<6}\n"
        info += "-" * 32 + "\n"
        
        try:
            sorted_nodes = sorted(self.G.nodes(), key=lambda x: int(x) if str(x).isdigit() else str(x))
        except:
            sorted_nodes = sorted(self.G.nodes())
            
        for node in sorted_nodes:
            info += f"{str(node):<6} | {levels_asap[node]:<5} | {levels_alap[node]:<5} | {slack[node]:<6}\n"
            
        info += "\n* Резерв = ALAP - ASAP.\n"
        info += "* Операции с резервом 0 лежат на критическом пути."
        
        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", "end")
        self.info_text.insert("1.0", info)
        self.info_text.configure(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = ASAP_ALAP_App(root)
    root.mainloop()