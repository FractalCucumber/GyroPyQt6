# cSpell:includeRegExp #.*
# cSpell:includeRegExp /(["]{3}|[']{3})[^\1]*?\1/g

import os
import json
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt_Functions import get_icon_by_name, get_res_path


# по идее не влияет на основную программу, так что проблем при открытии во время цикла быть не должно
class CustomDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(CustomDialog, self).__init__(parent)
        STYLE_SHEETS_FILENAME = 'res\StyleSheetsDialog.css'
        with open(get_res_path(STYLE_SHEETS_FILENAME), "r") as style_sheets:
            self.setStyleSheet(style_sheets.read())
        app_icon = QtGui.QIcon()
        for i in [16, 24, 32, 48]:
            app_icon.addFile(
                get_res_path(f'res\icon_{i}.png'), QtCore.QSize(i, i))
        self.setWindowIcon(app_icon)
        self.setMaximumSize(500, 150)
        self.setWindowTitle("Окно редактирования проектов")
        self.setWindowFlags(QtCore.Qt.WindowType.CustomizeWindowHint |
                            QtCore.Qt.WindowType.WindowCloseButtonHint)
        QBtn = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        self.button_box = QtWidgets.QDialogButtonBox(QBtn)
        self.button_box.button(
            QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout = QtWidgets.QGridLayout()
        message = QtWidgets.QLabel("Выберите путь к проекту и дайте название",
                                   wordWrap=True, maximumHeight=80)
        layout.addWidget(message, 0, 0, 1, 3)
        name_label = QtWidgets.QLabel("Имя:")
        layout.addWidget(name_label, 1, 0, 1, 1)
        self.project_name = QtWidgets.QLineEdit()
        self.project_name.textChanged.connect(self.check)
        layout.addWidget(self.project_name, 1, 1, 1, 2)
        path_label = QtWidgets.QLabel("Путь:")
        layout.addWidget(path_label, 2, 0, 1, 1)
        self.path_to_project = QtWidgets.QLineEdit()
        layout.addWidget(self.path_to_project, 2, 1, 1, 1)
        self.path_to_project.textChanged.connect(self.check)
        open_folder_btn = QtWidgets.QPushButton(
            icon=get_icon_by_name('open_folder'))
        layout.addWidget(open_folder_btn, 2, 2, 1, 1)
        open_folder_btn.clicked.connect(self.get_path)
        layout.addWidget(self.button_box, 3, 0, 1, 3)
        self.setLayout(layout)

    def check(self):
        if os.path.isdir(self.path_to_project.text()):
            # self.button_box.button(
                # QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
            self.path_to_project.setStyleSheet("color: white;")
        else:
            self.button_box.button(
                QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
            self.path_to_project.setStyleSheet("color: grey;")
        if os.path.isdir(self.path_to_project.text()) and len(self.project_name.text()):
            self.button_box.button(
                QtWidgets.QDialogButtonBox.Ok).setEnabled(True)

    def get_path(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Выбрать папку", os.path.dirname(self.path_to_project.text()))
            # self, "Выбрать папку", self.path.text())
        if folder:
            self.path_to_project.setText(folder)


class ProjectsComboBox(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super(ProjectsComboBox, self).__init__(parent)
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        # QToolButton  # есть wordWrap
        self.installEventFilter(self)
        self.dlg = CustomDialog()
        self.projects_dict = {}

    def delete_project_item(self):
        self.projects_dict.pop(self.currentText(), None)
        self.removeItem(self.currentIndex())
        
    def change_current_project_item(self):  # сделать этот пункт недоступным просто
        self.dlg.path_to_project.setText(
            self.projects_dict[self.currentText()])
        self.dlg.project_name.setText(self.currentText())
        if self.dlg.exec():  # сделать запуск с open(), потом принять сигнал завершения вместе с флагом
            self.setCurrentText('')
            self.projects_dict.pop(self.currentText(), None)
            self.apply_changes()

    def add_project_item(self):
        if self.dlg.exec():
            self.projects_dict[self.dlg.project_name.text()] = self.dlg.path_to_project.text()
            self.insertItem(0, self.dlg.project_name.text())
            self.setCurrentIndex(0)
            self.apply_changes()

    def apply_changes(self):
        self.projects_dict[self.dlg.project_name.text()] = self.dlg.path_to_project.text()
        self.setCurrentText(self.dlg.project_name.text())
        self.setItemText(self.currentIndex(), self.dlg.project_name.text())
        self.setItemData(self.currentIndex(),
                         self.projects_dict[self.dlg.project_name.text()],
                         QtCore.Qt.ItemDataRole.ToolTipRole)
        
    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.ContextMenu:
            menu = QtWidgets.QMenu(self)
            change_action = QtWidgets.QAction('Изменить проект', self)
            change_action.triggered.connect(self.change_current_project_item)
            menu.addAction(change_action)
            add_action = QtWidgets.QAction('Добавить проект', self)
            add_action.triggered.connect(self.add_project_item)
            menu.addAction(add_action)
            delete_action = QtWidgets.QAction('Удалить текущий проект', self)
            delete_action.triggered.connect(self.delete_project_item)
            if not self.count():
                change_action.setDisabled(True)
                delete_action.setDisabled(True)
            menu.addAction(delete_action)
            menu.exec(event.globalPos())
            return True
        return False

    def save_json(self, PROJECT_FILE_NAME):
        with open(PROJECT_FILE_NAME, 'w', encoding='utf-8') as f:
            json.dump(self.projects_dict,
                      f, ensure_ascii=False, indent=4)
        #     d = {"dict": self.custom_tab_plot_widget.projects_combo_box.projects_dict, "ddd22": False, "2ddd22": "f"}
        #     json.dump(
        #         d,
        #         f, ensure_ascii=False, indent=4)

    def load_json(self, PROJECT_FILE_NAME):
        with open(PROJECT_FILE_NAME, 'r', encoding='utf-8') as f:
            self.projects_dict = json.load(f)
        if self.projects_dict:  # keys сортируются автоматически
            self.addItems(self.projects_dict.keys())
            for i in range(self.count()):
                self.setItemData(
                    i, self.projects_dict.get(self.itemText(i)),
                    QtCore.Qt.ItemDataRole.ToolTipRole)    
# ----------------------------------------------------------------------------------------------
#
# ----------------------------------------------------------------------------------------------
#
# ----------------------------------------------------------------------------------------------


if __name__ == "__main__":
    import sys
    import PyQt_ApplicationClass
    import PyQt_ApplicationClassTest
    from PyQt5 import QtWidgets, QtGui
    app = QtWidgets.QApplication(sys.argv)
    splash = QtWidgets.QSplashScreen(QtGui.QPixmap(get_res_path('res/G.png')))
    splash.show()
    app.processEvents()

    test = True
    test = False
    if test:
        window = PyQt_ApplicationClassTest.AppWindowTest()
        pass
    else:
        window = PyQt_ApplicationClass.AppWindow()
    splash.finish(window)
    sys.exit(app.exec())