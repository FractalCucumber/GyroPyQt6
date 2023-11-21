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
# import numpy as np
import PyQt6_Logger
import PyQt6_Thread

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

class CustomComboBox(QtWidgets.QComboBox):
    def __init__(self, 
                 settings_name: str,
                 deafault_items_list: list,
                 editable_flag=True,
                 parent=None):
        super(CustomComboBox, self).__init__(parent)
        #  можно сразу комбо бок передавать вместе с настройками редактирования и валидатором
        self.setEditable(True)  # add to argument
        # self.currentIndex
        if not editable_flag:
            self.lineEdit().setReadOnly(True)
        # intValidator  # !!!
        self.settings = QtCore.QSettings(settings_name)
        if self.settings.contains("items"):
            self.addItems(
                self.settings.value("items"))
        else:
            self.addItems(deafault_items_list)
        if self.settings.contains("curr_index"):
            self.setCurrentIndex(
                self.settings.value("curr_index"))
            
        self.currentTextChanged.connect(
            self.combobox_changed)
            
    def combobox_changed(self, value):
        self.setItemText(self.currentIndex(), value)

    def save_value(self):
        self.settings.setValue(
            "items",
            [self.itemText(i)
             for i in range(self.count())])

    def save_index(self):
        self.settings.setValue(
            "curr_index", self.currentIndex())


class CustomViewBox(pg.ViewBox):
    def __init__(self, *args, **kwds):
        # kwds['enableMenu'] = True
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
        self.TIMER_READ_INTERVAL = 125*2
        self.timer_recieve = QtCore.QTimer(interval=self.TIMER_READ_INTERVAL)
        self.timer_recieve.timeout.connect(self.timerEvent)
        self.timer_sent_com = QtCore.QTimer(
            timerType=QtCore.Qt.TimerType.PreciseTimer)
        self.timer_sent_com.timeout.connect(self.timer_event_sent_com)

# ------ Init vars ------------------------------------------------------------
        self.PAUSE_INTERVAL_MS = 500
        self.count = 0
        self.progress_bar_value = 0
        self.total_time = 0
        self.total_cycle_num = 1
        self.current_cylce = 0
        STYLE_SHEETS_FILENAME = 'StyleSheets.css'
        self.Serial = QSerialPort(dataBits=QSerialPort.DataBits.Data8,
                                  stopBits=QSerialPort.StopBits.OneStop,
                                  parity=QSerialPort.Parity.NoParity)
        self.LABEL_STYLE = {'color': '#FFF', 'font-size': '14px'}
        self.COLOR_LIST = ['r', 'g', 'b']
# ------ GUI ------------------------------------------------------------------
        self.main_grid_layout = QtWidgets.QGridLayout(self)
# ------ Com Settings ---------------------------------------------------------

        self.com_param_groupbox = QtWidgets.QGroupBox(
            'Настройки порта', maximumWidth=300)
        self.com_param_groupbox_layout = QtWidgets.QGridLayout()

        self.com_list_widget = QtWidgets.QComboBox(editable=True)
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

        self.com_boderate_combo_box = CustomComboBox(
            settings_name="COM_speed_settings",
            deafault_items_list=["921600", "115200", "0"],
            editable_flag=True)

        self.int_validator = QtGui.QIntValidator()
        self.com_boderate_combo_box.setValidator(self.int_validator)

        self.com_param_groupbox_layout.addWidget(QtWidgets.QLabel('Speed:'),
                                                 1, 0)
        self.com_param_groupbox_layout.addWidget(self.com_boderate_combo_box,
                                                 1, 1)

        self.fs_combo_box = CustomComboBox(
            settings_name="fs_settings",
            deafault_items_list=['1000', '2000', '0'],
            editable_flag=True)
        self.fs_combo_box.setValidator(self.int_validator)
        self.com_param_groupbox_layout.addWidget(QtWidgets.QLabel('Fs, Hz:'),
                                                 2, 0)
        self.com_param_groupbox_layout.addWidget(self.fs_combo_box,
                                                 2, 1)

        self.com_param_groupbox.setLayout(self.com_param_groupbox_layout)
