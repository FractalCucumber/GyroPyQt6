
import logging
import sys

from PyQt6.QtWidgets import QFileDialog
# from PyQt6.QtWidgets import QDialog, QApplication, QFileDialog
# from PyQt6.QtCore import pyqtSignal, QThread, QIODevice
import os
import re
import time
# from pyqtgraph.Qt import QtCore, QtGui
from PyQt6.QtSerialPort import QSerialPort, QSerialPortInfo
from PyQt6 import QtGui
# from datetime import datetime
from PyQt6 import QtWidgets, QtCore
import PyQt6_Thread
# import PyQt6_QRunnable
# from PyQt6.QtCore import QRunnable, Qt, QThreadPool
import pyqtgraph as pg
import numpy as np

# -------------------------------------------------------------------------------------------------------------------------------------------------------------
#
# -------------------------------------------------------------------------------------------------------------------------------------------------------------

class QTextEditLogger():
    def __init__(self, parent):
        super().__init__()
        # def create_logger(path, widget: QtWidgets.QTextEdit):
        # logging.disable(logging.INFO) # disable logging for certain level
        self.widget = QtWidgets.QTextEdit(parent)
        self.widget.setReadOnly(True)
        
        log = logging.getLogger('main')
        log.setLevel(logging.INFO)

        file_formatter = logging.Formatter(
            ('#%(levelname)-s, %(pathname)s, line %(lineno)d, [%(asctime)s]: '
            '%(message)s'), datefmt='%Y-%m-%d %H:%M:%S'
        )
        # file_handler = logging.FileHandler('./log')
        logging.basicConfig(
            filename='pyqt6_log.log',
            filemode='w',
            format=('#%(levelname)-s, %(pathname)s, line %(lineno)d, [%(asctime)s]: %(message)s'),
            level=logging.INFO)

        log_window_formatter = logging.Formatter(
            ('>>> %(asctime)s %(message)s\n'), datefmt='%H:%M:%S'
        )
        log_window_handler = logging.Handler()
        log_window_handler.emit = lambda record: self.widget.insertPlainText(
            log_window_handler.format(record)
        )
        log_window_handler.setLevel(logging.WARNING)
        
        log_window_handler.setFormatter(log_window_formatter)
        # log.addHandler(file_handler)
        # log.addHandler(console_handler)
        log.addHandler(log_window_handler)

# class QTextEditLogger(logging.Handler):
#     def __init__(self, parent):
#         super().__init__()
#         self.widget = QtWidgets.QTextEdit(parent)
#         self.widget.setReadOnly(True)
#         # logging.basicConfig(level=logging.INFO,
#         #                     filemode="w",
#         #                     format="%(asctime)s %(levelname)s %(message)s",
#         #                     datefmt='%d-%b-%y %H:%M:%S')

#     def emit(self, record):
#         msg = self.format(record)
#         self.widget.append(msg)
#         # self.logTextBox.setFormatter(
#         #   logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))


class MyWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):

        QtWidgets.QWidget.__init__(self, parent)

        QtWidgets.QApplication.setAttribute(
            QtCore.Qt.ApplicationAttribute.
            AA_UseStyleSheetPropagationInWidgetStyles,
            True)  # наследование свойств оформления потомков от родителей

# ------ Timres ---------------------------------------------------------------

        self.timer = QtCore.QTimer()
        self.TIMER_INTERVAL = 125*2
        self.timer.setInterval(self.TIMER_INTERVAL)
        self.timer.timeout.connect(self.timerEvent)

        self.timer_sent_com = QtCore.QTimer()
        self.timer_sent_com.setTimerType(QtCore.Qt.TimerType.PreciseTimer)
        self.timer_sent_com.timeout.connect(self.timer_event_sent_com)

# ------ Init vars ------------------------------------------------------------
        self.PAUSE_INTERVAL_MS = 500
        self.count = 0
        self.progress_bar_value = 0
        self.total_time = 0
        self.total_cycle_num = 1

        self.Serial = QSerialPort()
        self.Serial.setDataBits(QSerialPort.DataBits.Data8)
        self.Serial.setParity(QSerialPort.Parity.NoParity)
        self.Serial.setStopBits(QSerialPort.StopBits.OneStop)

        # logging.getLogger().setLevel(logging.WARNING)
        # logging.getLogger().setLevel(logging.INFO)
        # logging.info(f"Start")
        style_sheets_filename = "StyleSheets.css"
