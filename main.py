import sys
from PySide6.QtWidgets import QApplication
from english_player.v110_window import MainWindowV110


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("English Video Player")
    window = MainWindowV110()
    window.resize(1320, 840)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
