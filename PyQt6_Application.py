
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
from PyQt6.QtCore import QRunnable, Qt, QThreadPool
import pyqtgraph as pg
import numpy as np

# -------------------------------------------------------------------------------------------------------------------------------------------------------------
#
# -------------------------------------------------------------------------------------------------------------------------------------------------------------


class QTextEditLogger(logging.Handler):
    def __init__(self, parent):
        super().__init__()
        # self.widget = QtWidgets.QPlainTextEdit(parent)
        # self.widget.setReadOnly(True)

        self.widget = QtWidgets.QTextEdit(parent)
        self.widget.setReadOnly(True)
        # logging.basicConfig(level=logging.INFO,
        #                     filemode="w",
        #                     format="%(asctime)s %(levelname)s %(message)s",
        #                     datefmt='%d-%b-%y %H:%M:%S')

    def emit(self, record):
        msg = self.format(record)
        # self.widget.appendPlainText(msg)
        # self.widget.appendPlainText(msg)
        self.widget.append(msg)
        # self.logTextBox = QTextEditLogger(self)
        # self.logTextBox.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        # logging.getLogger().addHandler(self.logTextBox)


class MyWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):

        QtWidgets.QWidget.__init__(self, parent)

        QtWidgets.QApplication.setAttribute(
            QtCore.Qt.ApplicationAttribute.
            AA_UseStyleSheetPropagationInWidgetStyles,
            True)  # наследование свойств оформления потомков от родителей

        self.main_grid = QtWidgets.QGridLayout(self)   # главный контейнер
        # self.main_grid.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

###############################################################################
# ------ Com Settings ---------------------------------------------------------

        self.block1_com_param = QtWidgets.QGroupBox(
            "&Настройки порта")  # объект группы

        self.subblock1_com_param = QtWidgets.QFormLayout()

        self.com_list_widget = QtWidgets.QComboBox()
        self.available_ports = QSerialPortInfo.availablePorts()
        if self.available_ports:
            for self.port in self.available_ports:
                self.com_list_widget.addItem(self.port.portName())

        self.subblock1_com_param.addRow('COM:', self.com_list_widget)
        
        self.com_boderate_widget = QtWidgets.QComboBox()
        self.com_boderate_widget.setEditable(True)
        self.settings = QtCore.QSettings("COM_speed")
        if self.settings.contains("COM_speed_list"):
            self.com_boderate_widget.addItems(
                self.settings.value("COM_speed_list"))
        else:
            self.com_boderate_widget.addItems(["921600", "115200"])
        if self.settings.contains("COM_index"):
            self.com_boderate_widget.setCurrentIndex(
                self.settings.value("COM_index"))
        
        # self.com_boderate_widget = QtWidgets.QLineEdit()
        # self.settings = QtCore.QSettings("COM_speed")  # save settings
        # if self.settings.contains("COM_speed"):
        #     self.com_boderate_widget.setText(str(self.settings.value("COM_speed")))
        # else:
        #     self.com_boderate_widget.setText(str(self.settings.value("921600")))
        # self.com_boderate_widget.setInputMask("9900000")
        # self.subblock1_com_param.addWidget(self.com_boderate_widget)

        self.subblock1_com_param.addRow('&Speed:', self.com_boderate_widget)
        # self.COMparamBox.addRow(self.COMparamBox)

        # self.subblock1_com_param.setFieldGrowthPolicy(self.subblock1_com_param.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        # self.subblock1_com_param.setVerticalSpacing()
        # self.subblock1_com_param.setSizeConstraint(self.subblock1_com_param.SizeConstraint.SetMaximumSize)
        # self.subblock1_com_param.setSizeConstraint(self.subblock1_com_param.SizeConstraint.SetDefaultConstraint)
        self.block1_com_param.setLayout(self.subblock1_com_param)
        # self.block1_com_param.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