###############################################################################
        self.main_grid_layout = QtWidgets.QGridLayout(self)  # контейнер
        # self.main_grid.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        # self.main_grid_layout.setColumnStretch(1, 1)
        # self.main_grid_layout.setColumnMinimumWidth(0, 150)
        # self.main_grid_layout.setColumnStretch(0, 0)
        # self.main_grid_layout.setColumnMinimumWidth(1, 300)
        # self.main_grid_layout.setColumnStretch(1, 0)
        
# ------ Com Settings ---------------------------------------------------------

        self.com_param_groupbox = QtWidgets.QGroupBox(
            "&Настройки порта")
        self.com_param_groupbox.setMaximumWidth(300)
        self.com_param_groupbox_layout = QtWidgets.QGridLayout()

        self.com_list_widget = QtWidgets.QComboBox()
        self.available_ports = QSerialPortInfo.availablePorts()
        if self.available_ports:
            for self.port in self.available_ports:
                self.com_list_widget.addItem(self.port.portName())

        self.com_param_groupbox_layout.addWidget(QtWidgets.QLabel('COM:'),
                                                 0, 0)
        self.com_param_groupbox_layout.addWidget(self.com_list_widget,
                                                 0, 1)

        self.com_boderate_widget = QtWidgets.QComboBox()
        self.com_boderate_widget.setEditable(True)
        self.settings = QtCore.QSettings("COM_speed")
        if self.settings.contains("COM_speed_list"):
            self.com_boderate_widget.addItems(
                self.settings.value("COM_speed_list"))
        else:
            self.com_boderate_widget.addItems(['921600', '115200', '00000'])

        if self.settings.contains("COM_index"):
            self.com_boderate_widget.setCurrentIndex(
                self.settings.value("COM_index"))

        self.com_param_groupbox_layout.addWidget(QtWidgets.QLabel('Speed:'),
                                                 1, 0)
        self.com_param_groupbox_layout.addWidget(self.com_boderate_widget,
                                                 1, 1)

        # self.subblock1_com_param.setFieldGrowthPolicy(self.subblock1_com_param.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        # self.subblock1_com_param.setVerticalSpacing()
        # self.subblock1_com_param.setSizeConstraint(self.subblock1_com_param.SizeConstraint.SetMaximumSize)
        self.FS_for_FFT = QtWidgets.QLineEdit("2000")
        self.com_param_groupbox_layout.addWidget(QtWidgets.QLabel('FS, Hz:'),
                                                 2, 0)
        self.com_param_groupbox_layout.addWidget(self.FS_for_FFT,
                                                 2, 1)

        self.com_param_groupbox.setLayout(self.com_param_groupbox_layout)
###############################################################################
# ------ File -----------------------------------------------------------------

        self.measurements_groupbox = QtWidgets.QGroupBox("&Измерения")
        self.measurements_groupbox.setMaximumWidth(300)
        self.measurements_groupbox_layout = QtWidgets.QGridLayout()

        self.choose_file = QtWidgets.QPushButton(
            "Выбрать")

        self.measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel("Measurement\ncycle file:"),
            0, 0)
        self.measurements_groupbox_layout.addWidget(self.choose_file,
                                                    0, 1)

        self.file_name_and_path = QtWidgets.QLineEdit()
        self.file_name_and_path.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.file_name_and_path.setReadOnly(True)
        self.measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel('Filename:'),
            1, 0)
        self.measurements_groupbox_layout.addWidget(self.file_name_and_path,
                                                    1, 1)

        self.cycle_num_widget = QtWidgets.QSpinBox()
        self.cycle_num_widget.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.cycle_num_widget.setMinimum(1)
        self.measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel("Cycle number:"),
            2, 0)
        self.measurements_groupbox_layout.addWidget(self.cycle_num_widget,
                                                    2, 1)

        self.measurements_groupbox.setLayout(self.measurements_groupbox_layout)
