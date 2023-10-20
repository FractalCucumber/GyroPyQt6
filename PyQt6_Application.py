
import logging
import numpy
import sys

from PyQt6.QtWidgets import QFileDialog
# from PyQt6.QtWidgets import QDialog, QApplication, QFileDialog
# import PyQt6.QtSerialPort  # лучше использовать эту
# from PyQt6.QtCore import pyqtSignal, QThread, QIODevice
# import serial.tools.list_ports
import os
import re
import time
# import numpy
# import pyqtgraph
# from pyqtgraph.Qt import QtCore, QtGui
from PyQt6.QtSerialPort import QSerialPort, QSerialPortInfo
from PyQt6 import QtGui
from datetime import datetime
from PyQt6 import QtWidgets, QtCore
# , QtGui
from pyqtgraph import PlotWidget, plot
# import matplotlib
# import PyQt6.QtSerialPort
import PyQt6_Thread
import PyQt6_QRunnable
from PyQt6.QtCore import QRunnable, Qt, QThreadPool
# import StyleSheets as Style

# -------------------------------------------------------------------------------------------------------------------------------------------------------------
#
# -------------------------------------------------------------------------------------------------------------------------------------------------------------


class QTextEditLogger(logging.Handler):
    def __init__(self, parent):
        super().__init__()
        self.widget = QtWidgets.QPlainTextEdit(parent)
        self.widget.setReadOnly(True)
        # logging.basicConfig(level=logging.INFO,
        #                     filemode="w",
        #                     format="%(asctime)s %(levelname)s %(message)s",
        #                     datefmt='%d-%b-%y %H:%M:%S')

    def emit(self, record):
        msg = self.format(record)
        self.widget.appendPlainText(msg)

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

###############################################################################

###############################################################################

        self.main_grid = QtWidgets.QGridLayout(self)   # главный контейнер
        self.main_grid.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
###############################################################################
        self.block1_com_param = QtWidgets.QGroupBox(
            "&Настройки порта")  # объект группы

        self.subblock1_com_param = QtWidgets.QFormLayout()

        self.com_name = QtWidgets.QComboBox()
        self.available_ports = QSerialPortInfo.availablePorts()
        if self.available_ports:
            for self.port in self.available_ports:
                self.com_name.addItem(self.port.portName())

        self.subblock1_com_param.addRow('COM:', self.com_name)

        self.com_boderate = QtWidgets.QLineEdit()

        self.settings = QtCore.QSettings("COM_speed")  # save settings
        if self.settings.contains("COM_speed"):
            self.com_boderate.setText(str(self.settings.value("COM_speed")))
        else:
            self.com_boderate.setText(str(self.settings.value("921600")))

        self.com_boderate.setInputMask("9900000")
        self.subblock1_com_param.addWidget(self.com_boderate)

        self.subblock1_com_param.addRow('&Speed:', self.com_boderate)
        # self.COMparamBox.addRow(self.COMparamBox)

        # self.subblock1_com_param.setFieldGrowthPolicy(self.subblock1_com_param.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        # self.subblock1_com_param.setVerticalSpacing()
        # self.subblock1_com_param.setSizeConstraint(self.subblock1_com_param.SizeConstraint.SetMaximumSize)
        # self.subblock1_com_param.setSizeConstraint(self.subblock1_com_param.SizeConstraint.SetDefaultConstraint)
        self.block1_com_param.setLayout(self.subblock1_com_param)
        # self.block1_com_param.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
###############################################################################
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
##############################################################################
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
##############################################################################
##############################################################################
        self.block1right = QtWidgets.QGroupBox(" ")
        self.subblock1right = QtWidgets.QFormLayout()

        self.list_data_from_file_ = QtCore.QStringListModel(self)
        self.data_from_file = QtWidgets.QListView(self)
        self.data_from_file.setModel(self.list_data_from_file_)

        self.subblock1right = QtWidgets.QFormLayout()
        # self.subblock1right.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.text_logs = QtWidgets.QTextEdit()
        self.text_logs.setReadOnly(True)

        self.subblock1right.addRow("&Содержимое\nфайла", self.data_from_file)
        self.subblock1right.addRow("&Logs:", self.text_logs)
        self.subblock1right.addRow(self.subblock1right)

        self.clear_button = QtWidgets.QPushButton("&Clear logs")
        self.subblock1right.addWidget(self.clear_button)

        self.start_button = QtWidgets.QPushButton("&START")
        # self.subblock1right.addWidget(self._start_button_)

        self.stop_button = QtWidgets.QPushButton("&STOP")
        self.stop_button.setDisabled(True)
        # self.subblock1right.addWidget(self._stop_button_)

        self.block1right.setLayout(self.subblock1right)
