import sys
import pandas as pd
import pickle
import requests
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QLabel, QScrollArea, QFrame, QMessageBox, QHBoxLayout,
    QCheckBox, QSlider, QGroupBox, QFormLayout
)
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import Qt
from ai_description import describe_exoplanet
import plotly.express as px

class ExoplanetApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Exoplanet Deluxe Edition")
        self.setGeometry(100, 100, 1100, 800)
        self.setStyleSheet("background-color: #1e1e1e; color: #ddd; font-family: Arial;")

        self.df = None
        self.filtered_df = None
        self.model = pickle.load(open("exoplanet_model.pkl", "rb"))
        self.current_page = 0
        self.page_size = 20

        self.layout = QVBoxLayout()

        logo = QLabel()
        pixmap = QPixmap("assets/kepler_logo.png").scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo.setPixmap(pixmap)
        logo.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(logo)

        self.label = QLabel("Wybierz plik CSV z danymi egzoplanet:")
        self.label.setFont(QFont("Arial", 12))
        self.label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.label)

        button_layout = QHBoxLayout()
        self.load_button = QPushButton("Wczytaj CSV")
        self.load_button.clicked.connect(self.load_csv)
        button_layout.addWidget(self.load_button)

        self.nasa_button = QPushButton("Pobierz dane z NASA")
        self.nasa_button.clicked.connect(self.fetch_nasa_data)
        button_layout.addWidget(self.nasa_button)

        self.demo_button = QPushButton("Dane demo")
        self.demo_button.clicked.connect(self.load_demo_data)
        button_layout.addWidget(self.demo_button)

        self.plot_button = QPushButton("Wykres")
        self.plot_button.clicked.connect(self.show_plot)
        self.plot_button.setEnabled(False)
        button_layout.addWidget(self.plot_button)

        self.save_button = QPushButton("Zapisz")
        self.save_button.clicked.connect(self.save_results)
        self.save_button.setEnabled(False)
        button_layout.addWidget(self.save_button)

        self.turbo_checkbox = QCheckBox("Tryb Turbo")
        self.turbo_checkbox.setChecked(False)
        button_layout.addWidget(self.turbo_checkbox)

        self.layout.addLayout(button_layout)

        self.filter_group = QGroupBox("Filtry")
        filter_layout = QFormLayout()

        self.slider_radius = QSlider(Qt.Horizontal)
        self.slider_radius.setRange(0, 20)
        self.slider_radius.setValue(0)
        filter_layout.addRow("Min promień:", self.slider_radius)

        self.slider_depth = QSlider(Qt.Horizontal)
        self.slider_depth.setRange(0, 10000)
        self.slider_depth.setValue(0)
        filter_layout.addRow("Min głębokość:", self.slider_depth)

        self.slider_period = QSlider(Qt.Horizontal)
        self.slider_period.setRange(0, 1000)
        self.slider_period.setValue(0)
        filter_layout.addRow("Min okres:", self.slider_period)

        self.habitable_checkbox = QCheckBox("Tylko możliwe do życia")
        filter_layout.addRow(self.habitable_checkbox)

        self.exoplanet_checkbox = QCheckBox("Tylko egzoplanety")
        filter_layout.addRow(self.exoplanet_checkbox)


        self.refresh_button = QPushButton("Odśwież filtry")
        self.refresh_button.clicked.connect(self.apply_filters)
        filter_layout.addRow(self.refresh_button)

        self.filter_group.setLayout(filter_layout)
        self.layout.addWidget(self.filter_group)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout()
        self.scroll_content.setLayout(self.scroll_layout)
        self.scroll.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll)

        nav_layout = QHBoxLayout()
        self.prev_button = QPushButton("Poprzednia")
        self.prev_button.clicked.connect(self.prev_page)
        nav_layout.addWidget(self.prev_button)

        self.page_label = QLabel("Strona 1")
        nav_layout.addWidget(self.page_label)

        self.next_button = QPushButton("Następna")
        self.next_button.clicked.connect(self.next_page)
        nav_layout.addWidget(self.next_button)

        self.layout.addLayout(nav_layout)

        self.stats_label = QLabel("")
        self.stats_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.stats_label)

        self.setLayout(self.layout)


    def load_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Wybierz plik CSV", "", "CSV Files (*.csv)")
        if file_path:
            self.process_file(file_path)

    def fetch_nasa_data(self):
        try:
            url = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=select+*+from+cumulative&format=csv"
            response = requests.get(url)
            file_path = "nasa_exoplanets.csv"
            with open(file_path, "wb") as f:
                f.write(response.content)
            QMessageBox.information(self, "NASA", "Dane z NASA zostały pobrane!")
            self.process_file(file_path)
        except Exception as e:
            QMessageBox.critical(self, "Błąd NASA", str(e))

    def load_demo_data(self):
        self.process_file("data/demo_exoplanets.csv")

    def process_file(self, file_path):
        try:
            df = pd.read_csv(file_path, sep=",", skiprows=0, on_bad_lines="skip", engine="python")
            df.columns = df.columns.str.strip().str.lower()
            required = ['koi_period', 'koi_duration', 'koi_depth', 'koi_prad', 'kepid']
            if not all(col in df.columns for col in required):
                QMessageBox.critical(self, "Błąd", f"Brakuje kolumn: {required}")
                return
            df = df[required].dropna()
            features = ['koi_period', 'koi_duration', 'koi_depth', 'koi_prad']
            df['prediction'] = self.model.predict(df[features])
            df['prediction_label'] = df['prediction'].apply(lambda x: "EGZOPLANETA" if x == 1 else "FAŁSZYWY POZYTYW")

