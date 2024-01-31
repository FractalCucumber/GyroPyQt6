import logging
from logging.handlers import RotatingFileHandler
import sys
from PyQt5.QtWidgets import QTextEdit
from PyQt5 import QtWidgets, QtGui, QtCore

# description:
# __Author__ = """By: _
# Email: _"""
# __Copyright__ = 'Copyright (c) 2023 _'
# __Version__ = 1.0


class QTextEditLogger(QTextEdit):
    # def __init__(self, parent, file_log=True, debug_enable=True):
    def __init__(self, parent=None, file_log=True):
        super(QTextEditLogger, self).__init__(
            parent,readOnly=True, objectName="logger")

        # def create_logger(path, widget: QTextEdit):
        # logging.disable(logging.INFO) # disable logging for certain level

        logger = logging.getLogger('main')
        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
            # logger.error(f"Uncaught exception {exc_type}, {exc_value}, {exc_traceback}")
        sys.excepthook = handle_exception
        # sys.unraisablehook

        if file_log:
            file_formatter = logging.Formatter(
                ('#%(levelname)-s,\t%(pathname)s:%(lineno)d,\t%(asctime)s, %(message)s'))
            file_handler = RotatingFileHandler(
                'logs\PyQt_VibroGyroTest.log', mode='w', encoding="utf-8", maxBytes=2_000_000, backupCount=10)
                # 'PyQt_VibroGyroTest.log', mode='w', encoding="utf-8", maxBytes=5120, backupCount=5)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
            logger.handlers[0].doRollover()
            # logging.basicConfig(  # не выводит сообщния на русском
            #     filename='GyroTestPyQt.log',
            #     filemode='w',
            #     format=('#%(levelname)-s,\t%(pathname)s:%(lineno)d,\t%(asctime)s, %(message)s'),
            #     # format=('#%(levelname)-s,\t%(pathname)s,\tline %(lineno)d,\t[%(asctime)s]: %(message)s'),
            #     level=logging.INFO,
            # )  #  encoding="utf-8" work since python 3.9

        # console_formatter = logging.Formatter(('#%(levelname)-s, %(pathname)s, '
        #                                     'line %(lineno)d: %(message)s'))
        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setLevel(logging.ERROR)
        logger.addHandler(console_handler)
        # console_handler.setFormatter(console_formatter)

        # log_window_formatter = logging.Formatter(
            # ('>>> %(asctime)s %(message)s\n'), datefmt='%H:%M:%S')
        self.log_window_handler = logging.Handler()
        # self.log_text_edit = QTextEdit(parent, readOnly=True, objectName="logger")
        # self.widget.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.NoTextInteraction)
        self.log_window_handler.emit = self.insert_text
        # log_window_handler.emit = lambda record: self.widget.insertPlainText(
            # log_window_handler.format(record)
        # )
        self.log_window_handler.setLevel(logging.INFO)
        self.log_window_handler.setFormatter(CustomFormatter())
        # self.log_window_handler.setFormatter(log_window_formatter)
        logger.addHandler(self.log_window_handler)
        self.setContextMenuPolicy(
            QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(
            self.__logsContextMenu)
        self.enable_debug_in_file = QtWidgets.QAction(
            "Debug in file", None, checkable=True)
        self.enable_debug_in_file.setChecked(True)
        self.enable_debug_in_file.triggered.connect(self.switch_log_mode)
        self.switch_log_mode()

    @QtCore.pyqtSlot()
    def insert_text(self, record):
        cur = self.textCursor()
        cur.movePosition(QtGui.QTextCursor.End)
        self.setTextCursor(cur)
        self.insertHtml(
            self.log_window_handler.format(record))
        # self.widget.insertPlainText(
            # self.log_window_handler.format(record))
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        # self.verticalScrollBar().setValue(
        #     self.verticalScrollBar().maximum())

    @QtCore.pyqtSlot()
    def __logsContextMenu(self):
        self._normalMenu = self.createStandardContextMenu()
        self._normalMenu.addSeparator()
        self._normalMenu.addAction(self.enable_debug_in_file)
        self._normalMenu.exec_(QtGui.QCursor.pos())

    def switch_log_mode(self):
        logger = logging.getLogger('main')
        if self.enable_debug_in_file.isChecked():
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
# -------------------------------------------------------------------------------------------------


class CustomFormatter():
    """Logging colored formatter"""
    # лучше не делать отдельным классом
    def __init__(self):
        self.FORMATS = {
            logging.DEBUG: '<font color="grey">>>></font> <font color="white">%(asctime)s</font> %(message)s<br />',
            logging.INFO: '<font color="grey">>>></font> <font color="green">%(asctime)s</font> %(message)s<br />',
            logging.WARNING: '<font color="grey">>>></font> <font color="orange">%(asctime)s</font> %(message)s<br />',
            logging.ERROR: '<font color="grey">>>></font> <font color="red">%(asctime)s</font> <font color="orange">%(message)s</font><br />',
            logging.CRITICAL: '<font color="grey">>>></font> <font color="red">%(asctime)s</font> <font color="orange">%(message)s</font><br />',
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt = '%H:%M:%S')
        return formatter.format(record)

# -------------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------------


if __name__ == "__main__":
    import PyQt_ApplicationClass
    from PyQt5 import QtWidgets
    app = QtWidgets.QApplication(sys.argv)
    window = PyQt_ApplicationClass.AppWindow()
    sys.exit(app.exec())