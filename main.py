import sys
from PySide6.QtWidgets import QApplication
from english_player.v200_window import MainWindowV200


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("English Video Player")
    window = MainWindowV200()
    window.resize(1500, 900)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
