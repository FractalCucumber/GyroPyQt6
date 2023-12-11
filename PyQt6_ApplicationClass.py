import logging
import sys
# from PyQt6.QtWidgets import QFileDialog
# from PyQt6.QtCore import pyqtSignal, QThread, QIODevice
import os
import re
# from pyqtgraph.Qt import QtCore, QtGui
# from datetime import datetime
# from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo
import pyqtgraph.exporters
import pyqtgraph as pg
import numpy as np
import PyQt6_Logger
import PyQt6_Thread
import PyQt6_TabWidget
from time import time
# pyinstaller PyQt6_Application.spec
#  pyinstaller --onefile --noconsole PyQt6_Application.py
# --add-data="Vibro_1_resources/icon_48.png:." PyQt6_Application.py
# pyinstaller --add-data "StyleSheets.css;." --add-data "icon_16.png;." --add-data "icon_24.png;." --add-data "icon_32.png;." --add-data "icon_48.png;." --onefile --windowed PyQt6_Application.py --exclude-module matplotlib --exclude-module hook --exclude-module setuptools --exclude-module DateTime --exclude-module pandas --exclude-module PyQt6.QtOpenGL --exclude-module PyQt6.QtOpenGLWidgets --exclude-module hooks --exclude-module hook --exclude-module pywintypes --exclude-module flask --exclude-module opengl32sw.dll
# pyinstaller --add-data "StyleSheets.css;." --add-data "icon_16.png;." --add-data "icon_24.png;." --add-data "icon_32.png;." --add-data "icon_48.png;." --windowed PyQt6_Application.py
# pyinstaller --add-data "StyleSheets.css;." --onefile --windowed PyQt6_Application.py
# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

class CustomComboBox(QtWidgets.QComboBox):
    def __init__(self,
                 settings_name: str,  # передавать сразу объект QtCore.QSettings, чтобы не создавать их
                 default_items_list: list = [],
                 editable_flag=True, 
                 uint_validator_enable=True,
                 parent=None):
        super(CustomComboBox, self).__init__(parent)
        self.setEditable(True)
        self.lineEdit().setReadOnly(not editable_flag)
        self.lineEdit().setAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter)
        if uint_validator_enable:
            self.int_validator = QtGui.QIntValidator(bottom=0)
            self.setValidator(self.int_validator)

        self.currentTextChanged.connect(
            lambda value: self.setItemText(self.currentIndex(), value))

        self.settings = QtCore.QSettings(settings_name)
        # self.settings = settings_name
        if self.settings.contains("items"):
            self.addItems(
                self.settings.value("items"))
        else:
            if len(default_items_list):
                return
            self.addItems(default_items_list)
        if self.settings.contains("curr_index"):
            self.setCurrentIndex(
                self.settings.value("curr_index"))
        if self.settings.contains("name"):
            for i in range(self.count()):
                if self.itemText(i) == self.settings.value("name"):
                    self.setCurrentIndex(i)
                    break

        # self.save_value = lambda: self.settings.setValue(
        #     "items",
        #     [self.itemText(i) for i in range(self.count())])

        # self.save_index = lambda: self.settings.setValue(
        #     "curr_index", self.currentIndex())

        # self.save_name = lambda: self.settings.setValue(
        #     "COM_current_name", self.currentText())
    def save_value(self):
        if self.count():
            self.settings.setValue(
                "items",
                [self.itemText(i) for i in range(self.count())])

    def save_index(self):
        if self.count():
            self.settings.setValue(
                "curr_index", self.currentIndex())

    def save_current_text(self):
        if self.count():
            self.settings.setValue(
                "name", self.currentText())


class MyWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):

        QtWidgets.QWidget.__init__(self, parent)
        QtWidgets.QApplication.setAttribute(
            QtCore.Qt.ApplicationAttribute.
            AA_UseStyleSheetPropagationInWidgetStyles,
            True)  # наследование свойств оформления потомков от родителей

# ------ Init vars ------------------------------------------------------------
        self.PLOT_TIME_INTERVAL_SEC = 10
        self.PAUSE_INTERVAL_MS = 500
        self.READ_INTERVAL_MS = 100*2 #  125*2
        self.folder_name = os.getcwd() + '/'
        self.count: int = 0
        self.progress_bar_value = 0
        self.progress_value = 0
        self.total_time: int = 0
        self.total_cycle_num: int = 1
        self.current_cylce: int = 0
        STYLE_SHEETS_FILENAME = 'StyleSheets.css'
        FILE_LOG_FLAG = True
        self.GYRO_NUMBER = 1
        self.filename_path_watcher = ""
        self.Serial = QSerialPort(dataBits=QSerialPort.DataBits.Data8,
                                  stopBits=QSerialPort.StopBits.OneStop,
                                  parity=QSerialPort.Parity.NoParity)