###############################################################################
# ------ File -----------------------------------------------------------------

        self.block2 = QtWidgets.QGroupBox("&Измерения")
        self.subblock2 = QtWidgets.QFormLayout()

        self.choose_file = QtWidgets.QPushButton(
            "Выбрать")

        # self.subblock2.addWidget(self._choose_file_)
        self.subblock2.addRow("&Файл\nцикла\nизмерений", self.choose_file)

        self.file_name_and_path = QtWidgets.QLineEdit()
        self.file_name_and_path.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.file_name_and_path.setReadOnly(True)
        self.subblock2.addWidget(self.file_name_and_path)
        self.subblock2.addRow("&Имя\nфайла:",
                              self.file_name_and_path)

        self.cycle_num_widget = QtWidgets.QSpinBox()
        self.cycle_num_widget.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.cycle_num_widget.setMinimum(1)
        self.subblock2.addWidget(self.cycle_num_widget)
        self.subblock2.addRow("&Количество\nциклов:",
                              self.cycle_num_widget)

        self.block2.setLayout(self.subblock2)
###############################################################################
# ------ File -----------------------------------------------------------------

        self.block3 = QtWidgets.QGroupBox("&Сохранение измерений")
        self.subblock3 = QtWidgets.QFormLayout()

        self.current_folder = QtWidgets.QLineEdit(os.getcwd())
        self.current_folder.setReadOnly(True)
        self.subblock3.addWidget(self.current_folder)
        self.subblock3.addRow("&Папка:", self.current_folder)

        self.file_name = QtWidgets.QLineEdit("test")
        self.subblock3.addWidget(self.file_name)
        self.subblock3.addRow("&<b>Имя файла:</b>", self.file_name)

        self.block3.setLayout(self.subblock3)

##############################################################################
# ------ Logger ---------------------------------------------------------------

        self.log_text_box = QTextEditLogger(self)
        # self.logTextBox.setFormatter(
        #   logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(self.log_text_box)
        # You can control the logging level
        # logging.getLogger().setLevel(logging.INFO)
        # logging.getLogger().setLevel(logging.WARNING)

# ------ Output logs and data from file ---------------------------------------

        self.block1right = QtWidgets.QGroupBox("")
        self.subblock1right = QtWidgets.QFormLayout()

        self.list_data_from_file_widget = QtCore.QStringListModel(self)
        self.list_view_from_file = QtWidgets.QListView(self)
        self.list_view_from_file.setModel(self.list_data_from_file_widget)

        self.subblock1right = QtWidgets.QFormLayout()
        # self.subblock1right.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.text_logs = QtWidgets.QTextEdit()
        self.text_logs.setReadOnly(True)

        self.subblock1right.addRow("&Содержимое\nфайла",
                                   self.list_view_from_file)
        # self.subblock1right.addRow("&Logs:", self.text_logs)
        self.subblock1right.addRow("&Logs:",
                                   self.log_text_box.widget)
        self.subblock1right.addRow(self.subblock1right)

        self.clear_button = QtWidgets.QPushButton("&Clear logs")
        self.subblock1right.addWidget(self.clear_button)

        self.start_button = QtWidgets.QPushButton("&START")
        # self.subblock1right.addWidget(self._start_button_)

        self.stop_button = QtWidgets.QPushButton("&STOP")
        self.stop_button.setDisabled(True)
        # self.subblock1right.addWidget(self._stop_button_)

        self.block1right.setLayout(self.subblock1right)