###############################################################################
# ------ File -----------------------------------------------------------------

        self.saving_measurements_groupbox = QtWidgets.QGroupBox(
            "&Сохранение измерений")
        self.saving_measurements_groupbox.setMaximumWidth(300)
        self.saving_measurements_groupbox_layout = QtWidgets.QGridLayout()

        self.saving_measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel("Папка:"), 0, 0)
        self.current_folder = QtWidgets.QLineEdit(os.getcwd())
        self.current_folder.setReadOnly(True)
        self.saving_measurements_groupbox_layout.addWidget(
            self.current_folder, 0, 1)

        self.saving_measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel("<b>Имя файла:</b>"), 1, 0)
        self.file_name = QtWidgets.QLineEdit("test")
        self.saving_measurements_groupbox_layout.addWidget(
            self.file_name, 1, 1)
        self.saving_measurements_groupbox.setLayout(
            self.saving_measurements_groupbox_layout)

##############################################################################
# ------ Logger ---------------------------------------------------------------

        self.log_text_box = QTextEditLogger(self)
        self.logger = logging.getLogger('main')
        # self.logger.info(f"Start")
        # self.logger.warning(f"Start11")

# ------ Output logs and data from file ---------------------------------------

        self.text_output_groupbox = QtWidgets.QGroupBox("")
        self.text_output_groupbox.setMaximumWidth(395)
        self.text_output_groupbox_layout = QtWidgets.QFormLayout()

        self.list_data_from_file_widget = QtCore.QStringListModel(self)
        self.list_view_from_file = QtWidgets.QListView(self)
        self.list_view_from_file.setModel(self.list_data_from_file_widget)

        self.text_output_groupbox_layout = QtWidgets.QFormLayout()
        # self.subblock1right.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        # self.text_logs = QtWidgets.QTextEdit()
        # self.text_logs.setReadOnly(True)

        self.text_output_groupbox_layout.addRow("&Содержимое\nфайла",
                                                self.list_view_from_file)
        # self.subblock1right.addRow("&Logs:", self.text_logs)
        self.text_output_groupbox_layout.addRow("&Logs:",
                                                self.log_text_box.widget)
        self.text_output_groupbox_layout.addRow(
            self.text_output_groupbox_layout)

        self.clear_button = QtWidgets.QPushButton("&Clear logs")
        self.text_output_groupbox_layout.addWidget(self.clear_button)

        self.start_button = QtWidgets.QPushButton("&START")
        # self.subblock1right.addWidget(self._start_button_)

        self.stop_button = QtWidgets.QPushButton("&STOP")
        self.stop_button.setDisabled(True)
        # self.subblock1right.addWidget(self._stop_button_)

        self.text_output_groupbox.setLayout(self.text_output_groupbox_layout)
###############################################################################
# ------ PLot -----------------------------------------------------------------

        self.plot_groupbox = QtWidgets.QGroupBox("&График")
        self.plot_groupbox.setMinimumWidth(395)
        self.plot_groupbox_layout = QtWidgets.QGridLayout()

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(1)
        self.progress_bar.setFormat('%v/%m sec')
        self.plot_groupbox_layout.addWidget(self.progress_bar, 0, 0, 1, 3)

        self.package_number_label = QtWidgets.QLabel("Package number:")
        self.plot_groupbox_layout.addWidget(self.package_number_label, 0, 3, 1, 2)
        self.package_number_label = QtWidgets.QLabel()
        self.plot_groupbox_layout.addWidget(self.package_number_label, 0, 5, 1, 1)

        # self.show_graph_1 = QtWidgets.QCheckBox("gyro 1")
        # self.show_graph_1.setCheckState(QtCore.Qt.CheckState.Checked)
        # self.show_graph_1.setObjectName("show_graph_1")
        # self.plot_groupbox_layout.addWidget(self.show_graph_1, 2, 0, 1, 2)
        # self.show_graph_2 = QtWidgets.QCheckBox("gyro 2")
        # self.show_graph_2.setCheckState(QtCore.Qt.CheckState.Checked)
        # self.show_graph_2.setObjectName("show_graph_2")
        # self.plot_groupbox_layout.addWidget(self.show_graph_2, 2, 2, 1, 2)
        # self.show_graph_3 = QtWidgets.QCheckBox("gyro 3")
        # self.show_graph_3.setCheckState(QtCore.Qt.CheckState.Checked)
        # self.show_graph_3.setObjectName("show_graph_3")
        # self.plot_groupbox_layout.addWidget(self.show_graph_3, 2, 4, 1, 2)

        # self.time_plot = pg.plot()
        self.time_plot = pg.PlotItem()
        self.time_plot.setTitle("Velosity Graph", size="14pt")
        self.time_plot.showGrid(x=True, y=True)

        self.time_plot.addLegend()
        # styles = {'color':'r', 'font-size':'20px'}
        self.time_plot.setLabel('left', 'Velosity',
                                units='radians per second')
        self.time_plot.setLabel('bottom', 'Data packages',
                                units='')

        self.curve_gyro1 = self.time_plot.plot(pen='r', name="gyro 1")
        self.curve_gyro2 = self.time_plot.plot(pen='g', name="gyro 2")
        self.curve_gyro3 = self.time_plot.plot(pen='b', name="gyro 3")

        self.curve_gyro1.setData([0, 0, 1, 1, 0], [0, 1, 1, 0, 0])

        self.plot = pg.PlotWidget(plotItem=self.time_plot)
        self.plot_groupbox_layout.addWidget(self.plot, 3, 0, 1, 6)
        # self.time_plot.ctrl.fftCheck.setChecked(False)  # fft

        self.fft_button = QtWidgets.QPushButton("&Time")
        self.plot_groupbox_layout.addWidget(self.fft_button, 4, 0, 1, 6)

        self.plot_groupbox.setLayout(self.plot_groupbox_layout)