# ------ Timres ---------------------------------------------------------------
        self.timer_recieve = QtCore.QTimer(interval=self.READ_INTERVAL_MS)
        self.timer_recieve.timeout.connect(self.timer_read_event)
        self.timer_sent_com = QtCore.QTimer(
            timerType=QtCore.Qt.TimerType.PreciseTimer)
        self.timer_sent_com.timeout.connect(self.timer_event_sent_com)
# ------ File watcher --------------------------------------------------------
        self.fs_watcher = QtCore.QFileSystemWatcher()
        # self.fs_watcher.directoryChanged.connect(self.directory_changed)
        self.fs_watcher.fileChanged.connect(self.check_filename_and_get_data)
# ------ Thread --------------------------------------------------------------
        self.prosessing_thr = PyQt6_Thread.MyThread(
            gyro_number=self.GYRO_NUMBER)
        self.prosessing_thr.package_num_signal.connect(self.plot_time_graph)
        self.prosessing_thr.fft_data_emit.connect(self.plot_fft)
        self.prosessing_thr.approximate_data_emit.connect(self.plot_fft_final)

# ------ GUI ------------------------------------------------------------------
        self.main_grid_layout = QtWidgets.QGridLayout(self)
# ------ Com Settings ---------------------------------------------------------
        """
        Block with COM port settings and sampling frequency selection
        """
        self.com_param_groupbox = QtWidgets.QGroupBox(
            'Настройки порта', maximumWidth=300)
        self.com_param_groupbox_layout = QtWidgets.QGridLayout()
        self.com_param_groupbox.setLayout(self.com_param_groupbox_layout)

        self.combo_box_name = CustomComboBox(
            settings_name="COM_name_settings",
            editable_flag=False, uint_validator_enable=False)

        self.get_avaliable_com()
        self.com_param_groupbox_layout.addWidget(QtWidgets.QLabel('COM:'),
                                                 0, 0, 1, 1)
        self.com_param_groupbox_layout.addWidget(self.combo_box_name,
                                                 0, 1, 1, 1)

        self.com_boderate_combo_box = CustomComboBox(
            settings_name="COM_speed_settings",
            default_items_list=['921600', '115200', '0'])
        self.com_param_groupbox_layout.addWidget(QtWidgets.QLabel('Скорость:'),
                                                 1, 0, 1, 1)  # Speed
        self.com_param_groupbox_layout.addWidget(self.com_boderate_combo_box,
                                                 1, 1, 1, 1)

        self.fs_combo_box = CustomComboBox(
            settings_name="fs_settings",
            default_items_list=['1000', '2000', '0'])
        self.com_param_groupbox_layout.addWidget(QtWidgets.QLabel('Fs, Hz:'),
                                                 2, 0, 1, 1)
        self.com_param_groupbox_layout.addWidget(self.fs_combo_box,
                                                 2, 1, 1, 1)
# ------ Measurement File -----------------------------------------------------
        """
        Block with button to open and edit measurement file
        """
        self.measurements_groupbox = QtWidgets.QGroupBox(
            'Измерения', maximumWidth=300)
        self.measurements_groupbox_layout = QtWidgets.QGridLayout()
        self.measurements_groupbox.setLayout(self.measurements_groupbox_layout)

        self.cycle_num_widget = QtWidgets.QSpinBox(
            minimum=1, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel('Число циклов:'), 0, 0, 3, 2)  # Cycle number
        self.measurements_groupbox_layout.addWidget(self.cycle_num_widget,
                                                    0, 2, 3, 2)

        # self.measurements_groupbox_layout.addWidget(
        #     QtWidgets.QLabel('Measurement\ncycle file:'), 1, 0, 1, 1)
        self.choose_file = QtWidgets.QPushButton('Выбрать файл')  # &Choose file
        self.measurements_groupbox_layout.addWidget(self.choose_file,
                                                    3, 0, 3, 4)

        self.edit_file_button = QtWidgets.QPushButton('Открыть файл')  # &Open file
        self.measurements_groupbox_layout.addWidget(self.edit_file_button,
                                                    12, 0, 3, 4)

        self.measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel('Путь:'), 6, 0, 3, 1)  # Filepath
        # self.file_name_and_path_widget = CustomComboBox(
        #     settings_name="file_settings",
        #     deafault_items_list=['', '', ''],
        #     editable_flag=False)
        self.filename_and_path_widget = QtWidgets.QTextEdit(
            objectName="with_bourder")
        self.filename_and_path_widget.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff) 
        self.filename_and_path_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored,
            QtWidgets.QSizePolicy.Policy.Ignored)
        self.measurements_groupbox_layout.addWidget(
            self.filename_and_path_widget, 6, 1, 3, 3)
        # self.measurements_groupbox_layout.setSizeConstraint(
        # QtWidgets.QLayout.SizeConstraint.SetNoConstraint)