##############################################################################
##############################################################################
##############################################################################
        self.block1rightright = QtWidgets.QGroupBox("&График")
        self.subblock1rightright = QtWidgets.QFormLayout()
        # self.view = view = pyqtgraph.PlotWidget()
        # self.curve = view.plot(name="Line")
        # self.curve = view.plotItem(name="Line")

        # self.random_array = numpy.random.random_sample(20)
        # # self.curve.setData(self.random_array)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setValue(1)
        self.progress_bar.setMaximum(1)
        self.progress_bar.setFormat('%v/%m sec')

        self.subblock1rightright.addWidget(self.progress_bar)

        self.package_number_label = QtWidgets.QLabel()
        self.subblock1rightright.addWidget(self.package_number_label)
    
        self.block1rightright.setLayout(self.subblock1rightright)
#########################################################################

        self.main_grid.addWidget(self.block1_com_param, 0, 0)
        self.main_grid.addWidget(self.block2, 1, 0)
        self.main_grid.addWidget(self.block3, 2, 0, 3, 1)
        self.main_grid.addWidget(self.block1right, 0, 1, 3, 1)
        self.main_grid.addWidget(self.start_button, 3, 1, 1, 1)
        self.main_grid.addWidget(self.stop_button, 4, 1, 1, 1)
        self.main_grid.addWidget(self.block1rightright, 0, 3, 5, 1)

        self.logTextBox = QTextEditLogger(self)
        # self.logTextBox.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(self.logTextBox)
        # You can control the logging level
        logging.getLogger().setLevel(logging.INFO)
        self.main_grid.addWidget(self.logTextBox.widget, 0, 4, 2, 40)

        self.setLayout(self.main_grid)  # здесь работа с графикой закончена
        # self.main_grid.setSizeConstraint(
        #     self.main_grid.SizeConstraint.SetDefaultConstraint)

# ------------------------------------------------------------------------------------------------------------------------
        # Style

        # self.block1_com_param.setObjectName("group1")
        # self.subblock1_com_param.setObjectName("group1")
        self.stop_button.setObjectName("stop_button")
        # self.choose_file.setObjectName("choose_file")
        self.start_button.setObjectName("start_button")
        with open("StyleSheets.css", "r") as StyleSheetsFile:
            self.setStyleSheet(StyleSheetsFile.read())

        app_icon = QtGui.QIcon()
        # app_icon.addFile('Vibro_1_resources/icon_16.png', QtCore.QSize(16, 16))
        # app_icon.addFile('Vibro_1_resources/icon_24.png', QtCore.QSize(24, 24))
        # app_icon.addFile('Vibro_1_resources/icon_32.png', QtCore.QSize(32, 32))
        app_icon.addFile('Vibro_1_resources/icon_48.png', QtCore.QSize(48, 48))
        app.setWindowIcon(app_icon)

# ------------------------------------------------------------------------------------------------------------------------
        self.start_button.clicked.connect(self.start) # test_serail  start
        self.stop_button.clicked.connect(self.stop)
        self.clear_button.clicked.connect(self.clear_logs)
        self.choose_file.clicked.connect(self.get_data_from_file)
        self.cycle_num_widget.valueChanged.connect(self.cycle_num_value_change)
        self.cycle_num_widget.valueChanged.connect(self.progress_bar_set_max)

# ------------------------------------------------------------------------------------------------------------------------
        # # нужен pyqtgraph
        # self.view = view =
        #
        # self.win = self.GraphicsWindow()
        # self.graphWidget = self.view = pyqtgraph.PlotWidget()
        # self.graphWidget.setBackground('w')
        # self.plt = pyqtgraph.plot()
        # self.plt.showGrid(x = True, y = True)

        # self.layout = QtWidgets.QGridLayout()
        # self.widget.setLayout(self.layout)
        # self.MainGrid.addWidget(self.plt, 0, 1, 3, 1)
        # self.MainGrid.addWidget(self.layout, 0, 9)
        # self.graphWidget.plotItem([1, 2], [2, 4])
        # self.curve = self.view.plot(name="Line")
        # self.MainGrid.addPlot
# ------------------------------------------------------------------------------------------------------------------------
        self.timer = QtCore.QTimer()
        
        self.timer_interval = 125*2
        self.timer.setInterval(self.timer_interval)
        self.timer.timeout.connect(self.timerEvent)

        self.timer_sent_com = QtCore.QTimer()
        self.timer_sent_com.setTimerType(QtCore.Qt.TimerType.PreciseTimer)
        self.timer_sent_com.timeout.connect(self.timer_event_sent_com)