#sprawdza czy jest życie na egzoplanecie
            df['habitable'] = df.apply(self.check_habitability, axis=1)

            self.df = df
            self.apply_filters()
            self.plot_button.setEnabled(True)
            self.save_button.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Błąd", str(e))
    def check_habitability(self, row):
  
        if (
        0.5 <= row['koi_prad'] <= 2.5 and
        50 <= row['koi_period'] <= 500 and
        row['koi_depth'] < 5000
        ):
            return "Możliwe warunki do życia"
        else:
            return "Warunki nie sprzyjają życiu"

    def apply_filters(self):
        if self.df is None:
            return
        df = self.df.copy()
        df = df[df['koi_prad'] >= self.slider_radius.value()]
        df = df[df['koi_depth'] >= self.slider_depth.value()]
        df = df[df['koi_period'] >= self.slider_period.value()]
        if self.habitable_checkbox.isChecked():
            df = df[df['habitable'] == "Możliwe warunki do życia"]
        if self.exoplanet_checkbox.isChecked():
            df = df[df['prediction'] == 1]
        self.filtered_df = df.reset_index(drop=True)
        self.current_page = 0
        self.update_page()


    def update_page(self):
        start = self.current_page * self.page_size
        end = start + self.page_size
        page_df = self.filtered_df.iloc[start:end]
        self.display_cards(page_df)
        self.show_stats(self.filtered_df)
        total_pages = max(1, (len(self.filtered_df) + self.page_size - 1) // self.page_size)
        self.page_label.setText(f"Strona {self.current_page + 1} z {total_pages}")
        self.prev_button.setEnabled(self.current_page > 0)
        self.next_button.setEnabled(end < len(self.filtered_df))

    def next_page(self):
        if (self.current_page + 1) * self.page_size < len(self.filtered_df):
            self.current_page += 1
            self.update_page()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_page()

    def display_cards(self, df):
        for i in reversed(range(self.scroll_layout.count())):
            self.scroll_layout.itemAt(i).widget().deleteLater()
        for _, row in df.iterrows():
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background-color: #2e2e2e;
                    border-radius: 10px;
                    padding: 10px;
                    margin: 5px;
                    border: 1px solid #444;
                }
                QLabel {
                    color: #ddd;
                    font-size: 12pt;
                }
            """)
            layout = QVBoxLayout()
            layout.addWidget(QLabel(f"ID: {row['kepid']}"))
            layout.addWidget(QLabel(f"Okres: {row['koi_period']}"))
            layout.addWidget(QLabel(f"Czas trwania: {row['koi_duration']}"))
            layout.addWidget(QLabel(f"Głębokość: {row['koi_depth']}"))
            layout.addWidget(QLabel(f"Promień: {row['koi_prad']}"))
            layout.addWidget(QLabel(f"Predykcja: {row['prediction_label']}"))
            layout.addWidget(QLabel(f"Życie: {row['habitable']}"))
            describe_button = QPushButton("Opisz")
            describe_button.clicked.connect(lambda _, r=row: self.show_description(r))
            layout.addWidget(describe_button)

            card.setLayout(layout)
            self.scroll_layout.addWidget(card)

    def show_description(self, row):
        description = describe_exoplanet(row)
        QMessageBox.information(self, f"Opis planety {row['kepid']}", description)

    def show_stats(self, df):
        total = len(df)
        exo = len(df[df['prediction'] == 1])
        false = total - exo
        avg_radius = round(df['koi_prad'].mean(), 2)
        avg_depth = round(df['koi_depth'].mean(), 2)
        avg_period = round(df['koi_period'].mean(), 2)
        self.stats_label.setText(
            f"📊 Statystyki: {total} rekordów | {exo} egzoplanet | {false} fałszywych | "
            f"Śr. promień: {avg_radius} | Śr. głębokość: {avg_depth} | Śr. okres: {avg_period}"
        )

    def show_plot(self):
        if self.df is not None and not self.turbo_checkbox.isChecked():
            fig = px.histogram(self.df, x="prediction_label", color="prediction_label",
                               title="Rozkład predykcji egzoplanet", text_auto=True)
            fig.update_layout(template="plotly_dark")
            fig.show()

    def save_results(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Zapisz jako", "", "CSV Files (*.csv)")
        if file_path and self.df is not None:
            self.df.to_csv(file_path, index=False)
            QMessageBox.information(self, "Zapisano", "Wyniki zostały zapisane!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ExoplanetApp()
    window.show()
    sys.exit(app.exec_())