# ------ Saving results -------------------------------------------------------
        """
        Block with info about saving measurements results
        """
        self.saving_measurements_groupbox = QtWidgets.QGroupBox(
            'Сохранение измерений', maximumWidth=300)
        self.saving_measurements_groupbox_layout = QtWidgets.QGridLayout()
        self.saving_measurements_groupbox.setLayout(
            self.saving_measurements_groupbox_layout)

        self.saving_measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel('<b>Папка:</b>'), 0, 0, 3, 1)
        # self.current_folder_label = QtWidgets.QLabel(
        #     self.folder_name, wordWrap=True, objectName="with_bourder",
        #     textInteractionFlags=QtCore.Qt.
        #     TextInteractionFlag.TextEditorInteraction)  # TextSelectableByMouse
        self.saving_result_folder_label = QtWidgets.QTextEdit(
            self.folder_name, objectName="with_bourder")
        # self.current_folder_label.setMinimumHeight(20)
        self.saving_result_folder_label.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff) 
        self.saving_result_folder_label.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored,
            QtWidgets.QSizePolicy.Policy.Ignored)
        self.saving_measurements_groupbox_layout.addWidget(
            self.saving_result_folder_label, 0, 1, 3, 2)

        self.saving_measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel('Имя\nфайла:'), 3, 0, 2, 1)
        self.file_name_path = QtWidgets.QLineEdit('test')
        self.saving_measurements_groupbox_layout.addWidget(
            self.file_name_path, 3, 1, 2, 2)
        self.choose_path_button = QtWidgets.QPushButton('Выбрать папку\nсохранения')
        self.saving_measurements_groupbox_layout.addWidget(
            self.choose_path_button, 5, 0, 1, 2)
        self.create_folder = QtWidgets.QCheckBox('Cоздавать\n   папку')
        self.saving_measurements_groupbox_layout.addWidget(
            self.create_folder, 5, 2, 1, 1)  # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
##############################################################################
# ------ Output logs and data from file ---------------------------------------
        self.text_output_groupbox = QtWidgets.QGroupBox(
            'Содержимое файла', maximumWidth=315, minimumWidth=215)
        self.text_output_groupbox_layout = QtWidgets.QGridLayout()
        self.text_output_groupbox.setLayout(self.text_output_groupbox_layout)

        self.table_widget = QtWidgets.QTableWidget(
            columnCount=3,
            editTriggers=QtWidgets.
            QAbstractItemView.EditTrigger.NoEditTriggers,
            selectionBehavior=QtWidgets.
            QAbstractItemView.SelectionBehavior.SelectRows)
        # self.table_widget.setRowHeight(0, 0) 
        self.table_widget.setHorizontalHeaderLabels(
            ["F, Hz", "A, \u00b0/s", "T, s"])
        self.table_widget.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table_widget.verticalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        # self.table_widget.verticalHeader().setSectionResizeMode(
            # QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

        self.text_output_groupbox_layout.addWidget(self.table_widget)

# ------ Logger ---------------------------------------------------------------
        """
        Logs widget
        """
        self.logs_groupbox = QtWidgets.QGroupBox(
            'Лог', maximumWidth=315)  # Logs
        self.logs_groupbox_layout = QtWidgets.QVBoxLayout()
        self.logs_groupbox.setLayout(self.logs_groupbox_layout)

        self.log_text_box = PyQt6_Logger.QTextEditLogger(
            self, file_log=FILE_LOG_FLAG)
        self.logger = logging.getLogger('main')

        self.logs_groupbox_layout.addWidget(self.log_text_box.widget)

        self.clear_button = QtWidgets.QPushButton('Очистить')  # Clear logs
        self.logs_groupbox_layout.addWidget(self.clear_button)

        self.start_button = QtWidgets.QPushButton(
            'Старт', objectName="start_button")  # START
        self.stop_button = QtWidgets.QPushButton(
            'Стоп', enabled=False, objectName="stop_button")  # STOP

