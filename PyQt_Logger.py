import logging
from PyQt5.QtWidgets import QTextEdit


class QTextEditLogger():
    def __init__(self, parent, file_log=True):
        super().__init__()

        # def create_logger(path, widget: QTextEdit):
        # logging.disable(logging.INFO) # disable logging for certain level

        log = logging.getLogger('main')
        log.setLevel(logging.INFO)

        if file_log:
            # logging.basicConfig(  # не выводит сообщния на русском
            #     filename='GyroTestPyQt.log',
            #     filemode='w',
            #     format=('#%(levelname)-s,\t%(pathname)s:%(lineno)d,\t%(asctime)s, %(message)s'),
            #     # format=('#%(levelname)-s,\t%(pathname)s,\tline %(lineno)d,\t[%(asctime)s]: %(message)s'),
            #     level=logging.INFO,
            # )  #  encoding="utf-8" work since python 3.9
            # выводит сообщния на русском
            file_formatter = logging.Formatter(
                ('#%(levelname)-s,\t%(pathname)s:%(lineno)d,\t%(asctime)s, %(message)s'))
            file_handler = logging.FileHandler('PyQt_VibroGyroTest.log', mode='w', encoding="utf-8")
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(file_formatter)
            log.addHandler(file_handler)
        # console_formatter = logging.Formatter(('#%(levelname)-s, %(pathname)s, '
                                            # 'line %(lineno)d: %(message)s'))
        # console_handler = logging.StreamHandler()
        # console_handler.setFormatter(console_formatter)
        # console_handler.setLevel(logging.DEBUG)
        # console_handler.setFormatter(console_formatter)

        log_window_formatter = logging.Formatter(
            ('>>> %(asctime)s %(message)s\n'), datefmt='%H:%M:%S'
        )
        log_window_handler = logging.Handler()
        self.widget = QTextEdit(parent, readOnly=True, objectName="logger")
        log_window_handler.emit = lambda record: self.widget.insertPlainText(
            log_window_handler.format(record)
        )
        log_window_handler.setLevel(logging.WARNING)

        log_window_handler.setFormatter(log_window_formatter)

        # log.addHandler(console_handler)
        log.addHandler(log_window_handler)