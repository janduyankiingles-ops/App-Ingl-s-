import sys
from PySide6.QtWidgets import QApplication
from english_player.v071_window import MainWindowV071


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("English Video Player")
    window = MainWindowV071()
    window.resize(1320, 840)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