###############################################################################
# ------ plot -----------------------------------------------------------------
        """
        Plots in tab widget
        """
        # self.plot_groupbox = QtWidgets.QGroupBox('График', minimumWidth=395)
        self.plot_groupbox = QtWidgets.QGroupBox(minimumWidth=395)
        self.plot_groupbox_layout = QtWidgets.QGridLayout()
        self.plot_groupbox.setLayout(self.plot_groupbox_layout)

        self.custom_tab_plot_widget = PyQt6_TabWidget.CustomTabWidget(
            GYRO_NUMBER=1)  # !

# ------ Others ------------------------------------------------------------
        self.progress_bar = QtWidgets.QProgressBar(
            format='%v/%m сек', maximum=1, value=self.progress_value)  # sec
        self.plot_groupbox_layout.addWidget(self.progress_bar,
                                            1, 0, 1, 13)

        self.package_number_label = QtWidgets.QLabel('Пакеты:')  # Package number
        self.plot_groupbox_layout.addWidget(self.package_number_label,
                                            1, 13, 1, 4)
        self.package_num_label = QtWidgets.QLabel('0')
        self.plot_groupbox_layout.addWidget(self.package_num_label,
                                            1, 17, 1, 1)

        self.save_image_button = QtWidgets.QPushButton('Графики в .png')  # Save\nimage
        self.plot_groupbox_layout.addWidget(self.save_image_button, 2, 0, 1, 6)
        self.save_settings_button = QtWidgets.QPushButton('Сохранить\nнастройки')  # Save settings
        self.plot_groupbox_layout.addWidget(self.save_settings_button, 2, 6, 1, 6)
        self.autosave_checkbox = QtWidgets.QCheckBox('Автосохранение\n     настроек')  # Autosave
        self.plot_groupbox_layout.addWidget(self.autosave_checkbox, 2, 12, 1, 6)

        self.check_box_list: list[QtWidgets.QCheckBox] = []
        self.check_box_list.append(QtWidgets.QCheckBox("видимость encoder",
                                                objectName="0", checked=True))
        self.check_box_list.append(QtWidgets.QCheckBox("видимость gyro 1",
                                                objectName="1", checked=True))
        for i in range(self.GYRO_NUMBER + 1):
            self.plot_groupbox_layout.addWidget(self.check_box_list[i],
                                            0, 7 * i, 1, 6 * (i + 1))

# ------ Set main grid --------------------------------------------------------
        self.main_grid_layout.addWidget(self.com_param_groupbox,
                                        0, 0, 5, 1)
        self.main_grid_layout.addWidget(self.measurements_groupbox,
                                        5, 0, 9, 1)
        self.main_grid_layout.addWidget(self.saving_measurements_groupbox,
                                        14, 0, 6, 1)
        self.main_grid_layout.addWidget(self.text_output_groupbox,
                                        0, 1, 10, 1)
        self.main_grid_layout.addWidget(self.logs_groupbox,
                                        10, 1, 8, 1)
        self.main_grid_layout.addWidget(self.start_button,
                                        18, 1, 1, 1)
        self.main_grid_layout.addWidget(self.stop_button,
                                        19, 1, 1, 1)
        self.main_grid_layout.addWidget(self.custom_tab_plot_widget,
                                        0, 2, 16, 1)
        self.main_grid_layout.addWidget(self.plot_groupbox,
                                        16, 2, 4, 2)
        self.setLayout(self.main_grid_layout)

# ------ Style ----------------------------------------------------------------
        with open(self.res_path(STYLE_SHEETS_FILENAME), "r") as style_sheets:
            self.setStyleSheet(style_sheets.read())
        app_icon = QtGui.QIcon()
        for i in [16, 24, 32, 48]:
            app_icon.addFile(self.res_path(f'icon_{i}.png'), QtCore.QSize(i, i))
        QtWidgets.QApplication.setWindowIcon(app_icon)

# ------ Set settings --------------------------------------------------------------------------
        self.load_previous_settings()