# ------ Set main grid --------------------------------------------------------

        self.main_grid_layout.addWidget(self.com_param_groupbox,
                                        0, 0, 1, 1)
        self.main_grid_layout.addWidget(self.measurements_groupbox,
                                        1, 0, 2, 1)
        self.main_grid_layout.addWidget(self.saving_measurements_groupbox,
                                        3, 0, 3, 1)
        self.main_grid_layout.addWidget(self.text_output_groupbox,
                                        0, 1, 4, 1)
        self.main_grid_layout.addWidget(self.start_button,
                                        4, 1, 1, 1)
        self.main_grid_layout.addWidget(self.stop_button,
                                        5, 1, 1, 1)
        self.main_grid_layout.addWidget(self.plot_groupbox,
                                        0, 3, 6, 1)
        self.setLayout(self.main_grid_layout)

# ------ Style ----------------------------------------------------------------

        # self.block1_com_param.setObjectName("group1")
        # self.subblock1_com_param.setObjectName("group1")
        self.stop_button.setObjectName("stop_button")
        # self.choose_file.setObjectName("choose_file")
        self.start_button.setObjectName("start_button")
        with open(style_sheets_filename, "r") as style_sheets_file:
            self.setStyleSheet(style_sheets_file.read())

        app_icon = QtGui.QIcon()
        app_icon.addFile('Vibro_1_resources/icon_16.png', QtCore.QSize(16, 16))
        app_icon.addFile('Vibro_1_resources/icon_24.png', QtCore.QSize(24, 24))
        app_icon.addFile('Vibro_1_resources/icon_32.png', QtCore.QSize(32, 32))
        app_icon.addFile('Vibro_1_resources/icon_48.png', QtCore.QSize(48, 48))
        app.setWindowIcon(app_icon)

# ------ Connect --------------------------------------------------------------

        self.start_button.clicked.connect(self.start)
        self.stop_button.clicked.connect(self.stop)
        self.clear_button.clicked.connect(self.clear_logs)
        self.choose_file.clicked.connect(self.get_data_from_file)
        self.cycle_num_widget.valueChanged.connect(self.cycle_num_value_change)
        self.cycle_num_widget.valueChanged.connect(self.progress_bar_set_max)
        self.fft_button.clicked.connect(self.plot_change)
        self.com_boderate_widget.currentTextChanged.connect(
            self.combobox_changed)
        # self.show_graph_1.stateChanged.connect(self.plot_show)
        # self.show_graph_2.stateChanged.connect(self.plot_show)
        # self.show_graph_3.stateChanged.connect(self.plot_show)
        # self.sender()
# ------ Thread --------------------------------------------------------------
        self.data_prosessing_thr = PyQt6_Thread.MyThread()
        self.data_prosessing_thr.package_num_signal.connect(
            self.signal_from_thread)

# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------
#
###############################################################################
#
# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------
#

    def start(self):
        self.exp_package_num = 0

        self.i = 0
        self.flag_wait = False
        self.bourder = np.array([0, 0])
        self.amp_and_freq = np.ndarray([])

        self.curve_gyro1.setData([])
        self.curve_gyro2.setData([])
        self.curve_gyro3.setData([])
        self.progress_bar.setValue(0)
        self.progress_value = 0
        self.count = 0
        self.current_cylce = 1
        self.package_num = 0
        self.flag_sent = False
        self.data_prosessing_thr.flag_start = True

        self.logger.info(F"\nPORT: {(self.com_list_widget.currentText())}\n")
        if not len(self.com_list_widget.currentText()):
            self.available_ports = QSerialPortInfo.availablePorts()
            for port in self.available_ports:
                self.com_list_widget.addItem(port.portName())
                self.logger.info(
                    f"PORT: {(self.com_list_widget.currentText())}\n")
        if not len(self.com_list_widget.currentText()):
            self.logger.info("Can't find COM port")
            QtWidgets.QMessageBox.critical(
                None, "Ошибка", "COM порт не найден")
            return

        if not self.com_boderate_widget.currentText().isdecimal():
            QtWidgets.QMessageBox.critical(
                None, "Ошибка", "Некорректная скорость порта")
            return

        self.Serial.setBaudRate(
            int(self.com_boderate_widget.currentText()))
        self.Serial.setPortName(
            self.com_list_widget.currentText())

        self.check_filename()
        if not self.total_time:
            self.cycle_num_value_change()
            self.get_data_from_file()
            if not self.total_time:
                self.logger.info("No data from file")
                return

        self.logger.info("Data from file was loaded")

        if not self.Serial.open(QtCore.QIODevice.OpenModeFlag.ReadWrite):
            self.logger.warning(
                f"Can't open {self.com_list_widget.currentText()}")
            return

        self.cycle_num_value_change()
        self.progress_bar_set_max()
        self.avaliable_butttons(True)
        self.amp_and_freq = np.resize(self.amp_and_freq,
                                      (len(self.list_time), 2))

        # self.timer.setInterval(self.timer_interval)
        self.logger.info(f"{self.com_list_widget.currentText()} open")
        self.logger.info(f"self.cycleNum = {self.total_cycle_num}")
        # self.text_logs.append(
        #   line := f">>> {time.strftime("%H:%M:%S")} Start")
        self.logger.warning("Start")

        # self.Serial.readAll()
        self.Serial.clear()
        # self.Serial.flush()
        # self.timer.setInterval(0)

        # self.timer_sent_com.setInterval(0)
        self.timer_event_sent_com()
        self.timer_sent_com.start()
        self.timer.start()

        self.data_prosessing_thr.FS = int(self.FS_for_FFT.text())
        self.data_prosessing_thr.TIMER_INTERVAL = self.TIMER_INTERVAL
        self.data_prosessing_thr.start()

# ------ Timer1 ---------------------------------------------------------------

    def timerEvent(self):
        self.progress_value += self.TIMER_INTERVAL/1000
        self.progress_bar.setValue(int(self.progress_value))
        self.logger.info(f"Progress: {self.progress_value}")
        # self.Serial.readyRead.connect(
        #     self.read_serial,
        #     QtCore.Qt.ConnectionType.SingleShotConnection)
        self.read_serial()

    def read_serial(self):
        if (bytes_num := self.Serial.bytesAvailable()) <= 14:
            self.logger.warning(f"No data from {
                self.com_list_widget.currentText()}")
            return
        if self.data_prosessing_thr.flag_recieve:
            self.logger.info("thread still work with previous datad!")
            return

        self.exp_package_num += int(bytes_num/14)
        self.logger.info(
            f"ready to read, bytes num = {bytes_num}, \
expected package num {self.exp_package_num}")
        self.data_prosessing_thr.rx = self.Serial.readAll().data()
        # self.Serial.flush()
        self.data_prosessing_thr.flag_recieve = True
        self.logger.info(f"thread_start, count = {self.count}")

