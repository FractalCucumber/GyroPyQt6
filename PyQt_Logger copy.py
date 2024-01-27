import logging
import sys
from PyQt5 import QtGui
# from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QTextEdit


# description:
__Author__ = """By: _
Email: _"""
__Copyright__ = 'Copyright (c) 2023 _'
__Version__ = 1.0


class QTextEditLogger():
    def __init__(self, parent, file_log=True, debug_enable=True):
        super().__init__()

        # def create_logger(path, widget: QTextEdit):
        # logging.disable(logging.INFO) # disable logging for certain level

        self.logger = logging.getLogger('main')
        if debug_enable:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)

        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            # logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
            self.logger.error('Uncaught exception',
                         exc_info=(exc_type, exc_value, exc_traceback))
        sys.excepthook = handle_exception  # главное
        # sys.unraisablehook

        if file_log:
            file_formatter = logging.Formatter(
                ('#%(levelname)-s,\t%(pathname)s:%(lineno)d,\t%(asctime)s, %(message)s'))
            file_handler = logging.FileHandler('PyQt_VibroGyroTest.log',
                                               mode='w', encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
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
        # console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # log_window_formatter = logging.Formatter(
            # ('<br/>>>> <font color="green">%(asctime)s</font> %(message)s'), datefmt='%H:%M:%S')
        # fmt = '<br/>>>> <font color="green">%(asctime)s</font> %(message)s'
            # ('>>> %(asctime)s %(message)s\n'), datefmt='%H:%M:%S')
        self.log_window_handler = logging.Handler()
        self.widget = QTextEdit(parent, readOnly=True, objectName="logger")
        self.log_window_handler.emit = self.record
        self.log_window_handler.setLevel(logging.INFO)
        self.log_window_handler.setFormatter(CustomFormatter())
        # self.log_window_handler.setFormatter(log_window_formatter)
        self.logger.addHandler(self.log_window_handler)
        # self.widget.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.NoTextInteraction)
        # log_window_handler.emit = lambda record: self.widget.insertPlainText(
            # log_window_handler.format(record)
        # )
    
    def record(self, record):
        # print(record.levelno)
        cur = self.widget.textCursor()
        cur.movePosition(QtGui.QTextCursor.End)
        # так пользователь сможет выделять текст,
        # но новые записи не будут перекрывать старые
        self.widget.setTextCursor(cur)
        self.widget.insertHtml(self.log_window_handler.format(record))
        # self.widget.insertPlainText(self.log_window_handler.format(record))
        self.widget.verticalScrollBar().setValue(
            self.widget.verticalScrollBar().maximum())
        # scrollbar = self.widget.verticalScrollBar()
        # scrollbar.setValue(scrollbar.maximum())


class CustomFormatter():
    """Logging colored formatter"""
    # лучше не делать отдельным классом
    def __init__(self):
        # super().__init__()
        self.FORMATS = {
            logging.DEBUG: '<br/>>>> <font color="white">%(asctime)s</font> %(message)s',
            logging.INFO: '<br/>>>> <font color="white">%(asctime)s</font> %(message)s',
            logging.WARNING: '<br/>>>> <font color="green">%(asctime)s</font> %(message)s',
            logging.ERROR: '<br/>>>> <font color="green">%(asctime)s</font><font color="red"> %(message)s</font>',
            logging.CRITICAL: '<br/>>>> <font color="green">%(asctime)s</font><font color="red"> %(message)s</font>'
        }
        # self.datefmt = '%H:%M:%S'

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        # self.fmt = log_fmt
        formatter = logging.Formatter(log_fmt, datefmt = '%H:%M:%S')
        # formatter = logging.Formatter(log_fmt, datefmt = '%H:%M:%S')
        return formatter.format(record)