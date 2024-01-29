import re
from PyQt5 import QtWidgets, QtCore


class CustomTableWidget(QtWidgets.QTableWidget):
    def __init__(self, parent=None):
        super(CustomTableWidget, self).__init__(parent)
        self.setColumnCount(3)
        self.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        # self.table_widget.setRowHeight(0, 0) 
        self.setHorizontalHeaderLabels(
            ["F, Hz", "A, \u00b0/s", "T, s"])
        self.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.verticalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.total_time = 0

    def set_table(self, file):
        self.setRowCount(0)
        self.total_time = 0
        for line in file:
            f_a_t = list(filter(None, re.split("F|A|T|\n", line)))
            self.add_and_fill_row(f_a_t)

    def add_and_fill_row(self, f_a_t: list):
        if (len(f_a_t) == 3 and all([item.isdecimal()
                                     for item in f_a_t])):
            self.setRowCount(self.rowCount() + 1)
            for j in range(3):
                item = QtWidgets.QTableWidgetItem(f_a_t[j])
                item.setTextAlignment(
                    QtCore.Qt.AlignmentFlag.AlignCenter)
                self.setItem(self.rowCount() - 1, j, item)
            self.total_time += int(f_a_t[-1])

    # get_current_F = lambda self: int(self.item(self.currentRow(), 0).data(QtCore.Qt.ItemDataRole.EditRole))
    def get_current_F(self):
        return int(self.item(
            self.currentRow(), 0).data(
                QtCore.Qt.ItemDataRole.EditRole))

    def get_current_A(self):
        return int(self.item(
            self.currentRow(), 1).data(
                QtCore.Qt.ItemDataRole.EditRole))

    def get_current_T(self):
        return int(self.item(
            self.currentRow(), 2).data(
                QtCore.Qt.ItemDataRole.EditRole)) * 1000