# ------- Timer2 --------------------------------------------------------------

    def timer_event_sent_com(self):
        # if not self.Serial.isOpen():
        #     self.text_logs.append(
        #         line := ">>> " + str(time.strftime("%H:%M:%S")) +
        #         " COM isn't open")
        #     self.logger.info(line)
        #     return
        self.logger.info(f"---sent_command--- Open? {self.Serial.isOpen()}")
        if self.flag_sent:
            if self.count >= len(self.list_time):
                if self.current_cylce < self.total_cycle_num:
                    self.cycle_end()
                else:
                    self.stop()
                    return

            self.list_view_from_file.setCurrentIndex(
                self.list_data_from_file_widget.index(self.count))
            self.sent_command()
            self.flag_sent = False
        else:
            self.Serial.write(bytes([0, 0, 0, 0, 0, 0, 0, 0]))
            self.timer_sent_com.setInterval(self.PAUSE_INTERVAL_MS)
            self.flag_sent = True
        self.logger.info("---end_sent_command")
        self.data_prosessing_thr.flag_sent = self.flag_sent

    def sent_command(self):
        F = int.to_bytes(self.list_freq[self.count],
                         length=2, byteorder='little', signed=False)
        A = int.to_bytes(self.list_amp[self.count],
                         length=2, byteorder='little', signed=False)

        self.Serial.write(
            bytes([77, 0, F[0], F[1], A[0], A[1], 0, 0]))
        self.logger.info("- Command was sent -")
        self.timer_sent_com.setInterval(
            self.list_time[self.count] * 1000)
        self.count += 1

# --------------------------------------------------------------------------------

    def cycle_end(self):
        # self.text_logs.append(
        self.logger.warning("End of cycle "
                            + str(self.current_cylce) + " of " +
                            str(self.total_cycle_num))

        self.current_cylce += 1
        self.count = 0

    def stop(self):
        self.avaliable_butttons(False)
        if self.timer_sent_com.isActive():
            self.timer_sent_com.stop()

        if self.timer.isActive():
            self.timer.stop()
            # self.text_logs.append(
            #     line :=
            #     ">>> " + str(time.strftime("%H:%M:%S")) +
            #     " End of measurements\n")
            # print(line)
            self.logger.warning("End of measurements\n")

        if self.Serial.isOpen():
            self.Serial.write(bytes([0, 0, 0, 0, 0, 0, 0, 0]))
            print(
                line := "COM close? " +
                str(self.Serial.waitForBytesWritten(1000)))
            self.logger.info(line)
            self.Serial.close()

        self.data_prosessing_thr.flag_start = False

