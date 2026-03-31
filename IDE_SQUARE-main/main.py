import sys
from PyQt5 import QtWidgets
from controllers.main_window_controller import MainWindowController

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    mainWindow = MainWindowController()
    mainWindow.show()
    sys.exit(app.exec_())