# ------ Signal Connect -------------------------------------------------------

        self.start_button.clicked.connect(self.start)
        self.stop_button.clicked.connect(self.stop)
        self.choose_file.clicked.connect(self.choose_and_load_file)
        self.cycle_num_widget.valueChanged.connect(self.cycle_num_value_change)
        self.cycle_num_widget.valueChanged.connect(self.progress_bar_set_max)
        self.save_image_button.clicked.connect(self.save_image)
        self.save_settings_button.clicked.connect(self.save_all_settings)
        # self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.choose_path_button.clicked.connect(
            self.choose_result_saving_path)
        self.filename_and_path_widget.textChanged.connect(
            self.filename_and_path_text_change)
        self.clear_button.clicked.connect(
            lambda: self.log_text_box.widget.clear())
        self.edit_file_button.clicked.connect(
            lambda: os.startfile(self.filename_and_path_widget.toPlainText()))
        for i in range(self.GYRO_NUMBER + 1):
            self.check_box_list[i].stateChanged.connect(
                self.custom_tab_plot_widget.change_curve_visibility)

        # self.fs = 500
        # self.plot_fft_final(True)
        # self.check_filename()
# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------
#
###############################################################################
#
# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------


    @QtCore.pyqtSlot()
    def start(self):
        self.exp_package_num = 0

        self.progress_bar.setValue(0)
        self.progress_value = 0
        self.count = 0
        self.current_cylce = 1
        self.package_num = 0
        self.flag_sent = False

        # Check COM port
        self.logger.info(F"\nPORT: {self.combo_box_name.currentText()}\n")
        if not len(self.combo_box_name.currentText()):
            self.get_avaliable_com()
            self.logger.info(
                f"PORT: {(self.combo_box_name.currentText())}\n")
        if not len(self.combo_box_name.currentText()):
            self.logger.info("")
            QtWidgets.QMessageBox.critical(
                None, "Error", "Can't find COM port")
            return
        self.Serial.setBaudRate(
            int(self.com_boderate_combo_box.currentText()))
        self.Serial.setPortName(
            self.combo_box_name.currentText())
        self.logger.info("Set COM settings")

        # Check filename and measurement file
        if not self.check_filename():
            return
        if not self.total_time:
            self.cycle_num_value_change()
            if not self.choose_and_load_file():
                self.logger.info("No data from file")
                return
        self.logger.info("Data from file was loaded")

        # Open COM
        if not self.Serial.open(QtCore.QIODevice.OpenModeFlag.ReadWrite):
            self.logger.warning(
                f"Can't open {self.combo_box_name.currentText()}")
            return

        self.cycle_num_value_change()
        self.progress_bar_set_max()
        self.avaliable_butttons(True)  # disable widgets

        self.logger.info(f"{self.combo_box_name.currentText()} open")
        self.logger.info(f"self.cycle_num = {self.total_cycle_num}")
        self.logger.warning("Start")

        # self.Serial.readAll()
        self.Serial.clear()
        # self.timer_recieve.setInterval(0)
        # self.timer_sent_com.setInterval(0)
        # Start timers
        self.start_time = time()  # !
        self.timer_event_sent_com()
        self.timer_sent_com.start()
        self.timer_recieve.start()
        self.fs = int(self.fs_combo_box.currentText())
        # Copy variables to another classes and start thread
        self.custom_tab_plot_widget.fs = self.fs
        self.prosessing_thr.fs = self.fs
        self.prosessing_thr.flag_start = True
        self.prosessing_thr.TIMER_INTERVAL = self.READ_INTERVAL_MS
        self.prosessing_thr.num_measurement_rows = self.num_rows
        self.prosessing_thr.total_cycle_num = self.total_cycle_num
        self.prosessing_thr.start()

        self.custom_tab_plot_widget.clear_plots()

# ------ Timer Recieve --------------------------------------------------------

    @QtCore.pyqtSlot()
    def timer_read_event(self):
        """
        Read data from COM port.
        Generate warning if avaliable less than 14 bytes
        """
        self.read_serial()
        # self.progress_value += self.READ_INTERVAL_MS/1000
        # self.progress_value = time() - self.start_time
        # # self.progress_value += time() - self.start_time
        # # self.start_time = time()
        # self.progress_bar.setValue(int(round(self.progress_value)))
        # self.logger.info(f"Progress: {self.progress_value}")

    def read_serial(self):
        bytes_num = self.Serial.bytesAvailable()
        if bytes_num <= 14:
            self.logger.warning(
                f"No data from {self.combo_box_name.currentText()}")
            return
        if self.prosessing_thr.flag_recieve:
            self.logger.warning("Thread still work with previous data")
            return
        # !!!
        self.progress_value = time() - self.start_time
        # self.progress_value += time() - self.start_time
        self.progress_bar.setValue(int(round(self.progress_value)))
        self.logger.info(f"Progress: {self.progress_value}")
        # !!!
        self.exp_package_num += int(bytes_num/14)
        self.logger.info(
            f"ready to read, bytes num = {bytes_num}," +
            f"expected package num {self.exp_package_num}")
        self.copy_variables_to_thread()
        self.logger.info(f"thr_start, count = {self.count}")

    def copy_variables_to_thread(self):
        self.prosessing_thr.rx = self.Serial.readAll().data()
        self.prosessing_thr.flag_recieve = True
        # self.logger.info(f"!!! prosessing_thr count = {self.prosessing_thr.count}")
        # self.logger.info(f"count = {self.count}")
        self.prosessing_thr.count = self.count
        self.prosessing_thr.flag_pause = self.flag_sent

