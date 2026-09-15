import sys
from PySide6.QtWidgets import QApplication
from english_player.v040_window import MainWindowV04


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("English Video Player")
    window = MainWindowV04()
    window.resize(1250, 800)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
