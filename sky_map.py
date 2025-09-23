
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QShortcut

class SkyMap(QWidget):
    def __init__(self, ra=None, dec=None, provider="aladin", fov_deg=0.5):
        super().__init__()
        self.setWindowTitle("🪐 Mapa nieba – lokalizacja egzoplanety")
        self.setGeometry(200, 200, 1000, 700)

        root = QVBoxLayout()

        # --- Toolbar ---
        toolbar = QHBoxLayout()
        self.toggle_btn = QPushButton("Pełny ekran (F11)")
        self.close_btn = QPushButton("Zamknij (Esc)")
        self.toggle_btn.clicked.connect(self.toggle_fullscreen)
        self.close_btn.clicked.connect(self.close)
        toolbar.addWidget(self.toggle_btn)
        toolbar.addStretch(1)
        toolbar.addWidget(self.close_btn)
        root.addLayout(toolbar)

        # --- Web view ---
        self.browser = QWebEngineView()

        # Normalizacja współrzędnych
        if ra is not None and dec is not None:
            try:
                ra = float(ra)
                dec = float(dec)
            except Exception:
                ra, dec = None, None

        # Wybór providera
        if provider == "wwt":
            url = "https://worldwidetelescope.org/webclient/"
            if ra is not None and dec is not None:
                url += f"?ra={ra}&dec={dec}&lookat=Sky"
        else:
            url = "https://aladin.u-strasbg.fr/AladinLite/"
            if ra is not None and dec is not None:
                url += f"?target={ra}%20{dec}&fov={float(fov_deg)}&survey=P%2FDSS2%2Fcolor"
            else:
                url += "?fov=60&survey=P%2FDSS2%2Fcolor"

        self.browser.load(QUrl(url))
        root.addWidget(self.browser)
        self.setLayout(root)

        # --- Shortcuts ---
        self._esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self._esc.activated.connect(self.close)
        self._f11 = QShortcut(QKeySequence(Qt.Key_F11), self)
        self._f11.activated.connect(self.toggle_fullscreen)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.toggle_btn.setText("Pełny ekran (F11)")
        else:
            self.showFullScreen()
            self.toggle_btn.setText("Okno (F11)")