# ------------------------------------------------------------------------------------------------------------------------
        # self.cycle_num = 1
        # self.curr_cylce = 1

        self.count = 0
        self.pr_bar = 0
        # self.choose_file.setDisabled(True)
        self.list_freq = []
        self.list_amp = []
        self.list_time = []
        self.total_cycle_num = self.cycle_num_widget.value()

        self.data_prosessing_thr = PyQt6_Thread.MyThread()  # create thread

        self.data_prosessing_thr.Serial.setDataBits(
                QSerialPort.DataBits.Data8)
        self.data_prosessing_thr.Serial.setParity(
                QSerialPort.Parity.NoParity)
        self.data_prosessing_thr.Serial.setStopBits(
                QSerialPort.StopBits.OneStop)

        self.data_prosessing_thr.sec_count.connect(self.on_change)

        logging.info(f"Start")
# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------
#
#
###############################################################################
#
#
# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------
# 1

    def start(self):
        
        self.progress_bar.setValue(0)
        self.val = 0
        self.count = 0  # сброс счетчика принятых данных
        self.curr_cylce = 1
        self.available_ports = QSerialPortInfo.availablePorts()
        self.flag_sent = False
        self.data_prosessing_thr.package_num = 0
        
        print(F"PORT: {len(self.com_name.currentText())}\n")
        #
        if not len(self.com_name.currentText()):
            for port in self.available_ports:
                self.com_name.addItem(port.portName())
                print(F"PORT: {len(self.com_name.currentText())}\n")
        # self.data_prosessing_thread.Serial = self.Serial

        self.check_filename()
        if not len(self.list_time):
            # logging.info("No data from file")
            self.get_data_from_file()

        if len(self.list_time):
            logging.info("Data from file was loaded")
            
            self.data_prosessing_thr.Serial.setPortName(
                self.com_name.currentText())
            self.data_prosessing_thr.Serial.setBaudRate(
                int(self.com_boderate.text()))

            if self.data_prosessing_thr.Serial.open(QtCore.QIODevice.OpenModeFlag.ReadWrite):
                self.data_prosessing_thr.Serial.clear()
                self.data_prosessing_thr.Serial.flush()

                if self.data_prosessing_thr.Serial.isReadable():
                    print(line := f"{self.com_name.currentText()} open and readable")
                    logging.info(line)

                    self.cycle_num_value_change()
                    self.progress_bar_set_max()
                    self.avaliable_butttons(True)
                    # self.timer.setInterval(0)
                    self.timer.start()
                    
                    self.timer_sent_com.setInterval(0)
                    self.timer_sent_com.start()

                    # self.timer.setInterval(self.timer_interval)

                    print(line := f"self.cycleNum = {self.total_cycle_num}")
                    logging.info(line)

                    self.text_logs.append(line :=
                        ">>> " + str(time.strftime("%H:%M:%S")) + " Start")
                    logging.info(line)
                # else:
                #     self.text_logs.append(
                #         ">>> " + str(time.strftime("%H:%M:%S")) +
                #         " No data from COM port")

# ----------------------------------------------------------------------------
    def timerEvent(self):

        # self.data_prosessing_thr.Serial.readyRead.connect(
        #     self.read_serial,
        #     QtCore.Qt.ConnectionType.SingleShotConnection)
        # ffffffffffffffffffffffff
        self.read_serial()
        
    def read_serial(self):

        if not self.data_prosessing_thr.isRunning():
            print("ready to read ------ Число байтов " +
                str(self.data_prosessing_thr.Serial.bytesAvailable()))
            self.data_prosessing_thr.rx = self.data_prosessing_thr.Serial.readAll().data()
            self.data_prosessing_thr.start()
            logging.info(f"thread_start, count = {self.count}")
        else:
            logging.info("thread_still_running!")

# ------------------------------------------------------------------------------------
    def timer_event_sent_com(self):

        if self.flag_sent:
            self.sent_command()
            self.flag_sent = False
        else:
            self.data_prosessing_thr.Serial.write(bytes([0, 0, 0, 0, 0, 0, 0, 0]))
            self.timer_sent_com.setInterval(1000)
            self.flag_sent = True

    def sent_command(self):

        if self.count >= len(self.list_time):
            if self.curr_cylce < self.total_cycle_num:
                self.cycle_end()
            else:
                self.stop()
                return

        if self.data_prosessing_thr.Serial.isWritable():
            print(line := "---sent_command---")
            logging.info(line)

            F_H = self.list_freq[self.count] >> 8
            F_L = self.list_freq[self.count] & (0xFF)
            A_H = self.list_amp[self.count] >> 8
            A_L = self.list_amp[self.count] & (0xFF)

            self.data_prosessing_thr.Serial.write(
                bytes([77, 0, F_L, F_H, A_L, A_H, 0, 0]))
            self.timer_sent_com.setInterval(
                self.list_time[self.count] * 1000)
            self.count += 1
        else:
            self.text_logs.append(
                line := ">>> " + str(time.strftime("%H:%M:%S")) +
                " Cannot sent data")
            logging.info(line)