###############################################################################
# ------ PLot -----------------------------------------------------------------

        self.block1rightright = QtWidgets.QGroupBox("&График")
        self.subblock1rightright = QtWidgets.QFormLayout()

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(1)
        self.progress_bar.setFormat('%v/%m sec')

        self.subblock1rightright.addWidget(self.progress_bar)

        self.package_number_label = QtWidgets.QLabel("Package number")
        self.subblock1rightright.addWidget(self.package_number_label)
        self.package_number_label = QtWidgets.QLabel()
        self.subblock1rightright.addWidget(self.package_number_label)

        self.show_graph_1 = QtWidgets.QCheckBox("Line 1")
        self.show_graph_1.setObjectName("show_graph_1")
        self.subblock1rightright.addWidget(self.show_graph_1)
        self.show_graph_2 = QtWidgets.QCheckBox("Line 2")
        self.show_graph_2.setObjectName("show_graph_2")
        self.subblock1rightright.addWidget(self.show_graph_2)
        self.show_graph_3 = QtWidgets.QCheckBox("Line 3")
        self.show_graph_3.setObjectName("show_graph_3")
        self.subblock1rightright.addWidget(self.show_graph_3)

        self.time_plot = pg.plot()
        # self.time_plot.QSizePolicy
        self.time_plot.showGrid(x=True, y=True)

        self.time_plot.addLegend()
        self.time_plot.setLabel('left', 'Velosity Amplitude', units='smth')
        self.time_plot.setLabel('bottom', 'Horizontal Values', units='smth')
        self.curve = []
        self.curve = self.time_plot.plot(pen='r')
        arr = np.array([1, 3, 4])
        arr2 = np.array([3, 5, 6])
        arr3 = np.array([5, 6, 7])
        self.curve[0].setData(arr)
        self.curve.setData(arr2)
        # self.curve.setData[0](arr)
        # self.curve.setData[1](np.array([4, 2, 3]))
        self.subblock1rightright.addWidget(self.time_plot)
        self.time_plot.getPlotItem().ctrl.fftCheck.setChecked(False) # fft

        self.fft_button = QtWidgets.QPushButton("&Time")
        self.subblock1rightright.addWidget(self.fft_button)

        # self.subblock1rightright.setSizeConstraint(
        #   self.subblock1rightright.SizeConstraint.SetMaximumSize)
        self.block1rightright.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding)
        self.block1rightright.setLayout(self.subblock1rightright)

# ------ Set main grid --------------------------------------------------------

        self.main_grid.addWidget(self.block1_com_param, 0, 0, 1, 1)
        self.main_grid.addWidget(self.block2, 1, 0, 1, 1)
        self.main_grid.addWidget(self.block3, 2, 0, 3, 1)

        self.main_grid.addWidget(self.block1right, 0, 1, 3, 1)
        self.main_grid.addWidget(self.start_button, 3, 1, 1, 1)
        self.main_grid.addWidget(self.stop_button, 4, 1, 1, 1)

        self.main_grid.addWidget(self.block1rightright, 0, 3, 5, 2)

        # self.main_grid.addWidget(self.log_text_box.widget, 0, 5, 5, 20)

        self.setLayout(self.main_grid)
        # self.main_grid.setSizeConstraint(
        #     self.main_grid.SizeConstraint.SetDefaultConstraint)

# ------ Style ----------------------------------------------------------------

        # self.block1_com_param.setObjectName("group1")
        # self.subblock1_com_param.setObjectName("group1")
        self.stop_button.setObjectName("stop_button")
        # self.choose_file.setObjectName("choose_file")
        self.start_button.setObjectName("start_button")
        with open("StyleSheets.css", "r") as StyleSheetsFile:
            self.setStyleSheet(StyleSheetsFile.read())

        app_icon = QtGui.QIcon()
        app_icon.addFile('Vibro_1_resources/icon_16.png', QtCore.QSize(16, 16))
        app_icon.addFile('Vibro_1_resources/icon_24.png', QtCore.QSize(24, 24))
        app_icon.addFile('Vibro_1_resources/icon_32.png', QtCore.QSize(32, 32))
        app_icon.addFile('Vibro_1_resources/icon_48.png', QtCore.QSize(48, 48))
        app.setWindowIcon(app_icon)

# ------ Connect --------------------------------------------------------------

        self.start_button.clicked.connect(self.start) # test_serail  start
        self.stop_button.clicked.connect(self.stop)
        self.clear_button.clicked.connect(self.clear_logs)
        self.choose_file.clicked.connect(self.get_data_from_file)
        self.cycle_num_widget.valueChanged.connect(self.cycle_num_value_change)
        self.cycle_num_widget.valueChanged.connect(self.progress_bar_set_max)
        self.fft_button.clicked.connect(self.plot_change)
        self.com_boderate_widget.currentTextChanged.connect(
            self.combobox_changed)
        self.show_graph_1.stateChanged.connect(self.plot_show)
        self.show_graph_2.stateChanged.connect(self.plot_show)
        self.show_graph_3.stateChanged.connect(self.plot_show)
        # self.sender()
