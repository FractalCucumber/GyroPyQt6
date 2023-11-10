import logging
import sys

from PyQt6.QtWidgets import QFileDialog
# from PyQt6.QtWidgets import QDialog, QApplication, QFileDialog
# from PyQt6.QtCore import pyqtSignal, QThread, QIODevice
import os
import re
# from pyqtgraph.Qt import QtCore, QtGui
from PyQt6.QtSerialPort import QSerialPort, QSerialPortInfo
from PyQt6 import QtGui
# from datetime import datetime
from PyQt6 import QtWidgets, QtCore
# import PyQt6_QRunnable
# from PyQt6.QtCore import QRunnable, Qt, QThreadPool
import pyqtgraph as pg
import numpy as np
import PyQt6_Logger
import PyQt6_Thread

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------


class CustomViewBox(pg.ViewBox):
    def __init__(self, *args, **kwds):
        kwds['enableMenu'] = False
        pg.ViewBox.__init__(self, *args, **kwds)
        self.setMouseMode(self.RectMode)
        
    # reimplement right-click to zoom out
    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.MouseButton.RightButton:
            self.autoRange()
    
    ## reimplement mouseDragEvent to disable continuous axis zoom
    def mouseDragEvent(self, ev, axis=None):
        if axis is not None and ev.button() == QtCore.Qt.MouseButton.RightButton:
            ev.ignore()
        else:
            pg.ViewBox.mouseDragEvent(self, ev, axis=axis)


class MyWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):

        QtWidgets.QWidget.__init__(self, parent)

        QtWidgets.QApplication.setAttribute(
            QtCore.Qt.ApplicationAttribute.
            AA_UseStyleSheetPropagationInWidgetStyles,
            True)  # наследование свойств оформления потомков от родителей

# ------ Timres ---------------------------------------------------------------

        self.timer_recieve = QtCore.QTimer()
        self.TIMER_INTERVAL = 125*2
        self.timer_recieve.setInterval(self.TIMER_INTERVAL)
        self.timer_recieve.timeout.connect(self.timerEvent)

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

        style_sheets_filename = "StyleSheets.css"
###############################################################################
        self.main_grid_layout = QtWidgets.QGridLayout(self)  # контейнер

# ------ Com Settings ---------------------------------------------------------

        self.com_param_groupbox = QtWidgets.QGroupBox(
            "Настройки порта")
        self.com_param_groupbox.setMaximumWidth(300)
        self.com_param_groupbox_layout = QtWidgets.QGridLayout()

        self.com_list_widget = QtWidgets.QComboBox()
        self.com_list_widget.setEditable(True)
        self.com_list_widget.lineEdit().setAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter)
        self.com_list_widget.lineEdit().setReadOnly(True)
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
        self.com_boderate_widget.lineEdit().setAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter)
        self.settings = QtCore.QSettings("COM_speed")
        if self.settings.contains("COM_speed_list"):
            self.com_boderate_widget.addItems(
                self.settings.value("COM_speed_list"))
        else:
            self.com_boderate_widget.addItems(['921600', '115200', '00000'])

        if self.settings.contains("COM_index"):
            self.com_boderate_widget.setCurrentIndex(
                self.settings.value("COM_index"))
        self.int_validator = QtGui.QIntValidator()
        self.com_boderate_widget.setValidator(self.int_validator)

        self.com_param_groupbox_layout.addWidget(QtWidgets.QLabel('Speed:'),
                                                 1, 0)
        self.com_param_groupbox_layout.addWidget(self.com_boderate_widget,
                                                 1, 1)
        # self.FS_for_FFT = QtWidgets.QComboBox()
        # self.FS_for_FFT.setEditable(True)
        # self.settings = QtCore.QSettings("COM_speed")
        # if self.settings.contains("FS_list"):
        #     self.FS_for_FFT.addItems(
        #         self.settings.value("FS_list"))
        # else:
        #     self.FS_for_FFT.addItems(['1000', '2000', 'xxx'])

        # if self.settings.contains("FS_index"):
        #     self.FS_for_FFT.setCurrentIndex(
        #         self.settings.value("FS_index"))

        self.FS_for_FFT = QtWidgets.QLineEdit("1000")
        self.FS_for_FFT.setValidator(self.int_validator)
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
            "Сохранение измерений")
        self.saving_measurements_groupbox.setMaximumWidth(300)
        self.saving_measurements_groupbox_layout = QtWidgets.QGridLayout()

        self.saving_measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel('Папка:'), 0, 0)
        self.current_folder = QtWidgets.QLineEdit(os.getcwd())
        self.current_folder.setReadOnly(True)
        self.saving_measurements_groupbox_layout.addWidget(
            self.current_folder, 0, 1)

        self.saving_measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel("<b>Имя файла:</b>"), 1, 0)
        self.file_name = QtWidgets.QLineEdit('test')
        self.saving_measurements_groupbox_layout.addWidget(
            self.file_name, 1, 1)
        self.saving_measurements_groupbox.setLayout(
            self.saving_measurements_groupbox_layout)

