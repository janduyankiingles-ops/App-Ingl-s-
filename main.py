import sys
from PySide6.QtWidgets import QApplication
from english_player.v090_window import MainWindowV090


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("English Video Player")
    window = MainWindowV090()
    window.resize(1320, 840)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