# ------ Timres ---------------------------------------------------------------

        self.timer = QtCore.QTimer()
        self.timer_interval = 125*2
        self.timer.setInterval(self.timer_interval)
        self.timer.timeout.connect(self.timerEvent)

        self.timer_sent_com = QtCore.QTimer()
        self.timer_sent_com.setTimerType(QtCore.Qt.TimerType.PreciseTimer)
        self.timer_sent_com.timeout.connect(self.timer_event_sent_com)

# ------ Init vars ------------------------------------------------------------

        self.count = 0
        self.progress_bar_value = 0
        self.total_time = 0
        self.total_cycle_num = 1

        self.data_prosessing_thr = PyQt6_Thread.MyThread()  # create thread
        self.Serial = QSerialPort()
        self.Serial.setDataBits(
                QSerialPort.DataBits.Data8)
        self.Serial.setParity(
                QSerialPort.Parity.NoParity)
        self.Serial.setStopBits(
                QSerialPort.StopBits.OneStop)
        self.data_prosessing_thr.sec_count.connect(self.signal_from_thread)

        logging.getLogger().setLevel(logging.INFO)
        logging.info(f"Start")
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
        
        self.time_plot.clear()
        self.progress_bar.setValue(0)
        self.progress_value = 0
        self.count = 0
        self.current_cylce = 1
        self.data_prosessing_thr.package_num = 0
        self.flag_sent = False
        self.data_prosessing_thr.flag_start = True
        
        logging.info(F"PORT: {(self.com_list_widget.currentText())}\n")
        if not len(self.com_list_widget.currentText()):
            self.available_ports = QSerialPortInfo.availablePorts()
            for port in self.available_ports:
                self.com_list_widget.addItem(port.portName())
                logging.info(F"PORT: {(self.com_list_widget.currentText())}\n")
        if not len(self.com_list_widget.currentText()):
            logging.info("Can't find COM port")
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
                logging.info("No data from file")
                return
        
        logging.info("Data from file was loaded")

        if not self.Serial.open(QtCore.QIODevice.OpenModeFlag.ReadWrite):
            logging.info(f"Can't open {self.com_list_widget.currentText()}")
            return

        self.cycle_num_value_change()
        self.progress_bar_set_max()
        self.avaliable_butttons(True)

        # self.timer.setInterval(self.timer_interval)
        logging.info(line := f"{self.com_list_widget.currentText()} open")
        logging.info(line := f"self.cycleNum = {self.total_cycle_num}")
        # self.text_logs.append(line := f">>> {time.strftime("%H:%M:%S")} Start")
        # logging.info(line)
        # logging.warning(line)

        self.Serial.clear()
        self.Serial.flush()
        # self.timer.setInterval(0)
        self.timer.start()
        self.timer_sent_com.setInterval(0)
        self.timer_sent_com.start()

        self.data_prosessing_thr.start()

# ------ Timer1 ---------------------------------------------------------------

    def timerEvent(self):
        self.progress_value += self.timer_interval/1000
        self.progress_bar.setValue(int(self.progress_value))
        logging.info(f"Progress: {self.progress_value}")
        # self.Serial.readyRead.connect(
        #     self.read_serial,
        #     QtCore.Qt.ConnectionType.SingleShotConnection)
        self.read_serial()

    def read_serial(self):
        if (bytes_num := self.Serial.bytesAvailable()) <= 14:
            logging.info("no data from COM port!")
            # logging.warning(f"> {time.strftime("%H:%M:%S")} No data from {self.com_list_widget.currentText()}")
            return
        if self.data_prosessing_thr.flag_recieve:
            logging.info("thread still work with previous datad!")
            return

        self.exp_package_num += int(bytes_num/14)
        logging.info(
            f"ready to read, bytes num = {bytes_num}, \
expected package num {self.exp_package_num}")
        self.data_prosessing_thr.rx = self.Serial.readAll().data()
        # self.Serial.flush()
        self.data_prosessing_thr.flag_recieve = True
        logging.info(f"thread_start, count = {self.count}")