##############################################################################
# ------ Logger ---------------------------------------------------------------

        self.log_text_box = PyQt6_Logger.QTextEditLogger(self)
        self.logger = logging.getLogger('main')

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

        self.text_output_groupbox_layout.addRow("Содержимое\nфайла",
                                                self.list_view_from_file)
        self.text_output_groupbox_layout.addRow("Logs:",
                                                self.log_text_box.widget)
        self.text_output_groupbox_layout.addRow(
            self.text_output_groupbox_layout)

        self.clear_button = QtWidgets.QPushButton("Clear logs")
        self.text_output_groupbox_layout.addWidget(self.clear_button)

        self.start_button = QtWidgets.QPushButton("START")

        self.stop_button = QtWidgets.QPushButton("STOP")
        self.stop_button.setDisabled(True)

        self.text_output_groupbox.setLayout(self.text_output_groupbox_layout)
###############################################################################
# ------ PLot -----------------------------------------------------------------
######################################################################
        self.tab_widget = QtWidgets.QTabWidget() 
        self.tab_widget.addTab(QtWidgets.QLabel("Coдepжимoe вкладки l"), "Вкладка &l") 
        self.tab_widget.addTab(QtWidgets.QLabel("Coдepжимoe вкладки 2"), "Вкладка &2") 
        self.tab_widget.addTab(QtWidgets.QLabel("Coдepжимoe вкладки 3"), "Вкладка &3") 
        self.tab_widget.setCurrentIndex(0) 
        # vbox = QtWidgets.QVBoxLayout() 
        self.plot_groupbox_layout.addWidget(self.tab_widget) 
#########################################################
        self.plot_groupbox = QtWidgets.QGroupBox("График")
        self.plot_groupbox.setMinimumWidth(395)
        self.plot_groupbox_layout = QtWidgets.QGridLayout()

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(1)
        self.progress_bar.setFormat('%v/%m sec')
        self.plot_groupbox_layout.addWidget(self.progress_bar,
                                            3, 0, 1, 5)

        self.package_number_label = QtWidgets.QLabel("Package number:")
        self.plot_groupbox_layout.addWidget(self.package_number_label,
                                            3, 5, 1, 3)
        self.current_package_number_label = QtWidgets.QLabel()
        self.current_package_number_label.setText('0')
        self.plot_groupbox_layout.addWidget(self.current_package_number_label,
                                            3, 8, 1, 1)
# ---------------------------------------------------------------------------
        self.time_plot_item = pg.PlotItem(viewBox=CustomViewBox())
        self.time_plot_item.setTitle("Velosity Graph", size="12pt")
        self.time_plot_item.showGrid(x=True, y=True)
        label_style = {'color': '#FFF', 'font-size': '14px'}

        self.time_plot_item.addLegend(offset=(-1, 1), labelTextSize='12pt',
                                      labelTextColor=pg.mkColor('w'))
        # self.time_plot_item.addLegend().setLabelTextColor
        self.time_plot_item.setLabel('left', 'Velosity',
                                     units='degress*100 per second',
                                     **label_style)
        self.time_plot_item.setLabel('bottom', 'Time',
                                     units='seconds', **label_style)

        self.curve_encoder = self.time_plot_item.plot(pen='w', name="encoder")
        self.curve_gyro1 = self.time_plot_item.plot(pen='r', name="gyro 1")
        self.curve_gyro2 = self.time_plot_item.plot(pen='g', name="gyro 2")
        self.curve_gyro3 = self.time_plot_item.plot(pen='b', name="gyro 3")

        self.curve_gyro_rectangle = self.time_plot_item.plot()

        self.region = pg.LinearRegionItem([0, 1])
        self.time_plot_item.addItem(self.region)
        # self.region.setRegion([0, 2])
        self.region.setMovable(False)

        # self.curve_gyro1.setData([0, 0, 1, 1, 0], [0, 1, 1, 0, 0])
        # self.curve_gyro1.appendData([3, 4], [3, 7])
        # self.curve_gyro1.setData([2, 1, 3, 4, 5], [2, 4, 6, 8, 10])
