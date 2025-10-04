import sys
import math
import pandas as pd
import pickle
import requests
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QLabel, QScrollArea, QFrame, QMessageBox, QHBoxLayout,
    QCheckBox, QSlider, QGroupBox, QFormLayout, QLineEdit,
    QComboBox, QSizePolicy, QSpacerItem, QProgressBar,
    QGridLayout, QTextEdit
)
from PyQt5.QtWidgets import QWidget as QtWidget
from PyQt5.QtGui import QFont, QPixmap, QIcon
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QGraphicsDropShadowEffect
from ai_description import describe_exoplanet
from planet_dialog import PlanetDialog
import plotly.express as px


ACCENT = "#22d3ee"  # cyjan
BG_DARK = "#0b1220"
CARD_BG = "#0f1726"
BORDER = "#1f2a44"
TEXT = "#e6eef8"
SUBTLE = "#b7c3d6"

# Głębszy motyw tylko dla okna opisu
DIALOG_BG = "#050913"
DIALOG_CARD = "#0a0f1d"
DIALOG_BORDER = "#111a2e"
DIALOG_TEXT = "#eaf2ff"


class ModernExoplanetApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Exoplanet — LAMBDA")
        self.setGeometry(80, 80, 1200, 820)
        self.setWindowIcon(QIcon("assets/kepler_logo.png"))

        # Global stylesheet — czystsza typografia, lepsze stany hover/pressed
        self.setStyleSheet(f"""
            QWidget {{ background-color: {BG_DARK}; color: {TEXT}; font-family: 'Segoe UI', Arial; }}
            QLabel#title {{ font-size: 22px; font-weight: 700; color: #fff; }}
            QLabel.small {{ color: {SUBTLE}; font-size: 11px; }}
            QGroupBox {{ border: 1px solid {BORDER}; border-radius: 12px; margin-top: 10px; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 2px 6px; color: {SUBTLE}; }}
            QScrollArea {{ border: none; }}

            QPushButton {{
                background-color: #162133;
                border: 1px solid {BORDER};
                border-radius: 10px;
                padding: 10px 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: #1c2a44; border-color: {ACCENT}; color: {ACCENT}; }}
            QPushButton:pressed {{ background-color: #0f1a33; }}

            QPushButton.primary {{ background-color: {ACCENT}; color: #001018; border: none; }}
            QPushButton.primary:hover {{ filter: brightness(1.1); }}

            QFrame.card {{ background-color: {CARD_BG}; border: 1px solid rgba(255,255,255,0.04); border-radius: 14px; }}
            QLabel.badge {{ border-radius: 999px; padding: 4px 10px; font-size: 11px; font-weight: 700; }}
            QLabel.badge.ok {{ background: rgba(34, 211, 238, .15); color: {ACCENT}; border: 1px solid rgba(34, 211, 238, .35); }}
            QLabel.badge.warn {{ background: rgba(245, 158, 11, .12); color: #f59e0b; border: 1px solid rgba(245, 158, 11, .3); }}
            QLabel.badge.err {{ background: rgba(239, 68, 68, .14); color: #ef4444; border: 1px solid rgba(239, 68, 68, .32); }}
        """)

        # Data
        self.df = None
        self.filtered_df = None
        self.model = None
        try:
            self.model = pickle.load(open("exoplanet_model.pkl", "rb"))
        except Exception as e:
            print("Error: failed to load the model at startup", e)

        # pagination
        self.current_page = 0
        self.page_size = 12

        # main layout: top toolbar + central area
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # --- top toolbar ---
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        logo = QLabel()
        pix = QPixmap("assets/kepler_logo.png")
        if not pix.isNull():
            pix = pix.scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo.setPixmap(pix)
        top_bar.addWidget(logo)

        title = QLabel("Exoplanet — LAMBDA")
        title.setObjectName("title")
        top_bar.addWidget(title)

        top_bar.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by ID (kepid) or label")
        self.search_input.returnPressed.connect(self.apply_filters)
        self.search_input.setMaximumWidth(420)
        top_bar.addWidget(self.search_input)

        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["6", "12", "24", "48"])
        self.page_size_combo.setCurrentText(str(self.page_size))
        self.page_size_combo.currentTextChanged.connect(self.on_page_size_change)
        top_bar.addWidget(QLabel("On page:"))
        top_bar.addWidget(self.page_size_combo)

        self.plot_button = QPushButton("Graph")
        self.plot_button.clicked.connect(self.show_plot)
        self.plot_button.setEnabled(False)
        top_bar.addWidget(self.plot_button)

        # Zamknij / minimalizuj — małe, dyskretne
        close_btn = QPushButton("✖")
        close_btn.setToolTip("Close app (Esc)")
        close_btn.setFixedSize(36, 36)
        close_btn.clicked.connect(self.close)
        top_bar.addWidget(close_btn)

        min_btn = QPushButton("▬")
        min_btn.setToolTip("Minimize window")
        min_btn.setFixedSize(36, 36)
        min_btn.clicked.connect(self.showMinimized)
        top_bar.addWidget(min_btn)

        main_layout.addLayout(top_bar)

        # --- central area ---
        center_layout = QHBoxLayout()
        center_layout.setSpacing(14)

        # sidebar (filtry)
        sidebar = QGroupBox("Filters and actions")
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setSpacing(8)

        load_btn = QPushButton("Import CSV")
        load_btn.clicked.connect(self.load_csv)
        load_btn.setProperty("class", "secondary")
        sidebar_layout.addWidget(load_btn)

        nasa_btn = QPushButton("Download data from NASA")
        nasa_btn.clicked.connect(self.fetch_nasa_data)
        sidebar_layout.addWidget(nasa_btn)

        demo_btn = QPushButton("Demo data")
        demo_btn.clicked.connect(self.load_demo_data)
        sidebar_layout.addWidget(demo_btn)

        # sliders with labels
        sliders = QGroupBox("Range")
        sliders_layout = QFormLayout()

        self.slider_radius = QSlider(Qt.Horizontal)
        self.slider_radius.setRange(0, 20)
        self.slider_radius.setValue(0)
        sliders_layout.addRow("Min radius (R⊕):", self.slider_radius)

        self.slider_depth = QSlider(Qt.Horizontal)
        self.slider_depth.setRange(0, 10000)
        self.slider_depth.setValue(0)
        sliders_layout.addRow("Min transition depth:", self.slider_depth)

        self.slider_period = QSlider(Qt.Horizontal)
        self.slider_period.setRange(0, 1000)
        self.slider_period.setValue(0)
        sliders_layout.addRow("Min period (days):", self.slider_period)

        sliders.setLayout(sliders_layout)
        sidebar_layout.addWidget(sliders)

        self.habitable_checkbox = QCheckBox("Only viable for life")
        sidebar_layout.addWidget(self.habitable_checkbox)

        self.exoplanet_checkbox = QCheckBox("Only confirmed exoplanets (prediciton)")
        sidebar_layout.addWidget(self.exoplanet_checkbox)

        apply_btn = QPushButton("Refresh filters")
        apply_btn.clicked.connect(self.apply_filters)
        apply_btn.setProperty("class", "primary")
        sidebar_layout.addWidget(apply_btn)

        save_btn = QPushButton("Save results")
        save_btn.clicked.connect(self.save_results)
        save_btn.setEnabled(False)
        self.save_btn = save_btn
        sidebar_layout.addWidget(save_btn)

        # turbo mode
        self.turbo_checkbox = QCheckBox("Turbo Mode - quick view")
        sidebar_layout.addWidget(self.turbo_checkbox)

        # progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        sidebar_layout.addWidget(self.progress)

        sidebar_layout.addStretch()
        sidebar.setLayout(sidebar_layout)
        sidebar.setMaximumWidth(360)
        center_layout.addWidget(sidebar)

        # content area: results + pagination
        content_box = QVBoxLayout()

        # results scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout()
        self.scroll_layout.setSpacing(10)
        self.scroll_content.setLayout(self.scroll_layout)
        self.scroll.setWidget(self.scroll_content)
        content_box.addWidget(self.scroll)

        # pagination controls
        pagination = QHBoxLayout()
        self.prev_button = QPushButton("◀ Previous")
        self.prev_button.clicked.connect(self.prev_page)
        self.prev_button.setEnabled(False)
        pagination.addWidget(self.prev_button)

        self.page_label = QLabel("Page 0 out of 0")
        pagination.addWidget(self.page_label)

        self.next_button = QPushButton("Next ▶")
        self.next_button.clicked.connect(self.next_page)
        self.next_button.setEnabled(False)
        pagination.addWidget(self.next_button)

        pagination.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.stats_label = QLabel("")
        self.stats_label.setProperty('class', 'small')
        pagination.addWidget(self.stats_label)

        content_box.addLayout(pagination)
        center_layout.addLayout(content_box)

        main_layout.addLayout(center_layout)

        # timer to animate progress to show loading feedback
        self.load_timer = QTimer()
        self.load_timer.timeout.connect(self._simulate_progress)
        self._progress_target = 0

        # small helper state
        self.page_size_selector = self.page_size_combo

        # save references for actions
        self.plot_button = self.plot_button
        self.save_btn = save_btn

        # Skróty klawiaturowe
        self.shortcut_setup()

    # ------------------- helpers -------------------
    def shortcut_setup(self):
        # proste skróty bez QShortcut (żeby nie dodawać importu): Esc zamyka, Ctrl+F fokusuje search
        self.keyPressEvent = self._key_press_override

    def _key_press_override(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        if event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_F:
            self.search_input.setFocus()

    def _get(self, row, key, default=None):
        try:
            if hasattr(row, 'get'):
                return row.get(key, default)
            return row[key] if key in row.index else default
        except Exception:
            return default

    def _safe_float(self, x):
        try:
            v = float(x)
            if pd.isna(v):
                return None
            return v
        except Exception:
            return None

    def _estimate_insolation(self, row):
        insol = self._safe_float(self._get(row, 'koi_insol'))
        if insol is not None:
            return insol
        teff = self._safe_float(self._get(row, 'koi_steff'))
        rstar = self._safe_float(self._get(row, 'koi_srad'))
        mstar = self._safe_float(self._get(row, 'koi_smass'))
        period = self._safe_float(self._get(row, 'koi_period'))
        a_au = None
        if period is not None and mstar is not None and mstar > 0:
            a_au = ((period/365.25)**2 * mstar)**(1/3)
        if teff is None or rstar is None or a_au is None or a_au == 0:
            return None
        l_rel = (rstar**2) * ((teff/5778.0)**4)
        insol = l_rel / (a_au**2)
        return insol

    # ------------------- data loading & processing -------------------
    def load_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Choose a CSV file", "", "CSV Files (*.csv)")
        if file_path:
            self._start_loading()
            QTimer.singleShot(50, lambda: self.process_file(file_path))

    def fetch_nasa_data(self):
        try:
            self._start_loading()
            url = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=select+*+from+cumulative&format=csv"
            response = requests.get(url, timeout=30)
            file_path = "nasa_exoplanets.csv"
            with open(file_path, "wb") as f:
                f.write(response.content)
            QMessageBox.information(self, "NASA", "Data from NASA downloaded.")
            QTimer.singleShot(50, lambda: self.process_file(file_path))
        except Exception as e:
            QMessageBox.critical(self, "Error NASA", str(e))
            self._stop_loading()

    def load_demo_data(self):
        self._start_loading()
        QTimer.singleShot(50, lambda: self.process_file("data/demo_exoplanets.csv"))

    def process_file(self, file_path):
        try:
            df = pd.read_csv(file_path, sep=",", skiprows=0, on_bad_lines="skip", engine="python")
            df.columns = df.columns.str.strip().str.lower()
            required = ['koi_period', 'koi_duration', 'koi_depth', 'koi_prad', 'kepid']
            optional = [c for c in ['ra', 'dec', 'koi_teq', 'koi_steff', 'koi_srad', 'koi_smass', 'koi_insol'] if c in df.columns]
            if not all(col in df.columns for col in required):
                QMessageBox.critical(self, "Error", f"Columns: {required}")
                self._stop_loading()
                return
            df = df[required + optional].dropna(subset=required)
            features = ['koi_period', 'koi_duration', 'koi_depth', 'koi_prad']
            for c in ['ra', 'dec', 'koi_teq', 'koi_steff', 'koi_srad', 'koi_smass', 'koi_insol']:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce')
            if all(c in df.columns for c in ['ra', 'dec']):
                df = df.dropna(subset=['ra', 'dec'])
                df = df[(df['ra'] >= 0) & (df['ra'] < 360) & (df['dec'] >= -90) & (df['dec'] <= 90)]

            if self.model is not None:
                df['prediction'] = self.model.predict(df[features])
            else:
                df['prediction'] = ((df['koi_prad'] > 0.8) & (df['koi_depth'] < 8000)).astype(int)

            df['prediction_label'] = df['prediction'].apply(lambda x: "EXOPLANET" if x == 1 else "FALSE POSITIVE")
            df['insolation_s_earth'] = df.apply(self._estimate_insolation, axis=1)
            df['habitable'] = df.apply(self.check_habitability, axis=1)

            self.df = df.reset_index(drop=True)
            self.filtered_df = self.df.copy()
            self.current_page = 0
            self.page_size = int(self.page_size_combo.currentText())
            self.update_page()

            self.plot_button.setEnabled(True)
            self.save_btn.setEnabled(True)
            self._stop_loading()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self._stop_loading()

    # -------------------- bardziej naukowe kryterium --------------------
    def check_habitability(self, row):
        r = self._safe_float(self._get(row, 'koi_prad'))
        teq = self._safe_float(self._get(row, 'koi_teq'))
        teff = self._safe_float(self._get(row, 'koi_steff'))
        S = self._safe_float(self._get(row, 'insolation_s_earth'))

        if teff is not None and not (2600 <= teff <= 7200):
            return "Conditions do not support life"

        rocky_strict = (r is not None) and (0.5 <= r <= 1.8)
        rocky_loose = (r is not None) and (0.5 <= r <= 2.5)

        if S is not None and rocky_strict and (0.35 <= S <= 1.5):
            return "Conditions support life"
        if S is not None and rocky_loose and (0.25 <= S <= 2.2):
            return "Conditions marginally support life"

        if teq is not None:
            if rocky_strict and (240 <= teq <= 330):
                return "Conditions support life"
            if rocky_loose and (200 <= teq <= 360):
                return "Marginally possible conditions"
        return "Conditions do not support life"

    # ------------------- filtering / pagination / UI update -------------------
    def apply_filters(self):
        if self.df is None:
            return
        df = self.df.copy()
        text = self.search_input.text().strip()
        if text:
            if text.isdigit():
                df = df[df['kepid'].astype(str).str.contains(text)]
            else:
                df = df[df['prediction_label'].str.contains(text, case=False) | df['habitable'].str.contains(text, case=False)]

        df = df[df['koi_prad'] >= self.slider_radius.value()]
        df = df[df['koi_depth'] >= self.slider_depth.value()]
        df = df[df['koi_period'] >= self.slider_period.value()]
        if self.habitable_checkbox.isChecked():
            df = df[df['habitable'].isin(["Conditions support life", "Conditions marginally support life"])]
        if self.exoplanet_checkbox.isChecked():
            df = df[df['prediction'] == 1]

        self.filtered_df = df.reset_index(drop=True)
        self.current_page = 0
        self.page_size = int(self.page_size_combo.currentText())
        self.update_page()

    def update_page(self):
        if self.filtered_df is None:
            return
        start = self.current_page * self.page_size
        end = start + self.page_size
        page_df = self.filtered_df.iloc[start:end]
        self.display_cards(page_df)
        self.show_stats(self.filtered_df)
        total_pages = max(1, (len(self.filtered_df) + self.page_size - 1) // self.page_size)
        self.page_label.setText(f"Page {self.current_page + 1} out of {total_pages}")
        self.prev_button.setEnabled(self.current_page > 0)
        self.next_button.setEnabled((self.current_page + 1) * self.page_size < len(self.filtered_df))

    def next_page(self):
        if (self.current_page + 1) * self.page_size < len(self.filtered_df):
            self.current_page += 1
            self.update_page()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_page()

    def _shadow(self, w, radius=24, opacity=0.3):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(radius)
        shadow.setColor(Qt.black)
        shadow.setXOffset(0)
        shadow.setYOffset(6)
        w.setGraphicsEffect(shadow)

    def _badge(self, text, kind="ok"):
        b = QLabel(text)
        b.setObjectName("badge")
        b.setProperty("class", f"badge {kind}")
        b.setAlignment(Qt.AlignCenter)
        return b

    def display_cards(self, df):
        for i in reversed(range(self.scroll_layout.count())):
            w = self.scroll_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        if df.empty:
            empty = QLabel("No results for the activated filters.")
            empty.setAlignment(Qt.AlignCenter)
            self.scroll_layout.addWidget(empty)
            return

        for _, row in df.iterrows():
            card = QFrame()
            card.setObjectName('card')
            card.setProperty('class', 'card')
            card_layout = QGridLayout(card)
            card_layout.setContentsMargins(14, 10, 14, 10)
            card_layout.setHorizontalSpacing(16)

            # lewa: identyfikacja
            left = QVBoxLayout()
            kep_label = QLabel(f"KepID: {row['kepid']}")
            kep_label.setFont(QFont('', 12, QFont.Weight.Bold))
            left.addWidget(kep_label)
            left.addWidget(QLabel(f"Radius (R⊕): {row['koi_prad']}"))
            left.addWidget(QLabel(f"Orbital period (days): {row['koi_period']}"))
            left.addWidget(QLabel(f"Transit depth: {row['koi_depth']}"))
            lwrap = QWidget(); lwrap.setLayout(left)
            card_layout.addWidget(lwrap, 0, 0)

            # środek: badge'e
            midw = QWidget(); mid = QVBoxLayout(midw)
            pred_label = str(row.get('prediction_label', '—'))
            hab_label = str(row.get('habitable', '—'))
            pred_badge = self._badge(pred_label, 'ok' if 'EXO' in pred_label else 'err')
            hab_kind = 'ok' if 'Conditions support life' in hab_label else ('warn' if 'Marginally' in hab_label else 'err')
            hab_badge = self._badge(hab_label, hab_kind)
            mid.addWidget(pred_badge)
            mid.addSpacing(6)
            mid.addWidget(hab_badge)
            if 'insolation_s_earth' in row and pd.notna(row['insolation_s_earth']):
                s = round(float(row['insolation_s_earth']), 3)
                mid.addSpacing(8)
                #mid.addWidget(QLabel(f"S (S⊕): {s}"))
            card_layout.addWidget(midw, 0, 1)

            # prawa: akcje
            rightw = QWidget(); right = QVBoxLayout(rightw)
            describe_btn = QPushButton("Description")
            describe_btn.setProperty("class", "primary")
            describe_btn.clicked.connect(lambda _, r=row: self.show_detail_dialog(r))
            right.addWidget(describe_btn)
            map_btn = QPushButton("Map")
            map_btn.clicked.connect(lambda _, r=row: self.show_sky_map(r))
            right.addWidget(map_btn)
            card_layout.addWidget(rightw, 0, 2)

            self._shadow(card, 20)
            self.scroll_layout.addWidget(card)

    # ======================== pełnoekranowy opis (stabilny, bez wideo) ========================
    def show_description(self, row):
        # Bez wyjątków krytycznych — wszystko w try/except
        try:
            description = describe_exoplanet(row)
        except Exception:
            description = "Missing description - failed to generate a description"

        dlg = QtWidget()
        dlg.setObjectName("opisRoot")
        dlg.setWindowTitle(f"Planet description {self._get(row,'kepid','')}")
        dlg.setWindowFlag(Qt.Window, True)
        dlg.setWindowModality(Qt.ApplicationModal)
        dlg.setStyleSheet(f"""
            QWidget#opisRoot {{ background-color: {DIALOG_BG}; color: {DIALOG_TEXT}; font-size: 16px; }}
            QLabel#heading {{ font-size: 24px; font-weight: 800; color: white; }}
            QTextEdit#desc {{ background: {DIALOG_CARD}; color: {DIALOG_TEXT}; border: 1px solid {DIALOG_BORDER}; border-radius: 12px; padding: 14px; font-size: 16px; }}
            QWidget#panel {{ background: {DIALOG_CARD}; border: 1px solid {DIALOG_BORDER}; border-radius: 14px; }}
            QLabel#caption {{ color: {DIALOG_TEXT}; padding: 8px 12px; font-size: 15px; }}
            QLabel.key {{ color:white; font-size: 15px; }}
            QLabel.val {{ color: white; font-weight: 600; font-size: 16px; }}
            QPushButton {{ background-color: #0f1a33; color: {DIALOG_TEXT}; border: 1px solid {DIALOG_BORDER}; border-radius: 10px; padding: 10px 14px; }}
            QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}
            QPushButton.primary {{ background-color: {ACCENT}; color: #001018; border: none; }}
        """)

        grid = QGridLayout(dlg)
        grid.setContentsMargins(18,18,18,18)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)

        # OPIS
        desc_box = QtWidget(); desc_box.setObjectName("panel")
        dlay = QVBoxLayout(desc_box); dlay.setContentsMargins(14,14,14,14)
        heading = QLabel(f"Planet {self._get(row,'kepid','')} — opis")
        heading.setObjectName("heading"); dlay.addWidget(heading)
        desc = QTextEdit(); desc.setReadOnly(True); desc.setObjectName("desc"); desc.setText(description)
        dlay.addWidget(desc)
        grid.addWidget(desc_box, 0, 0)

        # DANE
        params = QtWidget(); params.setObjectName("panel")
        form = QFormLayout(params); form.setHorizontalSpacing(16); form.setVerticalSpacing(10); form.setContentsMargins(16, 16, 16, 16)

        def _val(x, fmt="{:.3f}"):
            try:
                xf = float(x)
                if pd.isna(xf):
                    return "—"
                if abs(xf) >= 1000:
                    return f"{xf:.0f}"
                return fmt.format(xf)
            except Exception:
                return str(x) if (x is not None and x == x) else "—"

        prad    = self._safe_float(self._get(row, 'koi_prad'))
        period  = self._safe_float(self._get(row, 'koi_period'))
        depth   = self._safe_float(self._get(row, 'koi_depth'))
        dur     = self._safe_float(self._get(row, 'koi_duration'))
        teff    = self._safe_float(self._get(row, 'koi_steff'))
        rstar   = self._safe_float(self._get(row, 'koi_srad'))
        mstar   = self._safe_float(self._get(row, 'koi_smass'))
        insol   = self._safe_float(self._get(row, 'insolation_s_earth'))
        koi_ins = self._safe_float(self._get(row, 'koi_insol'))
        ra      = self._safe_float(self._get(row, 'ra'))
        dec     = self._safe_float(self._get(row, 'dec'))
        hab     = self._get(row, 'habitable', '—')
        pred    = self._get(row, 'prediction_label', '—')
        temp    = self._safe_float(self._get(row, 'koi_teq'))

        a_au = None
        if period is not None and mstar is not None and mstar > 0:
            a_au = ((period/365.25)**2 * mstar)**(1/3)
        l_rel = None
        if teff is not None and rstar is not None:
            l_rel = (rstar**2) * ((teff/5778.0)**4)
        if insol is None and l_rel is not None and a_au not in (None, 0):
            insol = l_rel / (a_au**2)

        # Pomocnicza funkcja dodawania wierszy
        def _kv(key_txt, val_txt):
            k = QLabel(key_txt); k.setObjectName("key")
            v = QLabel(val_txt); v.setObjectName("val")
            form.addRow(k, v)

        _kv("KepID:", str(self._get(row, "kepid", "")))
        _kv("Classification (prediction):", str(pred))
        _kv("Habitability:", str(hab))
        _kv("Planet radius (R⊕):", _val(prad))
        _kv("Orbital period (days):", _val(period))
        _kv("Transit depth (ppm):", _val(depth, "{:.0f}"))
        _kv("Time of transit (h):", _val(dur))
        _kv("Equilibrium temperature Teq (K):", _val(temp))
        _kv("S Stream (S⊕):", _val(insol))
        if koi_ins is not None:
            _kv("koi_insol (S⊕, catalog):", _val(koi_ins))
        _kv("Teff of a star (K):", _val(teff))
        _kv("Star radius (R☉):", _val(rstar))
        _kv("Star mass (M☉):", _val(mstar))
        if l_rel is not None:
            _kv("Star luminosity (L☉, est.):", _val(l_rel))
        if a_au is not None:
            _kv("Semimajor axis a (AU, est.):", _val(a_au))
        if ra is not None:
            _kv("RA (deg):", _val(ra))
        if dec is not None:
            _kv("DEC (deg):", _val(dec))

        grid.addWidget(params, 0, 1)

        # SEKCJA PLACEHOLDER RENDERA (bez multimediów)
        render_box = QtWidget(); render_box.setObjectName("panel")
        rlay = QVBoxLayout(render_box); rlay.setContentsMargins(12,12,12,12)
        caption = QLabel("Render (wideo): assets/lawa_rotacja.mp4 — podgląd wyłączony"); caption.setObjectName("caption")
        rlay.addWidget(caption)
        info = QLabel("To jest stabilny tryb bez odtwarzania wideo. Jeśli chcesz włączyć player, zainstaluj backend PyQt5 Multimedia (np. GStreamer) i zgłoś — dodam player z fallbackiem."); info.setWordWrap(True)
        rlay.addWidget(info)

        btn_close = QPushButton("Close  (Esc)")
        btn_close.clicked.connect(dlg.close)
        rlay.addWidget(btn_close, alignment=Qt.AlignRight)

        grid.addWidget(render_box, 1, 0, 1, 2)

        grid.setColumnStretch(0, 1); grid.setColumnStretch(1, 1)
        grid.setRowStretch(0, 1); grid.setRowStretch(1, 1)

        dlg.showFullScreen(); dlg.raise_(); dlg.activateWindow()

    def show_detail_dialog(self, row):
        # utrzymuj referencję, by GC nie zamknął okna
        if not hasattr(self, '_open_dialogs'):
            self._open_dialogs = []
        dlg = PlanetDialog(row, self)
        self._open_dialogs.append(dlg)
        dlg.exec_()
        try:
            self._open_dialogs.remove(dlg)
        except Exception:
            pass

    def show_sky_map(self, row):
        ra = self._get(row, 'ra')
        dec = self._get(row, 'dec')
        try:
            import pandas as _pd
            if ra is None or dec is None or _pd.isna(ra) or _pd.isna(dec):
                QMessageBox.information(self, 'Missing data', 'Missing RA/DEC coordinates for this planet dla tej planety.')
                return
        except Exception:
            pass
        try:
            from sky_map import SkyMap
            self._sky = SkyMap(ra=float(ra), dec=float(dec))
            self._sky.show()
        except Exception as e:
            QMessageBox.critical(self, 'Nightsky map', f'Failed to open map : {e}')

    def show_stats(self, df):
        total = len(df)
        exo = len(df[df['prediction'] == 1]) if 'prediction' in df.columns else 0
        avg_radius = round(df['koi_prad'].mean(), 2) if not df['koi_prad'].isnull().all() else 0
        avg_depth = round(df['koi_depth'].mean(), 2) if not df['koi_depth'].isnull().all() else 0
        avg_period = round(df['koi_period'].mean(), 2) if not df['koi_period'].isnull().all() else 0
        self.stats_label.setText(
            f"📊 {total} recorded — {exo} exoplanet | Avg. R: {avg_radius} | Avg. depth.: {avg_depth} | Avg. period: {avg_period}"
        )

    def show_plot(self):
        if self.df is None:
            return
        if not self.turbo_checkbox.isChecked():
            fig = px.histogram(self.df, x="habitable", color="habitable", title="Habitable Zone Graph")
            fig.update_layout(template="plotly_dark")
            fig.show()

    def save_results(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save as", "", "CSV Files (*.csv)")
        if file_path and self.df is not None:
            self.df.to_csv(file_path, index=False)
            QMessageBox.information(self, "Saved", "Results saved!")

    # ------------------- helpers: progress -------------------
    def on_page_size_change(self, txt):
        try:
            self.page_size = int(txt)
            self.update_page()
        except Exception:
            pass

    def _start_loading(self):
        self.progress.setValue(5)
        self._progress_target = 90
        if not hasattr(self, 'load_timer'):
            self.load_timer = QTimer()
            self.load_timer.timeout.connect(self._simulate_progress)
        self.load_timer.start(40)

    def _simulate_progress(self):
        v = self.progress.value()
        if v < self._progress_target:
            self.progress.setValue(min(v + 6, self._progress_target))
        else:
            self.load_timer.stop()

    def _stop_loading(self):
        self.progress.setValue(100)
        QTimer.singleShot(200, lambda: self.progress.setValue(0))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernExoplanetApp()
    window.showFullScreen()
    sys.exit(app.exec_())