###############################################################################
# ------ File -----------------------------------------------------------------

        self.measurements_groupbox = QtWidgets.QGroupBox('&Измерения', maximumWidth=300)
        self.measurements_groupbox_layout = QtWidgets.QGridLayout()

        self.measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel('Measurement cycle file:'), 1, 0, 1, 2)
        self.choose_file = QtWidgets.QPushButton('Выбрать')
        self.measurements_groupbox_layout.addWidget(self.choose_file, 2, 0, 1, 2)

        self.edit_file_button = QtWidgets.QPushButton('Открыть файл')
        self.measurements_groupbox_layout.addWidget(self.edit_file_button, 4, 0, 1, 2)

        self.file_name_and_path = QtWidgets.QLineEdit(
            readOnly=True, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel('Filename:'), 3, 0)
        self.measurements_groupbox_layout.addWidget(self.file_name_and_path,
                                                    3, 1)

        self.cycle_num_widget = QtWidgets.QSpinBox(
            minimum=1, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel('Cycle number:'), 0, 0)
        self.measurements_groupbox_layout.addWidget(self.cycle_num_widget,
                                                    0, 1)

        self.measurements_groupbox.setLayout(self.measurements_groupbox_layout)
###############################################################################
# ------ File -----------------------------------------------------------------

        self.saving_measurements_groupbox = QtWidgets.QGroupBox(
            'Сохранение измерений', maximumWidth=300)
        self.saving_measurements_groupbox_layout = QtWidgets.QGridLayout()

        self.saving_measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel('Папка:'), 0, 0)
        self.current_folder = QtWidgets.QLineEdit(os.getcwd(), readOnly=True)
        self.saving_measurements_groupbox_layout.addWidget(
            self.current_folder, 0, 1)

        self.saving_measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel('<b>Имя файла:</b>'), 1, 0)
        self.file_name = QtWidgets.QLineEdit('test')
        self.saving_measurements_groupbox_layout.addWidget(
            self.file_name, 1, 1)
        self.saving_measurements_groupbox.setLayout(
            self.saving_measurements_groupbox_layout)

