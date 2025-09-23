from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QMessageBox
from PyQt5.QtCore import Qt
from sky_map import SkyMap
from ai_description import describe_exoplanet
from PyQt5.QtWidgets import QApplication

class PlanetDialog(QDialog):
    def __init__(self, row, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Opis planety {row['kepid']}")
        self.setMinimumWidth(500)

        layout = QVBoxLayout()

        self.label = QLabel("Kliknij „Opisz”, aby wygenerować opis planety.")
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.label)

        opis_btn = QPushButton("Opisz")
        opis_btn.clicked.connect(lambda: self.generate_description(row))
        layout.addWidget(opis_btn)


        # Przycisk do mapy nieba
        map_btn = QPushButton("Pokaż na mapie")
        map_btn.clicked.connect(lambda: self.show_sky_map(row))
        layout.addWidget(map_btn)

        # Przycisk zamykający
        close_btn = QPushButton("Zamknij")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        self.setLayout(layout)

    def show_sky_map(self, row):
        ra = row.get("ra")
        dec = row.get("dec")
        if ra is not None and dec is not None:
            self.map_window = SkyMap(ra, dec)
            self.map_window.show()
        else:
            QMessageBox.information(self, "Brak danych", "Brak współrzędnych RA/DEC dla tej planety.")

    def generate_description(self, row):
        self.label.setText("⏳ Generowanie opisu...")
        QApplication.processEvents()  # odświeżenie GUI
        description = describe_exoplanet(row)
        self.label.setText(description)
