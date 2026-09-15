import sys
from PySide6.QtWidgets import QApplication
from english_player.v046_window import MainWindowV046


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("English Video Player")
    window = MainWindowV046()
    window.resize(1250, 800)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