##############################################################################
# ------ Output logs and data from file ---------------------------------------

        self.text_output_groupbox = QtWidgets.QGroupBox(
            'Содержимое файла', maximumWidth=395)
        # self.text_output_groupbox_layout = QtWidgets.QFormLayout()
        self.text_output_groupbox_layout = QtWidgets.QGridLayout()

        self.table_widget = QtWidgets.QTableWidget(
            columnCount=3, editTriggers=QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        # self.tableWidget.setRowCount(1)  # u"\u00b0"
        self.table_widget.setHorizontalHeaderLabels(["F, Hz", "A, \u00b0/s", "T, s"])
        # если добавить возможность редактировать таблицу,
        # то надо пересчитывать время симуляции
        # protoItem = QtWidgets.QTableWidgetItem()
        # protoItem.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        # # set other things like read-only with QTableWidgetItem.setFlags, etc.
        # # set prototype item for all items created from now
        # self.table_widget.setItemPrototype(protoItem)

        # self.tableWidget.item().ed
        # self.tableWidget.horizontalHeader().setSectionResizeMode( 
            # QtWidgets.QHeaderView.Stretch) 
        # item = QtWidgets.QTableWidgetItem()
        # item.setData(QtCore.Qt.ItemDataRole.EditRole, 5)
        # self.tableWidget.setItem(0, 0, item)
        # print(self.tableWidget.item(0, 0))
        # print(self.tableWidget.item(0, 0).data(QtCore.Qt.ItemDataRole.EditRole)) 
        # print(type(self.tableWidget.item(0, 0).data(QtCore.Qt.ItemDataRole.EditRole))) 
        # print(self.tableWidget.item(0, 0).data(int))
        # self.tableWidget.setItem(0,1, QtWidgets.QTableWidgetItem("City"))
        # self.tableWidget.setItem(1,0, QtWidgets.QTableWidgetItem("Aloysius"))
        # self.tableWidget.horizontalHeader().setStretchLastSection(True)
        self.table_widget.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table_widget.verticalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        # item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        # self.tableWidget.setTextAlignment(4)

        # self.tableWidget.setstr
        # self.tableWidget.setCurrentItem(2,2)
        # self.tableWidget.setSelectionMode(
            # QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        # self.tableWidget.disconnect()
        self.table_widget.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        # self.tableWidget.selectRow(1)
        # self.tableWidget.resizeColumnsToContents()
        # self.tableWidget.resizeRowsToContents()

        self.text_output_groupbox_layout.addWidget(self.table_widget)
        self.text_output_groupbox.setLayout(self.text_output_groupbox_layout)

        self.text_output_groupbox2 = QtWidgets.QGroupBox(
            'Logs:', maximumWidth=395)
        # self.text_output_groupbox_layout = QtWidgets.QFormLayout()
        self.logs_groupbox_layout = QtWidgets.QVBoxLayout()
# ------ Logger ---------------------------------------------------------------
        self.log_text_box = PyQt6_Logger.QTextEditLogger(self)
        self.logger = logging.getLogger('main')

        self.logs_groupbox_layout.addWidget(self.log_text_box.widget)

        self.clear_button = QtWidgets.QPushButton('Clear logs')
        self.logs_groupbox_layout.addWidget(self.clear_button)

        self.start_button = QtWidgets.QPushButton('START')
        self.stop_button = QtWidgets.QPushButton('STOP', enabled=False)

        self.text_output_groupbox2.setLayout(self.logs_groupbox_layout)

###############################################################################
# ------ plot -----------------------------------------------------------------

        self.plot_groupbox = QtWidgets.QGroupBox('График', minimumWidth=395)
        self.plot_groupbox_layout = QtWidgets.QGridLayout()

# ------ time plot ------------------------------------------------------------

        self.time_plot_item = pg.PlotItem(viewBox=CustomViewBox())
        self.time_plot = pg.PlotWidget(plotItem=self.time_plot_item)
        self.time_plot_item.setTitle('Velosity Graph', size='12pt')
        self.time_plot_item.showGrid(x=True, y=True)
        self.time_plot_item.addLegend(offset=(-1, 1), labelTextSize='12pt',
                                      labelTextColor=pg.mkColor('w'))
        self.time_plot_item.setLabel('left', 'Velosity',
                                     units='\u00b0/second',
                                     **self.LABEL_STYLE)
        self.time_plot_item.setLabel('bottom', 'Time',
                                     units='seconds', **self.LABEL_STYLE)

        self.time_curves = [self.time_plot_item.plot(pen='w', name="encoder")]
        for i in range(3):
            self.time_curves.append(self.time_plot_item.plot(
                pen=self.COLOR_LIST[i], name=f"gyro {i + 1}"))

        self.curve_gyro_rectangle = self.time_plot_item.plot()

        self.region = pg.LinearRegionItem([0, 1], movable=False)
        self.time_plot_item.addItem(self.region)

        self.time_curves[0].setData([0, 0, 2, 2, 0], [0, 3, 3, 0, 0])
        self.time_curves[1].setData([0, 0, 1.5, 1.5, 0], [0, 2, 2, 0, 0])

# ------ Tab widget ----------------------------------------------------------- 
        self.tab_widget = QtWidgets.QTabWidget(tabsClosable=True) 

        self.contact_page = QtWidgets.QWidget(self)
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.time_plot)
        self.spectrum_button = QtWidgets.QPushButton("FFT (doesn't work)")
        self.layout.addWidget(self.spectrum_button)
        self.contact_page.setLayout(self.layout)
        self.tab_widget.addTab(self.contact_page, "Time plot &1") 

        self.phase_curves: list[pg.PlotCurveItem] = []
        self.amp_curves: list[pg.PlotCurveItem] = []

        # self.current_cylce = 1  # don't forget to delete
        # ind = self.current_cylce - 1
        self.phase_plot_list: list[pg.PlotWidget] = []
        self.amp_plot_list: list[pg.PlotWidget] = []
        self.contact_page: list[QtWidgets.QWidget] = []
        # ind += 1
        self.append_fft_plot_tab(0)
        # self.current_cylce += 1
        # self.append_tab()
        # self.current_cylce += 1
        # self.append_tab()

        self.phase_curves[0].setData([0, 0, 5, 2.5, 0], [0, 6, 6, 0, 0])
        # self.phase_curves[5].setData([0, 0, 2.5, 0.5, 0], [0, 3, 3, 0, 0])
