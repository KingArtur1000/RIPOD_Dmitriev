import tkinter as tk
from tkinter import ttk, messagebox
import xmlrpc.server
import xmlrpc.client
import threading
import networkx as nx
import time

# ---------- Светлая цветовая схема ----------
BG_MAIN   = "#f4f6f9"
BG_PANEL  = "#ffffff"
FG_MAIN   = "#212529"
FG_MUTED  = "#6c757d"
ACCENT    = "#0d6efd"
BORDER    = "#dee2e6"
COLORS    = ["#0d6efd", "#198754", "#dc3545", "#ffc107", "#0dcaf0", "#6f42c1", "#d63384", "#fd7e14"]

# =====================================================================
# КОМПОНЕНТ (COM-СЕРВЕР)
# =====================================================================
class PlannerComponent:
    def ping(self):
        """Служебный метод для проверки связи"""
        return "pong"

    def calculate_plan(self, edges_list, p):
        G = nx.DiGraph()
        edges = []
        for pair in edges_list:
            try:
                u, v = pair.split("-")
                edges.append((u.strip(), v.strip()))
            except ValueError:
                pass
        
        G.add_edges_from(edges)
        if not nx.is_directed_acyclic_graph(G):
            return {"error": "Граф содержит циклы!"}

        priorities = {}
        for node in reversed(list(nx.topological_sort(G))):
            succs = list(G.successors(node))
            priorities[node] = 1 if not succs else 1 + max(priorities[s] for s in succs)

        proc_free_time = [0] * p
        assigned_proc = {}
        start_time = {}
        end_time = {}
        scheduled = set()

        while len(scheduled) < len(G.nodes()):
            ready = [n for n in G.nodes() if n not in scheduled and all(pr in scheduled for pr in G.predecessors(n))]
            if not ready: break
            
            ready.sort(key=lambda x: (-priorities[x], str(x)))
            min_time = min(proc_free_time)
            free_procs = [i for i in range(p) if proc_free_time[i] == min_time]

            for proc in free_procs:
                if not ready: break
                task = ready.pop(0)
                preds = list(G.predecessors(task))
                dep_time = max([end_time[pr] for pr in preds]) if preds else 0
                
                st = max(proc_free_time[proc], dep_time)
                et = st + 1
                
                proc_free_time[proc] = et
                assigned_proc[task] = proc
                start_time[task] = st
                end_time[task] = et
                scheduled.add(task)

        return {
            "assigned_proc": assigned_proc,
            "start_time": start_time,
            "end_time": end_time,
            "makespan": max(end_time.values()) if end_time else 0
        }

def start_com_server():
    # Используем 127.0.0.1 вместо localhost для скорости
    server = xmlrpc.server.SimpleXMLRPCServer(("127.0.0.1", 8000), allow_none=True, logRequests=False)
    # Включаем встроенные методы (listMethods)
    server.register_introspection_functions()
    # Регистрируем наш компонент
    server.register_instance(PlannerComponent())
    print("COM-сервер запущен на порту 8000...")
    server.serve_forever()

