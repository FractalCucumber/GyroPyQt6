import logging
import sys
from PyQt5.QtWidgets import QTextEdit


class QTextEditLogger():
    def __init__(self, parent, file_log=True, debug_enable=True):
        super().__init__()

        # def create_logger(path, widget: QTextEdit):
        # logging.disable(logging.INFO) # disable logging for certain level

        logger = logging.getLogger('main')
        if debug_enable:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
        sys.excepthook = handle_exception  # главное

        if file_log:
            file_formatter = logging.Formatter(
                ('#%(levelname)-s,\t%(pathname)s:%(lineno)d,\t%(asctime)s, %(message)s'))
            file_handler = logging.FileHandler('PyQt_VibroGyroTest.log',
                                               mode='w', encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
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
        logger.addHandler(console_handler)

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
        logger.addHandler(log_window_handler)