######################################################################
        self.progress_bar = QtWidgets.QProgressBar(
            format='%v/%m sec', maximum=1, value=0)
        self.plot_groupbox_layout.addWidget(self.progress_bar,
                                            5, 0, 1, 5)

        self.package_number_label = QtWidgets.QLabel('Package number:')
        self.plot_groupbox_layout.addWidget(self.package_number_label,
                                            5, 5, 1, 3)
        self.current_package_num_label = QtWidgets.QLabel()
        self.current_package_num_label.setText('0')
        self.plot_groupbox_layout.addWidget(self.current_package_num_label,
                                            5, 8, 1, 1)

        self.plot_groupbox_layout.addWidget(self.tab_widget,
                                            0, 0, 4, 9)

        self.plot_groupbox.setLayout(self.plot_groupbox_layout)

# ------ Set main grid --------------------------------------------------------

        self.main_grid_layout.addWidget(self.com_param_groupbox,
                                        0, 0, 1, 1)
        self.main_grid_layout.addWidget(self.measurements_groupbox,
                                        1, 0, 2, 1)
        self.main_grid_layout.addWidget(self.saving_measurements_groupbox,
                                        3, 0, 3, 1)

        self.main_grid_layout.addWidget(self.text_output_groupbox,
                                        0, 1, 2, 1)
        self.main_grid_layout.addWidget(self.text_output_groupbox2,
                                        2, 1, 2, 1)
        self.main_grid_layout.addWidget(self.start_button,
                                        4, 1, 1, 1)
        self.main_grid_layout.addWidget(self.stop_button,
                                        5, 1, 1, 1)
        
        self.main_grid_layout.addWidget(self.plot_groupbox,
                                        0, 2, 6, 1)
        self.setLayout(self.main_grid_layout)

# ------ Style ----------------------------------------------------------------

        # self.block1_com_param.setObjectName("group1")
        # self.subblock1_com_param.setObjectName("group1")
        self.stop_button.setObjectName("stop_button")
        # self.choose_file.setObjectName("choose_file")
        self.start_button.setObjectName("start_button")
        with open(STYLE_SHEETS_FILENAME, "r") as style_sheets_file:
            self.setStyleSheet(style_sheets_file.read())

        app_icon = QtGui.QIcon()
        app_icon.addFile('Vibro_1_resources/icon_16.png', QtCore.QSize(16, 16))
        app_icon.addFile('Vibro_1_resources/icon_24.png', QtCore.QSize(24, 24))
        app_icon.addFile('Vibro_1_resources/icon_32.png', QtCore.QSize(32, 32))
        app_icon.addFile('Vibro_1_resources/icon_48.png', QtCore.QSize(48, 48))
        QtWidgets.QApplication.setWindowIcon(app_icon)

