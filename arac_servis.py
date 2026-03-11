"""
Araç Servis Takip Sistemi
Windows masaüstü uygulaması — Python 3 + Tkinter + SQLite
Kurulum gerekmez. Python 3 yüklüyse doğrudan çalıştırın:
    python arac_servis.py
"""

import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont
import sqlite3
import os
import re
from datetime import datetime
import sys
import shutil
import base64
from tkinter import filedialog

# ── EXE mi yoksa script mi çalışıyor? ─────────────────────────────────────
def _uygulama_klasoru():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

APP_DIR = _uygulama_klasoru()
FOTO_KLASOR = os.path.join(APP_DIR, "servis_fotograflari")
os.makedirs(FOTO_KLASOR, exist_ok=True)

# ── Veritabanı yolu (uygulamanın yanında) ──────────────────────────────────
DB_PATH = os.path.join(APP_DIR, "servis_kayitlari.db")

# ── Türk plaka regex ───────────────────────────────────────────────────────
PLATE_RE = re.compile(r"^(\d{2})\s?([A-ZÇĞİÖŞÜ]{1,3})\s?(\d{2,4})$", re.IGNORECASE)

# ══════════════════════════════════════════════════════════════════════════
# VERİTABANI
# ══════════════════════════════════════════════════════════════════════════
def db_connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def db_init():
    conn = db_connect()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS araclar (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            plaka       TEXT    NOT NULL UNIQUE COLLATE NOCASE,
            sahip_adi   TEXT    NOT NULL,
            marka       TEXT,
            model       TEXT,
            yil         TEXT,
            telefon     TEXT,
            kayit_tarihi TEXT DEFAULT (date('now'))
        );

        CREATE TABLE IF NOT EXISTS servisler (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            arac_id     INTEGER NOT NULL REFERENCES araclar(id) ON DELETE CASCADE,
            tarih       TEXT    NOT NULL,
            notlar      TEXT
        );

        CREATE TABLE IF NOT EXISTS islemler (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            servis_id   INTEGER NOT NULL REFERENCES servisler(id) ON DELETE CASCADE,
            aciklama    TEXT    NOT NULL,
            tutar       REAL    NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS fotograflar (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            servis_id   INTEGER NOT NULL REFERENCES servisler(id) ON DELETE CASCADE,
            islem_id    INTEGER,
            dosya_adi   TEXT    NOT NULL,
            aciklama    TEXT,
            eklenme     TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()

    # Migration: eski veritabanlarına islem_id sütunu ekle
    try:
        conn.execute("ALTER TABLE fotograflar ADD COLUMN islem_id INTEGER")
        conn.commit()
    except Exception:
        pass

    # Araç fotoğrafları tablosu
    conn.execute("""
        CREATE TABLE IF NOT EXISTS arac_fotograflar (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            arac_id   INTEGER NOT NULL REFERENCES araclar(id) ON DELETE CASCADE,
            dosya_adi TEXT    NOT NULL,
            aciklama  TEXT,
            eklenme   TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()

def ara_arac(metin):
    metin = metin.strip()
    conn = db_connect()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM araclar
        WHERE plaka LIKE ? OR sahip_adi LIKE ?
        ORDER BY sahip_adi
    """, (f"%{metin}%", f"%{metin}%"))
    rows = c.fetchall()
    conn.close()
    return rows

def arac_ekle(plaka, sahip, marka, model, yil, tel):
    conn = db_connect()
    try:
        conn.execute(
            "INSERT INTO araclar (plaka, sahip_adi, marka, model, yil, telefon) VALUES (?,?,?,?,?,?)",
            (plaka.replace(" ", "").upper(), sahip, marka, model, yil, tel)
        )
        conn.commit()
        return True, "Araç başarıyla kaydedildi."
    except sqlite3.IntegrityError:
        return False, "Bu plaka zaten kayıtlı!"
    finally:
        conn.close()

def arac_sil(arac_id):
    conn = db_connect()
    conn.execute("DELETE FROM araclar WHERE id=?", (arac_id,))
    conn.commit()
    conn.close()

def servisler_getir(arac_id):
    conn = db_connect()
    rows = conn.execute(
        "SELECT * FROM servisler WHERE arac_id=? ORDER BY tarih DESC", (arac_id,)
    ).fetchall()
    conn.close()
    return rows

def servis_ekle(arac_id, tarih, notlar):
    conn = db_connect()
    cur = conn.execute(
        "INSERT INTO servisler (arac_id, tarih, notlar) VALUES (?,?,?)",
        (arac_id, tarih, notlar)
    )
    sid = cur.lastrowid
    conn.commit()
    conn.close()
    return sid

def servis_sil(servis_id):
    conn = db_connect()
    conn.execute("DELETE FROM servisler WHERE id=?", (servis_id,))
    conn.commit()
    conn.close()

def islemler_getir(servis_id):
    conn = db_connect()
    rows = conn.execute(
        "SELECT * FROM islemler WHERE servis_id=? ORDER BY id", (servis_id,)
    ).fetchall()
    conn.close()
    return rows

def islem_ekle(servis_id, aciklama, tutar):
    conn = db_connect()
    conn.execute(
        "INSERT INTO islemler (servis_id, aciklama, tutar) VALUES (?,?,?)",
        (servis_id, aciklama, tutar)
    )
    conn.commit()
    conn.close()

def islem_sil(islem_id):
    conn = db_connect()
    conn.execute("DELETE FROM islemler WHERE id=?", (islem_id,))
    conn.commit()
    conn.close()

def foto_ekle(servis_id, dosya_adi, aciklama="", islem_id=None):
    conn = db_connect()
    conn.execute(
        "INSERT INTO fotograflar (servis_id, islem_id, dosya_adi, aciklama) VALUES (?,?,?,?)",
        (servis_id, islem_id, dosya_adi, aciklama)
    )
    conn.commit()
    conn.close()

def foto_listele(servis_id):
    conn = db_connect()
    rows = conn.execute(
        "SELECT * FROM fotograflar WHERE servis_id=? ORDER BY eklenme", (servis_id,)
    ).fetchall()
    conn.close()
    return rows

def foto_listele_islem(islem_id):
    conn = db_connect()
    rows = conn.execute(
        "SELECT * FROM fotograflar WHERE islem_id=? ORDER BY eklenme", (islem_id,)
    ).fetchall()
    conn.close()
    return rows

def foto_sil(foto_id, dosya_adi):
    conn = db_connect()
    conn.execute("DELETE FROM fotograflar WHERE id=?", (foto_id,))
    conn.commit()
    conn.close()
    tam_yol = os.path.join(FOTO_KLASOR, dosya_adi)
    if os.path.exists(tam_yol):
        os.remove(tam_yol)

def arac_foto_ekle(arac_id, dosya_adi, aciklama=""):
    conn = db_connect()
    conn.execute(
        "INSERT INTO arac_fotograflar (arac_id, dosya_adi, aciklama) VALUES (?,?,?)",
        (arac_id, dosya_adi, aciklama)
    )
    conn.commit()
    conn.close()

def arac_foto_listele(arac_id):
    conn = db_connect()
    rows = conn.execute(
        "SELECT * FROM arac_fotograflar WHERE arac_id=? ORDER BY eklenme", (arac_id,)
    ).fetchall()
    conn.close()
    return rows

def arac_foto_sil(foto_id, dosya_adi):
    conn = db_connect()
    conn.execute("DELETE FROM arac_fotograflar WHERE id=?", (foto_id,))
    conn.commit()
    conn.close()
    tam_yol = os.path.join(FOTO_KLASOR, dosya_adi)
    if os.path.exists(tam_yol):
        os.remove(tam_yol)


# ══════════════════════════════════════════════════════════════════════════
# RENKLER & STİL
# ══════════════════════════════════════════════════════════════════════════
BG        = "#0f1117"
SURFACE   = "#1a1d26"
SURFACE2  = "#22263a"
BORDER    = "#2e3348"
ACCENT    = "#e8b84b"
ACCENT2   = "#4b9fe8"
DANGER    = "#e85454"
SUCCESS   = "#4be896"
TEXT      = "#e2e6f3"
MUTED     = "#636b8a"
WHITE     = "#ffffff"


def style_btn(btn, color=ACCENT, fg=BG, **kw):
    btn.configure(
        bg=color, fg=fg, activebackground=color, activeforeground=fg,
        relief="flat", bd=0, padx=14, pady=6, cursor="hand2",
        font=("Segoe UI", 9, "bold"), **kw
    )

def style_entry(ent):
    ent.configure(
        bg=SURFACE2, fg=TEXT, insertbackground=TEXT,
        relief="flat", bd=0, highlightthickness=1,
        highlightbackground=BORDER, highlightcolor=ACCENT,
        font=("Segoe UI", 10)
    )


# ══════════════════════════════════════════════════════════════════════════
# ANA PENCERE
# ══════════════════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Araç Servis Takip Sistemi")
        self.geometry("1100x750")
        self.minsize(900, 600)
        self.configure(bg=BG)
        self.resizable(True, True)

        # İkon — boş ama ayarlanabilir
        try:
            self.iconbitmap(default="")
        except Exception:
            pass

        db_init()

        self._aktif_arac = None
        self._aktif_servis = None

        self._build_ui()

    # ── Ana layout ────────────────────────────────────────────────────────
    def _build_ui(self):
        # Başlık şeridi
        header = tk.Frame(self, bg=ACCENT, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="🔧  ARAÇ SERVİS TAKİP SİSTEMİ",
                 bg=ACCENT, fg=BG, font=("Segoe UI", 14, "bold"),
                 padx=24).pack(side="left", fill="y")
        tk.Label(header, text=f"  {datetime.now().strftime('%d.%m.%Y')}",
                 bg=ACCENT, fg=BG, font=("Segoe UI", 10)).pack(side="right", padx=16, fill="y")

        # Ana içerik
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=18, pady=14)

        # Sol sütun (arama + liste)
        left = tk.Frame(body, bg=BG, width=340)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        # Sağ sütun (detaylar)
        right = tk.Frame(body, bg=BG)
        right.pack(side="right", fill="both", expand=True, padx=(16, 0))

        self._build_left(left)
        self._build_right(right)

    # ── Sol panel ─────────────────────────────────────────────────────────
    def _build_left(self, parent):
        # Arama kutusu
        search_card = tk.Frame(parent, bg=SURFACE, pady=14, padx=14)
        search_card.pack(fill="x", pady=(0, 12))

        tk.Label(search_card, text="PLAKA veya ARAÇ SAHİBİ ARA",
                 bg=SURFACE, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w")

        row = tk.Frame(search_card, bg=SURFACE)
        row.pack(fill="x", pady=(6, 0))

        self.search_var = tk.StringVar()

        ent = tk.Entry(row, textvariable=self.search_var, font=("Segoe UI", 11, "bold"))
        style_entry(ent)
        ent.pack(side="left", fill="x", expand=True, ipady=6)
        ent.bind("<space>", lambda e: "break")
        ent.bind("<Return>", lambda e: self._ara())

        btn_ara = tk.Button(row, text="🔍 Ara", command=self._ara)
        style_btn(btn_ara, color=ACCENT, fg=BG)
        btn_ara.pack(side="left", padx=(8, 0))

        btn_ekle = tk.Button(row, text="＋ Ekle", command=self._arac_ekle_dialog)
        style_btn(btn_ekle, color=ACCENT2, fg=WHITE)
        btn_ekle.pack(side="left", padx=(6, 0))

        tk.Label(search_card, text="Plaka formatı: 34 ABC 1234",
                 bg=SURFACE, fg=MUTED, font=("Segoe UI", 7)).pack(anchor="w", pady=(4, 0))

        # Sonuç listesi
        lbl = tk.Frame(parent, bg=SURFACE)
        lbl.pack(fill="x")
        tk.Label(lbl, text="ARAÇLAR", bg=SURFACE, fg=MUTED,
                 font=("Segoe UI", 8, "bold"), padx=12, pady=6).pack(anchor="w")

        list_frame = tk.Frame(parent, bg=SURFACE)
        list_frame.pack(fill="both", expand=True)

        sb = tk.Scrollbar(list_frame, bg=SURFACE2, troughcolor=BORDER,
                          activebackground=ACCENT, relief="flat", width=8)
        sb.pack(side="right", fill="y")

        self.listbox = tk.Listbox(
            list_frame, bg=SURFACE, fg=TEXT, selectbackground=ACCENT,
            selectforeground=BG, relief="flat", bd=0, activestyle="none",
            font=("Segoe UI", 10), yscrollcommand=sb.set, cursor="hand2"
        )
        self.listbox.pack(fill="both", expand=True)
        sb.config(command=self.listbox.yview)
        self.listbox.bind("<<ListboxSelect>>", self._secim)

        self._arac_listesi = []
        self._ara()

    # ── Sağ panel ─────────────────────────────────────────────────────────
    def _build_right(self, parent):
        # Araç bilgi kartı
        self.info_card = tk.Frame(parent, bg=SURFACE, pady=14, padx=18)
        self.info_card.pack(fill="x")
        self._build_info_card()

        # Servisler + işlemler
        bottom = tk.Frame(parent, bg=BG)
        bottom.pack(fill="both", expand=True, pady=(12, 0))

        # Servis tarihleri
        srv_col = tk.Frame(bottom, bg=BG, width=220)
        srv_col.pack(side="left", fill="y")
        srv_col.pack_propagate(False)

        tk.Label(srv_col, text="SERVİS TARİHLERİ",
                 bg=BG, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 6))

        srv_list_f = tk.Frame(srv_col, bg=SURFACE)
        srv_list_f.pack(fill="both", expand=True)

        sb2 = tk.Scrollbar(srv_list_f, bg=SURFACE2, troughcolor=BORDER,
                           activebackground=ACCENT, relief="flat", width=8)
        sb2.pack(side="right", fill="y")

        self.srv_listbox = tk.Listbox(
            srv_list_f, bg=SURFACE, fg=TEXT, selectbackground=ACCENT2,
            selectforeground=WHITE, relief="flat", bd=0, activestyle="none",
            font=("Courier New", 10), yscrollcommand=sb2.set, cursor="hand2"
        )
        self.srv_listbox.pack(fill="both", expand=True)
        sb2.config(command=self.srv_listbox.yview)
        self.srv_listbox.bind("<<ListboxSelect>>", self._servis_sec)

        btn_row = tk.Frame(srv_col, bg=BG)
        btn_row.pack(fill="x", pady=(6, 0))
        self.btn_srv_ekle = tk.Button(btn_row, text="＋ Tarih Ekle",
                                      command=self._servis_ekle_dialog, state="disabled")
        style_btn(self.btn_srv_ekle, color=SUCCESS, fg=BG)
        self.btn_srv_ekle.pack(side="left")

        self.btn_srv_sil = tk.Button(btn_row, text="✕ Tarih Sil",
                                     command=self._servis_sil, state="disabled")
        style_btn(self.btn_srv_sil, color=DANGER, fg=WHITE)
        self.btn_srv_sil.pack(side="left", padx=(6, 0))


        # İşlemler
        ops_col = tk.Frame(bottom, bg=BG)
        ops_col.pack(side="right", fill="both", expand=True, padx=(14, 0))

        hdr_row = tk.Frame(ops_col, bg=BG)
        hdr_row.pack(fill="x", pady=(0, 6))
        tk.Label(hdr_row, text="YAPILAN İŞLEMLER",
                 bg=BG, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(side="left")
        tk.Label(hdr_row, text="Çift tık: Düzenle  |  Delete: Satır Sil",
                 bg=BG, fg=MUTED, font=("Segoe UI", 7)).pack(side="right")

        # Izgara dış çerçeve
        grid_outer = tk.Frame(ops_col, bg=SURFACE, bd=0)
        grid_outer.pack(fill="both", expand=True)

        # Başlık satırı
        hdr = tk.Frame(grid_outer, bg=SURFACE2)
        hdr.pack(fill="x")
        tk.Label(hdr, text="  Fotoğraf", bg=SURFACE2, fg=ACCENT,
                 font=("Segoe UI", 9, "bold"), anchor="center", width=11).pack(side="left")
        tk.Frame(hdr, bg=BORDER, width=1).pack(side="left", fill="y")
        tk.Label(hdr, text="  İşlem Açıklaması", bg=SURFACE2, fg=ACCENT,
                 font=("Segoe UI", 9, "bold"), anchor="w", width=20).pack(side="left")
        tk.Frame(hdr, bg=BORDER, width=1).pack(side="left", fill="y")
        tk.Label(hdr, text="  Tutar (₺)", bg=SURFACE2, fg=ACCENT,
                 font=("Segoe UI", 9, "bold"), anchor="w", width=14).pack(side="left")
        tk.Frame(grid_outer, bg=BORDER, height=1).pack(fill="x")

        # Scrollable satır alanı
        canvas = tk.Canvas(grid_outer, bg=SURFACE, highlightthickness=0)
        vsb = tk.Scrollbar(grid_outer, orient="vertical", command=canvas.yview,
                           bg=SURFACE2, troughcolor=BORDER, width=8, relief="flat")
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self.grid_frame = tk.Frame(canvas, bg=SURFACE)
        self._grid_window = canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")

        def _on_frame_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        def _on_canvas_configure(e):
            canvas.itemconfig(self._grid_window, width=e.width)

        self.grid_frame.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        def _scroll(e):
            canvas.yview_scroll(-1*(e.delta//120), "units")
        canvas.bind("<MouseWheel>", _scroll)
        self.grid_frame.bind("<MouseWheel>", _scroll)
        self._edit_canvas = canvas
        self._canvas_scroll = _scroll

        # Toplam + yeni satır
        ops_footer = tk.Frame(ops_col, bg=BG)
        ops_footer.pack(fill="x", pady=(8, 0))

        self.lbl_toplam = tk.Label(ops_footer, text="TOPLAM: ₺0.00",
                                   bg=BG, fg=ACCENT, font=("Segoe UI", 11, "bold"))
        self.lbl_toplam.pack(side="left")

        self.btn_yeni_satir = tk.Button(ops_footer, text="＋ Yeni Satır",
                                        command=self._yeni_satir_ekle, state="disabled")
        style_btn(self.btn_yeni_satir, color=ACCENT, fg=BG)
        self.btn_yeni_satir.pack(side="right")

        # Foto butonları satır içine taşındı — burada sadece yeni satır butonu kalır

    # ── Araç bilgi kartı ──────────────────────────────────────────────────
    def _build_info_card(self):
        for w in self.info_card.winfo_children():
            w.destroy()

        if not self._aktif_arac:
            tk.Label(self.info_card, text="Lütfen bir araç seçin...",
                     bg=SURFACE, fg=MUTED, font=("Segoe UI", 11)).pack(anchor="w")
            return

        a = self._aktif_arac
        plaka = a["plaka"]
        sahip = a["sahip_adi"]
        marka = a["marka"] or "—"
        model = a["model"] or "—"
        yil   = a["yil"] or "—"
        tel   = a["telefon"] or "—"

        top = tk.Frame(self.info_card, bg=SURFACE)
        top.pack(fill="x")

        # Plaka etiketi
        plaka_lbl = tk.Label(top, text=plaka.upper(),
                             bg=ACCENT, fg=BG,
                             font=("Courier New", 20, "bold"),
                             padx=18, pady=4, relief="flat")
        plaka_lbl.pack(side="left")

        info_txt = tk.Frame(top, bg=SURFACE)
        info_txt.pack(side="left", padx=18)

        tk.Label(info_txt, text=sahip, bg=SURFACE, fg=TEXT,
                 font=("Segoe UI", 13, "bold")).grid(row=0, column=0, columnspan=4, sticky="w")

        details = [("Marka", marka), ("Model", model), ("Yıl", yil), ("Tel", tel)]
        for i, (k, v) in enumerate(details):
            tk.Label(info_txt, text=f"{k}:", bg=SURFACE, fg=MUTED,
                     font=("Segoe UI", 9)).grid(row=1, column=i*2, sticky="w", padx=(0, 2))
            tk.Label(info_txt, text=v, bg=SURFACE, fg=TEXT,
                     font=("Segoe UI", 9, "bold")).grid(row=1, column=i*2+1, sticky="w", padx=(0, 16))

        # Butonlar — sağ taraf
        btn_frame = tk.Frame(top, bg=SURFACE)
        btn_frame.pack(side="right", anchor="center")

        btn_duzenle = tk.Button(btn_frame, text="✏  BİLGİLERİ DÜZENLE",
                                command=self._arac_duzenle_dialog,
                                bg=ACCENT2, fg=WHITE,
                                font=("Segoe UI", 10, "bold"), relief="flat",
                                bd=0, padx=18, pady=8, cursor="hand2",
                                activebackground="#3a8fd4", activeforeground=WHITE)
        btn_duzenle.pack(side="top", fill="x", pady=(0, 6))

        btn_foto_arac = tk.Button(btn_frame, text="🖼  Araç Fotoğrafları",
                                  command=self._arac_fotograflari_goster,
                                  bg="#6c3483", fg=WHITE,
                                  font=("Segoe UI", 9, "bold"), relief="flat",
                                  bd=0, padx=18, pady=5, cursor="hand2",
                                  activebackground="#9b59b6", activeforeground=WHITE)
        btn_foto_arac.pack(side="top", fill="x", pady=(0, 6))

        btn_sil = tk.Button(btn_frame, text="🗑  Aracı Sil",
                            command=self._arac_sil, bg=DANGER, fg=WHITE,
                            font=("Segoe UI", 9, "bold"), relief="flat",
                            bd=0, padx=18, pady=5, cursor="hand2",
                            activebackground="#c73a3a", activeforeground=WHITE)
        btn_sil.pack(side="top", fill="x")

    # ══════════════════════════════════════════════════════════════════════
    # ARAMA
    # ══════════════════════════════════════════════════════════════════════
    def _ara(self, *_):
        q = self.search_var.get().replace(" ", "").strip()
        self.listbox.delete(0, "end")
        self._arac_listesi = []

        if len(q) < 1:
            sonuclar = ara_arac("")
        else:
            sonuclar = ara_arac(q)

        for row in sonuclar:
            self._arac_listesi.append(dict(row))
            self.listbox.insert("end", f"  {row['plaka'].upper()}  –  {row['sahip_adi']}")

    def _secim(self, event=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        self._aktif_arac = self._arac_listesi[sel[0]]
        self._aktif_servis = None
        self._build_info_card()
        self._servis_listesi_yukle()
        self.btn_srv_ekle.config(state="normal")

    # ══════════════════════════════════════════════════════════════════════
    # ARAÇ EKLEME
    # ══════════════════════════════════════════════════════════════════════
    def _arac_ekle_dialog(self):
        self._arac_form_dialog()

    def _arac_duzenle_dialog(self):
        if not self._aktif_arac:
            return
        self._arac_form_dialog_genisletilmis(self._aktif_arac)

    def _arac_form_dialog_genisletilmis(self, arac):
        """Düzenleme dialogu: bilgiler + fotoğraf sekmesi."""
        dlg = tk.Toplevel(self)
        dlg.title("Araç Düzenle")
        dlg.configure(bg=BG)
        dlg.geometry("520x520")
        dlg.grab_set()
        dlg.transient(self)
        px = self.winfo_x() + (self.winfo_width() - 520) // 2
        py = self.winfo_y() + (self.winfo_height() - 520) // 2
        dlg.geometry(f"520x520+{px}+{py}")

        tk.Label(dlg, text="ARAÇ DÜZENLE", bg="#4b9fe8", fg=WHITE,
                 font=("Segoe UI", 11, "bold"), pady=10).pack(fill="x")

        # Sekme bar
        tab_bar = tk.Frame(dlg, bg=SURFACE2)
        tab_bar.pack(fill="x")

        content = tk.Frame(dlg, bg=BG)
        content.pack(fill="both", expand=True, padx=0, pady=0)

        # Footer
        footer = tk.Frame(dlg, bg=BG, padx=16, pady=10)
        footer.pack(fill="x", side="bottom")

        frames = {}
        tab_btns = {}

        def goster_sekme(ad):
            for k, f in frames.items():
                f.pack_forget()
            frames[ad].pack(fill="both", expand=True, padx=16, pady=12)
            for k, b in tab_btns.items():
                b.config(bg=ACCENT if k == ad else SURFACE2,
                         fg=BG if k == ad else MUTED)

        for ad, lbl in [("bilgiler", "📋 Bilgiler"), ("fotograflar", "📷 Fotoğraflar")]:
            f = tk.Frame(content, bg=BG)
            frames[ad] = f
            b = tk.Button(tab_bar, text=lbl, bg=SURFACE2, fg=MUTED,
                          font=("Segoe UI", 9, "bold"), relief="flat", bd=0,
                          padx=16, pady=7, cursor="hand2",
                          command=lambda a=ad: goster_sekme(a))
            b.pack(side="left")
            tab_btns[ad] = b

        # ── Bilgiler sekmesi ──────────────────────────────────────────────
        bf = frames["bilgiler"]
        fields = [
            ("Plaka *",      "plaka",     arac["plaka"]),
            ("Araç Sahibi *","sahip_adi", arac["sahip_adi"]),
            ("Marka",        "marka",     arac["marka"] or ""),
            ("Model",        "model",     arac["model"] or ""),
            ("Yıl",          "yil",       arac["yil"] or ""),
            ("Telefon",      "telefon",   arac["telefon"] or ""),
        ]
        entries = {}
        for lbl_t, key, val in fields:
            r = tk.Frame(bf, bg=BG)
            r.pack(fill="x", pady=4)
            tk.Label(r, text=lbl_t, bg=BG, fg=MUTED,
                     font=("Segoe UI", 9), width=16, anchor="w").pack(side="left")
            e = tk.Entry(r, font=("Segoe UI", 10))
            style_entry(e)
            e.pack(side="left", fill="x", expand=True, ipady=5)
            e.insert(0, val)
            if key == "plaka":
                e.bind("<space>", lambda ev: "break")
            entries[key] = e

        def kaydet_bilgi():
            plaka = entries["plaka"].get().replace(" ", "").strip().upper()
            sahip = entries["sahip_adi"].get().strip()
            marka = entries["marka"].get().strip()
            model = entries["model"].get().strip()
            yil   = entries["yil"].get().strip()
            tel   = entries["telefon"].get().strip()
            if not plaka:
                messagebox.showwarning("Uyarı", "Plaka giriniz.", parent=dlg); return
            if not sahip:
                messagebox.showwarning("Uyarı", "Araç sahibi giriniz.", parent=dlg); return
            if not PLATE_RE.match(plaka):
                messagebox.showwarning("Uyarı",
                    "Geçersiz plaka!\nÖrnek: 34ABC1234", parent=dlg); return
            try:
                conn = db_connect()
                conn.execute("""UPDATE araclar SET plaka=?, sahip_adi=?, marka=?,
                    model=?, yil=?, telefon=? WHERE id=?""",
                    (plaka, sahip, marka, model, yil, tel, arac["id"]))
                conn.commit(); conn.close()
            except sqlite3.IntegrityError:
                messagebox.showerror("Hata",
                    f"'{plaka}' plakası zaten kayıtlı!", parent=dlg); return
            dlg.destroy()
            self._ara()
            sonuclar = ara_arac(plaka)
            if sonuclar:
                self._aktif_arac = dict(sonuclar[0])
                self._build_info_card()

        tk.Button(footer, text="💾 Kaydet", command=kaydet_bilgi,
                  bg=ACCENT, fg=BG, font=("Segoe UI", 10, "bold"),
                  relief="flat", bd=0, padx=18, pady=6, cursor="hand2").pack(side="right")
        tk.Button(footer, text="İptal", command=dlg.destroy,
                  bg=SURFACE2, fg=TEXT, font=("Segoe UI", 10),
                  relief="flat", bd=0, padx=14, pady=6, cursor="hand2").pack(side="right", padx=(0, 8))

        # ── Fotoğraflar sekmesi ───────────────────────────────────────────
        ff = frames["fotograflar"]
        self._arac_foto_sekme_yukle(ff, arac["id"])

        goster_sekme("bilgiler")

    def _arac_form_dialog(self, arac=None):
        dlg = _Dialog(self, "Araç Bilgileri" if not arac else "Araç Düzenle", width=440, height=400)

        fields = [
            ("Plaka *", "plaka", arac["plaka"] if arac else ""),
            ("Araç Sahibi *", "sahip_adi", arac["sahip_adi"] if arac else ""),
            ("Marka", "marka", (arac["marka"] or "") if arac else ""),
            ("Model", "model", (arac["model"] or "") if arac else ""),
            ("Yıl", "yil", (arac["yil"] or "") if arac else ""),
            ("Telefon", "telefon", (arac["telefon"] or "") if arac else ""),
        ]

        entries = {}
        for lbl, key, val in fields:
            r = tk.Frame(dlg.body, bg=SURFACE2)
            r.pack(fill="x", pady=4)
            tk.Label(r, text=lbl, bg=SURFACE2, fg=MUTED,
                     font=("Segoe UI", 9), width=16, anchor="w").pack(side="left")
            e = tk.Entry(r, font=("Segoe UI", 10))
            style_entry(e)
            e.pack(side="left", fill="x", expand=True, ipady=5)
            e.insert(0, val)
            if key == "plaka":
                e.bind("<space>", lambda ev: "break")
            entries[key] = e

        def kaydet():
            plaka  = entries["plaka"].get().replace(" ", "").strip().upper()
            sahip  = entries["sahip_adi"].get().strip()
            marka  = entries["marka"].get().strip()
            model  = entries["model"].get().strip()
            yil    = entries["yil"].get().strip()
            tel    = entries["telefon"].get().strip()

            if not plaka:
                messagebox.showwarning("Uyarı", "Plaka giriniz.", parent=dlg)
                return
            if not sahip:
                messagebox.showwarning("Uyarı", "Araç sahibi giriniz.", parent=dlg)
                return
            if not PLATE_RE.match(plaka):
                messagebox.showwarning("Uyarı",
                    "Geçersiz plaka formatı!\nÖrnek: 34 ABC 1234 ya da 06 TT 345",
                    parent=dlg)
                return

            if arac:
                # Güncelleme — plaka dahil tüm alanlar
                try:
                    conn = db_connect()
                    conn.execute("""
                        UPDATE araclar SET plaka=?, sahip_adi=?, marka=?, model=?, yil=?, telefon=?
                        WHERE id=?
                    """, (plaka, sahip, marka, model, yil, tel, arac["id"]))
                    conn.commit()
                    conn.close()
                except sqlite3.IntegrityError:
                    messagebox.showerror("Hata", f"'{plaka}' plakası zaten başka bir araçta kayıtlı!", parent=dlg)
                    return
                dlg.destroy()
                self._ara()
                sonuclar = ara_arac(plaka)
                if sonuclar:
                    self._aktif_arac = dict(sonuclar[0])
                    self._build_info_card()
            else:
                ok, msg = arac_ekle(plaka, sahip, marka, model, yil, tel)
                if ok:
                    dlg.destroy()
                    self._ara()
                    # Yeni araç seç
                    sonuclar = ara_arac(plaka)
                    if sonuclar:
                        self._aktif_arac = dict(sonuclar[0])
                        self._build_info_card()
                        self._servis_listesi_yukle()
                        self.btn_srv_ekle.config(state="normal")
                else:
                    messagebox.showerror("Hata", msg, parent=dlg)

        tk.Button(dlg.footer, text="Kaydet", command=kaydet,
                  bg=ACCENT, fg=BG, font=("Segoe UI", 10, "bold"),
                  relief="flat", bd=0, padx=18, pady=6, cursor="hand2").pack(side="right")
        tk.Button(dlg.footer, text="İptal", command=dlg.destroy,
                  bg=SURFACE2, fg=TEXT, font=("Segoe UI", 10),
                  relief="flat", bd=0, padx=14, pady=6, cursor="hand2").pack(side="right", padx=(0, 8))

    # ══════════════════════════════════════════════════════════════════════
    # ARAÇ SİL
    # ══════════════════════════════════════════════════════════════════════
    def _arac_sil(self):
        if not self._aktif_arac:
            return
        plaka = self._aktif_arac["plaka"]
        if not messagebox.askyesno("Aracı Sil",
                f"'{plaka}' plakalı araç ve tüm servis kayıtları silinecek.\nEmin misiniz?",
                icon="warning"):
            return
        arac_sil(self._aktif_arac["id"])
        self._aktif_arac = None
        self._aktif_servis = None
        self._build_info_card()
        self._servis_listesi_yukle()
        self.btn_srv_ekle.config(state="disabled")
        self.btn_srv_sil.config(state="disabled")
        self.btn_yeni_satir.config(state="disabled")
        self._ara()

    # ══════════════════════════════════════════════════════════════════════
    # SERVİSLER
    # ══════════════════════════════════════════════════════════════════════
    def _servis_listesi_yukle(self):
        self.srv_listbox.delete(0, "end")
        self._servis_listesi = []
        for w in self.grid_frame.winfo_children():
            w.destroy()
        self._grid_rows = []
        self.lbl_toplam.config(text="TOPLAM: ₺0.00")
        self.btn_yeni_satir.config(state="disabled")
        self.btn_srv_sil.config(state="disabled")

        if not self._aktif_arac:
            return

        rows = servisler_getir(self._aktif_arac["id"])
        for row in rows:
            self._servis_listesi.append(dict(row))
            self.srv_listbox.insert("end", f"  {row['tarih']}")

    def _servis_sec(self, event=None):
        sel = self.srv_listbox.curselection()
        if not sel:
            return
        self._aktif_servis = self._servis_listesi[sel[0]]
        self._islem_listesi_yukle()
        self.btn_srv_sil.config(state="normal")

    def _servis_ekle_dialog(self):
        if not self._aktif_arac:
            return

        dlg = _Dialog(self, "Servis Tarihi Ekle", width=380, height=220)

        r1 = tk.Frame(dlg.body, bg=SURFACE2)
        r1.pack(fill="x", pady=4)
        tk.Label(r1, text="Tarih (GG.AA.YYYY) *", bg=SURFACE2, fg=MUTED,
                 font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
        tarih_e = tk.Entry(r1, font=("Courier New", 11))
        style_entry(tarih_e)
        tarih_e.pack(side="left", fill="x", expand=True, ipady=5)
        tarih_e.insert(0, datetime.now().strftime("%d.%m.%Y"))

        r2 = tk.Frame(dlg.body, bg=SURFACE2)
        r2.pack(fill="x", pady=4)
        tk.Label(r2, text="Notlar", bg=SURFACE2, fg=MUTED,
                 font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
        notlar_e = tk.Entry(r2, font=("Segoe UI", 10))
        style_entry(notlar_e)
        notlar_e.pack(side="left", fill="x", expand=True, ipady=5)

        def kaydet():
            tarih = tarih_e.get().strip()
            notlar = notlar_e.get().strip()
            if not tarih:
                messagebox.showwarning("Uyarı", "Tarih giriniz.", parent=dlg)
                return
            try:
                datetime.strptime(tarih, "%d.%m.%Y")
            except ValueError:
                messagebox.showwarning("Uyarı", "Tarih formatı: GG.AA.YYYY", parent=dlg)
                return
            servis_ekle(self._aktif_arac["id"], tarih, notlar)
            dlg.destroy()
            self._servis_listesi_yukle()

        tk.Button(dlg.footer, text="Kaydet", command=kaydet,
                  bg=ACCENT, fg=BG, font=("Segoe UI", 10, "bold"),
                  relief="flat", bd=0, padx=18, pady=6, cursor="hand2").pack(side="right")
        tk.Button(dlg.footer, text="İptal", command=dlg.destroy,
                  bg=SURFACE2, fg=TEXT, font=("Segoe UI", 10),
                  relief="flat", bd=0, padx=14, pady=6, cursor="hand2").pack(side="right", padx=(0, 8))

    def _servis_sil(self):
        if not self._aktif_servis:
            return
        tarih = self._aktif_servis["tarih"]
        if not messagebox.askyesno("Tarih Sil",
                f"'{tarih}' tarihli servis ve tüm işlemleri silinecek.\nEmin misiniz?",
                icon="warning"):
            return
        servis_sil(self._aktif_servis["id"])
        self._aktif_servis = None
        self._servis_listesi_yukle()

    # ══════════════════════════════════════════════════════════════════════
    # İŞLEMLER — EXCEL TARZI IZGARA
    # ══════════════════════════════════════════════════════════════════════
    def _islem_listesi_yukle(self):
        # Tüm satırları temizle
        for w in self.grid_frame.winfo_children():
            w.destroy()
        self._grid_rows = []   # [{frame, acik_var, tutar_var, islem_id, separator}]

        if not self._aktif_servis:
            self.lbl_toplam.config(text="TOPLAM: ₺0.00")
            self.btn_yeni_satir.config(state="disabled")
            return

        self.btn_yeni_satir.config(state="normal")
        rows = islemler_getir(self._aktif_servis["id"])
        for row in rows:
            self._satir_ekle_widget(row["id"], row["aciklama"], row["tutar"])

        self._toplam_guncelle()

    def _satir_ekle_widget(self, islem_id, aciklama="", tutar=0.0):
        """Izgara içine bir satır (Frame+Entry) ekler."""
        idx = len(self._grid_rows)
        row_bg = SURFACE if idx % 2 == 0 else SURFACE2

        frame = tk.Frame(self.grid_frame, bg=row_bg)
        frame.pack(fill="x")

        # ── Foto küçük resim sütunu ───────────────────────────────────────
        foto_btn = tk.Label(frame, bg=row_bg, cursor="hand2",
                            width=11, height=4, anchor="center", relief="flat",
                            font=("Segoe UI", 8))
        foto_btn.pack(side="left", padx=2, pady=2)
        tk.Frame(frame, bg=BORDER, width=1).pack(side="left", fill="y", pady=2)

        # Fotoğraf sütunu — tıklayınca ekle veya gör
        def _foto_guncelle(btn=foto_btn, ri_ref=None):
            # ri_ref sonradan set edilecek
            ri_cur = ri_ref[0] if ri_ref else None
            iid = ri_cur["islem_id"] if ri_cur else None

            if not iid:
                btn.config(text="📷 Ekle", fg=MUTED, image="")
                return

            fotos = foto_listele_islem(iid)
            if not fotos:
                btn.config(text="📷 Ekle", fg=MUTED, image="")
                return

            # Fotoğraf var — küçük resim
            tam_yol = os.path.join(FOTO_KLASOR, fotos[0]["dosya_adi"])
            if not os.path.exists(tam_yol):
                btn.config(text="📷 ?", fg=DANGER, image="")
                return
            try:
                from PIL import Image as PI, ImageTk as PIT
                img = PI.open(tam_yol)
                img.thumbnail((76, 56), PI.LANCZOS)
                imgtk = PIT.PhotoImage(img)
                btn.config(image=imgtk, text="", width=78, height=58)
                btn.imgtk = imgtk
                if len(fotos) > 1:
                    btn.config(text=f" +{len(fotos)}", compound="bottom",
                               font=("Segoe UI", 7, "bold"), fg=ACCENT)
            except Exception:
                btn.config(text=f"📷 {len(fotos)}", fg=ACCENT, image="")


        # Açıklama girişi
        acik_var = tk.StringVar(value=aciklama)
        acik_e = tk.Entry(frame, textvariable=acik_var,
                          bg=row_bg, fg=TEXT, insertbackground=TEXT,
                          relief="flat", bd=0, font=("Segoe UI", 10),
                          highlightthickness=0)
        acik_e.pack(side="left", fill="x", expand=True, ipady=6, padx=(4, 2))
        acik_e.bind("<MouseWheel>", lambda e: self._canvas_scroll(e) if hasattr(self, "_canvas_scroll") else None)

        sep = tk.Frame(frame, bg=BORDER, width=1)
        sep.pack(side="left", fill="y", pady=2)

        # Tutar girişi
        tutar_var = tk.StringVar(value=f"{tutar:.2f}" if tutar else "")
        tutar_e = tk.Entry(frame, textvariable=tutar_var, width=12,
                           bg=row_bg, fg=ACCENT, insertbackground=ACCENT,
                           relief="flat", bd=0, font=("Courier New", 10, "bold"),
                           highlightthickness=0, justify="right")
        tutar_e.pack(side="left", ipady=6, padx=(4, 2))
        tutar_e.bind("<MouseWheel>", lambda e: self._canvas_scroll(e) if hasattr(self, "_canvas_scroll") else None)

        # Sil butonu (hover'da görünür)
        sil_btn = tk.Button(frame, text="✕", bg=row_bg, fg=MUTED,
                            relief="flat", bd=0, padx=6, pady=2,
                            cursor="hand2", font=("Segoe UI", 9),
                            activebackground=DANGER, activeforeground=WHITE)
        sil_btn.pack(side="right", padx=(0, 4))

        sep2 = tk.Frame(self.grid_frame, bg=BORDER, height=1)
        sep2.pack(fill="x")

        ri_ref = [None]  # forward reference
        row_info = {
            "frame": frame, "sep2": sep2,
            "acik_var": acik_var, "tutar_var": tutar_var,
            "acik_e": acik_e, "tutar_e": tutar_e,
            "islem_id": islem_id,
            "foto_btn": foto_btn,
            "foto_guncelle": lambda: _foto_guncelle(ri_ref=ri_ref)
        }
        ri_ref[0] = row_info
        self._grid_rows.append(row_info)

        # Foto tıklama — row_info artık hazır
        def _foto_tikla(event, ri=row_info):
            # Henüz kaydedilmemişse boş kayıt aç
            if not ri["islem_id"]:
                if not self._aktif_servis:
                    return
                conn = db_connect()
                cur = conn.execute(
                    "INSERT INTO islemler (servis_id, aciklama, tutar) VALUES (?,?,?)",
                    (self._aktif_servis["id"], "", 0.0)
                )
                ri["islem_id"] = cur.lastrowid
                conn.commit()
                conn.close()
            iid = ri["islem_id"]
            fotos = foto_listele_islem(iid)
            if fotos:
                self._islem_fotograflari_goster(iid)
            else:
                self._islem_foto_ekle(iid)

        foto_btn.bind("<Button-1>", _foto_tikla)
        # İlk yükleme de ri_ref kullanarak yap
        frame.after(100, lambda: _foto_guncelle(ri_ref=ri_ref))

        # Kaydetme fonksiyonu
        def _kaydet(event=None, ri=row_info):
            self._satir_kaydet(ri)

        def _tab_next(event=None, ri=row_info):
            self._satir_kaydet(ri)
            nxt_idx = self._grid_rows.index(ri) + 1
            if nxt_idx < len(self._grid_rows):
                self._grid_rows[nxt_idx]["acik_e"].focus_set()
            else:
                self._yeni_satir_ekle()
            return "break"

        def _sil(ri=row_info):
            acik = ri["acik_var"].get().strip()
            isim = f'"{acik}"' if acik else "bu satırı"
            if not messagebox.askyesno("Satırı Sil",
                    f"{isim} silmek istediğinizden emin misiniz?",
                    parent=self):
                return
            if ri["islem_id"]:
                islem_sil(ri["islem_id"])
            ri["frame"].destroy()
            ri["sep2"].destroy()
            self._grid_rows.remove(ri)
            self._toplam_guncelle()

        acik_e.bind("<Return>", lambda e, ri=row_info: (self._satir_kaydet(ri), tutar_e.focus_set()))
        acik_e.bind("<FocusOut>", _kaydet)
        tutar_e.bind("<Return>", _tab_next)
        tutar_e.bind("<FocusOut>", _kaydet)
        tutar_e.bind("<Tab>", _tab_next)
        acik_e.bind("<Delete>", lambda e, ri=row_info: None)   # sadece metin sil
        frame.bind("<Delete>", lambda e, ri=row_info: _sil(ri))

        sil_btn.config(command=_sil)

        # Hover renk efekti
        def _hover_on(e, f=frame, b=sil_btn, fb=foto_btn, bg=row_bg):
            f.config(bg="#2a2d3a"); acik_e.config(bg="#2a2d3a"); tutar_e.config(bg="#2a2d3a")
            b.config(bg="#2a2d3a", fg=DANGER); fb.config(bg="#2a2d3a")
        def _hover_off(e, f=frame, b=sil_btn, fb=foto_btn, bg=row_bg):
            f.config(bg=bg); acik_e.config(bg=bg); tutar_e.config(bg=bg)
            b.config(bg=bg, fg=MUTED); fb.config(bg=bg)

        for w in (frame, acik_e, tutar_e, sil_btn, foto_btn):
            w.bind("<Enter>", _hover_on)
            w.bind("<Leave>", _hover_off)
            w.bind("<MouseWheel>", lambda e: self._canvas_scroll(e) if hasattr(self, "_canvas_scroll") else None)

    def _satir_kaydet(self, ri):
        """Satırdaki veriyi veritabanına yazar/günceller."""
        if not self._aktif_servis:
            return
        acik = ri["acik_var"].get().strip()
        tutar_str = ri["tutar_var"].get().strip().replace(",", ".")
        if not acik:
            return
        try:
            tutar = float(tutar_str) if tutar_str else 0.0
        except ValueError:
            tutar = 0.0
            ri["tutar_var"].set("0.00")

        if ri["islem_id"]:
            # Güncelle
            conn = db_connect()
            conn.execute("UPDATE islemler SET aciklama=?, tutar=? WHERE id=?",
                         (acik, tutar, ri["islem_id"]))
            conn.commit()
            conn.close()
        else:
            # Yeni kayıt
            conn = db_connect()
            cur = conn.execute(
                "INSERT INTO islemler (servis_id, aciklama, tutar) VALUES (?,?,?)",
                (self._aktif_servis["id"], acik, tutar)
            )
            ri["islem_id"] = cur.lastrowid
            conn.commit()
            conn.close()
            # Foto butonunu aktif hale getir
            if "foto_guncelle" in ri:
                ri["foto_guncelle"]()

        ri["tutar_var"].set(f"{tutar:.2f}")
        self._toplam_guncelle()

    def _toplam_guncelle(self):
        toplam = 0.0
        for ri in self._grid_rows:
            try:
                toplam += float(ri["tutar_var"].get().replace(",", ".") or 0)
            except ValueError:
                pass
        self.lbl_toplam.config(text=f"TOPLAM: ₺{toplam:,.2f}")

    def _yeni_satir_ekle(self):
        if not self._aktif_servis:
            return
        self._satir_ekle_widget(None, "", 0.0)
        # Yeni satırın açıklama alanına odaklan
        if self._grid_rows:
            self._grid_rows[-1]["acik_e"].focus_set()
        self._edit_canvas.yview_moveto(1.0)


    # ══════════════════════════════════════════════════════════════════════
    # KAMERA TARAMA
    # ══════════════════════════════════════════════════════════════════════

    # ══════════════════════════════════════════════════════════════════════
    # ARAÇ FOTOĞRAFLARI
    # ══════════════════════════════════════════════════════════════════════
    def _arac_fotograflari_goster(self):
        if not self._aktif_arac:
            return
        fotograflar = arac_foto_listele(self._aktif_arac["id"])
        if not fotograflar:
            if messagebox.askyesno("Fotoğraf Yok",
                "Bu araca ait fotoğraf yok.\nŞimdi eklemek ister misiniz?",
                parent=self):
                self._arac_foto_ekle_dialog(self._aktif_arac["id"], None)
            return
        self._foto_viewer(fotograflar, f"{self._aktif_arac['plaka']} — Fotoğraflar")

    def _arac_foto_ekle_dialog(self, arac_id, parent_win):
        pw = parent_win or self
        win = tk.Toplevel(pw)
        win.title("Araç Fotoğrafı Ekle")
        win.configure(bg=BG)
        win.geometry("520x360")
        win.resizable(False, False)
        win.grab_set()
        win.transient(pw)
        px = pw.winfo_x() + (pw.winfo_width() - 520) // 2
        py = pw.winfo_y() + (pw.winfo_height() - 360) // 2
        win.geometry(f"520x360+{px}+{py}")

        tk.Label(win, text="ARAÇ FOTOĞRAFI EKLE", bg="#9b59b6", fg=WHITE,
                 font=("Segoe UI", 11, "bold"), pady=10).pack(fill="x")

        body = tk.Frame(win, bg=BG, padx=20, pady=14)
        body.pack(fill="both", expand=True)

        secilen = [None]

        # Önizleme
        on_f = tk.Frame(body, bg=SURFACE, width=170, height=130)
        on_f.pack_propagate(False)
        on_f.pack(side="right", padx=(12, 0))
        on_lbl = tk.Label(on_f, bg=SURFACE, fg=MUTED, text="Önizleme", font=("Segoe UI", 9))
        on_lbl.pack(expand=True)

        def onizle(yol):
            try:
                from PIL import Image as PI, ImageTk as PIT
                img = PI.open(yol); img.thumbnail((166, 126), PI.LANCZOS)
                imgtk = PIT.PhotoImage(img)
                on_lbl.config(image=imgtk, text=""); on_lbl.imgtk = imgtk
            except Exception:
                on_lbl.config(text="Önizleme yok", image="")

        sol = tk.Frame(body, bg=BG)
        sol.pack(side="left", fill="both", expand=True)

        dosya_var = tk.StringVar(value="Henüz seçilmedi...")
        tk.Label(sol, textvariable=dosya_var, bg=BG, fg=MUTED,
                 font=("Segoe UI", 8), wraplength=260, anchor="w").pack(fill="x", pady=(0, 10))

        btn_ref = [None]

        def dosya_sec():
            yol = filedialog.askopenfilename(parent=win, title="Fotoğraf Seç",
                filetypes=[("Resim", "*.jpg *.jpeg *.png *.bmp *.gif *.webp"), ("Tümü", "*.*")])
            if yol:
                secilen[0] = yol; dosya_var.set(os.path.basename(yol))
                btn_ref[0].config(state="normal"); onizle(yol)

        def kam_cek():
            self._kamera_ile_cek(win, secilen, dosya_var, btn_ref, onizle)

        tk.Button(sol, text="📁  Dosyadan Seç", command=dosya_sec,
                  bg=ACCENT2, fg=WHITE, font=("Segoe UI", 10, "bold"),
                  relief="flat", bd=0, padx=14, pady=8, cursor="hand2").pack(fill="x", pady=(0, 6))
        tk.Button(sol, text="📷  Kamerayla Çek", command=kam_cek,
                  bg="#9b59b6", fg=WHITE, font=("Segoe UI", 10, "bold"),
                  relief="flat", bd=0, padx=14, pady=8, cursor="hand2").pack(fill="x", pady=(0, 14))

        tk.Label(sol, text="Açıklama:", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        acik_e = tk.Entry(sol, font=("Segoe UI", 10))
        style_entry(acik_e)
        acik_e.pack(fill="x", ipady=5, pady=(4, 0))

        footer2 = tk.Frame(win, bg=BG, padx=20, pady=10)
        footer2.pack(fill="x")

        def kaydet():
            if not secilen[0]: return
            try:
                import uuid
                ext = os.path.splitext(secilen[0])[1].lower() or ".jpg"
                yeni_ad = f"{uuid.uuid4().hex}{ext}"
                shutil.copy2(secilen[0], os.path.join(FOTO_KLASOR, yeni_ad))
                arac_foto_ekle(arac_id, yeni_ad, acik_e.get().strip())
                win.destroy()
                messagebox.showinfo("Tamam", "Fotoğraf eklendi!", parent=pw)
            except Exception as ex:
                messagebox.showerror("Hata", f"Eklenemedi:\n{ex}", parent=win)

        btn_kyd = tk.Button(footer2, text="✅ Kaydet", command=kaydet, state="disabled",
                            bg=SUCCESS, fg=BG, font=("Segoe UI", 10, "bold"),
                            relief="flat", bd=0, padx=18, pady=6, cursor="hand2")
        btn_kyd.pack(side="right")
        btn_ref[0] = btn_kyd
        tk.Button(footer2, text="İptal", command=win.destroy,
                  bg=SURFACE2, fg=TEXT, font=("Segoe UI", 10),
                  relief="flat", bd=0, padx=14, pady=6, cursor="hand2").pack(side="right", padx=(0, 8))

    def _arac_foto_sekme_yukle(self, frame, arac_id):
        """Düzenleme dialogundaki fotoğraflar sekmesi."""
        for w in frame.winfo_children():
            w.destroy()

        fotograflar = arac_foto_listele(arac_id)

        # Üst araç çubuğu
        ust = tk.Frame(frame, bg=BG)
        ust.pack(fill="x", pady=(0, 8))
        tk.Label(ust, text=f"{len(fotograflar)} fotoğraf", bg=BG, fg=MUTED,
                 font=("Segoe UI", 9)).pack(side="left")
        tk.Button(ust, text="＋ Fotoğraf Ekle",
                  command=lambda: [self._arac_foto_ekle_dialog(arac_id, frame.winfo_toplevel()),
                                   frame.after(500, lambda: self._arac_foto_sekme_yukle(frame, arac_id))],
                  bg="#9b59b6", fg=WHITE, font=("Segoe UI", 9, "bold"),
                  relief="flat", bd=0, padx=12, pady=5, cursor="hand2").pack(side="right")

        if not fotograflar:
            tk.Label(frame, text="Henüz fotoğraf eklenmemiş.\nYukarıdaki butonu kullanın.",
                     bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(expand=True)
            return

        # Izgara: 3 sütun küçük resimler
        grid_f = tk.Frame(frame, bg=BG)
        grid_f.pack(fill="both", expand=True)

        for i, foto in enumerate(fotograflar):
            col = i % 3
            row_idx = i // 3
            cell = tk.Frame(grid_f, bg=SURFACE, padx=4, pady=4)
            cell.grid(row=row_idx, column=col, padx=6, pady=6, sticky="nsew")

            # Resim
            img_lbl = tk.Label(cell, bg=SURFACE, cursor="hand2", width=14, height=6)
            img_lbl.pack()

            tam_yol = os.path.join(FOTO_KLASOR, foto["dosya_adi"])
            try:
                from PIL import Image as PI, ImageTk as PIT
                img = PI.open(tam_yol); img.thumbnail((110, 80), PI.LANCZOS)
                imgtk = PIT.PhotoImage(img)
                img_lbl.config(image=imgtk, text=""); img_lbl.imgtk = imgtk
            except Exception:
                img_lbl.config(text="📷", font=("Segoe UI", 20), fg=MUTED)

            # Açıklama
            acik = foto["aciklama"] or ""
            if acik:
                tk.Label(cell, text=acik[:18], bg=SURFACE, fg=MUTED,
                         font=("Segoe UI", 7)).pack()

            # Tıklayınca büyük aç
            def _ac(e, yol=tam_yol):
                if os.path.exists(yol):
                    import subprocess; subprocess.Popen(["start", "", yol], shell=True)
            img_lbl.bind("<Button-1>", _ac)

            # Sil butonu
            def _sil(fid=foto["id"], fad=foto["dosya_adi"]):
                if messagebox.askyesno("Sil", "Bu fotoğraf silinecek?", parent=frame.winfo_toplevel()):
                    arac_foto_sil(fid, fad)
                    self._arac_foto_sekme_yukle(frame, arac_id)
            tk.Button(cell, text="🗑", command=_sil,
                      bg=SURFACE, fg=MUTED, font=("Segoe UI", 8),
                      relief="flat", bd=0, cursor="hand2",
                      activebackground=DANGER, activeforeground=WHITE).pack()

        for c in range(3):
            grid_f.columnconfigure(c, weight=1)

    # ══════════════════════════════════════════════════════════════════════
    # FOTOĞRAF İŞLEMLERİ
    # ══════════════════════════════════════════════════════════════════════
    def _foto_ekle_dialog(self):
        if not self._aktif_servis:
            return

        win = tk.Toplevel(self)
        win.title("Fotoğraf Ekle")
        win.configure(bg=BG)
        win.geometry("560x400")
        win.resizable(False, False)
        win.grab_set()
        win.transient(self)
        px = self.winfo_x() + (self.winfo_width() - 560) // 2
        py = self.winfo_y() + (self.winfo_height() - 400) // 2
        win.geometry(f"560x400+{px}+{py}")

        tk.Label(win, text="FOTOĞRAF EKLE", bg="#9b59b6", fg=WHITE,
                 font=("Segoe UI", 11, "bold"), pady=10).pack(fill="x")

        body = tk.Frame(win, bg=BG, padx=24, pady=14)
        body.pack(fill="both", expand=True)

        secilen = [None]  # dosya yolu veya geçici yol

        # ── Önizleme alanı ────────────────────────────────────────────────
        onizleme_f = tk.Frame(body, bg=SURFACE, width=200, height=150)
        onizleme_f.pack_propagate(False)
        onizleme_f.pack(side="right", padx=(12, 0))
        onizleme_lbl = tk.Label(onizleme_f, bg=SURFACE, fg=MUTED,
                                text="Önizleme", font=("Segoe UI", 9))
        onizleme_lbl.pack(expand=True)

        def onizle(yol):
            try:
                from PIL import Image as PI, ImageTk as PIT
                img = PI.open(yol)
                img.thumbnail((196, 146), PI.LANCZOS)
                imgtk = PIT.PhotoImage(img)
                onizleme_lbl.config(image=imgtk, text="")
                onizleme_lbl.imgtk = imgtk
            except Exception:
                onizleme_lbl.config(text="Önizleme yok", image="")

        # ── Sol: butonlar ─────────────────────────────────────────────────
        sol = tk.Frame(body, bg=BG)
        sol.pack(side="left", fill="both", expand=True)

        dosya_var = tk.StringVar(value="Henüz seçilmedi...")
        tk.Label(sol, textvariable=dosya_var, bg=BG, fg=MUTED,
                 font=("Segoe UI", 8), wraplength=280, anchor="w").pack(fill="x", pady=(0, 10))

        def dosya_sec():
            yol = filedialog.askopenfilename(
                parent=win, title="Fotoğraf Seç",
                filetypes=[("Resim Dosyaları", "*.jpg *.jpeg *.png *.bmp *.gif *.webp"),
                           ("Tüm Dosyalar", "*.*")]
            )
            if yol:
                secilen[0] = yol
                dosya_var.set(os.path.basename(yol))
                btn_kaydet.config(state="normal")
                onizle(yol)

        tk.Button(sol, text="📁  Dosyadan Seç",
                  command=dosya_sec,
                  bg=ACCENT2, fg=WHITE, font=("Segoe UI", 10, "bold"),
                  relief="flat", bd=0, padx=14, pady=8, cursor="hand2",
                  activebackground="#3a8fd4", activeforeground=WHITE).pack(fill="x", pady=(0, 6))

        def kamerayla_cek():
            # Kamera seçim penceresi
            self._kamera_ile_cek(win, secilen, dosya_var, btn_kaydet_ref, onizle)

        tk.Button(sol, text="📷  Kamerayla Çek",
                  command=kamerayla_cek,
                  bg="#9b59b6", fg=WHITE, font=("Segoe UI", 10, "bold"),
                  relief="flat", bd=0, padx=14, pady=8, cursor="hand2",
                  activebackground="#6c3483", activeforeground=WHITE).pack(fill="x", pady=(0, 14))

        # Açıklama
        tk.Label(sol, text="Açıklama:", bg=BG, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w")
        acik_e = tk.Entry(sol, font=("Segoe UI", 10))
        style_entry(acik_e)
        acik_e.pack(fill="x", ipady=5, pady=(4, 0))

        # Alt butonlar
        footer = tk.Frame(win, bg=BG, padx=24, pady=10)
        footer.pack(fill="x")

        def kaydet():
            if not secilen[0]:
                return
            try:
                import uuid
                ext = os.path.splitext(secilen[0])[1].lower() or ".jpg"
                yeni_ad = f"{uuid.uuid4().hex}{ext}"
                hedef = os.path.join(FOTO_KLASOR, yeni_ad)
                shutil.copy2(secilen[0], hedef)
                foto_ekle(self._aktif_servis["id"], yeni_ad, acik_e.get().strip())
                win.destroy()
                messagebox.showinfo("Tamam", "Fotoğraf başarıyla eklendi!", parent=self)
            except Exception as ex:
                messagebox.showerror("Hata", f"Fotoğraf eklenemedi:\n{ex}", parent=win)

        btn_kaydet = tk.Button(footer, text="✅ Kaydet",
                               command=kaydet, state="disabled",
                               bg=SUCCESS, fg=BG, font=("Segoe UI", 10, "bold"),
                               relief="flat", bd=0, padx=18, pady=6, cursor="hand2")
        btn_kaydet.pack(side="right")
        btn_kaydet_ref = [btn_kaydet]

        tk.Button(footer, text="İptal", command=win.destroy,
                  bg=SURFACE2, fg=TEXT, font=("Segoe UI", 10),
                  relief="flat", bd=0, padx=14, pady=6, cursor="hand2").pack(side="right", padx=(0, 8))

    def _kamera_ile_cek(self, parent_win, secilen, dosya_var, btn_kaydet_ref, onizle_fn):
        """Kamera açar, fotoğraf çeker. Geçici dosya yok — bellek üzerinden."""
        try:
            import cv2
            from PIL import Image as PI, ImageTk as PIT
        except ImportError:
            messagebox.showerror("Hata",
                "Kamera için opencv-python gerekli:\n"
                "  pip install opencv-python pillow",
                parent=parent_win)
            return

        # Kameraları tara — C++ seviye hataları da bastır
        import sys as _sys, io as _io
        kameralar = []
        for i in range(3):
            # C++ stderr'i file descriptor seviyesinde kapat
            _old_fd = os.dup(2)
            _nul = open(os.devnull, 'w')
            os.dup2(_nul.fileno(), 2)
            _sys.stderr = _io.StringIO()
            try:
                c = cv2.VideoCapture(i)
                if c.isOpened():
                    ret, _ = c.read()
                    if ret:
                        kameralar.append(i)
                c.release()
            except Exception:
                pass
            finally:
                os.dup2(_old_fd, 2)
                os.close(_old_fd)
                _nul.close()
                _sys.stderr = sys.__stderr__

        if not kameralar:
            messagebox.showerror("Hata", "Hiç kamera bulunamadı!", parent=parent_win)
            return

        kam_win = tk.Toplevel(parent_win)
        kam_win.title("Kamerayla Fotoğraf Çek")
        kam_win.configure(bg=BG)
        kam_win.geometry("680x520")
        kam_win.grab_set()
        kam_win.transient(parent_win)
        px = parent_win.winfo_x() + (parent_win.winfo_width() - 680) // 2
        py = parent_win.winfo_y() + (parent_win.winfo_height() - 520) // 2
        kam_win.geometry(f"680x520+{px}+{py}")

        tk.Label(kam_win, text="KAMERAYLA FOTOĞRAF ÇEK", bg="#9b59b6", fg=WHITE,
                 font=("Segoe UI", 11, "bold"), pady=10).pack(fill="x")

        # Çok kamera varsa seçici
        secili_kam = tk.IntVar(value=kameralar[0])
        if len(kameralar) > 1:
            ust = tk.Frame(kam_win, bg=BG)
            ust.pack(fill="x", padx=12, pady=(4, 0))
            tk.Label(ust, text="Kamera:", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="left")
            for ki in kameralar:
                tk.Radiobutton(ust, text=f"Kamera {ki}", variable=secili_kam, value=ki,
                               bg=BG, fg=TEXT, selectcolor=SURFACE2,
                               font=("Segoe UI", 9), cursor="hand2").pack(side="left", padx=6)

        canvas_k = tk.Canvas(kam_win, bg="#000", width=640, height=400, highlightthickness=0)
        canvas_k.pack(padx=16, pady=6)

        lbl_d = tk.Label(kam_win, text="Kamera açılıyor...", bg=BG, fg=MUTED, font=("Segoe UI", 9))
        lbl_d.pack()

        btn_row = tk.Frame(kam_win, bg=BG)
        btn_row.pack(fill="x", padx=16, pady=6)

        cam_running = [True]
        last_frame = [None]
        cap = [None]

        import threading as _th
        import time as _time

        pending_frame = [None]  # thread → UI köprüsü

        def kamera_dongu():
            ki = secili_kam.get()
            cap[0] = cv2.VideoCapture(ki)
            if not cap[0].isOpened():
                kam_win.after(0, lambda: lbl_d.config(text="Kamera açılamadı!", fg=DANGER))
                return
            cam_running[0] = True
            kam_win.after(0, lambda: lbl_d.config(
                text="Hazır — Fotoğraf Çek butonuna basın", fg=SUCCESS))
            while cam_running[0]:
                ret, frame = cap[0].read()
                if ret:
                    last_frame[0] = frame
                    pending_frame[0] = frame
                _time.sleep(0.033)  # ~30fps okuma

        def ui_dongu():
            """Ana thread'de canvas'ı günceller — flicker yok."""
            if not cam_running[0]:
                return
            f = pending_frame[0]
            if f is not None:
                pending_frame[0] = None
                try:
                    h, w = f.shape[:2]
                    scale = min(640/w, 400/h)
                    rsz = cv2.resize(f, (int(w*scale), int(h*scale)))
                    rgb = cv2.cvtColor(rsz, cv2.COLOR_BGR2RGB)
                    pil = PI.fromarray(rgb)
                    imgtk = PIT.PhotoImage(pil)
                    canvas_k.imgtk = imgtk
                    canvas_k.delete("all")
                    canvas_k.create_image(320, 200, image=imgtk, anchor="center")
                except Exception:
                    pass
            kam_win.after(40, ui_dongu)  # ~25fps UI

        def kapat_kamera():
            cam_running[0] = False
            _th.Thread(target=lambda: (
                _time.sleep(0.15),
                cap[0].release() if cap[0] else None
            ), daemon=True).start()
            kam_win.destroy()

        def cek():
            if last_frame[0] is None:
                messagebox.showwarning("Uyarı", "Görüntü alınamadı.", parent=kam_win)
                return
            # Doğrudan belleğe — geçici dosya yok
            frame_rgb = cv2.cvtColor(last_frame[0], cv2.COLOR_BGR2RGB)
            pil_img = PI.fromarray(frame_rgb)

            import uuid, io
            yeni_ad = f"kamera_{uuid.uuid4().hex}.jpg"
            hedef = os.path.join(FOTO_KLASOR, yeni_ad)
            pil_img.save(hedef, "JPEG", quality=92)

            secilen[0] = hedef
            dosya_var.set("Kamerayla çekildi ✓")
            btn_kaydet_ref[0].config(state="normal")
            onizle_fn(hedef)
            kapat_kamera()

        if len(kameralar) > 1:
            def kamera_degistir():
                cam_running[0] = False
                if cap[0]: cap[0].release()
                _time.sleep(0.2)
                cam_running[0] = True
                _th.Thread(target=kamera_dongu, daemon=True).start()
            tk.Button(btn_row, text="🔄 Kamera Değiştir", command=kamera_degistir,
                      bg=SURFACE2, fg=TEXT, font=("Segoe UI", 9, "bold"),
                      relief="flat", bd=0, padx=12, pady=6, cursor="hand2").pack(side="left")

        tk.Button(btn_row, text="📸  Fotoğraf Çek", command=cek,
                  bg=ACCENT, fg=BG, font=("Segoe UI", 11, "bold"),
                  relief="flat", bd=0, padx=20, pady=7, cursor="hand2").pack(side="left", padx=(8, 0))
        tk.Button(btn_row, text="İptal", command=kapat_kamera,
                  bg=DANGER, fg=WHITE, font=("Segoe UI", 10, "bold"),
                  relief="flat", bd=0, padx=14, pady=7, cursor="hand2").pack(side="right")

        kam_win.protocol("WM_DELETE_WINDOW", kapat_kamera)
        _th.Thread(target=kamera_dongu, daemon=True).start()
        kam_win.after(100, ui_dongu)

    def _islem_fotograflari_goster(self, islem_id):
        """Belirli bir işlemin fotoğraflarını gösterir."""
        fotograflar = foto_listele_islem(islem_id)
        if not fotograflar:
            # Fotoğraf yok — eklemek ister mi?
            if messagebox.askyesno("Fotoğraf Yok",
                "Bu işleme ait fotoğraf yok.\nŞimdi fotoğraf eklemek ister misiniz?",
                parent=self):
                self._islem_foto_ekle(islem_id)
            return
        self._foto_viewer(fotograflar, f"İşlem Fotoğrafları")

    def _islem_foto_ekle(self, islem_id):
        """Belirli bir işleme fotoğraf ekler."""
        if not self._aktif_servis:
            return

        win = tk.Toplevel(self)
        win.title("İşleme Fotoğraf Ekle")
        win.configure(bg=BG)
        win.geometry("560x380")
        win.resizable(False, False)
        win.grab_set()
        win.transient(self)
        px = self.winfo_x() + (self.winfo_width() - 560) // 2
        py = self.winfo_y() + (self.winfo_height() - 380) // 2
        win.geometry(f"560x380+{px}+{py}")

        tk.Label(win, text="İŞLEME FOTOĞRAF EKLE", bg="#9b59b6", fg=WHITE,
                 font=("Segoe UI", 11, "bold"), pady=10).pack(fill="x")

        body = tk.Frame(win, bg=BG, padx=24, pady=14)
        body.pack(fill="both", expand=True)

        secilen = [None]

        onizleme_f = tk.Frame(body, bg=SURFACE, width=180, height=140)
        onizleme_f.pack_propagate(False)
        onizleme_f.pack(side="right", padx=(12, 0))
        onizleme_lbl = tk.Label(onizleme_f, bg=SURFACE, fg=MUTED,
                                text="Önizleme", font=("Segoe UI", 9))
        onizleme_lbl.pack(expand=True)

        def onizle(yol):
            try:
                from PIL import Image as PI, ImageTk as PIT
                img = PI.open(yol)
                img.thumbnail((176, 136), PI.LANCZOS)
                imgtk = PIT.PhotoImage(img)
                onizleme_lbl.config(image=imgtk, text="")
                onizleme_lbl.imgtk = imgtk
            except Exception:
                onizleme_lbl.config(text="Önizleme yok", image="")

        sol = tk.Frame(body, bg=BG)
        sol.pack(side="left", fill="both", expand=True)

        dosya_var = tk.StringVar(value="Henüz seçilmedi...")
        tk.Label(sol, textvariable=dosya_var, bg=BG, fg=MUTED,
                 font=("Segoe UI", 8), wraplength=260, anchor="w").pack(fill="x", pady=(0, 10))

        def dosya_sec():
            yol = filedialog.askopenfilename(
                parent=win, title="Fotoğraf Seç",
                filetypes=[("Resim Dosyaları", "*.jpg *.jpeg *.png *.bmp *.gif *.webp"),
                           ("Tüm Dosyalar", "*.*")]
            )
            if yol:
                secilen[0] = yol
                dosya_var.set(os.path.basename(yol))
                btn_kaydet.config(state="normal")
                onizle(yol)

        btn_ref = [None]

        def kamerayla_cek():
            self._kamera_ile_cek(win, secilen, dosya_var, btn_ref, onizle)

        tk.Button(sol, text="📁  Dosyadan Seç",
                  command=dosya_sec,
                  bg=ACCENT2, fg=WHITE, font=("Segoe UI", 10, "bold"),
                  relief="flat", bd=0, padx=14, pady=8, cursor="hand2").pack(fill="x", pady=(0, 6))

        tk.Button(sol, text="📷  Kamerayla Çek",
                  command=kamerayla_cek,
                  bg="#9b59b6", fg=WHITE, font=("Segoe UI", 10, "bold"),
                  relief="flat", bd=0, padx=14, pady=8, cursor="hand2").pack(fill="x", pady=(0, 14))

        tk.Label(sol, text="Açıklama:", bg=BG, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w")
        acik_e = tk.Entry(sol, font=("Segoe UI", 10))
        style_entry(acik_e)
        acik_e.pack(fill="x", ipady=5, pady=(4, 0))

        footer = tk.Frame(win, bg=BG, padx=24, pady=10)
        footer.pack(fill="x")

        def kaydet():
            if not secilen[0]:
                return
            try:
                import uuid
                ext = os.path.splitext(secilen[0])[1].lower() or ".jpg"
                yeni_ad = f"{uuid.uuid4().hex}{ext}"
                hedef = os.path.join(FOTO_KLASOR, yeni_ad)
                shutil.copy2(secilen[0], hedef)
                foto_ekle(self._aktif_servis["id"], yeni_ad,
                          acik_e.get().strip(), islem_id=islem_id)
                win.destroy()
                # İlgili satırın foto butonunu güncelle
                for ri in self._grid_rows:
                    if ri.get("islem_id") == islem_id and "foto_guncelle" in ri:
                        ri["foto_guncelle"]()
                        break
            except Exception as ex:
                messagebox.showerror("Hata", f"Fotoğraf eklenemedi:\n{ex}", parent=win)

        btn_kaydet = tk.Button(footer, text="✅ Kaydet",
                               command=kaydet, state="disabled",
                               bg=SUCCESS, fg=BG, font=("Segoe UI", 10, "bold"),
                               relief="flat", bd=0, padx=18, pady=6, cursor="hand2")
        btn_kaydet.pack(side="right")
        btn_ref[0] = btn_kaydet

        tk.Button(footer, text="İptal", command=win.destroy,
                  bg=SURFACE2, fg=TEXT, font=("Segoe UI", 10),
                  relief="flat", bd=0, padx=14, pady=6, cursor="hand2").pack(side="right", padx=(0, 8))

    def _foto_viewer(self, fotograflar, baslik="Fotoğraflar"):
        """Fotoğraf listesini gösterir (paylaşılan viewer)."""
        foto_data = [dict(f) for f in fotograflar]
        win = tk.Toplevel(self)
        win.title(baslik)
        win.configure(bg=BG)
        win.geometry("820x560")
        win.grab_set()
        win.transient(self)
        px = self.winfo_x() + (self.winfo_width() - 820) // 2
        py = self.winfo_y() + (self.winfo_height() - 560) // 2
        win.geometry(f"820x560+{px}+{py}")

        tk.Label(win, text=baslik.upper(), bg="#9b59b6", fg=WHITE,
                 font=("Segoe UI", 11, "bold"), pady=10).pack(fill="x")

        sol = tk.Frame(win, bg=SURFACE, width=220)
        sol.pack(side="left", fill="y")
        sol.pack_propagate(False)
        tk.Label(sol, text="Fotoğraflar", bg=SURFACE2, fg=ACCENT,
                 font=("Segoe UI", 9, "bold"), pady=6).pack(fill="x")
        listbox = tk.Listbox(sol, bg=SURFACE, fg=TEXT, selectbackground=ACCENT2,
                             selectforeground=WHITE, relief="flat", bd=0,
                             font=("Segoe UI", 9), activestyle="none", cursor="hand2")
        listbox.pack(fill="both", expand=True)
        for f in foto_data:
            ad = f["aciklama"] or os.path.basename(f["dosya_adi"])
            listbox.insert("end", f"  {ad}")

        sag = tk.Frame(win, bg=BG)
        sag.pack(side="right", fill="both", expand=True)
        preview_canvas = tk.Canvas(sag, bg="#000", highlightthickness=0)
        preview_canvas.pack(fill="both", expand=True, padx=8, pady=8)
        lbl_bilgi = tk.Label(sag, text="", bg=BG, fg=MUTED, font=("Segoe UI", 8))
        lbl_bilgi.pack()
        btn_row2 = tk.Frame(sag, bg=BG)
        btn_row2.pack(fill="x", padx=8, pady=(0, 8))

        def goster(event=None):
            sel = listbox.curselection()
            if not sel: return
            f = foto_data[sel[0]]
            tam_yol = os.path.join(FOTO_KLASOR, f["dosya_adi"])
            if not os.path.exists(tam_yol):
                preview_canvas.delete("all")
                preview_canvas.create_text(200, 150, text="Dosya bulunamadı!", fill=DANGER, font=("Segoe UI", 12))
                return
            try:
                from PIL import Image as PI, ImageTk as PIT
                img = PI.open(tam_yol)
                cw = preview_canvas.winfo_width() or 560
                ch = preview_canvas.winfo_height() or 400
                img.thumbnail((cw, ch), PI.LANCZOS)
                imgtk = PIT.PhotoImage(img)
                preview_canvas.delete("all")
                preview_canvas.imgtk = imgtk
                preview_canvas.create_image(cw//2, ch//2, image=imgtk, anchor="center")
                lbl_bilgi.config(text=f.get("eklenme", ""))
            except Exception as ex:
                preview_canvas.delete("all")
                preview_canvas.create_text(200, 150, text=f"Açılamadı: {ex}", fill=DANGER, font=("Segoe UI", 10))

        def sistemde_ac():
            sel = listbox.curselection()
            if not sel: return
            f = foto_data[sel[0]]
            tam_yol = os.path.join(FOTO_KLASOR, f["dosya_adi"])
            if os.path.exists(tam_yol):
                import subprocess
                subprocess.Popen(["start", "", tam_yol], shell=True)

        def sil_foto():
            sel = listbox.curselection()
            if not sel: return
            f = foto_data[sel[0]]
            if not messagebox.askyesno("Sil", "Bu fotoğraf silinecek. Emin misiniz?", parent=win):
                return
            foto_sil(f["id"], f["dosya_adi"])
            foto_data.pop(sel[0])
            listbox.delete(sel[0])
            preview_canvas.delete("all")
            lbl_bilgi.config(text="")
            self._islem_listesi_yukle()

        listbox.bind("<<ListboxSelect>>", goster)
        tk.Button(btn_row2, text="🖥 Büyük Aç", command=sistemde_ac,
                  bg=ACCENT2, fg=WHITE, font=("Segoe UI", 9, "bold"),
                  relief="flat", bd=0, padx=12, pady=5, cursor="hand2").pack(side="left")
        tk.Button(btn_row2, text="🗑 Sil", command=sil_foto,
                  bg=DANGER, fg=WHITE, font=("Segoe UI", 9, "bold"),
                  relief="flat", bd=0, padx=12, pady=5, cursor="hand2").pack(side="left", padx=(6, 0))
        tk.Button(btn_row2, text="Kapat", command=win.destroy,
                  bg=SURFACE2, fg=TEXT, font=("Segoe UI", 9),
                  relief="flat", bd=0, padx=12, pady=5, cursor="hand2").pack(side="right")

    def _fotograflari_goster(self):
        if not self._aktif_servis:
            return
        fotograflar = foto_listele(self._aktif_servis["id"])
        if not fotograflar:
            messagebox.showinfo("Fotoğraflar",
                "Bu servise ait fotoğraf bulunmuyor.",
                parent=self)
            return
        self._foto_viewer(fotograflar, f"Fotoğraflar — {self._aktif_servis['tarih']}")


# ══════════════════════════════════════════════════════════════════════════
# YARDIMCI: MODAL DİALOG
# ══════════════════════════════════════════════════════════════════════════
class _Dialog(tk.Toplevel):
    def __init__(self, parent, title, width=400, height=300):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=SURFACE2)
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)

        # Ortalama
        px = parent.winfo_x() + (parent.winfo_width() - width) // 2
        py = parent.winfo_y() + (parent.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{px}+{py}")

        tk.Label(self, text=title, bg=ACCENT, fg=BG,
                 font=("Segoe UI", 11, "bold"), pady=10).pack(fill="x")

        self.body = tk.Frame(self, bg=SURFACE2, padx=18, pady=14)
        self.body.pack(fill="both", expand=True)

        sep = tk.Frame(self, bg=BORDER, height=1)
        sep.pack(fill="x")

        self.footer = tk.Frame(self, bg=SURFACE2, padx=16, pady=10)
        self.footer.pack(fill="x")


# ══════════════════════════════════════════════════════════════════════════
# ÇALIŞTIR
# ══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = App()
    app.mainloop()