# ------- Timer Sent ----------------------------------------------------------

    @QtCore.pyqtSlot()
    def timer_event_sent_com(self):
        """
        Sent command with frequency and amplitude or stop vibration
        """
        if self.flag_sent:
            self.logger.info(f"count = {self.count}, num_rows={self.num_rows}")
            if self.count >= self.num_rows:
                if self.current_cylce < self.total_cycle_num:
                    self.cycle_end()
                else:
                    self.stop()
                    return
        if self.flag_sent:
            self.sent_vibro_command()
        else:
            self.sent_stop_vibro_command()
        self.flag_sent = not self.flag_sent
        self.logger.info("---end_sent_command")

    def sent_stop_vibro_command(self):
        self.Serial.write(bytes([0, 0, 0, 0, 0, 0, 0, 0]))
        self.timer_sent_com.setInterval(self.PAUSE_INTERVAL_MS)

    def sent_vibro_command(self):
        self.table_widget.selectRow(self.count)
        F = int.to_bytes(int(self.table_widget.item(self.count, 0).data(
            QtCore.Qt.ItemDataRole.EditRole)),
                         length=2, byteorder='little', signed=False)
        A = int.to_bytes(int(self.table_widget.item(self.count, 1).data(
            QtCore.Qt.ItemDataRole.EditRole)),
                         length=2, byteorder='little', signed=False)
        self.Serial.write(
            bytes([77, 0, F[0], F[1], A[0], A[1], 0, 0]))
        self.timer_sent_com.setInterval(
            int(self.table_widget.item(
                self.count, 2).data(QtCore.Qt.ItemDataRole.EditRole)) * 1000)
        self.count += 1
        self.logger.info("- Command was sent -")

# ----- End cycle, stop, etc --------------------------------------------------

    def cycle_end(self):
        self.logger.warning(
            f"End of cycle {self.current_cylce} of {self.total_cycle_num}")
        self.current_cylce += 1
        self.count = 0
        self.custom_tab_plot_widget.append_fft_plot_tab()
        self.prosessing_thr.new_cycle()

    def stop(self):
        self.avaliable_butttons(False)
        if self.timer_sent_com.isActive():
            self.timer_sent_com.stop()

        if self.timer_recieve.isActive():
            self.timer_recieve.stop()

        self.logger.info(
            f"% = {self.progress_value}, " +
            f"total time = {self.progress_bar.maximum()}")
        # if self.prosessing_thr.flag_start:
        #     # self.save_image()
        #     if self.progress_value < self.progress_bar.maximum():
        #         self.timer_read_event()

        if self.Serial.isOpen():
            self.Serial.write(bytes([0, 0, 0, 0, 0, 0, 0, 0]))
            self.logger.info("COM close? " +
                             str(self.Serial.waitForBytesWritten(250)))
            self.Serial.close()
            self.logger.warning("End of measurements\n")
            if self.progress_bar_value:
                check = int(self.package_num / self.progress_bar_value)
                if not (0.95 * self.fs < check < 1.05 * self.fs):
                    QtWidgets.QMessageBox.critical(
                        None, "Warning",
                        f"You set fs = {self.fs} Hz," +
                        f"but in fact it's close to {check} Hz")
        self.prosessing_thr.flag_start = False