# ------ Signal Connect -------------------------------------------------------

        self.start_button.clicked.connect(self.start)
        self.stop_button.clicked.connect(self.stop)
        self.clear_button.clicked.connect(self.clear_logs)
        self.choose_file.clicked.connect(self.get_data_from_file)
        self.spectrum_button.clicked.connect(self.plot_change)
        self.cycle_num_widget.valueChanged.connect(self.cycle_num_value_change)
        self.cycle_num_widget.valueChanged.connect(self.progress_bar_set_max)
        self.com_boderate_combo_box.currentTextChanged.connect(
            self.combobox_changed)
        self.edit_file_button.clicked.connect(self.open_file)
        # self.tab_widget.tabCloseRequested.connect(self.close_tab)
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

    # def change_plot2(self):
    #     if self.hhh:
    #         self.contact_page = QtWidgets.QWidget(self)
    #         self.layout = QtWidgets.QVBoxLayout()
    #         self.layout.addWidget(self.time_plot)
    #         self.spectrum_button = QtWidgets.QPushButton("FFT (doesn't work)")
    #         self.layout.addWidget(self.spectrum_button)
    #         self.contact_page.setLayout(self.layout)
    #         self.tab_widget.(self.contact_page, "Time plot &1") 
    #     else:
    #         self.contact_page = QtWidgets.QWidget(self)
    #         self.layout = QtWidgets.QVBoxLayout()
    #         self.layout.addWidget(self.time_plot)
    #         self.spectrum_button = QtWidgets.QPushButton("FFT (doesn't work)")
    #         self.layout.addWidget(self.spectrum_button)
    #         self.contact_page.setLayout(self.layout)
    #         self.tab_widget.addTab(self.contact_page, "sp plot &3") 
    #     self.hhh = not self.hhh

    def start(self):
        self.exp_package_num = 0

        # self.time_plot_item.clear()
        # self.amp_plot_item.clear()
        # self.phase_plot_item.clear()
        # maybe better to use 'clear'

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
            int(self.com_boderate_combo_box.currentText()))
        self.Serial.setPortName(
            self.com_list_widget.currentText())

        self.check_filename()
        if not self.total_time:
            self.cycle_num_value_change()
            if not self.get_data_from_file():
                self.logger.info("No data from file")
                return
        self.logger.info("Data from file was loaded")

        if not self.Serial.open(QtCore.QIODevice.OpenModeFlag.ReadWrite):
            self.logger.warning(
                f"Can't open {self.com_list_widget.currentText()}")
            return

        self.cycle_num_value_change()
        self.progress_bar_set_max()
        self.avaliable_butttons(True)  # expand

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

        self.fs = int(self.fs_combo_box.currentText())
        self.prosessing_thr.fs = self.fs
        self.prosessing_thr.flag_start = True
        self.prosessing_thr.TIMER_INTERVAL = self.TIMER_READ_INTERVAL
        self.prosessing_thr.start()

        # self.append_tab(1)
        # self.append_tab(2)
        # self.append_tab(3)
        for i in range(self.tab_widget.count() - 2):
            self.tab_widget.removeTab(2)  # tabs num decreased during 'for' cycle

        self.time_curves[0].setData([])
        for i in range(3):
            self.time_curves[i + 1].setData([])
            self.amp_curves[i].setData([])
            self.phase_curves[i].setData([])

# ------ Timer Recieve ------------------------------------------------------------

    def timerEvent(self):
        """
        Read data from COM port. Generate warning if avaliable less than 14 bytes
        """
        self.read_serial()
        self.progress_value += self.TIMER_READ_INTERVAL/1000
        self.progress_bar.setValue(int(self.progress_value))
        self.logger.info(f"Progress: {self.progress_value}")

    def read_serial(self):
        if (bytes_num := self.Serial.bytesAvailable()) <= 14:
            self.logger.warning(
                f"No data from {self.com_list_widget.currentText()}")
            return
        if self.prosessing_thr.flag_recieve:
            self.logger.info("thread still work with previous data!")
            return

        self.exp_package_num += int(bytes_num/14)
        self.logger.info(
            f"ready to read, bytes num = {bytes_num}, \
expected package num {self.exp_package_num}")
        self.copy_variables_to_thread()
        self.logger.info(f"thread_start, count = {self.count}")

    def copy_variables_to_thread(self):
        self.prosessing_thr.rx = self.Serial.readAll().data()
        self.prosessing_thr.flag_recieve = True
        self.prosessing_thr.count = self.count
        self.prosessing_thr.flag_pause = self.flag_sent

# ------- Timer Sent ------------------------------------------------------------

    def timer_event_sent_com(self):
        """
        Sent command with frequency and amplitude or stop vibration
        """
        if self.flag_sent:
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
        # print(self.tableWidget.currentRow())
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

