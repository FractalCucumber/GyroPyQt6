from PyQt5 import QtWidgets, QtCore
import os
from PyQt_Functions import get_icon_by_name, get_res_path


class CustomDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        STYLE_SHEETS_FILENAME = 'res\StyleSheets2.css'
        with open(get_res_path(STYLE_SHEETS_FILENAME), "r") as style_sheets:
            self.setStyleSheet(style_sheets.read())
        self.setMaximumSize(500, 175)
        self.setWindowTitle("Окно редактирования проектов")
        self.setWindowFlags(QtCore.Qt.WindowType.CustomizeWindowHint |
                            QtCore.Qt.WindowType.WindowCloseButtonHint)
        self.QBtn = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        self.button_box = QtWidgets.QDialogButtonBox(self.QBtn)
        self.button_box.button(
            QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.layout = QtWidgets.QGridLayout()
        message = QtWidgets.QLabel("Выберите путь к проекту и дайте название",
                                   wordWrap=True, maximumHeight=80)
        self.layout.addWidget(message, 0, 0, 1, 3)
        name_label = QtWidgets.QLabel("Имя:")
        self.layout.addWidget(name_label, 1, 0, 1, 1)
        self.name = QtWidgets.QLineEdit()
        self.name.textChanged.connect(self.check)
        self.layout.addWidget(self.name, 1, 1, 1, 2)
        path_label = QtWidgets.QLabel("Путь:")
        self.layout.addWidget(path_label, 2, 0, 1, 1)
        self.path = QtWidgets.QLineEdit()
        self.layout.addWidget(self.path, 2, 1, 1, 1)
        self.path.textChanged.connect(self.check)
        open_folder_btn = QtWidgets.QPushButton(icon=get_icon_by_name('open_folder'))
        self.layout.addWidget(open_folder_btn, 2, 2, 1, 1)
        open_folder_btn.clicked.connect(self.get_path)
        self.layout.addWidget(self.button_box, 3, 0, 1, 3)
        self.setLayout(self.layout)

    def check(self):
        if os.path.exists(self.path.text()) and len(self.name.text()):
            self.button_box.button(
                QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.button_box.button(
                QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

    # def closeEvent(self, a0):

    def get_path(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Выберите файл",
            ".", "Excel Files (*.xls *.xlsx)")
        if filename:
            self.path.setText(str(filename))


class ProjectsComboBox(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super(ProjectsComboBox, self).__init__(parent)
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        # QToolButton # есть wordWrap
        self.installEventFilter(self)
        self.dlg = CustomDialog()
        self.projects_dict = {}

    def delete_xlsx_item(self):
        self.projects_dict.pop(self.currentText(), None)
        self.removeItem(self.currentIndex())
        
    def change_current_xlsx_item(self):
        if not self.count():
            return
        self.dlg.path.setText(
            self.projects_dict[self.currentText()])
        self.dlg.name.setText(self.currentText())
        if self.dlg.exec():
            self.projects_dict.pop(self.currentText(), None)
            self.apply_changes()

    def add_xlsx_item(self):
        if self.dlg.exec():
            self.insertItem(0, self.dlg.name.text())
            self.setCurrentIndex(0)
            self.apply_changes()

    def apply_changes(self):
        self.projects_dict[self.dlg.name.text()] = self.dlg.path.text()
        self.setCurrentText(self.dlg.name.text())
        self.setItemText(self.currentIndex(), self.dlg.name.text())
        self.setItemData(self.currentIndex(),
                         self.projects_dict[self.dlg.name.text()],
                         QtCore.Qt.ItemDataRole.ToolTipRole)
        
    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.ContextMenu:
            menu = QtWidgets.QMenu(self)
            action = QtWidgets.QAction('Изменить проект', self)
            action.triggered.connect(self.change_current_xlsx_item)
            menu.addAction(action)
            action = QtWidgets.QAction('Добавить проект', self)
            action.triggered.connect(self.add_xlsx_item)
            menu.addAction(action)
            action = QtWidgets.QAction('Удалить текущий проект', self)
            action.triggered.connect(self.delete_xlsx_item)
            menu.addAction(action)
            menu.exec_(event.globalPos())
            return True
        return False
