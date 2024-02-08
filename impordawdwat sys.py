import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QApplication, QGridLayout, QToolTip


class MyWidget(QWidget):

    def __init__(self):
        super().__init__()

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            'QWidget { background: #007AA5; border-radius: 3px;}')
        self.setMouseTracking(True)

    def mouseMoveEvent(self, e):
        # print(type(e))
        # print(type(e.pos()))
        self.x = e.pos().x()
        self.y = e.pos().y()

        p = self.mapToGlobal(e.pos())

        QToolTip.showText(p, f'{self.x}:{self.y}')


class Example(QWidget):

    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):

        grid = QGridLayout()

        r = c = 0

        for _ in range(9):
            grid.addWidget(MyWidget(), r, c)

            c += 1

            if c % 3 == 0:
                c = 0
                r += 1

        self.setLayout(grid)

        self.setGeometry(400, 300, 500, 350)
        self.setWindowTitle('Mouse positions')
        self.show()


def main():

    app = QApplication(sys.argv)
    ex = Example()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()