# ----- End cycle, stop, etc ---------------------------------------------------------------

    def cycle_end(self):
        self.logger.warning(
            f"End of cycle {self.current_cylce} of {self.total_cycle_num}")
        self.current_cylce += 1
        self.count = 0

        self.append_fft_plot_tab(self.current_cylce - 1)  # !!!

    def stop(self):
        self.avaliable_butttons(False)
        if self.timer_sent_com.isActive():
            self.timer_sent_com.stop()

        if self.timer_recieve.isActive():
            self.timer_recieve.stop()
            self.logger.warning("End of measurements\n")

        if self.Serial.isOpen():
            self.Serial.write(bytes([0, 0, 0, 0, 0, 0, 0, 0]))
            self.logger.info("COM close? " +
                str(self.Serial.waitForBytesWritten(1000)))
            self.Serial.close()
        self.prosessing_thr.flag_start = False

###############################################################################
# ----- plotting --------------------------------------------------------------

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

    def plot_time_graph(self, s):
        self.package_num = s
        self.logger.info(f"thread_stop, count = {self.count}\n\
package_num = {self.package_num}")
        self.current_package_num_label.setText(str(self.package_num))

        num_of_points_shown = 10*self.fs
        if self.package_num > num_of_points_shown:
            start_i = self.package_num - num_of_points_shown
        else:
            start_i = 0

        self.time_curves[0].setData(
            self.prosessing_thr.all_data[start_i:self.package_num, 0]/self.fs,
            self.prosessing_thr.all_data[start_i:self.package_num, 2]/1000)
        self.time_curves[1].setData(
            self.prosessing_thr.all_data[start_i:self.package_num, 0]/self.fs,
            self.prosessing_thr.all_data[start_i:self.package_num, 1]/(-100))
        # selftime_curves[2].setData(
        #     self.prosessing_thr.all_data[start_i:self.package_num, 0]/self.FS,
        #     self.prosessing_thr.all_data[start_i:self.package_num, 2])
        # selftime_curves[3].setData(
        #     self.prosessing_thr.all_data[start_i:self.package_num, 0]/self.FS,
        #     self.prosessing_thr.all_data[start_i:self.package_num, 3])

    def plot_fft(self, _):
        self.logger.info("plot_fft")
        ind = (self.current_cylce - 1)*3

        self.amp_curves[ind].setData(self.prosessing_thr.amp_and_freq[:, 2],
                                     self.prosessing_thr.amp_and_freq[:, 0])
        # self.amp_curve_gyro2.setData( #  use for instead
        self.phase_curves[ind].setData(self.prosessing_thr.amp_and_freq[:, 2],
                                       self.prosessing_thr.amp_and_freq[:, 1])
        # y0 = self.list_amp[self.count]*1000
        # x1 = self.prosessing_thr.bourder[0]/self.FS
        # x2 = self.prosessing_thr.bourder[1]/self.FS
        self.region.setRegion([self.prosessing_thr.bourder[0]/self.fs,
                               self.prosessing_thr.bourder[1]/self.fs])
        # self.curve_gyro_rectangle.setData(x=[x1, x1, x2, x2, x1],
                                        #   y=[-y0, y0, y0, -y0, -y0])
        # self.prosessing_thr.all_data[start_i:self.package_num, 0]/self.FS,
        # self.prosessing_thr.all_data[start_i:self.package_num, 2])

    def plot_fft_final(self, _):
        ind = (self.current_cylce - 1)*3
        self.logger.info("Plot final graphic")
        self.amp_curves[ind].setData(self.prosessing_thr.approximate[2, :],
                                     self.prosessing_thr.approximate[0, :])
        self.phase_curves[ind].setData(self.prosessing_thr.approximate[2, :],
                                       self.prosessing_thr.approximate[1, :])