# ------- Timer2 --------------------------------------------------------------

    def timer_event_sent_com(self):
        # if not self.Serial.isWritable():
        #     self.text_logs.append(
        #         line := ">>> " + str(time.strftime("%H:%M:%S")) +
        #         " Cannot sent data")
        #     logging.info(line)
        #     return
        # if not self.Serial.isOpen():
        #     self.text_logs.append(
        #         line := ">>> " + str(time.strftime("%H:%M:%S")) +
        #         " COM isn't open")
        #     logging.info(line)
        #     return

        logging.info(f"---sent_command--- Open? {self.Serial.isOpen()}")
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
            self.timer_sent_com.setInterval(1000)
            self.flag_sent = True

    def sent_command(self):
        F_H = self.list_freq[self.count] >> 8
        F_L = self.list_freq[self.count] & (0xFF)
        A_H = self.list_amp[self.count] >> 8
        A_L = self.list_amp[self.count] & (0xFF)

        self.Serial.write(
            bytes([77, 0, F_L, F_H, A_L, A_H, 0, 0]))
        logging.info("- Command was sent -")
        self.timer_sent_com.setInterval(
            self.list_time[self.count] * 1000)
        self.count += 1

# --------------------------------------------------------------------------------

    def cycle_end(self):
        self.text_logs.append(
            line :=
            ">>> " + str(time.strftime("%H:%M:%S")) + " End of cycle "
            + str(self.current_cylce) + " of " +
            str(self.total_cycle_num))
        logging.info(line)
        logging.warning(line)

        self.current_cylce += 1
        self.count = 0

    def stop(self):
        self.data_prosessing_thr.flag_start = False

        self.avaliable_butttons(False)
        if self.timer_sent_com.isActive():
            self.timer_sent_com.stop()

        if self.timer.isActive():
            self.timer.stop()
            self.text_logs.append(
                line :=
                ">>> " + str(time.strftime("%H:%M:%S")) +
                " End of measurements\n")
            # print(line)
            logging.info(line)
            logging.warning(line)

        if self.Serial.isOpen():
            self.Serial.write(bytes([0, 0, 0, 0, 0, 0, 0, 0]))
            print(
                line := "COM close? " +
                str(self.Serial.waitForBytesWritten(1000)))
            logging.info(line)
            self.Serial.close()
        