# -----------------------------------------------------------------------------
        self.amp_plot_item = pg.PlotItem(viewBox=CustomViewBox())
        self.amp_plot_item.setTitle("Amp Graph", size="12pt")
        self.amp_plot_item.showGrid(x=True, y=True)

        self.amp_plot_item.addLegend(offset=(-1, 1), labelTextSize='12pt',
                                     labelTextColor=pg.mkColor('w'))
        self.amp_plot_item.setLabel('left', 'Amplitude',
                                    units='', **label_style)
        self.amp_plot_item.setLabel('bottom', 'Frequency',
                                    units='Hz', **label_style)
        symbol_size = 6
        self.amp_curve_gyro1 = self.amp_plot_item.plot(
            pen='r', name="gyro 1", symbol="o",
            symbolSize=symbol_size, symbolBrush='r')
        self.amp_curve_gyro2 = self.amp_plot_item.plot(
            pen='g', name="gyro 2", symbol="o",
            symbolSize=symbol_size, symbolBrush='g')
        self.amp_curve_gyro3 = self.amp_plot_item.plot(
            pen='b', name="gyro 3", symbol="o",
            symbolSize=symbol_size, symbolBrush='b')
# ----------------------------------------------------------------------------
        self.phase_plot_item = pg.PlotItem(viewBox=CustomViewBox())
        self.phase_plot_item.setTitle("Phase Graph", size="12pt")
        self.phase_plot_item.showGrid(x=True, y=True)

        self.phase_plot_item.addLegend(offset=(-1, 1), labelTextSize='12pt',
                                       labelTextColor=pg.mkColor('w'))

        self.phase_plot_item.setLabel('left', 'Phase',
                                      units='', **label_style)
        self.phase_plot_item.setLabel('bottom', 'Frequency',
                                      units='Hz', **label_style)
        self.phase_curve_gyro1 = self.phase_plot_item.plot(
            pen='r', name="gyro 1", symbol="o",
            symbolSize=symbol_size, symbolBrush='r')
        self.phase_curve_gyro2 = self.phase_plot_item.plot(
            pen='g', name="gyro 2", symbol="o",
            symbolSize=symbol_size, symbolBrush='g')
        self.phase_curve_gyro3 = self.phase_plot_item.plot(
            pen='b', name="gyro 3", symbol="o",
            symbolSize=symbol_size, symbolBrush='b')

        # self.phase_curve_gyro1.setData([0, 0, 1, 1, 0], [0, 1, 1, 0, 0])
#  ----------------------------------------------------------------------------
# pw = pg.PlotWidget(viewBox=vb, enableMenu=False)
        self.time_plot = pg.PlotWidget(plotItem=self.time_plot_item, enableMenu=False)
        self.spectrum_button = QtWidgets.QPushButton("FFT (doesn't work)")
        # 
        self.amp_plot = pg.PlotWidget(plotItem=self.amp_plot_item)
        self.phase_plot = pg.PlotWidget(plotItem=self.phase_plot_item)
        self.amp_plot.hide()
        self.phase_plot.hide()

        self.plot_groupbox_layout.addWidget(self.time_plot,
                                            0, 0, 1, 9)
        self.plot_groupbox_layout.addWidget(self.spectrum_button,
                                            1, 0, 1, 9)
        self.plot_groupbox_layout.addWidget(self.amp_plot,
                                            0, 0, 1, 9)
        self.plot_groupbox_layout.addWidget(self.phase_plot,
                                            1, 0, 1, 9)
        self.show_fft_button = QtWidgets.QPushButton("Time plot")
        self.plot_groupbox_layout.addWidget(self.show_fft_button,
                                            2, 0, 1, 9)

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
        QtWidgets.QApplication.setWindowIcon(app_icon)

