import tkinter as tk
from tkinter import font as tkfont

# ── Colours (matching the HTML dark-green theme) ──────────────────────────────
BG       = "#050a05"
CARD_BG  = "#071007"
INPUT_BG = "#021802"
BTN_BG   = "#048d26"
BTN_HOV  = "#06a32e"
FG       = "#c8ffc8"
FG_DIM   = "#88ff88"
ACCENT   = "#00ff41"
HR_COL   = "#1a3d1a"

# ── Instrument data ───────────────────────────────────────────────────────────
INSTRUMENTS = [
    ("UB (Ultra T-Bond)", "UB",  1000,  32, 5940),
    ("ZB (30Y)",          "ZB",  1000,  32, 4200),
    ("ZN (10Y)",          "ZN",  1000,  64, 2156),
    ("ZF (5Y)",           "ZF",  1000, 128, 1438),
    ("ZT (2Y)",           "ZT",  2000, 256, 1380),
]

# ── Helpers ───────────────────────────────────────────────────────────────────
def bond_to_decimal(price: str, tick_denom: int) -> float:
    price = price.strip()
    if "'" in price:
        whole_s, frac_s = price.split("'", 1)
        whole = float(whole_s) if whole_s else 0.0
        frac  = float(frac_s)  if frac_s  else 0.0
        return whole + frac / tick_denom
    return float(price) if price else 0.0

def decimal_to_bond(price: float, tick_denom: int) -> str:
    if price < 0:
        return ""
    whole = int(price)
    frac  = price - whole
    ticks = round(frac * tick_denom)
    digits = 2 if tick_denom == 32 else 3
    return f"{whole}'{str(ticks).zfill(digits)}"