###############################################################################
    def plot_show(self):
        if self.sender().objectName() == "show_graph_1":
            if self.curve_gyro1.isVisible():
                self.curve_gyro1.hide()
            else:
                self.curve_gyro1.show()
            return

        if self.sender().objectName() == "show_graph_2":
            if self.curve_gyro2.isVisible():
                self.curve_gyro2.hide()
            else:
                self.curve_gyro2.show()
            return

        if self.sender().objectName() == "show_graph_3":
            if self.curve_gyro3.isVisible():
                self.curve_gyro3.hide()
            else:
                self.curve_gyro3.show()
            return

    def cycle_num_value_change(self):
        if not self.timer.isActive():  # is this required?
            self.total_cycle_num = self.cycle_num_widget.value()

    def progress_bar_set_max(self):
        if self.total_time and not self.timer.isActive():  # is this required?
            self.progress_bar.setMaximum(int(
                self.PAUSE_INTERVAL_MS/1000 + self.total_cycle_num *
                (self.total_time +
                 len(self.list_time) * self.PAUSE_INTERVAL_MS/1000)))
            self.progress_bar.setValue(0)

    def avaliable_butttons(self, flag_start: bool):
        self.start_button.setDisabled(flag_start)
        self.stop_button.setDisabled(not flag_start)
        self.choose_file.setDisabled(flag_start)

    def signal_from_thread(self, s):
        self.package_num = s
        self.logger.info(f"thread_stop, count = {self.count}\n\
package_num = {self.package_num}")
        self.package_number_label.setText(
            str(self.package_num))

        num_of_points_shown = 20000
        if self.package_num > num_of_points_shown:
            start_ind = self.package_num - num_of_points_shown
        else:
            start_ind = 0
        self.curve_gyro1.setData(
            self.data_prosessing_thr.all_data[start_ind:self.package_num, 0],
            self.data_prosessing_thr.all_data[start_ind:self.package_num, 2])
        self.curve_gyro2.setData(
            self.data_prosessing_thr.all_data[start_ind:self.package_num, 0],
            self.data_prosessing_thr.all_data[start_ind:self.package_num, 2]*2)
        # self.curve_3.setData(
        #     self.data_prosessing_thr.all_data[start_ind:self.package_num, 0],
        #     self.data_prosessing_thr.all_data[start_ind:self.package_num, 2]/2)

        # self.curve_3.setData(self.data_prosessing_thr.all_data[:, 2]/2)

        # self.data_for_fft_graph(
        #     self.data_prosessing_thr.all_data[:, 2],
        #     self.data_prosessing_thr.all_data[:, 2]*2,
        #     2000)

    # def data_for_fft_graph(self, encoder: np.ndarray, gyro: np.ndarray, Fs):
    #     # fft_data = np.array([]) 
        
    #     # self.i
        
    #     self.logger.info(f"flag_sent = {self.flag_sent}")
    #     if not self.flag_sent:
    #         self.flag_wait = True
    #         # self.logger.info(f"flag_wait = {self.flag_wait}, i= {self.i}")
    #         self.i += 1
    #         if self.i < 1*1000/self.TIMER_INTERVAL:
    #             self.bourder[0] = self.package_num
    #             # self.logger.info(f"bourder[0] = {self.bourder[0]}")
    #     if self.flag_wait:
    #         if self.flag_sent:
    #             self.flag_wait = False
    #             self.bourder[1] = self.package_num
    #             self.i = 0
    #             self.logger.info(f"\n\tbourders = {self.bourder}, self.count = {self.count}")

    #             [Amp, dPhase, Freq] = self.fft_data(
    #                 gyro[self.bourder[0]:self.bourder[1]],
    #                 encoder[self.bourder[0]:self.bourder[1]],
    #                 2000)

    #             self.amp_and_freq[(self.count - 1), :] = [Freq, Amp]
    #             self.time_plot.plot([self.bourder[0], self.bourder[1], self.bourder[0], self.bourder[1]],
    #                                 [-50000*Amp, 50000*Amp, 50000*Amp, -50000*Amp], pen='b', name="vsdfdsf1")
    #             self.curve_3.setData(self.amp_and_freq[:(self.count), 0], self.amp_and_freq[:(self.count), 1])
    #             print(self.amp_and_freq[:(self.count), :])

    # def fft_data(self, gyro: np.ndarray, encoder: np.ndarray, FS):
    #     #   AmpPhF Summary of this function goes here
    #     #   Detailed explanation goes here
    #     #   Amp [безразмерна¤]- соотношение амплитуд воздействи¤ (encoder)
    #     #   и реакции гироскопа(gyro) = gyro/encoder
    #     #   dPhase [радианы] - разница фаз = gyro - encoder
    #     #   Freq [√ц] - частота гармоники (воздействия)
    #     #   gyro [град/с] - показани¤ гироскопа во время гармонического воздействия
    #     #   encoder [град/с] - показани¤ энкодера, задающего гармоническое воздействие
    #     #   FS [√ц] - частота дискретизации

    #     # T = 1/FS
    #     L = len(gyro)  # L = size(gyro,1);  # длина записи
    #     # t = (0:L-1)*T  # вектор времени
    #     # t = np.arrange(0, L - 1, 1) * T
    #     NFFT = np.array([], dtype=int)
    #     next_power = np.ceil(np.log2(L))  # показатель степени 2 дл¤ числа длины записи
    #     NFFT = int(np.power(2, next_power))
    #     self.logger.info(f"\nNFFT {NFFT}, next_power {next_power}, len(gyro) {len(gyro)}")
    #     Yg = np.fft.fft(gyro, NFFT)/L  # преобразование Фурье сигнала гироскопа
    #     Ye = np.fft.fft(encoder, NFFT)/L  # преобразование Фурье сигнала энкодера
    #     f = FS/2 * np.linspace(0, 1, int(NFFT/2 + 1), endpoint=True)  # получение вектора частот
    #     self.logger.info(f"\nYe {Ye}\tYg {Yg}")
    #     #  delta_phase = asin(2*mean(encoder1.*gyro1)/(mean(abs(encoder1))*mean(abs(gyro1))*pi^2/4))*180/pi
    #     ng = np.argmax(Yg[0:int(NFFT/2)])
    #     Mg = 2*abs(Yg[ng])
    #     Freq = f[ng]
        
    #     ne = np.argmax(Ye[0:int(NFFT/2)])
    #     Me = 2*abs(Ye[ne])
    #     self.logger.info(f"\tMe {Me} \tMg {Mg}")

    #     dPhase = np.angle(Yg[ng], deg=False) - np.angle(Ye[ne], deg=False)
    #     Amp = Mg/Me
    #     self.logger.info(f"FFt results\tPhase {dPhase}\tAmp {Amp}\tFreq {Freq}")
    #     #  Amp = std(gyro)/std(encoder)% пошуму (метод —урова)
    #     with open("fft.txt", 'a') as file:
    #         np.savetxt(file, [Amp, dPhase, Freq], delimiter='\t', fmt='%d')
    #     return [Amp, dPhase, Freq]