# =====================================================================
# КЛИЕНТ (GUI)
# =====================================================================
class ClientApp:
    def __init__(self, root):
        self.root = root
        root.title("Лабораторная 8: Клиент-Сервер (COM архитектура)")
        self._center(1400, 850)
        root.minsize(1000, 650)
        root.configure(bg=BG_MAIN)

        self.default_edges = "1-2, 1-3, 2-4, 3-4, 4-5, 3-6, 5-7, 6-7"
        
        # Подключение к серверу
        self.proxy = xmlrpc.client.ServerProxy("http://127.0.0.1:8000/", allow_none=True)
        
        self._build_style()
        self._build_ui()
        
        self.check_connection()

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
        main.columnconfigure(0, weight=0, minsize=400)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        left = ttk.Frame(main, padding=15)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        
        right = ttk.Frame(main, style="Main.TFrame")
        right.grid(row=0, column=1, sticky="nsew")

        self._build_controls(left)
        self._build_visualizer(right)

    def _build_controls(self, parent):
        ttk.Label(parent, text="COM Клиент", style="Title.TLabel").pack(anchor="w")
        ttk.Label(parent, text="Удаленный вызов планировщика", style="Sub.TLabel").pack(anchor="w", pady=(0, 10))

        self.conn_frame = ttk.Frame(parent)
        self.conn_frame.pack(fill="x", pady=5)
        self.conn_lbl = tk.Label(self.conn_frame, text=" Статус: Проверка... ", bg="#ffc107", fg="#000", font=("Segoe UI", 9, "bold"), padx=10, pady=4)
        self.conn_lbl.pack(anchor="w")

        cfg_frame = ttk.LabelFrame(parent, text=" Параметры ", padding=10)
        cfg_frame.pack(fill="x", pady=10)
        
        ttk.Label(cfg_frame, text="Количество процессоров:").pack(anchor="w")
        self.proc_var = tk.IntVar(value=2)
        ttk.Spinbox(cfg_frame, from_=1, to=8, textvariable=self.proc_var, width=5).pack(anchor="w", pady=5)

        input_frame = ttk.LabelFrame(parent, text=" Граф (в виде A-B) ", padding=10)
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
        ttk.Button(btn_frame, text="Отправить на сервер", command=self.request_plan).pack(side="left", fill="x", expand=True)

        log_frame = ttk.LabelFrame(parent, text=" Журнал интерфейса ", padding=10)
        log_frame.pack(fill="both", expand=True, pady=(10, 0))
        
        self.log_text = tk.Text(log_frame, height=8, bg=BG_MAIN, fg=FG_MAIN, bd=1, 
                                 relief="solid", font=("Consolas", 9), wrap="word", 
                                 padx=8, pady=8, highlightthickness=1, highlightbackground=BORDER)
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")

    def _build_visualizer(self, parent):
        viz_frame = ttk.LabelFrame(parent, text=" Диаграмма Ганта (ответ от сервера) ", padding=5)
        viz_frame.pack(fill="both", expand=True)
        
        self.canvas = tk.Canvas(viz_frame, bg="#ffffff", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

    def check_connection(self):
        try:
            # Вызываем наш собственный метод ping, а не system.listMethods
            response = self.proxy.ping()
            if response == "pong":
                self.conn_lbl.configure(text=" Статус: Подключено (Порт 8000) ", bg="#198754", fg="#fff")
        except Exception as e:
            self.conn_lbl.configure(text=" Статус: Нет связи с сервером ", bg="#dc3545", fg="#fff")
        self.root.after(2000, self.check_connection)

    def paste_from_clipboard(self):
        try:
            text = self.root.clipboard_get()
            self.edges_entry.delete("1.0", "end")
            self.edges_entry.insert("1.0", text)
        except tk.TclError:
            pass

    def log(self, msg):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def request_plan(self):
        text = self.edges_entry.get("1.0", "end-1c").replace("\n", ",").replace(" ", "")
        edges = [pair for pair in text.split(",") if pair]
        
        if not edges:
            messagebox.showwarning("Внимание", "Нет данных.")
            return

        p = self.proc_var.get()
        self.log(f"Вызов компонента: calculate_plan(edges={len(edges)}, p={p})")

        try:
            result = self.proxy.calculate_plan(edges, p)
            
            if "error" in result:
                self.log(f"Ошибка от компонента: {result['error']}")
                messagebox.showerror("Ошибка", result['error'])
                return

            self.log("Ответ от компонента получен успешно.")
            self.log(f"Makespan: {result['makespan']}")
            
            self.draw_gantt(result['assigned_proc'], result['start_time'], result['end_time'], result['makespan'], p)

        except Exception as e:
            self.log(f"Ошибка RPC: {e}")
            messagebox.showerror("Ошибка подключения", f"Не удалось связаться с COM-компонентом.\nДетали: {e}")

    def draw_gantt(self, assigned_proc, start_time, end_time, makespan, p):
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 50: return

        time_scale = (w - 150) / max(makespan, 1)

        for i in range(int(makespan) + 2):
            x = 100 + i * time_scale
            self.canvas.create_line(x, 30, x, h-30, fill="#dee2e6", dash=(4, 4))
            self.canvas.create_text(x, 15, text=f"{i}s", fill=FG_MUTED, font=("Segoe UI", 9))

        y_offset = 50
        line_height = 50

        for task, proc in assigned_proc.items():
            st = start_time[task]
            et = end_time[task]
            dur = et - st
            
            y = y_offset + proc * line_height
            x1 = 100 + st * time_scale
            x2 = 100 + et * time_scale
            
            color = COLORS[proc % len(COLORS)]
            self.canvas.create_rectangle(x1, y, x2, y+30, fill=color, outline="white", width=2)
            self.canvas.create_text((x1+x2)/2, y+15, text=f"Оп. {task}", fill="white", font=("Segoe UI", 9, "bold"))
            
        for i in range(p):
            self.canvas.create_text(50, 50 + i * line_height + 15, text=f"Процессор {i}", fill=FG_MAIN, font=("Segoe UI", 9))

if __name__ == "__main__":
    server_thread = threading.Thread(target=start_com_server, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    root = tk.Tk()
    app = ClientApp(root)
    root.mainloop()