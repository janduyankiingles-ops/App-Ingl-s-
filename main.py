import sys
from PySide6.QtWidgets import QApplication
from english_player.v133_window import MainWindowV133


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("English Video Player")
    window = MainWindowV133()
    window.resize(1460, 900)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
