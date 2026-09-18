import sys
from PySide6.QtWidgets import QApplication
from english_player.v139_window import MainWindowV139


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("English Video Player")
    window = MainWindowV139()
    window.resize(1500, 900)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