#---------------------------------------------------------

    def combobox_changed(self, value):
        self.com_boderate_widget.setItemText(
            self.com_boderate_widget.currentIndex(), value)

    def plot_change(self):
        if self.fft_button.text() == "FFT":
            self.fft_button.setText("Time")
            self.time_plot.ctrl.fftCheck.setChecked(False)
            self.time_plot.setLabel(
                'bottom', 'Horizontal Values', units='smth')
        else:
            self.fft_button.setText("FFT")
            self.time_plot.ctrl.fftCheck.setChecked(True)
            self.time_plot.setLabel(
                'bottom', 'Frequency', units='Hz')

    def clear_logs(self):
        # self.text_logs.clear()
        self.log_text_box.widget.clear()
# -----------------------------------------------------------------------------

    def check_filename(self):
        filename = self.file_name.text()
        if not len(filename):
            filename = 'test'

        extension = '.txt'
        new_name = filename + extension
        i = 1
        while os.path.exists(new_name):
            new_name = filename + "(" + str(i) + ")" + extension
            i += 1
        self.data_prosessing_thr.filename = new_name
# -----------------------------------------------------------------------------

    def get_data_from_file(self):
        filename, filetype = QFileDialog.getOpenFileName(
            self,
            "Выберите методику измерений",
            ".",
            "Text Files(*.txt)")
        if not filename:
            return

        with open(filename, 'r') as f:
            self.file_name_and_path.setText(os.path.basename(filename))
            self.current_folder.setText(os.getcwd())
            Data = []
            self.list_freq = []
            self.list_amp = []
            self.list_time = []
            print("\n\n")
            for line in f:
                f_a_t = list(filter(None, re.split("F|A|T|\n", line)))
                if (len(f_a_t) == 3 and f_a_t[0].isdecimal() and
                    f_a_t[1].isdecimal() and f_a_t[2].isdecimal()):

                    self.list_freq.append(int(f_a_t[0]))
                    self.list_amp.append(int(f_a_t[1]))
                    self.list_time.append(int(f_a_t[2]))

                    Data.append(
                        f"F={f_a_t[0]}\tA={f_a_t[1]}\tT={f_a_t[2]}")

            self.total_time = sum(self.list_time)
            self.list_data_from_file_widget.setStringList(Data)
            self.progress_bar_set_max()

    def closeEvent(self, event):
        self.stop()
        self.settings.setValue(
            "COM_speed_list",
            [self.com_boderate_widget.itemText(i)
             for i in range(self.com_boderate_widget.count())])
        self.settings.setValue(
            "COM_index", self.com_boderate_widget.currentIndex())
        print("\nExit\n")
        self.logger.warning("\nExit\n")

# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------
#
###############################################################################
#
# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------


if __name__ == "__main__":

    # self.logger.basicConfig(level=logging.INFO,
    #                     filename="pyqt6_log.log", filemode="w",
    #                     format="%(asctime)s %(levelname)s %(message)s",
    #                     datefmt='%d-%b-%y %H:%M:%S')
    # logging.basicConfig(level=logging.INFO,
    #                     filename="pyqt6_logging.log", filemode="w",
    #                     format="%(asctime)s %(levelname)s %(message)s")
    # logging.disable(logging.INFO) # disable logging for certain level
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')  # 'Fusion' ... QtWidgets.QStyle
    window = MyWindow()
    window.setWindowTitle("Gyro")
    # window.resize(850, 500)
    window.show()
    sys.exit(app.exec())
