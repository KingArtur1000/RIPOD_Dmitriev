import tkinter as tk
from tkinter import ttk, messagebox
import networkx as nx
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

# ---------- Светлая цветовая схема ----------
BG_MAIN   = "#f4f6f9"  # Общий фон приложения
BG_PANEL  = "#ffffff"  # Фон панелей
FG_MAIN   = "#212529"  # Темный текст
FG_MUTED  = "#6c757d"  # Серый текст
ACCENT    = "#0d6efd"  # Синий акцент
ACCENT2   = "#198754"  # Зеленый
BORDER    = "#dee2e6"  # Границы
GRAPH_BG  = "#ffffff"  # Фон графика


class ASAPApp:
    def __init__(self, root):
        self.root = root
        root.title("Лабораторная 2: Планирование ASAP")
        self._center(1300, 800)
        root.minsize(1000, 600)
        root.configure(bg=BG_MAIN)

        self.G = nx.DiGraph()
        self.default_edges = "1-2, 1-3, 2-4, 3-4, 4-5, 3-6, 5-7, 6-7"
        
        self._build_style()
        self._build_ui()
        self.update_graph()

    def _center(self, w, h):
        """Центрирование окна на экране"""
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _build_style(self):
        """Настройка стилей ttk для светлой темы"""
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
        
        # Кнопки
        s.configure("TButton", font=("Segoe UI", 10, "bold"), background=ACCENT, foreground="white", borderwidth=0, padding=6)
        s.map("TButton", background=[("active", "#0b5ed7")])
        
        # Таблица (Treeview)
        s.configure("Treeview", background=BG_PANEL, foreground=FG_MAIN, fieldbackground=BG_PANEL, rowheight=28, font=("Segoe UI", 10))
        s.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background=BG_MAIN, foreground=FG_MAIN, padding=4)
        
        # Рамки
        s.configure("TLabelframe", background=BG_PANEL, foreground=FG_MAIN, bordercolor=BORDER)
        s.configure("TLabelframe.Label", background=BG_PANEL, foreground=FG_MAIN, font=("Segoe UI", 10, "bold"))

    def _build_ui(self):
        # Главный контейнер
        main = ttk.Frame(self.root, padding=15, style="Main.TFrame")
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=0, minsize=350)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        # Левая панель управления
        left = ttk.Frame(main, padding=15)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        
        # Правая панель (Граф + Таблица)
        right = ttk.Frame(main, style="Main.TFrame")
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=3)
        right.rowconfigure(1, weight=1)

        self._build_controls(left)
        self._build_graph_area(right)
        self._build_table_area(right)

    def _build_controls(self, parent):
        ttk.Label(parent, text="Планировщик ASAP", style="Title.TLabel").pack(anchor="w")
        ttk.Label(parent, text="Синхронное планирование процессов", style="Sub.TLabel").pack(anchor="w", pady=(0, 15))

        # Ввод данных
        input_frame = ttk.LabelFrame(parent, text=" Входные данные (Граф) ", padding=10)
        input_frame.pack(fill="x", pady=5)
        
        ttk.Label(input_frame, text="Зависимости (Формат: A-B, где A→B):").pack(anchor="w", pady=(0, 5))
        self.edges_entry = tk.Text(input_frame, height=6, width=30, font=("Consolas", 10), 
                                   bg=BG_MAIN, fg=FG_MAIN, relief="solid", bd=1, 
                                   highlightthickness=1, highlightbackground=BORDER)
        self.edges_entry.pack(fill="x")
        self.edges_entry.insert("1.0", self.default_edges)
        
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        ttk.Button(btn_frame, text="Построить план", command=self.update_graph).pack(side="left", fill="x", expand=True)
        
        # Результаты (Анализ)
        info_frame = ttk.LabelFrame(parent, text=" Анализ ", padding=10)
        info_frame.pack(fill="both", expand=True, pady=(15, 0))
        
        self.info_text = tk.Text(info_frame, height=10, bg=BG_MAIN, fg=FG_MAIN, bd=1, 
                                 relief="solid", font=("Segoe UI", 10), wrap="word", 
                                 padx=10, pady=10, highlightthickness=1, highlightbackground=BORDER)
        self.info_text.pack(fill="both", expand=True)
        self.info_text.configure(state="disabled")

    def _build_graph_area(self, parent):
        frame = ttk.Frame(parent, padding=10)
        frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        
        self.fig = Figure(figsize=(6, 4), dpi=100, facecolor=GRAPH_BG)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor(GRAPH_BG)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        
        toolbar = NavigationToolbar2Tk(self.canvas, frame, pack_toolbar=False)
        toolbar.update()
        toolbar.pack(fill="x")

    def _build_table_area(self, parent):
        frame = ttk.LabelFrame(parent, text=" Последовательно-параллельный план ", padding=10)
        frame.grid(row=1, column=0, sticky="nsew")
        
        columns = ("level", "operations", "count")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=5)
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
        """Парсинг строки зависимостей в список ребер"""
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
        """Основной метод: расчет ASAP и запуск отрисовки"""
        self.G.clear()
        edges = self.parse_edges()
        
        if not edges:
            messagebox.showwarning("Внимание", "Введите хотя бы одну зависимость (например, 1-2)")
            return

        self.G.add_edges_from(edges)

        if not nx.is_directed_acyclic_graph(self.G):
            messagebox.showerror("Ошибка", "Граф содержит циклы!\nАлгоритм ASAP применим только к ациклическим графам (DAG).")
            return

        # --- АЛГОРИТМ ASAP ---
        levels = {}
        for node in nx.topological_sort(self.G):
            preds = list(self.G.predecessors(node))
            if not preds:
                levels[node] = 0
            else:
                levels[node] = max(levels[p] for p in preds) + 1

        # Группировка по ярусам (шагам)
        schedule = {}
        for node, lvl in levels.items():
            schedule.setdefault(lvl, []).append(node)

        self.draw_graph(levels)
        self.update_table(schedule)
        self.update_info(schedule, len(edges))

    def draw_graph(self, levels):
        """Кастомная отрисовка графа с выравниванием по шагам"""
        self.ax.clear()
        
        # --- АЛГОРИТМ РАССТАНОВКИ ---
        pos = {}
        max_level = max(levels.values()) if levels else 0
        
        # Группируем узлы по их уровню (шагу)
        nodes_by_level = {}
        for node, lvl in levels.items():
            nodes_by_level.setdefault(lvl, []).append(node)
            
        # Расставляем узлы по координатам
        for lvl, nodes in nodes_by_level.items():
            # Сортируем узлы, чтобы они не менялись местами при перерисовке
            try:
                nodes.sort(key=lambda x: int(x) if str(x).isdigit() else str(x))
            except:
                nodes.sort()
                
            count = len(nodes)
            for i, node in enumerate(nodes):
                x = lvl
                # Центрируем узлы по вертикали (0 - верхний, отрицательные - ниже)
                y = (i - (count - 1) / 2.0) * -1.5
                pos[node] = (x, y)
        # -----------------------------

        # Рисуем вертикальные линии (шаги) для наглядности
        for lvl in range(max_level + 1):
            self.ax.axvline(x=lvl, color="#dee2e6", linestyle="--", zorder=0, linewidth=1.5)
            self.ax.text(lvl, 1.2, f"Шаг {lvl}", ha="center", va="bottom", 
                         fontsize=11, color=FG_MUTED, fontweight="bold")

        # Рисуем ребра (стрелки)
        nx.draw_networkx_edges(self.G, pos, ax=self.ax, edge_color="#6c757d", 
                               width=2, arrowsize=20, arrows=True, node_size=900)

        # Настройка цветов вершин (градиент от светлого к темно-синему)
        unique_levels = sorted(set(levels.values()))
        cmap = matplotlib.colormaps["Blues"]
        denom = max(1, max(unique_levels))
        colors = [cmap(0.3 + 0.5 * (levels[n] / denom)) for n in self.G.nodes()]

        # Рисуем сами вершины
        nx.draw_networkx_nodes(self.G, pos, ax=self.ax, node_size=900, 
                               node_color=colors, edgecolors="#212529", linewidths=1.5)
        
        # Подписи вершин
        nx.draw_networkx_labels(self.G, pos, ax=self.ax, font_size=13, 
                                font_color="#000000", font_weight="bold")

        # Настройка границ, чтобы ничего не обрезалось
        self.ax.set_axis_off()
        self.ax.margins(x=0.05, y=0.15)
        self.fig.tight_layout()
        self.canvas.draw_idle()

    def update_table(self, schedule):
        """Обновление таблицы последовательно-параллельного плана"""
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for lvl in sorted(schedule.keys()):
            ops = sorted(schedule[lvl], key=lambda x: int(x) if x.isdigit() else x)
            self.tree.insert("", "end", values=(f"Шаг {lvl}", ", ".join(ops), len(ops)))

    def update_info(self, schedule, edge_count):
        """Обновление текстовой панели с аналитикой"""
        total_ops = sum(len(ops) for ops in schedule.values())
        parallel_steps = len(schedule)
        max_parallel = max(len(ops) for ops in schedule.values())
        
        # Вычисление эффективности
        efficiency = (total_ops / (parallel_steps * max_parallel)) * 100 if max_parallel > 0 else 0
        
        info = (
            f"Всего операций: {total_ops}\n"
            f"Зависимостей (ребер): {edge_count}\n"
            f"Временных шагов (длина плана): {parallel_steps}\n"
            f"Макс. параллельных операций: {max_parallel}\n"
            f"Эффективность использования ярусов: {efficiency:.1f}%\n\n"
            "Алгоритм ASAP минимизирует время выполнения за счет "
            "максимального распараллеливания."
        )
        
        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", "end")
        self.info_text.insert("1.0", info)
        self.info_text.configure(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = ASAPApp(root)
    root.mainloop()