# ------ Connect --------------------------------------------------------------

        self.start_button.clicked.connect(self.start)
        self.stop_button.clicked.connect(self.stop)
        self.clear_button.clicked.connect(self.clear_logs)
        self.choose_file.clicked.connect(self.get_data_from_file)
        self.cycle_num_widget.valueChanged.connect(self.cycle_num_value_change)
        self.cycle_num_widget.valueChanged.connect(self.progress_bar_set_max)
        self.show_fft_button.clicked.connect(self.plot_change)
        self.com_boderate_widget.currentTextChanged.connect(
            self.combobox_changed)
        # self.show_graph_1.stateChanged.connect(self.plot_show)
        # self.show_graph_2.stateChanged.connect(self.plot_show)
        # self.show_graph_3.stateChanged.connect(self.plot_show)
        # self.sender()
# ------ Thread --------------------------------------------------------------
        self.prosessing_thr = PyQt6_Thread.MyThread()
        self.prosessing_thr.package_num_signal.connect(
            self.plot_time_graph)
        self.prosessing_thr.fft_data_emit.connect(
            self.plot_fft)
        self.prosessing_thr.approximate_data_emit.connect(
            self.plot_fft_final)

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

        self.curve_gyro_rectangle.setData([])
        self.curve_encoder.setData([])
        self.curve_gyro1.setData([])
        self.amp_curve_gyro1.setData([])
        self.phase_curve_gyro1.setData([])
        self.curve_gyro2.setData([])
        self.amp_curve_gyro2.setData([])
        self.phase_curve_gyro2.setData([])
        self.curve_gyro3.setData([])
        self.amp_curve_gyro3.setData([])
        self.phase_curve_gyro3.setData([])

        self.progress_bar.setValue(0)
        self.progress_value = 0
        self.count = 0
        self.current_cylce = 1
        self.package_num = 0
        self.flag_sent = False

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

        # self.timer_recieve.setInterval(self.timer_interval)
        self.logger.info(f"{self.com_list_widget.currentText()} open")
        self.logger.info(f"self.cycleNum = {self.total_cycle_num}")
        self.logger.warning("Start")

        # self.Serial.readAll()
        self.Serial.clear()
        # self.timer_recieve.setInterval(0)
        # self.timer_sent_com.setInterval(0)
        self.timer_event_sent_com()
        self.timer_sent_com.start()
        self.timer_recieve.start()

        self.FS = int(self.FS_for_FFT.text())
        self.prosessing_thr.FS = self.FS
        self.prosessing_thr.flag_start = True
        self.prosessing_thr.TIMER_INTERVAL = self.TIMER_INTERVAL
        self.prosessing_thr.start()

# ------ Timer1 ---------------------------------------------------------------

    def timerEvent(self):
        self.progress_value += self.TIMER_INTERVAL/1000
        self.progress_bar.setValue(int(self.progress_value))
        self.logger.info(f"Progress: {self.progress_value}")
        self.read_serial()

    def read_serial(self):
        if (bytes_num := self.Serial.bytesAvailable()) <= 14:
            self.logger.warning(f"No data from {
                self.com_list_widget.currentText()}")
            return
        if self.prosessing_thr.flag_recieve:
            self.logger.info("thread still work with previous data!")
            return

        self.exp_package_num += int(bytes_num/14)
        self.logger.info(
            f"ready to read, bytes num = {bytes_num}, \
expected package num {self.exp_package_num}")
        # self.data_prosessing_thr.flag_recieve = True
        self.copy_varibles_to_thread()
        self.logger.info(f"thread_start, count = {self.count}")

    def copy_varibles_to_thread(self):
        self.prosessing_thr.rx = self.Serial.readAll().data()
        self.prosessing_thr.flag_recieve = True
        self.prosessing_thr.count = self.count
        self.prosessing_thr.flag_pause = self.flag_sent

