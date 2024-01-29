from PyQt5 import QtWidgets, QtCore, QtGui


class CustomComboBox(QtWidgets.QComboBox):
    def __init__(self,
                 settings: QtCore.QSettings,  # передавать сразу объект QtCore.QSettings, чтобы не создавать их
                 settings_name: str = 'Deafault',
                 default_items_list = [''],
                 editable_flag=True,
                 uint_validator_enable=True,
                 parent=None):
        super(CustomComboBox, self).__init__(parent)
        self.settings_name = settings_name
        self.setEditable(True)
        self.lineEdit().setReadOnly(not editable_flag)
        self.lineEdit().setAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter)
        if uint_validator_enable:
            self.int_validator = QtGui.QIntValidator(bottom=0)
            self.setValidator(self.int_validator)

        self.currentTextChanged.connect(
            lambda value: self.setItemText(self.currentIndex(), value))

        # self.settings = QtCore.QSettings(settings_name)
        self.settings = settings
        if self.settings.contains("item_" + self.settings_name):
            for i in range(self.count()):
                self.removeItem(i)
            self.addItems(
                self.settings.value("item_" + self.settings_name))
        else:
            if not len(default_items_list[0]):
                return
            self.addItems(default_items_list)
        if self.settings.contains("curr_index_" + self.settings_name):
            if self.count() >= int(self.settings.value("curr_index_" + self.settings_name)):
                self.setCurrentIndex(
                    int(self.settings.value("curr_index_" + self.settings_name)))

        # self.save_value = lambda: self.settings.setValue(
        #     "items",
        #     [self.itemText(i) for i in range(self.count())])
        # self.save_index = lambda: self.settings.setValue(
        #     "curr_index", self.currentIndex())
        # self.save_name = lambda: self.settings.setValue(
        #     "COM_current_name", self.currentText())
    def get_ind(self):
        if self.settings.contains("name" + self.settings_name):
            for i in range(self.count()):
                if self.itemText(i) == self.settings.value("name" + self.settings_name):
                    self.setCurrentIndex(i)
                    break

    def save_all(self):
        self.save_value()
        self.save_index()

    def save_value(self):
        if self.count():
            self.settings.setValue(
                "item_" + self.settings_name,
                [self.itemText(i) for i in range(self.count())])

    def save_index(self):
        if self.count():
            self.settings.setValue(
                "curr_index_" + self.settings_name,
                self.currentIndex())

    def save_current_text(self):
        if self.count():
            self.settings.setValue(
                "name" + self.settings_name,
                self.currentText())