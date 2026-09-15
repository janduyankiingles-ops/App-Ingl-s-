import sys
from PySide6.QtWidgets import QApplication
from english_player.v047_window import MainWindowV047


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("English Video Player")
    window = MainWindowV047()
    window.resize(1250, 800)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