# ----- plot change ------------------------------------------------------------
    def plot_change(self):
        if self.spectrum_button.text() == "Frequency plot":
            self.spectrum_button.setText("Time plot")
            self.time_plot_item.ctrl.fftCheck.setChecked(False)
            self.time_plot_item.setLabel(
                'bottom', 'Time', units='seconds')
        else:
            self.spectrum_button.setText("Frequency plot")
            self.time_plot_item.ctrl.fftCheck.setChecked(False)
            self.time_plot_item.setLabel(
                'bottom', 'Frequency', units='Hz')

    # def spectrum_show(self):
    #     t = ""
    #     if t == "Frequency plot":
    #         self.time_plot.ctrl.fftCheck.setChecked(False)
    #     else:
    #         self.time_plot.ctrl.fftCheck.setChecked(True)
    #     pass

    def append_fft_plot_tab(self, index):
        self.contact_page.append(QtWidgets.QWidget(self))
        self.layout = QtWidgets.QVBoxLayout()
        self.append_phase_plot()
        self.layout.addWidget(self.phase_plot_list[index])
        self.append_amp_plot()
        self.layout.addWidget(self.amp_plot_list[index])
        self.contact_page[index].setLayout(self.layout)
        self.tab_widget.addTab(
            self.contact_page[index], f"Freq №{index + 1}")

    def append_amp_plot(self):
        self.amp_plot_item = pg.PlotItem(viewBox=CustomViewBox())
        self.amp_plot_item.setTitle('Amp Graph', size='12pt')
        self.amp_plot_item.showGrid(x=True, y=True)
        self.amp_plot_item.addLegend(offset=(-1, 1), labelTextSize='12pt',
                                     labelTextColor=pg.mkColor('w'))
        self.amp_plot_item.setLabel('left', 'Amplitude',
                                    units='', **self.LABEL_STYLE)
        self.amp_plot_item.setLabel('bottom', 'Frequency',
                                    units='Hz', **self.LABEL_STYLE)
        # self.SYMBOL_SIZE = 6
        for i in range(3):
            self.amp_curves.append(self.amp_plot_item.plot(
                pen=self.COLOR_LIST[i], name=f"gyro {i + 1}", symbol="o",
                symbolSize=6, symbolBrush=self.COLOR_LIST[i]))
        self.amp_plot_list.append(pg.PlotWidget(plotItem=self.amp_plot_item))

    def append_phase_plot(self):
        self.phase_plot_item = pg.PlotItem(viewBox=CustomViewBox())
        self.phase_plot_item.setTitle('Phase Graph', size='12pt')
        self.phase_plot_item.showGrid(x=True, y=True)
        self.phase_plot_item.addLegend(offset=(-1, 1), labelTextSize='12pt',
                                       labelTextColor=pg.mkColor('w'))
        self.phase_plot_item.setLabel('left', 'Phase',
                                      units='rad', **self.LABEL_STYLE)  # \u00b0
        self.phase_plot_item.setLabel('bottom', 'Frequency',
                                      units='Hz', **self.LABEL_STYLE)
        for i in range(3):
            self.phase_curves.append(self.phase_plot_item.plot(
                pen=self.COLOR_LIST[i], name=f"gyro {i + 1}", symbol="o",
                symbolSize=6, symbolBrush=self.COLOR_LIST[i]))
        self.phase_plot_list.append(pg.PlotWidget(plotItem=self.phase_plot_item))

# ------ Widgets events -----------------------------------------------

    def cycle_num_value_change(self):
        if not self.timer_recieve.isActive():  # is this required?
            self.total_cycle_num = self.cycle_num_widget.value()

    def progress_bar_set_max(self):
        if self.total_time and not self.timer_recieve.isActive():  # is this required?
            self.progress_bar.setMaximum(int(
                self.PAUSE_INTERVAL_MS/1000 + self.total_cycle_num *
                (self.total_time +
                 self.num_rows * self.PAUSE_INTERVAL_MS/1000)))
            self.progress_bar.setValue(0)

    def avaliable_butttons(self, flag_running: bool):
        self.start_button.setDisabled(flag_running)
        self.stop_button.setDisabled(not flag_running)
        self.choose_file.setDisabled(flag_running)

    def combobox_changed(self, value):
        self.com_boderate_combo_box.setItemText(
            self.com_boderate_combo_box.currentIndex(), value)
        
    # def close_tab(self,index):
        # self.tab_widget.removeTab(index)

    def clear_logs(self):
        self.log_text_box.widget.clear()