# ------- Timer2 --------------------------------------------------------------

    def timer_event_sent_com(self):
        """
        Sent command with frequency and amplitude or stop vibration
        """
        if self.flag_sent:
            if self.count >= len(self.list_time):
                if self.current_cylce < self.total_cycle_num:
                    self.cycle_end()
                else:
                    self.stop()
                    return

        if self.flag_sent:
            self.list_view_from_file.setCurrentIndex(
                self.list_data_from_file_widget.index(self.count))
            self.sent_command()
        else:
            self.Serial.write(bytes([0, 0, 0, 0, 0, 0, 0, 0]))
            self.timer_sent_com.setInterval(self.PAUSE_INTERVAL_MS)
        self.flag_sent = not self.flag_sent
        self.logger.info("---end_sent_command")

    def sent_command(self):
        F = int.to_bytes(self.list_freq[self.count],
                         length=2, byteorder='little', signed=False)
        A = int.to_bytes(self.list_amp[self.count],
                         length=2, byteorder='little', signed=False)
        self.Serial.write(
            bytes([77, 0, F[0], F[1], A[0], A[1], 0, 0]))
        self.timer_sent_com.setInterval(
            self.list_time[self.count] * 1000)
        self.count += 1
        self.logger.info("- Command was sent -")

# --------------------------------------------------------------------------------

    def cycle_end(self):
        self.logger.warning("End of cycle "
                            + str(self.current_cylce) + " of " +
                            str(self.total_cycle_num))
        self.current_cylce += 1
        self.count = 0

    def stop(self):
        self.avaliable_butttons(False)
        if self.timer_sent_com.isActive():
            self.timer_sent_com.stop()

        if self.timer_recieve.isActive():
            self.timer_recieve.stop()
            self.logger.warning("End of measurements\n")

        if self.Serial.isOpen():
            self.Serial.write(bytes([0, 0, 0, 0, 0, 0, 0, 0]))
            print(
                line := "COM close? " +
                str(self.Serial.waitForBytesWritten(1000)))
            self.logger.info(line)
            self.Serial.close()

        self.prosessing_thr.flag_start = False

