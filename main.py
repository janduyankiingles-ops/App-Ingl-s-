import sys
from PySide6.QtWidgets import QApplication
from english_player.v043_window import MainWindowV043


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("English Video Player")
    window = MainWindowV043()
    window.resize(1250, 800)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