# ── Main App ──────────────────────────────────────────────────────────────────
class BondCalcApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Treasury Futures Position Size Calculator")
        self.configure(bg=BG)
        self.resizable(False, False)

        # current instrument state
        self.point_value = tk.IntVar(value=1000)
        self.tick_denom  = tk.IntVar(value=32)

        self._build_ui()
        self._select_instrument(0)          # activate first tab

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        card = tk.Frame(self, bg=CARD_BG, bd=0, highlightthickness=1,
                        highlightbackground=ACCENT, padx=28, pady=22)
        card.pack(padx=20, pady=20)

        # Title
        tk.Label(card, text="Futures Position Size Calculator",
                 bg=CARD_BG, fg=ACCENT,
                 font=("Arial", 15, "bold")).pack(pady=(0, 12))

        # ── Tabs ──────────────────────────────────────────────────────────────
        tab_frame = tk.Frame(card, bg=CARD_BG)
        tab_frame.pack(fill="x", pady=(0, 10))

        self.tab_btns = []
        for i, (label, *_) in enumerate(INSTRUMENTS):
            btn = tk.Button(
                tab_frame, text=label, bg=INPUT_BG, fg=FG,
                activebackground="#0f260f", activeforeground=FG,
                relief="flat", bd=1, highlightthickness=1,
                highlightbackground=ACCENT, cursor="hand2",
                font=("Arial", 9),
                command=lambda idx=i: self._select_instrument(idx)
            )
            btn.pack(side="left", expand=True, fill="x", padx=2)
            self.tab_btns.append(btn)

        # ── Spec bar ─────────────────────────────────────────────────────────
        self.spec_var = tk.StringVar()
        tk.Label(card, textvariable=self.spec_var,
                 bg=CARD_BG, fg=FG_DIM, font=("Arial", 11),
                 anchor="w").pack(fill="x", pady=(0, 8))

        # ── Input fields ──────────────────────────────────────────────────────
        self.account_var = tk.StringVar(value="25000")
        self.risk_var    = tk.StringVar(value="2")
        self.margin_var  = tk.StringVar(value="5940")
        self.entry_var   = tk.StringVar()
        self.stop_var    = tk.StringVar()

        fields = [
            ("Account Balance ($)", self.account_var),
            ("Risk %",              self.risk_var),
            ("Margin ($)",          self.margin_var),
            ("Entry Price",         self.entry_var,  "e.g. 117'02"),
            ("Stop Loss",           self.stop_var,   "e.g. 116'165"),
        ]

        self.entries = {}
        for item in fields:
            lbl_text = item[0]
            var       = item[1]
            ph        = item[2] if len(item) > 2 else None

            tk.Label(card, text=lbl_text, bg=CARD_BG, fg=FG_DIM,
                     font=("Arial", 10), anchor="w").pack(fill="x")

            ent = tk.Entry(card, textvariable=var,
                           bg=INPUT_BG, fg=FG, insertbackground=FG,
                           relief="flat", bd=0, highlightthickness=1,
                           highlightbackground=ACCENT,
                           font=("Arial", 12))
            ent.pack(fill="x", ipady=6, pady=(2, 8))

            if ph:
                self._add_placeholder(ent, var, ph)

            self.entries[lbl_text] = ent

        # ── Calculate button ──────────────────────────────────────────────────
        calc_btn = tk.Button(
            card, text="CALCULATE", bg=BTN_BG, fg="white",
            activebackground=BTN_HOV, activeforeground="white",
            relief="flat", bd=0, cursor="hand2",
            font=("Arial", 13, "bold"),
            command=self._calculate
        )
        calc_btn.pack(fill="x", ipady=8, pady=(4, 12))

        # ── Results panel ─────────────────────────────────────────────────────
        self.results_frame = tk.Frame(card, bg=CARD_BG)
        # (hidden until first calculation)

        self.contracts_var    = tk.StringVar()
        self.risk_total_var   = tk.StringVar()
        self.margin_total_var = tk.StringVar()
        self.distance_var     = tk.StringVar()
        self.risk_contr_var   = tk.StringVar()
        self.r1_var           = tk.StringVar()
        self.r2_var           = tk.StringVar()
        self.r3_var           = tk.StringVar()

        # Big contract count
        tk.Label(self.results_frame, textvariable=self.contracts_var,
                 bg=CARD_BG, fg=ACCENT,
                 font=("Arial", 28, "bold")).pack(pady=(0, 6))

        rf = self.results_frame
        self._result_row(rf, "Total Risk:",              self.risk_total_var)
        self._result_row(rf, "Margin Required:",         self.margin_total_var)
        self._result_row(rf, "Stop Distance (points):",  self.distance_var)
        self._result_row(rf, "Risk per Contract:",       self.risk_contr_var)

        tk.Frame(rf, bg=HR_COL, height=1).pack(fill="x", pady=8)

        self._result_row(rf, "1R Target:", self.r1_var)
        self._result_row(rf, "2R Target:", self.r2_var)
        self._result_row(rf, "3R Target:", self.r3_var)

    def _result_row(self, parent, label: str, var: tk.StringVar):
        row = tk.Frame(parent, bg=CARD_BG)
        row.pack(fill="x", pady=1)
        tk.Label(row, text=label, bg=CARD_BG, fg=FG,
                 font=("Arial", 11), anchor="w").pack(side="left")
        tk.Label(row, textvariable=var, bg=CARD_BG, fg=ACCENT,
                 font=("Arial", 11, "bold"), anchor="e").pack(side="right")

    # ── Placeholder helper ────────────────────────────────────────────────────
    @staticmethod
    def _add_placeholder(entry: tk.Entry, var: tk.StringVar, text: str):
        entry.insert(0, text)
        entry.config(fg="#3a7a3a")

        def on_focus_in(e):
            if var.get() == text:
                var.set("")
                entry.config(fg=FG)

        def on_focus_out(e):
            if var.get() == "":
                var.set(text)
                entry.config(fg="#3a7a3a")

        entry.bind("<FocusIn>",  on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)

    # ── Instrument selection ──────────────────────────────────────────────────
    def _select_instrument(self, idx: int):
        _, sym, pv, td, margin = INSTRUMENTS[idx]
        self.point_value.set(pv)
        self.tick_denom.set(td)
        self.margin_var.set(str(margin))
        self.spec_var.set(
            f"{sym}  |  Tick 1/{td}  |  1 pt = ${pv:,}  |  Margin ${margin:,}"
        )
        for i, btn in enumerate(self.tab_btns):
            btn.config(bg="#002b0c" if i == idx else INPUT_BG,
                       font=("Arial", 9, "bold") if i == idx else ("Arial", 9))

    # ── Calculation ───────────────────────────────────────────────────────────
    def _calculate(self):
        try:
            account      = float(self.account_var.get().replace(",", ""))
            risk_pct     = float(self.risk_var.get())
            margin       = float(self.margin_var.get())
            td           = self.tick_denom.get()
            pv           = self.point_value.get()

            entry_raw = self.entry_var.get().strip()
            stop_raw  = self.stop_var.get().strip()

            # ignore placeholder text
            for ph in ("e.g. 117'02", "e.g. 116'165"):
                if entry_raw == ph: entry_raw = ""
                if stop_raw  == ph: stop_raw  = ""

            entry = bond_to_decimal(entry_raw, td)
            stop  = bond_to_decimal(stop_raw,  td)

            stop_distance    = abs(entry - stop)
            risk_per_contract = stop_distance * pv
            max_risk         = account * (risk_pct / 100)

            contracts    = int(max_risk // risk_per_contract) if risk_per_contract > 0 else 0
            total_risk   = contracts * risk_per_contract
            total_margin = contracts * margin

            direction = "LONG" if entry > stop else ("SHORT" if entry < stop else "FLAT")
            sign = 1 if direction == "LONG" else -1

            r1 = entry + sign * stop_distance
            r2 = entry + sign * 2 * stop_distance
            r3 = entry + sign * 3 * stop_distance

            self.contracts_var.set(
                f"{contracts} {'Contract' if contracts == 1 else 'Contracts'}"
            )
            self.risk_total_var.set(f"${total_risk:,.2f}")
            self.margin_total_var.set(f"${total_margin:,.0f}")
            self.distance_var.set(f"{stop_distance:.6f}")
            self.risk_contr_var.set(f"${risk_per_contract:,.2f}")
            self.r1_var.set(decimal_to_bond(r1, td))
            self.r2_var.set(decimal_to_bond(r2, td))
            self.r3_var.set(decimal_to_bond(r3, td))

            self.results_frame.pack(fill="x")

        except Exception as exc:
            self.contracts_var.set("Error")
            self.risk_total_var.set(str(exc))
            for v in (self.margin_total_var, self.distance_var,
                      self.risk_contr_var, self.r1_var, self.r2_var, self.r3_var):
                v.set("")
            self.results_frame.pack(fill="x")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = BondCalcApp()
    app.mainloop()