###############################################################################
    # def plot_show(self):
    #     if self.sender().objectName() == "show_graph_1":
    #         if self.curve_gyro1.isVisible():
    #             self.curve_gyro1.hide()
    #         else:
    #             self.curve_gyro1.show()
    #         return

    #     if self.sender().objectName() == "show_graph_2":
    #         if self.curve_gyro2.isVisible():
    #             self.curve_gyro2.hide()
    #         else:
    #             self.curve_gyro2.show()
    #         return

    #     if self.sender().objectName() == "show_graph_3":
    #         if self.curve_gyro3.isVisible():
    #             self.curve_gyro3.hide()
    #         else:
    #             self.curve_gyro3.show()
    #         return

    def cycle_num_value_change(self):
        if not self.timer_recieve.isActive():  # is this required?
            self.total_cycle_num = self.cycle_num_widget.value()

    def progress_bar_set_max(self):
        if self.total_time and not self.timer_recieve.isActive():  # is this required?
            self.progress_bar.setMaximum(int(
                self.PAUSE_INTERVAL_MS/1000 + self.total_cycle_num *
                (self.total_time +
                 len(self.list_time) * self.PAUSE_INTERVAL_MS/1000)))
            self.progress_bar.setValue(0)

    def avaliable_butttons(self, flag_start: bool):
        self.start_button.setDisabled(flag_start)
        self.stop_button.setDisabled(not flag_start)
        self.choose_file.setDisabled(flag_start)

    def plot_time_graph(self, s):
        self.package_num = s
        self.logger.info(f"thread_stop, count = {self.count}\n\
package_num = {self.package_num}")
        self.current_package_number_label.setText(
            str(self.package_num))

        num_of_points_shown = 10*self.FS
        if self.package_num > num_of_points_shown:
            start_i = self.package_num - num_of_points_shown
        else:
            start_i = 0

        self.curve_encoder.setData(
            self.prosessing_thr.all_data[start_i:self.package_num, 0]/self.FS,
            self.prosessing_thr.all_data[start_i:self.package_num, 2]/1000)
        self.curve_gyro1.setData(
            self.prosessing_thr.all_data[start_i:self.package_num, 0]/self.FS,
            self.prosessing_thr.all_data[start_i:self.package_num, 1]/(-100))
        # self.curve_gyro2.setData(
        #     self.prosessing_thr.all_data[start_i:self.package_num, 0]/self.FS,
        #     self.prosessing_thr.all_data[start_i:self.package_num, 2])
        # self.curve_gyro3.setData(
        #     self.prosessing_thr.all_data[start_i:self.package_num, 0]/self.FS,
        #     self.prosessing_thr.all_data[start_i:self.package_num, 3])

        # self.curve_3.setData(self.data_prosessing_thr.all_data[:, 2]/2)
        
        # self.data_for_fft_graph(
        #     self.data_prosessing_thr.all_data[:, 2],
        #     self.data_prosessing_thr.all_data[:, 2]*2,
        #     2000)

    def plot_fft(self, s):
        self.logger.info("plot_fft")
        # self.fft_curve.setData(
        #     self.prosessing_thr.amp_and_freq[:, 0],
        #     self.prosessing_thr.amp_and_freq[:, 2])
        self.amp_curve_gyro1.setData(self.prosessing_thr.amp_and_freq[:, 2],
                                     self.prosessing_thr.amp_and_freq[:, 0])
        # self.amp_curve_gyro2.setData(
        # self.amp_curve_gyro3.setData(
        self.phase_curve_gyro1.setData(self.prosessing_thr.amp_and_freq[:, 2],
                                       self.prosessing_thr.amp_and_freq[:, 1])

        # y0 = self.list_amp[self.count]*1000
        # x1 = self.prosessing_thr.bourder[0]/self.FS
        # x2 = self.prosessing_thr.bourder[1]/self.FS

        self.region.setRegion([self.prosessing_thr.bourder[0]/self.FS,
                               self.prosessing_thr.bourder[1]/self.FS])
        # self.curve_gyro_rectangle.setData(x=[x1, x1, x2, x2, x1],
                                        #   y=[-y0, y0, y0, -y0, -y0])

        # self.prosessing_thr.all_data[start_i:self.package_num, 0]/self.FS,
        # self.prosessing_thr.all_data[start_i:self.package_num, 2])

    def plot_fft_final(self, s):
        self.logger.info("Plot final graphic")
        self.amp_curve_gyro1.setData(self.prosessing_thr.approximate[2, :],
                                     self.prosessing_thr.approximate[0, :])
        self.phase_curve_gyro1.setData(self.prosessing_thr.approximate[2, :],
                                       self.prosessing_thr.approximate[1, :])
# ----------------------------------------------------------------------------=

    def combobox_changed(self, value):
        self.com_boderate_widget.setItemText(
            self.com_boderate_widget.currentIndex(), value)

    def plot_change(self):
        if self.show_fft_button.text() == "Frequency plot":
            self.time_plot.show()
            self.spectrum_button.show()
            self.amp_plot.hide()
            self.phase_plot.hide()
            self.show_fft_button.setText("Time plot")
            # self.time_plot.ctrl.fftCheck.setChecked(False)
            # self.time_plot.setLabel(
            #     'bottom', 'Horizontal Values', units='smth')
        else:
            self.time_plot.hide()
            self.spectrum_button.hide()
            self.amp_plot.show()
            self.phase_plot.show()
            self.show_fft_button.setText("Frequency plot")
            # self.time_plot.ctrl.fftCheck.setChecked(True)
            # self.time_plot.setLabel(
            #     'bottom', 'Frequency', units='Hz')

    def spectrum_show(self):
        t = ""
        if t == "Frequency plot":
            self.time_plot.ctrl.fftCheck.setChecked(False)
        else:
            self.time_plot.ctrl.fftCheck.setChecked(True)
        pass

    def clear_logs(self):
        self.log_text_box.widget.clear()
# -----------------------------------------------------------------------------

    def check_filename(self):  # change for three files
        filename = self.file_name.text()
        if not len(filename):
            filename = 'test'

        extension = '.txt'
        new_name = filename + extension
        i = 1
        while os.path.exists(new_name):
            new_name = filename + "(" + str(i) + ")" + extension
            i += 1
        self.prosessing_thr.filename = new_name
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

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')  # 'Fusion' ... QtWidgets.QStyle
    window = MyWindow()
    window.setWindowTitle("Gyro")
    # window.resize(850, 500)
    window.show()
    sys.exit(app.exec())
