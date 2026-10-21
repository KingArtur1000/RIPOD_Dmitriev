import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk


# ---------- Цветовая схема ----------
BG      = "#181825"
PANEL   = "#1e1e2e"
PANEL2  = "#313244"
FG      = "#cdd6f4"
MUTED   = "#9399b2"
ACCENT  = "#89b4fa"
ACCENT2 = "#f38ba8"
ACCENT3 = "#a6e3a1"
GRID    = "#45475a"


# ---------- Формулы ----------
def R_basic(a, n):
    """Базовый закон Амдала."""
    n = np.asarray(n, dtype=float)
    return 1.0 / ((1.0 - a) + a / n)


def R_net(a, n, c):
    """Сетевой закон Амдала (модель Гюнтера)."""
    n = np.asarray(n, dtype=float)
    return n / (1.0 + (1.0 - a) * (n - 1.0) + c * n * (n - 1.0))


# ---------- Приложение ----------
class AmdahlApp:
    def __init__(self, root):
        self.root = root
        root.title("Закон Амдала — моделирование параллельного ускорения")
        self._center(1280, 760)
        root.minsize(1000, 600)
        root.configure(bg=BG)

        # Переменные состояния
        self.mode   = tk.StringVar(value="both")
        self.a      = tk.DoubleVar(value=0.90)
        self.nmax   = tk.IntVar(value=128)
        self.c      = tk.DoubleVar(value=0.002)
        self.family = tk.BooleanVar(value=False)
        self.logx   = tk.BooleanVar(value=True)

        self._build_style()
        self._build_ui()
        self.update_plot()

    # -------- Вспомогательное --------
    def _center(self, w, h):
        x = (self.root.winfo_screenwidth()  - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # -------- Стили --------
    def _build_style(self):
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure(".", background=PANEL, foreground=FG, fieldbackground=PANEL2)
        s.configure("TFrame", background=PANEL)
        s.configure("TLabel", background=PANEL, foreground=FG, font=("Segoe UI", 10))
        s.configure("Title.TLabel", font=("Segoe UI", 13, "bold"), foreground=ACCENT)
        s.configure("Sub.TLabel", font=("Segoe UI", 9), foreground=MUTED)
        s.configure("Value.TLabel", font=("Consolas", 10), foreground=ACCENT3)
        s.configure("TRadiobutton", background=PANEL, foreground=FG, focuscolor=PANEL)
        s.map("TRadiobutton", background=[("active", PANEL2)])
        s.configure("TCheckbutton", background=PANEL, foreground=FG, focuscolor=PANEL)
        s.map("TCheckbutton", background=[("active", PANEL2)])
        s.configure("TScale", background=PANEL, troughcolor=PANEL2)
        s.configure("TLabelframe", background=PANEL, foreground=ACCENT, bordercolor=GRID)
        s.configure("TLabelframe.Label", background=PANEL, foreground=ACCENT)
        s.configure("TSeparator", background=GRID)

    # -------- Общий каркас --------
    def _build_ui(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=0, minsize=350)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        left  = ttk.Frame(main, padding=(0, 0, 12, 0))
        left.grid(row=0, column=0, sticky="nsew")
        right = ttk.Frame(main)
        right.grid(row=0, column=1, sticky="nsew")

        self._build_controls(left)
        self._build_plot(right)

    # -------- Панель управления --------
    def _build_controls(self, parent):
        ttk.Label(parent, text="Параметры модели", style="Title.TLabel").pack(anchor="w")
        ttk.Label(parent, text="Закон Амдала — параллельное ускорение",
                  style="Sub.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Separator(parent).pack(fill="x", pady=4)

        mode_frame = ttk.LabelFrame(parent, text=" Режим ", padding=8)
        mode_frame.pack(fill="x", pady=6)
        for val, txt in [("basic",   "Базовый закон"),
                         ("network", "Сетевой закон"),
                         ("both",    "Оба закона")]:
            ttk.Radiobutton(mode_frame, text=txt, value=val, variable=self.mode,
                            command=self.update_plot).pack(anchor="w")

        self._slider(parent, "Доля параллельных вычислений  a",
                     self.a, 0.0, 0.999, lambda v: f"{v:.3f}")
        self._slider(parent, "Максимум процессоров  N",
                     self.nmax, 2, 1024, lambda v: f"{int(v)}", resolution=1)
        self._slider(parent, "Сетевые накладные расходы  c",
                     self.c, 0.0, 0.02, lambda v: f"{v:.4f}")

        opt = ttk.LabelFrame(parent, text=" Отображение ", padding=8)
        opt.pack(fill="x", pady=(8, 4))
        ttk.Checkbutton(opt, text="Семейство кривых (разные a)",
                        variable=self.family, command=self.update_plot).pack(anchor="w")
        ttk.Checkbutton(opt, text="Логарифмическая шкала по n",
                        variable=self.logx, command=self.update_plot).pack(anchor="w")

        info = ttk.LabelFrame(parent, text=" Результаты ", padding=8)
        info.pack(fill="both", expand=True, pady=(8, 0))
        self.info_text = tk.Text(info, height=12, bg=PANEL2, fg=FG, bd=0,
                                 font=("Consolas", 9), wrap="word",
                                 padx=8, pady=6, insertbackground=FG)
        self.info_text.pack(fill="both", expand=True)
        self.info_text.configure(state="disabled")

    def _slider(self, parent, label, var, lo, hi, fmt, resolution=None):
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=(8, 2))
        top = ttk.Frame(frame); top.pack(fill="x")
        ttk.Label(top, text=label).pack(side="left")
        val_lbl = ttk.Label(top, text=fmt(var.get()), style="Value.TLabel")
        val_lbl.pack(side="right")

        scale = ttk.Scale(frame, from_=lo, to=hi, variable=var, orient="horizontal")
        scale.pack(fill="x", pady=(2, 0))

        def on_scale(v):
            if resolution:
                var.set(int(round(float(v) / resolution) * resolution))
            else:
                var.set(float(v))

        scale.configure(command=on_scale)

        def on_var(*_):
            val_lbl.configure(text=fmt(var.get()))
            if hasattr(self, "canvas"):
                self.update_plot()

        var.trace_add("write", on_var)

    # -------- Область графика --------
    def _build_plot(self, parent):
        self.fig = Figure(figsize=(8, 6), dpi=100, facecolor=PANEL2)
        self.ax  = self.fig.add_subplot(111)
        self.ax.set_facecolor(PANEL2)

        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        toolbar = NavigationToolbar2Tk(self.canvas, parent, pack_toolbar=False)
        toolbar.update()
        toolbar.pack(fill="x")

    def _style_axes(self):
        self.ax.tick_params(colors=FG, labelsize=9)
        for spine in self.ax.spines.values():
            spine.set_color(GRID)

    # -------- Отрисовка --------
    def update_plot(self, *args):
        nmin = 1
        nmax = max(2, int(self.nmax.get()))
        n_plot = np.linspace(nmin, nmax, 600)

        a, c = self.a.get(), self.c.get()
        mode = self.mode.get()

        ax = self.ax
        ax.clear()
        self._style_axes()

        # Палитра для семейства кривых
        try:
            cmap = matplotlib.colormaps["viridis"]
        except Exception:
            cmap = matplotlib.cm.get_cmap("viridis")

        def draw(x, y, color, label, ls="-", lw=2.2):
            ax.plot(x, y, color=color, linestyle=ls, linewidth=lw, label=label)

        if self.family.get():
            family_a = [0.5, 0.75, 0.9, 0.99]
            for i, av in enumerate(family_a):
                col = cmap(0.15 + 0.7 * i / (len(family_a) - 1))
                if mode in ("basic", "both"):
                    draw(n_plot, R_basic(av, n_plot), col,
                         f"Базовый, a={av}", "--", 1.6)
                if mode in ("network", "both"):
                    draw(n_plot, R_net(av, n_plot, c), col,
                         f"Сетевой, a={av}", "-", 2.0)
        else:
            if mode in ("basic", "both"):
                draw(n_plot, R_basic(a, n_plot), ACCENT,
                     f"Базовый: a={a:.3f}", "-", 2.6)
            if mode in ("network", "both"):
                draw(n_plot, R_net(a, n_plot, c), ACCENT2,
                     f"Сетевой: a={a:.3f}, c={c:.4f}", "-", 2.6)

        ax.set_xlabel("Число процессоров n", color=FG, fontsize=10)
        ax.set_ylabel("Ускорение  R(n)",      color=FG, fontsize=10)
        ax.set_title("Моделирование закона Амдала", color=FG, fontsize=11, pad=10)
        ax.grid(True, which="both", linestyle=":", alpha=0.35, color=GRID)
        ax.set_xscale("log" if self.logx.get() else "linear")
        ax.set_xlim(nmin, nmax)

        leg = ax.legend(loc="best", facecolor=PANEL, edgecolor=GRID,
                        fontsize=8, framealpha=0.9)
        for t in leg.get_texts():
            t.set_color(FG)

        self.canvas.draw_idle()
        self._update_info(a, c, nmax, mode)

    # -------- Информационная панель --------
    def _update_info(self, a, c, nmax, mode):
        n_test = np.arange(1, nmax + 1)
        lines = [f"a = {a:.3f}   N = {nmax}   c = {c:.4f}", ""]

        if mode in ("basic", "both"):
            Rb    = R_basic(a, n_test)
            limit = 1.0 / (1.0 - a) if a < 1.0 else float("inf")
            lines += [
                "[Базовый закон]",
                f"  R(N)  = {Rb[-1]:.3f}",
                f"  R(∞)  = {limit:.3f}",
                "",
            ]

        if mode in ("network", "both"):
            Rn  = R_net(a, n_test, c)
            idx = int(np.argmax(Rn))
            lines += [
                "[Сетевой закон]",
                f"  R(N)   = {Rn[-1]:.3f}",
                f"  max R  = {Rn[idx]:.3f}  при n = {n_test[idx]}",
                "",
            ]

        lines += [
            "Обозначения:",
            "  R(n) — ускорение",
            "  a    — доля параллельной части",
            "  c    — сетевые накладные расходы",
            "",
            "Формулы:",
            "  Базовый: R = 1 / ((1-a) + a/n)",
            "  Сетевой: R = n / (1 + (1-a)(n-1) + c·n·(n-1))",
        ]

        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", "end")
        self.info_text.insert("1.0", "\n".join(lines))
        self.info_text.configure(state="disabled")


def main():
    root = tk.Tk()
    AmdahlApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()