###############################################################################
    def plot_show(self):
        # print(self.sender().findChild())
        print(self.sender().objectName())
        if self.sender().objectName() == "show_graph_1":
            print(self.sender())
        if self.sender().objectName() == "show_graph_2":

            if self.time_plot.isVisible():
                self.time_plot.hide() 
            else:
                self.time_plot.show()

        if self.sender().objectName() == "show_graph_3":
            print(self.sender())

    def cycle_num_value_change(self):
        if not self.timer.isActive(): # is this required?
            self.total_cycle_num = self.cycle_num_widget.value()

    def progress_bar_set_max(self):
        if self.total_time and not self.timer.isActive(): # is this required?
            self.progress_bar.setMaximum(
                (self.total_time + len(self.list_time)) * self.total_cycle_num + 1)
            self.progress_bar.setValue(0)

    def avaliable_butttons(self, flag_start: bool):
        self.start_button.setDisabled(flag_start)
        self.stop_button.setDisabled(not flag_start)
        self.choose_file.setDisabled(flag_start)

    def signal_from_thread(self, s):  # по этому сигналу можно в логи писать
        logging.info(f"thread_stop, count = {self.count}\n\
package_num = {self.data_prosessing_thr.package_num}")
        self.package_number_label.setText(
            str(self.data_prosessing_thr.package_num))

        
        # self.pen1 = pg.mkPen(color='r')
        # name1 = "1"
        # self.pen2 = pg.mkPen(color='g')
        # name2 = "2"
        # self.pen3 = pg.mkPen(color='g')
        # name3 = "3"
        # self.time_plot.plot(
        #     self.data_prosessing_thr.nums_united[:, 0],
        #     self.data_prosessing_thr.nums_united[:, 2],
        #     pen=self.pen1, name=name1)
        # self.time_plot.plot(
        #     self.data_prosessing_thr.nums_united[:, 0],
        #     self.data_prosessing_thr.nums_united[:, 2]/2,
        #     pen=self.pen2, name=name2)
        # self.time_plot.plot(
        #     self.data_prosessing_thr.nums_united[:, 0],
        #     self.data_prosessing_thr.nums_united[:, 2]/4,
        #     pen=self.pen3, name=name3)
            #pen=(255, 0, 0), name="Red curve")
        
        # self.time_plot.plot(
        #     self.data_prosessing_thr.nums_united[:, 0],
        #     self.data_prosessing_thr.nums_united[:, 2]/2,
        #     pen=(0, 255, 0), name="Red curve")
        # self.time_plot.setData(
        #     self.data_prosessing_thr.nums_united[:, 0],
        #     self.data_prosessing_thr.nums_united[:, 2]/2,
        #     pen=(0, 255, 0), name="Red curve")

            # curve.setData
        
    def combobox_changed(self, value):
        self.com_boderate_widget.setItemText(
            self.com_boderate_widget.currentIndex(), value)

    def plot_change(self):
        if self.fft_button.text() == "FFT":
            self.fft_button.setText("Time")
            self.time_plot.getPlotItem().ctrl.fftCheck.setChecked(False)
            self.time_plot.setLabel('bottom', 'Horizontal Values', units='smth')
        else:
            self.fft_button.setText("FFT")
            self.time_plot.getPlotItem().ctrl.fftCheck.setChecked(True)
            self.time_plot.setLabel('bottom', 'Frequency', units='Hz')

    def clear_logs(self):
        self.text_logs.clear()
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
                if (f_a_t := list(filter(None, re.split("F|A|T|\n", line)))):
                    if (len(f_a_t) == 3 and f_a_t[0].isdecimal()
                        and f_a_t[1].isdecimal() and f_a_t[2].isdecimal()):

                        self.list_freq.append(int(f_a_t[0]))
                        self.list_amp.append(int(f_a_t[1]))
                        self.list_time.append(int(f_a_t[2]))

                        Data.append(f"F={f_a_t[0]} A={f_a_t[1]} T={f_a_t[2]}")

            self.total_time = sum(self.list_time)

            self.list_data_from_file_widget.setStringList(Data)
            self.progress_bar_set_max()
            # self.list_view_from_file.setSelectionRectVisible(True)

    def closeEvent(self, event):
        self.stop()
        # self.settings.setValue("COM_speed", self.com_boderate_widget.text())
        self.settings.setValue(
            "COM_speed_list",
            [self.com_boderate_widget.itemText(i)
             for i in range(self.com_boderate_widget.count())])
        self.settings.setValue(
            "COM_index", self.com_boderate_widget.currentIndex())
        print("\nExit\n")
        logging.info("\nExit\n")
        logging.warning("\nExit\n")

# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------
#
###############################################################################
#
# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------


if __name__ == "__main__":

    # logging.basicConfig(level=logging.INFO,
    #                     filename="pyqt6_log.log", filemode="w",
    #                     format="%(asctime)s %(levelname)s %(message)s",
    #                     datefmt='%d-%b-%y %H:%M:%S')
    logging.basicConfig(level=logging.INFO,
                        filename="pyqt6_log.log", filemode="w",
                        format="%(asctime)s %(levelname)s %(message)s")
    # logging.disable(logging.INFO) # disable logging for certain level
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion') # 'Fusion' ... QtWidgets.QStyle
    window = MyWindow()
    window.setWindowTitle("Gyro")
    # window.resize(850, 500)
    window.show()
    sys.exit(app.exec())
