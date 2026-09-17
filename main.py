import sys
from PySide6.QtWidgets import QApplication
from english_player.v055_window import MainWindowV055


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("English Video Player")
    window = MainWindowV055()
    window.resize(1320, 840)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
