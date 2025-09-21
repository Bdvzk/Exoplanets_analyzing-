import sys
import pandas as pd
import pickle
import requests
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QLabel, QScrollArea, QFrame, QMessageBox, QHBoxLayout,
    QCheckBox, QSlider, QGroupBox, QFormLayout, QLineEdit,
    QComboBox, QSizePolicy, QSpacerItem, QProgressBar
)
from PyQt5.QtGui import QFont, QPixmap, QIcon
from PyQt5.QtCore import Qt, QTimer
from ai_description import describe_exoplanet
import plotly.express as px


class ModernExoplanetApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Exoplanet — Deluxe UI")
        self.setGeometry(80, 80, 1200, 820)
        self.setWindowIcon(QIcon("assets/kepler_logo.png"))

        # dark theme (elegancki, kontrastowy)
        self.setStyleSheet("""
            QWidget { background-color: #0f1720; color: #e6eef8; font-family: 'Segoe UI', Arial; }
            QLabel#title { font-size: 22px; font-weight: 700; color: #fff; }
            QPushButton { background-color: #1f2937; border-radius: 10px; padding: 8px 12px; }
            QPushButton:hover { background-color: #2b3a4a; }
            QGroupBox { border: 1px solid #203040; border-radius: 8px; margin-top: 6px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px 0 5px; }
            QScrollArea { border: none; }
            QFrame.card { background-color: #0f1726; border: 1px solid rgba(255,255,255,0.03); border-radius: 12px; }
            QLabel.small { color: #b7c3d6; font-size: 11px; }
        """)

        # Data
        self.df = None
        self.filtered_df = None
        self.model = None
        try:
            self.model = pickle.load(open("exoplanet_model.pkl", "rb"))
        except Exception as e:
            print("Uwaga: nie udało się załadować modelu przy starcie:", e)

        # pagination
        self.current_page = 0
        self.page_size = 12

        # main layout: top toolbar + central area (sidebar + content)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # --- top toolbar ---
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        logo = QLabel()
        pix = QPixmap("assets/kepler_logo.png")
        if not pix.isNull():
            pix = pix.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo.setPixmap(pix)
        top_bar.addWidget(logo)

        title = QLabel("Exoplanet — Deluxe Edition")
        title.setObjectName("title")
        top_bar.addWidget(title)

        top_bar.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Szukaj po ID (kepid) lub etykiecie predykcji...")
        self.search_input.returnPressed.connect(self.apply_filters)
        self.search_input.setMaximumWidth(360)
        top_bar.addWidget(self.search_input)

        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["6", "12", "24", "48"])
        self.page_size_combo.setCurrentText(str(self.page_size))
        self.page_size_combo.currentTextChanged.connect(self.on_page_size_change)
        top_bar.addWidget(QLabel("Na stronie:"))
        top_bar.addWidget(self.page_size_combo)

        self.plot_button = QPushButton("Pokaż wykres")
        self.plot_button.clicked.connect(self.show_plot)
        self.plot_button.setEnabled(False)
        top_bar.addWidget(self.plot_button)

        main_layout.addLayout(top_bar)

        # --- central area ---
        center_layout = QHBoxLayout()
        center_layout.setSpacing(14)

        # sidebar (filtry)
        sidebar = QGroupBox("Filtry i akcje")
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setSpacing(8)

        load_btn = QPushButton("Wczytaj CSV")
        load_btn.clicked.connect(self.load_csv)
        sidebar_layout.addWidget(load_btn)

        nasa_btn = QPushButton("Pobierz dane z NASA")
        nasa_btn.clicked.connect(self.fetch_nasa_data)
        sidebar_layout.addWidget(nasa_btn)

        demo_btn = QPushButton("Dane demo")
        demo_btn.clicked.connect(self.load_demo_data)
        sidebar_layout.addWidget(demo_btn)

        # sliders with labels
        sliders = QGroupBox("Zakresy")
        sliders_layout = QFormLayout()

        self.slider_radius = QSlider(Qt.Horizontal)
        self.slider_radius.setRange(0, 20)
        self.slider_radius.setValue(0)
        sliders_layout.addRow("Min promień (R⊕):", self.slider_radius)

        self.slider_depth = QSlider(Qt.Horizontal)
        self.slider_depth.setRange(0, 10000)
        self.slider_depth.setValue(0)
        sliders_layout.addRow("Min głębokość:", self.slider_depth)

        self.slider_period = QSlider(Qt.Horizontal)
        self.slider_period.setRange(0, 1000)
        self.slider_period.setValue(0)
        sliders_layout.addRow("Min okres (dni):", self.slider_period)

        sliders.setLayout(sliders_layout)
        sidebar_layout.addWidget(sliders)

        self.habitable_checkbox = QCheckBox("Tylko możliwe do życia")
        sidebar_layout.addWidget(self.habitable_checkbox)

        self.exoplanet_checkbox = QCheckBox("Tylko potwierdzone egzoplanety (predykcja)")
        sidebar_layout.addWidget(self.exoplanet_checkbox)

        apply_btn = QPushButton("Odśwież filtry")
        apply_btn.clicked.connect(self.apply_filters)
        sidebar_layout.addWidget(apply_btn)

        save_btn = QPushButton("Zapisz wyniki")
        save_btn.clicked.connect(self.save_results)
        save_btn.setEnabled(False)
        self.save_btn = save_btn
        sidebar_layout.addWidget(save_btn)

        # turbo mode
        self.turbo_checkbox = QCheckBox("Tryb Turbo — szybkie podglądy")
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
        self.prev_button = QPushButton("◀ Poprzednia")
        self.prev_button.clicked.connect(self.prev_page)
        self.prev_button.setEnabled(False)
        pagination.addWidget(self.prev_button)

        self.page_label = QLabel("Strona 0 z 0")
        pagination.addWidget(self.page_label)

        self.next_button = QPushButton("Następna ▶")
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

    # ------------------- data loading & processing -------------------
    def load_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Wybierz plik CSV", "", "CSV Files (*.csv)")
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
            QMessageBox.information(self, "NASA", "Dane z NASA pobrane.")
            QTimer.singleShot(50, lambda: self.process_file(file_path))
        except Exception as e:
            QMessageBox.critical(self, "Błąd NASA", str(e))
            self._stop_loading()

    def load_demo_data(self):
        self._start_loading()
        QTimer.singleShot(50, lambda: self.process_file("data/demo_exoplanets.csv"))

    def process_file(self, file_path):
        try:
            df = pd.read_csv(file_path, sep=",", skiprows=0, on_bad_lines="skip", engine="python")
            df.columns = df.columns.str.strip().str.lower()
            required = ['koi_period', 'koi_duration', 'koi_depth', 'koi_prad', 'kepid']
            if not all(col in df.columns for col in required):
                QMessageBox.critical(self, "Błąd", f"Brakuje kolumn: {required}")
                self._stop_loading()
                return
            df = df[required].dropna()
            features = ['koi_period', 'koi_duration', 'koi_depth', 'koi_prad']

            if self.model is not None:
                df['prediction'] = self.model.predict(df[features])
            else:
                # fallback: prosty heurystyczny predictor (jeśli model nie jest dostępny)
                df['prediction'] = ((df['koi_prad'] > 0.8) & (df['koi_depth'] < 8000)).astype(int)

            df['prediction_label'] = df['prediction'].apply(lambda x: "EGZOPLANETA" if x == 1 else "FAŁSZYWY POZYTYW")

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
            QMessageBox.critical(self, "Błąd", str(e))
            self._stop_loading()

    def check_habitability(self, row):
        if (
            0.5 <= row['koi_prad'] <= 2.5 and
            50 <= row['koi_period'] <= 500 and
            row['koi_depth'] < 5000
        ):
            return "Możliwe warunki do życia"
        else:
            return "Warunki nie sprzyjają życiu"

    # ------------------- filtering / pagination / UI update -------------------
    def apply_filters(self):
        if self.df is None:
            return
        df = self.df.copy()
        # wyszukiwanie tekstowe
        text = self.search_input.text().strip()
        if text:
            # prosty filtr: numeric -> kepid, else wyszukaj w labelach
            if text.isdigit():
                df = df[df['kepid'].astype(str).str.contains(text)]
            else:
                df = df[df['prediction_label'].str.contains(text, case=False) | df['habitable'].str.contains(text, case=False)]

        df = df[df['koi_prad'] >= self.slider_radius.value()]
        df = df[df['koi_depth'] >= self.slider_depth.value()]
        df = df[df['koi_period'] >= self.slider_period.value()]
        if self.habitable_checkbox.isChecked():
            df = df[df['habitable'] == "Możliwe warunki do życia"]
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
        self.page_label.setText(f"Strona {self.current_page + 1} z {total_pages}")
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

    def display_cards(self, df):
        # wyczyść
        for i in reversed(range(self.scroll_layout.count())):
            w = self.scroll_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        if df.empty:
            empty = QLabel("Brak wyników dla aktualnych filtrów.")
            empty.setAlignment(Qt.AlignCenter)
            self.scroll_layout.addWidget(empty)
            return

        # utwórz ładne karty
        for _, row in df.iterrows():
            card = QFrame()
            card.setObjectName('card')
            card.setProperty('class', 'card')
            card.setStyleSheet("")
            card_layout = QHBoxLayout()
            card_layout.setContentsMargins(12, 8, 12, 8)

            # left: ikonka + podstawowe info
            left = QVBoxLayout()
            kep_label = QLabel(f"KepID: {row['kepid']}")
            kep_label.setFont(QFont('', 11, QFont.Weight.Bold))
            left.addWidget(kep_label)
            left.addWidget(QLabel(f"Promień (R⊕): {row['koi_prad']}"))
            left.addWidget(QLabel(f"Okres (dni): {row['koi_period']}"))
            left.addWidget(QLabel(f"Głębokość: {row['koi_depth']}"))

            card_layout.addLayout(left)

            # middle: predykcja + habitability
            mid = QVBoxLayout()
            pred = QLabel(f"Predykcja: {row['prediction_label']}")
            pred.setFont(QFont('', 10, QFont.Weight.DemiBold))
            mid.addWidget(pred)
            hab = QLabel(f"Życie: {row['habitable']}")
            mid.addWidget(hab)
            card_layout.addLayout(mid)

            # right: akcje
            right = QVBoxLayout()
            describe_btn = QPushButton("Opisz")
            describe_btn.clicked.connect(lambda _, r=row: self.show_description(r))
            right.addWidget(describe_btn)

            view_btn = QPushButton("Szczegóły")
            view_btn.clicked.connect(lambda _, r=row: self.show_detail_dialog(r))
            right.addWidget(view_btn)

            card_layout.addLayout(right)
            card.setLayout(card_layout)
            self.scroll_layout.addWidget(card)

    def show_description(self, row):
        try:
            description = describe_exoplanet(row)
        except Exception:
            description = "Brak opisu — nie udało się wygenerować opisu." 
        QMessageBox.information(self, f"Opis planety {row['kepid']}", description)

    def show_detail_dialog(self, row):
        # prosty dialog z danymi — można rozbudować
        text = (
            f"KepID: {row['kepid']}\n"
            f"Promień: {row['koi_prad']} R⊕\n"
            f"Okres: {row['koi_period']} dni\n"
            f"Czas trwania: {row['koi_duration']}\n"
            f"Głębokość: {row['koi_depth']}\n"
            f"Predykcja: {row['prediction_label']}\n"
            f"Habitability: {row['habitable']}"
        )
        QMessageBox.information(self, f"Szczegóły {row['kepid']}", text)

    def show_stats(self, df):
        total = len(df)
        exo = len(df[df['prediction'] == 1]) if 'prediction' in df.columns else 0
        false = total - exo
        avg_radius = round(df['koi_prad'].mean(), 2) if not df['koi_prad'].isnull().all() else 0
        avg_depth = round(df['koi_depth'].mean(), 2) if not df['koi_depth'].isnull().all() else 0
        avg_period = round(df['koi_period'].mean(), 2) if not df['koi_period'].isnull().all() else 0
        self.stats_label.setText(
            f"📊 {total} rekordów — {exo} egzoplanet | Śr. R: {avg_radius} | Śr. głęb.: {avg_depth} | Śr. okres: {avg_period}"
        )

    def show_plot(self):
        if self.df is None:
            return
        if not self.turbo_checkbox.isChecked():
            fig = px.histogram(self.df, x="prediction_label", color="prediction_label", title="Rozkład predykcji")
            fig.update_layout(template="plotly_dark")
            fig.show()

    def save_results(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Zapisz jako", "", "CSV Files (*.csv)")
        if file_path and self.df is not None:
            self.df.to_csv(file_path, index=False)
            QMessageBox.information(self, "Zapisano", "Wyniki zostały zapisane!")

    # ------------------- helpers -------------------
    def on_page_size_change(self, txt):
        try:
            self.page_size = int(txt)
            self.update_page()
        except Exception:
            pass

    def _start_loading(self):
        self.progress.setValue(5)
        self._progress_target = 90
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
    window.show()
    sys.exit(app.exec_())
