import sys
from PySide6.QtWidgets import QApplication
from english_player.v134_window import MainWindowV134


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("English Video Player")
    window = MainWindowV134()
    window.resize(1540, 900)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