###############################################################################
# ----- plotting --------------------------------------------------------------

    @QtCore.pyqtSlot(int)
    def plot_time_graph(self, s):
        self.package_num = s
        self.logger.info(f"thr_stop, count = {self.count}\n" +
                         f"package_num = {self.package_num}")
        self.package_num_label.setText(str(self.package_num))

        points_shown = self.PLOT_TIME_INTERVAL_SEC * self.fs
        start_i = (self.package_num - points_shown 
                   if self.package_num > points_shown else 0)
        self.custom_tab_plot_widget.plot_time_graph(
            self.prosessing_thr.all_data[start_i:self.package_num, 0] / self.fs,
            self.prosessing_thr.all_data[start_i:self.package_num, 2] / 1000,
            self.prosessing_thr.all_data[start_i:self.package_num, 1] 
            / self.prosessing_thr.k_amp / 1000)

    @QtCore.pyqtSlot(bool)
    def plot_fft(self, _):
        """
        Adds points to frequency graphs
        """
        self.custom_tab_plot_widget.set_fft_data(
            self.prosessing_thr.amp_and_freq_for_plot,
            self.prosessing_thr.bourder)
        self.logger.info("plot_fft")

    @QtCore.pyqtSlot(bool)
    def plot_fft_final(self, _):
        self.logger.info("Final median plot")
        self.custom_tab_plot_widget.plot_fft_median(
            self.prosessing_thr.amp_and_freq_for_plot,
            np.array([]))

    @QtCore.pyqtSlot()
    def save_image(self):
        self.logger.info("Save image")
        if self.check_filename():
            self.custom_tab_plot_widget.save_plot_image(
                self.prosessing_thr.filename[0])
            self.logger.info("Saving complite")

# ------ Widgets events -------------------------------------------------------

    def cycle_num_value_change(self):
        # if not self.timer_recieve.isActive():  # is this required?
        self.total_cycle_num = self.cycle_num_widget.value()

    def progress_bar_set_max(self):
        if self.total_time and not self.timer_recieve.isActive():  # is this required?
            # self.progress_bar.setMaximum(int(
            #     self.PAUSE_INTERVAL_MS/1000 + self.total_cycle_num *
            #     (self.total_time +
            #      self.num_rows * self.PAUSE_INTERVAL_MS / 1000)))
            self.total_cycle_num = self.cycle_num_widget.value()
            self.progress_bar.setMaximum(int(
                self.total_cycle_num * (self.total_time +
                 self.num_rows * self.PAUSE_INTERVAL_MS / 1000)))
            # self.progress_bar.setValue(0)

    def avaliable_butttons(self, flag_running: bool):
        """Enable or disable widgets"""
        self.cycle_num_widget.setDisabled(flag_running)
        self.edit_file_button.setDisabled(flag_running)
        self.save_image_button.setDisabled(flag_running)
        self.start_button.setDisabled(flag_running)
        self.stop_button.setDisabled(not flag_running)
        self.choose_file.setDisabled(flag_running)

    def get_avaliable_com(self):  # проверить
        """Append avaliable com ports to combo box widget"""
        self.combo_box_name.addItems(
              [ports.portName() 
               for ports in QSerialPortInfo.availablePorts()])