# ------ file name and data from file ---------------------------------------------------------

    def check_filename(self):  # change for three files
        # filename = self.file_name.text()
        # if not len(filename):
        #     filename = 'test'

        # extension = '.txt'
        # new_name = filename + extension
        # i = 1
        # while os.path.exists(new_name):
        #     new_name = filename + f"({i})" + extension
        #     i += 1
        # self.prosessing_thr.filename = new_name
        folder_name = 'results'
        if not os.path.isdir(folder_name):
            os.mkdir(folder_name)
        filename = folder_name + '/' + self.file_name.text()
        if not len(filename):
            filename = 'test_1'

        extension = '.txt'
        new_name_1 = filename + "_1" + extension
        new_name_2 = filename + "_2" + extension
        new_name_3 = filename + "_3" + extension
        if not (os.path.exists(new_name_1) or
                os.path.exists(new_name_2) or
                os.path.exists(new_name_3)):
            self.prosessing_thr.filename[0] = filename
            self.prosessing_thr.filename[1] = extension
            return

        i = 1
        while (os.path.exists(new_name_1) or
                os.path.exists(new_name_2) or
                os.path.exists(new_name_3)):
            new_name_1 = filename + f"_1({i})" + extension
            new_name_2 = filename + f"_2({i})" + extension
            new_name_3 = filename + f"_3({i})" + extension
            i += 1
        self.prosessing_thr.filename[0] = filename
        self.prosessing_thr.filename[1] = f"({i - 1})" + extension

    def get_data_from_file(self):
        # !!!! добавить кнопку, которая открывает файл,
        # чтобы его можно было редачить
        # import subprocess
        # subprocess.Popen(["notepad","pyqt6_log.log"])
        # os.system("notepad filename.txt")

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите методику измерений",
            ".",
            "Text Files(*.txt)")
        if not filename:
            return False

        with open(filename, 'r') as file:
            self.file_name_and_path.setText(os.path.basename(filename))
            self.current_folder.setText(os.getcwd())
            i = 0
            self.total_time = 0
            for line in file:
                f_a_t = list(filter(None, re.split("F|A|T|\n", line)))
                if (len(f_a_t) == 3 and f_a_t[0].isdecimal() and
                    f_a_t[1].isdecimal() and f_a_t[2].isdecimal()):
                    i += 1
                    self.table_widget.setRowCount(i)
                    for j in range(3):
                        item = QtWidgets.QTableWidgetItem(f_a_t[j])
                        item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                        self.table_widget.setItem(i-1, j, item) 
                    self.total_time += int(f_a_t[2]) 
            self.num_rows = i
            self.progress_bar_set_max()
            return self.total_time > 0
    
    def open_file(self):  # didn't work
        os.startfile(self.file_name_and_path.text())
        # self.get_data_from_file()
        with open(self.file_name_and_path.text(), 'r') as file:
            # self.file_name_and_path.setText(os.path.basename(filename))
            # self.current_folder.setText(os.getcwd())
            i = 0
            self.total_time = 0
            for line in file:
                f_a_t = list(filter(None, re.split("F|A|T|\n", line)))
                if (len(f_a_t) == 3 and f_a_t[0].isdecimal() and
                    f_a_t[1].isdecimal() and f_a_t[2].isdecimal()):

                    i += 1
                    self.table_widget.setRowCount(i)
                    self.table_widget.setItem(i-1, 0, QtWidgets.QTableWidgetItem(f_a_t[0])) 
                    self.table_widget.setItem(i-1, 1, QtWidgets.QTableWidgetItem(f_a_t[1])) 
                    self.table_widget.setItem(i-1, 2, QtWidgets.QTableWidgetItem(f_a_t[2]))
                    self.total_time += int(f_a_t[2]) 
            self.num_rows = i
            self.progress_bar_set_max()
            return self.total_time > 0

    def closeEvent(self, _):
        self.stop()
        self.com_boderate_combo_box.save_value()
        self.com_boderate_combo_box.save_index()
        self.fs_combo_box.save_value()
        self.fs_combo_box.save_index()
        self.logger.warning("Exit")

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