# --------------------------------------------------------------------------------

    def cycle_end(self):

        self.text_logs.append(
            line :=
            ">>> " + str(time.strftime("%H:%M:%S")) + " End of cycle "
            + str(self.curr_cylce) + " of " +
            str(self.total_cycle_num))
        logging.info(line)
        self.curr_cylce += 1
        self.count = 0

    def stop(self):

        self.avaliable_butttons(False)
        if self.timer_sent_com.isActive():
            self.timer_sent_com.stop()

        if self.timer.isActive():
            self.timer.stop()

            self.text_logs.append(
                line :=
                ">>> " + str(time.strftime("%H:%M:%S")) + " End of measurements")
            print(line)
            logging.info(line)

        if self.data_prosessing_thr.Serial.isOpen():
            self.data_prosessing_thr.Serial.write(bytes([0, 0, 0, 0, 0, 0, 0, 0]))
            print(
                line := "COM close? " +
                str(self.data_prosessing_thr.Serial.waitForBytesWritten(1000)))
            logging.info(line)
            self.data_prosessing_thr.Serial.close()

#################################################################################

    def cycle_num_value_change(self):

        if not self.timer.isActive(): # is this required?
            self.total_cycle_num = self.cycle_num_widget.value()

    def progress_bar_set_max(self):

        length = len(self.list_time)
        if length and not self.timer.isActive(): # is this required?
            self.progress_bar.setMaximum(
                (self.total_time + length) * self.total_cycle_num + 1)
            self.progress_bar.setValue(0)

    def avaliable_butttons(self, flag_start: bool):

        self.start_button.setDisabled(flag_start)
        self.stop_button.setDisabled(not flag_start)
        self.choose_file.setDisabled(flag_start)

    def on_change(self, s):  # по этому сигналу можно в логи писать

        logging.info(F"thread_stop, count = {self.count}")
        self.val += self.timer_interval/1000
        self.package_number_label.setText(
            str(self.data_prosessing_thr.package_num))
        print(self.data_prosessing_thr.package_num)
        self.progress_bar.setValue(int(self.val)) 

    def clear_logs(self):
        self.text_logs.clear()
# -----------------------------------------------------------------------------

    def check_filename(self):

        filename = self.file_name.text()
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
        if filename:
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
                        if len(f_a_t) == 3 and f_a_t[0].isdecimal() and f_a_t[1].isdecimal() and f_a_t[2].isdecimal():
                            self.list_freq.append(int(f_a_t[0]))
                            self.list_amp.append(int(f_a_t[1]))
                            self.list_time.append(int(f_a_t[2]))

                            Data.append(f"F={f_a_t[0]} A={f_a_t[1]} T={f_a_t[2]}")

                self.total_time = sum(self.list_time)

                # self.total_cycle_num = self.cycle_num_widget.value()

                self.list_data_from_file_.setStringList(Data)

                self.progress_bar_set_max()

                # self.list_data_from_file_.itemData(self, 2)
                # self.data_from_file.setSelectionRectVisible(True)
                # self.data_from_file.setSelectionModel()
                # self.data_from_file.selectionModel().selection()

                # theIndices = [1,3,5]
                # theQIndexObjects = [self.list_data_from_file_.createIndex(
                #               rowIndex, 0, 2) for rowIndex in theIndices]
                # for Qindex in theQIndexObjects:
                #     self.data_from_file.selectionModel().select(Qindex)

                # item = QtGui.QStandardltem(
                # QtGui.Qicon(iconfile),
                # lst[row])
                # sti. appendRow (item)

    def closeEvent(self, event):
        self.stop()
        self.settings.setValue("COM_speed", self.com_boderate.text())
        print("\n     Exit\n")

# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------
#
#
###############################################################################
#
#
# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO,
                        filename="pyqt6_log.log", filemode="w",
                        format="%(asctime)s %(levelname)s %(message)s",
                        datefmt='%d-%b-%y %H:%M:%S')
    # logging.disable(logging.INFO) # disable logging for certain level
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion') # 'Fusion' ... QtWidgets.QStyle
    window = MyWindow()
    window.setWindowTitle("Gyro")
    # window.resize(850, 500)
    window.show()
    sys.exit(app.exec())