# ------ file name and data from file -----------------------------------------

    def check_filename(self):  # changed for three files
        # print( os.path.exists(self.current_folder_label.())) 
        if not os.path.exists(self.saving_result_folder_label.toPlainText()):  # text
            QtWidgets.QMessageBox.critical(
                None, "Error", "The file path does not exist!")
            return False
        if not len(self.file_name_path.text()):
            filename = self.folder_name + 'test'
        else:
            filename = self.folder_name + self.file_name_path.text()
        extension = '.txt'
        if self.create_folder.isChecked():
            folder = re.split("_", self.file_name_path.text())[0]
            if not os.path.isdir(folder):
                os.mkdir(folder)
            filename = self.folder_name + folder + '/' + self.file_name_path.text()
            self.saving_result_folder_label.setText(self.folder_name + folder + '/')

        new_name_list: list[str] = []
        if self.GYRO_NUMBER == 1:
                new_name_list.append(filename + extension)
        else:
            for j in range(self.GYRO_NUMBER):
                new_name_list.append(filename + f"_{j + 1}" + extension)

        if not any(os.path.exists(name) for name in new_name_list):  # os.path.exists(new_name_list):
            self.prosessing_thr.filename = [filename, extension]
            return True

        i = 0
        while any(os.path.exists(name) for name in new_name_list):  # os.path.exists(new_name_list):
            i += 1
            if self.GYRO_NUMBER == 1:
                new_name_list[0] = filename + f"({i})" + extension
            else:
                for j in range(self.GYRO_NUMBER):
                    new_name_list[j] = filename + f"_{j + 1}({i})" + extension
        self.prosessing_thr.filename = [filename, f"({i})" + extension]
        return True

    # def directory_changed(self, path):
    #     self.logger.info(f'Directory Changed: {path}')
    #     print(f'Directory Changed: {path}')

    @QtCore.pyqtSlot()
    def choose_result_saving_path(self):
        temp = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Выбрать папку", ".")
        if not len(temp):
            return
        self.folder_name = temp + '/'
        self.saving_result_folder_label.setText(self.folder_name)

    @QtCore.pyqtSlot()
    def check_filename_and_get_data(self, path):
        self.logger.info(
            f'File Changed, {path},' +
            f'thr run: {self.prosessing_thr.flag_start}')
        if not self.prosessing_thr.flag_start and os.path.exists(path):
            self.get_data_from_file(path)

    def choose_and_load_file(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Выберите методику измерений",
            ".",
            "Text Files(*.txt)")
        if not filename:
            return False
        self.logger.info(
            f"filename: {filename}, basebame: {os.path.basename(filename)}")
        if len(self.filename_path_watcher):
            self.fs_watcher.removePath(self.filename_path_watcher)
        self.filename_path_watcher = filename  # os.path.basename(filename)
        self.fs_watcher.addPath(self.filename_path_watcher)
        self.filename_and_path_widget.setText(filename)
        return self.get_data_from_file(self.filename_path_watcher)

    @QtCore.pyqtSlot()
    def filename_and_path_text_change(self):
        if not os.path.exists(self.filename_and_path_widget.toPlainText()):  # text
            self.logger.warning("The file path does not exist!")
            # доработать, чтобы человек не получал кучу таких уведомлений
            return False
        if len(self.filename_and_path_widget.toPlainText()):
            self.fs_watcher.removePath(self.filename_path_watcher)
        self.filename_path_watcher = self.filename_and_path_widget.toPlainText()  # os.path.basename(filename)
        self.fs_watcher.addPath(self.filename_path_watcher)
        
        return self.get_data_from_file(self.filename_path_watcher)

    def get_data_from_file(self, filename_path_watcher):
        """
        Get data from file and put it in table
        """
        with open(filename_path_watcher, 'r') as file:
            i = 0
            self.table_widget.setRowCount(i)
            self.total_time = 0
            for line in file:
                f_a_t = list(filter(None, re.split("F|A|T|\n", line)))
                if (len(f_a_t) == 3 and f_a_t[0].isdecimal() and
                    f_a_t[1].isdecimal() and f_a_t[2].isdecimal()):
                    i += 1
                    self.table_widget.setRowCount(i)
                    for j in range(3):
                        item = QtWidgets.QTableWidgetItem(f_a_t[j])
                        item.setTextAlignment(
                            QtCore.Qt.AlignmentFlag.AlignCenter)
                        self.table_widget.setItem(i-1, j, item)
                    self.total_time += int(f_a_t[2])
            self.num_rows = i
            self.progress_bar_set_max()
        return self.total_time > 0

    # @QtCore.pyqtSlot()
    # def open_file(self):
    #     os.startfile(self.filename_and_path_widget.toPlainText())

    def res_path(self, relative_path):
        """
        Get absolute path to resource, works for PyInstaller
        """
        base_path = getattr(
            sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)

    def closeEvent(self, _):
        """
        Sending stop command to the vibrostand and saving user settings
        """
        self.stop()
        self.settings.setValue("autosave",
                                self.autosave_checkbox.checkState())
        if self.autosave_checkbox.checkState():
            self.save_all_settings()
        self.logger.warning("Saving the settings and exit")

    def save_all_settings(self):
        self.com_boderate_combo_box.save_value()
        self.com_boderate_combo_box.save_index()
        self.fs_combo_box.save_value()
        self.fs_combo_box.save_index()
        self.combo_box_name.save_current_text()
        self.settings.setValue("cycle_num",
                                self.cycle_num_widget.value())
        self.settings.setValue("filename",
                                self.filename_and_path_widget.toPlainText())
        self.settings.setValue("current_folder",
                               self.saving_result_folder_label.toPlainText())  # text

    def load_previous_settings(self):
        self.settings = QtCore.QSettings("settings")
        if self.settings.contains("cycle_num"):
            self.cycle_num_widget.setValue(
                self.settings.value("cycle_num"))
        if self.settings.contains("autosave"):
            self.autosave_checkbox.setChecked(
                self.settings.value("autosave"))
        if self.settings.contains("filename"):
            name = self.settings.value("filename")
            if os.path.exists(name):
                self.filename_and_path_widget.setText(name)
                if self.get_data_from_file(name):
                    self.logger.warning("The previous file is loaded")
        if self.settings.contains("current_folder"):
            if os.path.isdir(self.settings.value("current_folder")):
                self.saving_result_folder_label.setText(
                    self.settings.value("current_folder"))

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
#
###############################################################################
#
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')  # 'Fusion' ... QtWidgets.QStyle
    window = MyWindow()
    window.setWindowTitle("Gyro")
    # window.resize(850, 500)
    window.show()
    sys.exit(app.exec())