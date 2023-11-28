import logging
import sys
# from PyQt6.QtWidgets import QFileDialog
# from PyQt6.QtCore import pyqtSignal, QThread, QIODevice
import os
import re
# from pyqtgraph.Qt import QtCore, QtGui
# from datetime import datetime
# from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtSerialPort import QSerialPort, QSerialPortInfo
import pyqtgraph.exporters
import pyqtgraph as pg
import numpy as np
import PyQt6_Logger
import PyQt6_Thread


#  pyinstaller --onefile --noconsole PyQt6_Application.py
# --add-data="Vibro_1_resources/icon_16.png:."
# --add-data="Vibro_1_resources/icon_24.png:."
# --add-data="Vibro_1_resources/icon_32.png:."
# --add-data="Vibro_1_resources/icon_48.png:." PyQt6_Application.py
# pyinstaller --add-data "StyleSheets.css:." --add-data "icon_16.png:." --add-data "icon_24.png:." --add-data "icon_32.png:." --add-data "icon_48.png:." --onefile --windowed PyQt6_Application.py --exclude-module matplotlib --exclude-module hook --exclude-module setuptools --exclude-module DateTime --exclude-module pandas --exclude-module PyQt6.QtOpenGL --exclude-module PyQt6.QtOpenGLWidgets --exclude-module hooks --exclude-module hook --exclude-module pywintypes --exclude-module flask --exclude-module opengl32sw.dll
# pyinstaller --add-data "StyleSheets.css:." --onefile --windowed PyQt6_Application.py
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
        self.setEditable(True)
        if not editable_flag:
            self.lineEdit().setReadOnly(True)
        # intValidator
        self.settings = QtCore.QSettings(settings_name)
        if self.settings.contains("items"):
            self.addItems(
                self.settings.value("items"))
        else:
            self.addItems(deafault_items_list)
        if self.settings.contains("curr_index"):
            self.setCurrentIndex(
                self.settings.value("curr_index"))

        self.lineEdit().setAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter)
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
        # self.setMouseMode(self.RectMode)

    #  reimplement right-click to zoom out
    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.MouseButton.RightButton:
            self.autoRange()

    #  reimplement mouseDragEvent to disable continuous axis zoom
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

# ------ Init vars ------------------------------------------------------------
        self.PLOT_TIME_INTERVAL_SEC = 10
        self.PAUSE_INTERVAL_MS = 500
        self.READ_INTERVAL_MS = 125*2
        self.FOLDER_NAME = 'results'
        self.count = 0
        self.progress_bar_value = 0
        self.progress_value = 0
        self.total_time = 0
        self.total_cycle_num = 1
        self.current_cylce = 0
        STYLE_SHEETS_FILENAME = 'StyleSheets.css'
        FILE_LOG_FLAG = False
        self.GYRO_NUMBER = 1
        self.LABEL_STYLE = {'color': '#FFF', 'font-size': '16px'}
        self.COLOR_LIST = ['r', 'g', 'b']
        self.filename_path_watcher = ""
        self.Serial = QSerialPort(dataBits=QSerialPort.DataBits.Data8,
                                  stopBits=QSerialPort.StopBits.OneStop,
                                  parity=QSerialPort.Parity.NoParity)
# ------ Timres ---------------------------------------------------------------
        self.timer_recieve = QtCore.QTimer(interval=self.READ_INTERVAL_MS)
        self.timer_recieve.timeout.connect(self.timerEvent)
        self.timer_sent_com = QtCore.QTimer(
            timerType=QtCore.Qt.TimerType.PreciseTimer)
        self.timer_sent_com.timeout.connect(self.timer_event_sent_com)
# ------ File watcher --------------------------------------------------------
        self.fs_watcher = QtCore.QFileSystemWatcher()
        # self.fs_watcher.directoryChanged.connect(self.directory_changed)
        self.fs_watcher.fileChanged.connect(self.file_changed)
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

        self.com_list_widget = QtWidgets.QComboBox(editable=True)
        self.com_list_widget.lineEdit().setAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter)
        self.com_list_widget.lineEdit().setReadOnly(True)
        
        self.get_avaliable_com()

        self.com_param_groupbox_layout.addWidget(QtWidgets.QLabel('COM:'),
                                                 0, 0, 1, 1)
        self.com_param_groupbox_layout.addWidget(self.com_list_widget,
                                                 0, 1, 1, 1)

        self.com_boderate_combo_box = CustomComboBox(
            settings_name="COM_speed_settings",
            deafault_items_list=["921600", "115200", "0"],
            editable_flag=True)

        self.int_validator = QtGui.QIntValidator(bottom=0)
        self.com_boderate_combo_box.setValidator(self.int_validator)

        self.com_param_groupbox_layout.addWidget(QtWidgets.QLabel('Speed:'),
                                                 1, 0, 1, 1)
        self.com_param_groupbox_layout.addWidget(self.com_boderate_combo_box,
                                                 1, 1, 1, 1)

        self.fs_combo_box = CustomComboBox(
            settings_name="fs_settings",
            deafault_items_list=['1000', '2000', '0'],
            editable_flag=True)
        self.fs_combo_box.setValidator(self.int_validator)
        self.com_param_groupbox_layout.addWidget(QtWidgets.QLabel('Fs, Hz:'),
                                                 2, 0, 1, 1)
        self.com_param_groupbox_layout.addWidget(self.fs_combo_box,
                                                 2, 1, 1, 1)

        self.com_param_groupbox.setLayout(self.com_param_groupbox_layout)

# ------ Measurement File -----------------------------------------------------
        """
        Block with button to open and edit measurement file
        """
        self.measurements_groupbox = QtWidgets.QGroupBox(
            'Измерения', maximumWidth=300)
        self.measurements_groupbox_layout = QtWidgets.QGridLayout()

        self.cycle_num_widget = QtWidgets.QSpinBox(
            minimum=1, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel('Cycle number:'), 0, 0, 3, 1)
        self.measurements_groupbox_layout.addWidget(self.cycle_num_widget,
                                                    0, 1, 3, 1)
        self.cycle_num_settings = QtCore.QSettings("cycle_num_settings")
        if self.cycle_num_settings.contains("cycle_num"):
            self.cycle_num_widget.setValue(
                self.cycle_num_settings.value("cycle_num"))

        # self.measurements_groupbox_layout.addWidget(
        #     QtWidgets.QLabel('Measurement\ncycle file:'), 1, 0, 1, 1)
        self.choose_file = QtWidgets.QPushButton('&Choose file')
        self.measurements_groupbox_layout.addWidget(self.choose_file,
                                                    3, 0, 3, 2)

        self.edit_file_button = QtWidgets.QPushButton('&Open file')
        self.measurements_groupbox_layout.addWidget(self.edit_file_button,
                                                    12, 0, 3, 2)

        self.measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel('Filepath:'), 6, 0, 2, 1)
        # self.file_name_and_path_widget = CustomComboBox(
        #     settings_name="file_settings",
        #     deafault_items_list=['', '', ''],
        #     editable_flag=False)
        # QLineEdit readOnly=True, 
        self.filename_and_path_widget = QtWidgets.QLabel(
            alignment=QtCore.Qt.AlignmentFlag.AlignHCenter,
            wordWrap=True, objectName="with_bourder",
            textInteractionFlags=QtCore.Qt.
            TextInteractionFlag.TextSelectableByMouse)
        self.measurements_groupbox_layout.addWidget(
            self.filename_and_path_widget, 9, 0, 1, 2)
        # self.measurements_groupbox_layout.setRowStretch(0, 3)
        # self.measurements_groupbox_layout.setRowStretch(1, 3)
        # self.measurements_groupbox_layout.setRowStretch(2, 1)
        # self.measurements_groupbox_layout.setRowStretch(3, 1)
        # self.measurements_groupbox_layout.setRowStretch(4, 1)
        # self.measurements_groupbox.setFlat(True)  # прозрачность
        # self.measurements_groupbox_layout.setSizeConstraint(
            # QtWidgets.QLayout.SizeConstraint.SetNoConstraint)
        self.measurements_groupbox.setLayout(self.measurements_groupbox_layout)

# ------ Saving results -------------------------------------------------------
        """
        Block with info about saving measurements results
        """
        self.saving_measurements_groupbox = QtWidgets.QGroupBox(
            'Сохранение измерений', maximumWidth=300)
        self.saving_measurements_groupbox_layout = QtWidgets.QGridLayout()

        self.saving_measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel('<b>Папка:</b>'), 0, 0, 2, 1)
        self.current_folder_label = QtWidgets.QLabel(
            os.getcwd(), wordWrap=True, objectName="with_bourder",
            textInteractionFlags=QtCore.Qt.
            TextInteractionFlag.TextSelectableByMouse)

        self.current_folder_label.setText(os.getcwd())

        self.saving_measurements_groupbox_layout.addWidget(
            self.current_folder_label, 0, 1, 2, 1)

        self.saving_measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel('Имя\nфайла:'), 2, 0, 3, 1)
        self.file_name_path = QtWidgets.QLineEdit('test')
        self.saving_measurements_groupbox_layout.addWidget(
            self.file_name_path, 2, 1, 3, 1)
        self.saving_measurements_groupbox.setLayout(
            self.saving_measurements_groupbox_layout)

##############################################################################
# ------ Output logs and data from file ---------------------------------------
        self.text_output_groupbox = QtWidgets.QGroupBox(
            'Содержимое файла', maximumWidth=315, minimumWidth=215)
        # self.text_output_groupbox_layout = QtWidgets.QFormLayout()
        self.text_output_groupbox_layout = QtWidgets.QGridLayout()

        self.table_widget = QtWidgets.QTableWidget(
            columnCount=3,
            editTriggers=QtWidgets.
            QAbstractItemView.EditTrigger.NoEditTriggers,
            selectionBehavior=QtWidgets.
            QAbstractItemView.SelectionBehavior.SelectRows)
        # self.tableWidget.setRowCount(1)
        self.table_widget.setHorizontalHeaderLabels(
            ["F, Hz", "A, \u00b0/s", "T, s"])
        self.table_widget.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table_widget.verticalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)

        self.text_output_groupbox_layout.addWidget(self.table_widget)
        self.text_output_groupbox.setLayout(self.text_output_groupbox_layout)

        self.logs_groupbox = QtWidgets.QGroupBox(
            'Logs:', maximumWidth=315)
# ------ Logger ---------------------------------------------------------------
        """
        Logs widget
        """
        self.logs_groupbox_layout = QtWidgets.QVBoxLayout()
        self.log_text_box = PyQt6_Logger.QTextEditLogger(self,
                                                         file_log=FILE_LOG_FLAG)
        self.logger = logging.getLogger('main')

        self.logs_groupbox_layout.addWidget(self.log_text_box.widget)

        self.clear_button = QtWidgets.QPushButton('Clear logs')
        self.logs_groupbox_layout.addWidget(self.clear_button)

        self.start_button = QtWidgets.QPushButton(
            'START',objectName="start_button")
        self.stop_button = QtWidgets.QPushButton(
            'STOP', enabled=False, objectName="stop_button")

        self.logs_groupbox.setLayout(self.logs_groupbox_layout)

###############################################################################
# ------ plot -----------------------------------------------------------------
        """
        Plots in tab widget
        """
        # self.plot_groupbox = QtWidgets.QGroupBox('График', minimumWidth=395)
        self.plot_groupbox = QtWidgets.QGroupBox(minimumWidth=395)
        self.plot_groupbox_layout = QtWidgets.QGridLayout()

# ------ time plot ------------------------------------------------------------

        self.time_plot_item = pg.PlotItem(viewBox=CustomViewBox())
        self.time_plot = pg.PlotWidget(plotItem=self.time_plot_item)
        self.time_plot_item.setTitle('Velosity Graph', size='13pt')
        self.time_plot_item.showGrid(x=True, y=True)
        self.time_plot_item.addLegend(offset=(-1, 1), labelTextSize='12pt',
                                      labelTextColor=pg.mkColor('w'))
        self.time_plot_item.setLabel('left', 'Velosity',
                                     units='\u00b0/second', **self.LABEL_STYLE)
        self.time_plot_item.setLabel('bottom', 'Time',
                                     units='seconds', **self.LABEL_STYLE)

        self.time_curves = [self.time_plot_item.plot(pen='w', name="encoder")]
        for i in range(self.GYRO_NUMBER):
            self.time_curves.append(self.time_plot_item.plot(
                pen=self.COLOR_LIST[i], name=f"gyro {i + 1}"))

        self.curve_gyro_rectangle = self.time_plot_item.plot()

        self.region = pg.LinearRegionItem([0, 1], movable=False)
        self.time_plot_item.addItem(self.region)

        # self.time_curves[0].setData([0, 0, 2, 2, 0], [0, 3, 3, 0, 0])
        # self.time_curves[1].setData([0, 0, 1.5, 1.5, 0], [0, 2, 2, 0, 0])
        # x = [1, 5, 10, 15, 20, 25, 33, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 118, 120, 122, 125, 130, 135, 140, 150, 156, 162, 170, 180, 190, 200, 205, 210, 215, 220, 225, 230, 235, 240, 245, 250, 255, 260, 265, 270, 275, 280, 285, 290, 300, 310]
        x = [1, 5, 10, 15, 20, 25, 33, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 102, 105, 107, 110, 115, 118, 120, 122, 125, 130, 135, 140, 150, 156, 162, 170, 180, 190, 200, 205, 210, 215, 220, 225, 230, 235, 240, 243, 247, 250, 255, 260, 265, 270, 275, 280, 285, 290, 295, 300, 305, 310, 315]
        # amp =np.array([96, 97, 108, 112, 113, 114, 121, 127, 136, 163, 166, 191, 219, 240, 258, 284, 400, 371, 450, 699, 791, 1154, 631, 697, 722, 743, 834, 823, 918, 995, 1022, 1125, 1220, 1244, 1373, 1468, 1618, 1851, 1865, 2166, 2548, 2539, 3409, 3521, 3514, 4220, 3473, 2573, 3081, 3028, 3028, 3230, 3056, 3132, 3102, 3621, 3669, 4561])/100
        amp =np.array(
            [94, 99, 105, 114, 112, 113, 122, 127, 137, 160, 169, 205, 221, 243, 292, 306, 339, 392, 419, 554, 861, 913, 1079, 1276, 595, 645, 659, 666, 781, 810, 863, 948, 1024, 1103, 1227, 1329, 1319, 1362, 1468, 1791, 1921, 1959, 2641, 2477, 3384, 3484, 3254, 4482, 3888, 3931, 2795, 3021, 3246, 3046, 3147, 3505, 3424, 3430, 4049, 4157, 4385, 3980, 5340, 4897]
            )/100
        self.time_curves[0].setData(x, amp)

        freq_approximation = np.linspace(1, 330, num=300)
        k_list = np.polyfit(x, amp, 4)
        print(k_list)
        k_list[-1] = k_list[-1] + 0.1
        k_list[-2] = k_list[-2]*0.2
        k_list[-3] = k_list[-3]*0.8
        print(k_list)
        # аппроксимирующую функцию можно разбить на столько диапазонов,
        # сколько учатков с разной амплитудой у нас имеется
        amp_approximation = ((-4.75368112e-09)*freq_approximation**4 +
                             (2.06569833e-06)*freq_approximation**3 +
                             (2.02236573e-04)*freq_approximation**2 +
                             1.60865286e-03*freq_approximation) + 9.41254199e-01
        # fun = np.poly1d(k_list)
        # amp_approximation = np.array(fun(freq_approximation))
        self.time_curves[1].setData(freq_approximation, amp_approximation)

        # freq_approximation = np.linspace(1, 110, num=300)
        # r = 42
        # k_list = np.polyfit(x[0:-r], amp[0:-r], 6)
        # fun = np.poly1d(k_list)
        # print(f'{list(k_list)}')
        # amp_approximation = np.array(fun(freq_approximation))

        # self.time_curves[1].setData(freq_approximation, amp_approximation)
        # freq_approximation = np.linspace(110, 300, num=300)
        # r = 25
        # k_list = np.polyfit(x[r:len(x)], amp[r:len(x)], 7)
        # fun = np.poly1d(k_list)
        # print(f'{list(k_list)}')
        # amp_approximation = np.array(fun(freq_approximation))

        # self.time_curves[2].setData(freq_approximation, amp_approximation)
        # self.time_curves[2].setData(freq_approximation, np.exp(0.479) * np.exp(0.0255*freq_approximation))

# ------ Tab widget -----------------------------------------------------------
        # self.tab_widget = QtWidgets.QTabWidget(tabsClosable=True)
        self.tab_widget = QtWidgets.QTabWidget()

        self.page = QtWidgets.QWidget(self)
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.time_plot)
        self.spectrum_button = QtWidgets.QPushButton("Time plot")
        self.layout.addWidget(self.spectrum_button)
        self.page.setLayout(self.layout)
        self.tab_widget.addTab(self.page, "&Time plot")

        self.phase_curves: list[pg.PlotCurveItem] = []
        self.amp_curves: list[pg.PlotCurveItem] = []
        self.phase_plot_list: list[pg.PlotWidget] = []
        self.amp_plot_list: list[pg.PlotWidget] = []

        self.contact_page: list[QtWidgets.QWidget] = []
        self.append_fft_plot_tab(0)
        # self.tab_widget.setTabText(self.tab_widget.count() - 1, "&FC")
        self.phase_curves[0].setData([0, 0, 5, 2.5, 0], [0, 6, 6, 0, 0])
        # self.phase_curves[5].setData([0, 0, 2.5, 0.5, 0], [0, 3, 3, 0, 0])

        self.plot_groupbox_layout.addWidget(self.tab_widget,
                                            0, 0, 4, 9)

        self.progress_bar = QtWidgets.QProgressBar(
            format='%v/%m sec', maximum=1, value=self.progress_value)
        # self.progress_bar.setSizePolicy(QtWidgets.QSizePolicy.PolicyFlag.ExpandFlag)
        self.plot_groupbox_layout.addWidget(self.progress_bar,
                                            6, 2, 1, 7)

        self.package_number_label = QtWidgets.QLabel('Package number:')
        self.plot_groupbox_layout.addWidget(self.package_number_label,
                                            5, 2, 1, 3)
        self.current_package_num_label = QtWidgets.QLabel('0')
        self.plot_groupbox_layout.addWidget(self.current_package_num_label,
                                            5, 5, 1, 1)

        self.save_image_button = QtWidgets.QPushButton('Save\nimage')
        self.plot_groupbox_layout.addWidget(self.save_image_button, 5, 0, 2, 1)

        self.save_settings_button = QtWidgets.QPushButton('Save settings')
        self.plot_groupbox_layout.addWidget(self.save_settings_button, 5, 1, 1, 1)

        self.autosave_checkbox = QtWidgets.QCheckBox('Autosave')
        self.plot_groupbox_layout.addWidget(self.autosave_checkbox, 6, 1, 1, 1)
        self.autosave_settings = QtCore.QSettings("autosave_settings")
        if self.autosave_settings.contains("autosave"):
            # print(self.autosave_settings.value("autosave"))
            self.autosave_checkbox.setChecked(
                self.autosave_settings.value("autosave"))
            
        self.plot_groupbox.setLayout(self.plot_groupbox_layout)

        self.filename_settings = QtCore.QSettings("filename_settings")
        if self.filename_settings.contains("filename"):  # load prev file
            if os.path.exists(name := self.filename_settings.value("filename")):
                self.filename_and_path_widget.setText(name)
                if self.get_data_from_file(name):
                    self.logger.warning("The previous file is loaded")
# ------ Set main grid --------------------------------------------------------

        self.main_grid_layout.addWidget(self.com_param_groupbox,
                                        0, 0, 1, 1)
        self.main_grid_layout.addWidget(self.measurements_groupbox,
                                        1, 0, 2, 1)
        self.main_grid_layout.addWidget(self.saving_measurements_groupbox,
                                        3, 0, 3, 1)

        self.main_grid_layout.addWidget(self.text_output_groupbox,
                                        0, 1, 2, 1)
        self.main_grid_layout.addWidget(self.logs_groupbox,
                                        2, 1, 2, 1)
        self.main_grid_layout.addWidget(self.start_button,
                                        4, 1, 1, 1)
        self.main_grid_layout.addWidget(self.stop_button,
                                        5, 1, 1, 1)

        self.main_grid_layout.addWidget(self.plot_groupbox,
                                        0, 2, 6, 1)
        self.setLayout(self.main_grid_layout)

# ------ Style ----------------------------------------------------------------

        with open(self.res_path(STYLE_SHEETS_FILENAME), "r") as style_sheets:
            self.setStyleSheet(style_sheets.read())

        app_icon = QtGui.QIcon()
        for i in [16, 24, 32, 48]:
            app_icon.addFile(self.res_path(f'icon_{i}.png'), QtCore.QSize(i, i))
        QtWidgets.QApplication.setWindowIcon(app_icon)

# ------ Signal Connect -------------------------------------------------------

        self.start_button.clicked.connect(self.start)
        self.stop_button.clicked.connect(self.stop)
        self.clear_button.clicked.connect(self.clear_logs)
        self.choose_file.clicked.connect(self.choose_and_load_file)
        self.spectrum_button.clicked.connect(self.plot_change)
        self.cycle_num_widget.valueChanged.connect(self.cycle_num_value_change)
        self.cycle_num_widget.valueChanged.connect(self.progress_bar_set_max)
        self.com_boderate_combo_box.currentTextChanged.connect(
            self.combobox_changed)
        self.edit_file_button.clicked.connect(self.open_file)
        self.save_image_button.clicked.connect(self.save_image)
        self.save_settings_button.clicked.connect(self.save_all_settings)
        # self.tab_widget.tabCloseRequested.connect(self.close_tab)

# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------
#
###############################################################################
#
# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------
#

    @QtCore.pyqtSlot()
    def start(self):
        self.exp_package_num = 0

        self.progress_bar.setValue(0)
        self.progress_value = 0
        self.count = 0
        self.current_cylce = 1
        self.package_num = 0
        self.flag_sent = False

        self.logger.info(F"\nPORT: {(self.com_list_widget.currentText())}\n")
        if not len(self.com_list_widget.currentText()):
            self.get_avaliable_com()
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
            if not self.choose_and_load_file():
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
        self.prosessing_thr.TIMER_INTERVAL = self.READ_INTERVAL_MS
        self.prosessing_thr.num_measurement_rows = self.num_rows
        self.prosessing_thr.start()

        for i in range(self.tab_widget.count() - 2):
            self.tab_widget.removeTab(2)
            self.contact_page.pop()

        self.time_curves[0].setData([])
        for i in range(self.GYRO_NUMBER):
            self.time_curves[i + 1].setData([])
            self.amp_curves[i].setData([])
            self.phase_curves[i].setData([])

# ------ Timer Recieve --------------------------------------------------------

    @QtCore.pyqtSlot()
    def timerEvent(self):
        """
        Read data from COM port.
        Generate warning if avaliable less than 14 bytes
        """
        self.read_serial()
        self.progress_value += self.READ_INTERVAL_MS/1000
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

# ------- Timer Sent ----------------------------------------------------------

    @QtCore.pyqtSlot()
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

        self.append_fft_plot_tab(self.current_cylce - 1)  # !!!
        self.prosessing_thr.new_cycle()

    def stop(self):
        self.avaliable_butttons(False)
        if self.timer_sent_com.isActive():
            self.timer_sent_com.stop()

        if self.timer_recieve.isActive():
            self.timer_recieve.stop()

        self.logger.info(
            f"% = {self.progress_value}, " +
            "total time = {self.progress_bar.maximum()}")
        if self.prosessing_thr.flag_start:
            # self.save_image()
            if self.progress_value < self.progress_bar.maximum():
                self.timerEvent()

        if self.Serial.isOpen():
            self.Serial.write(bytes([0, 0, 0, 0, 0, 0, 0, 0]))
            self.logger.info("COM close? " +
                             str(self.Serial.waitForBytesWritten(1000)))
            self.Serial.close()
            self.logger.warning("End of measurements\n")
        self.prosessing_thr.flag_start = False

###############################################################################
# ----- plotting --------------------------------------------------------------

    @QtCore.pyqtSlot(int)
    def plot_time_graph(self, s):
        self.package_num = s
        self.logger.info(f"thread_stop, count = {self.count}\n" +
                         f"package_num = {self.package_num}")
        self.current_package_num_label.setText(str(self.package_num))

        num_of_points_shown = self.PLOT_TIME_INTERVAL_SEC*self.fs
        if self.package_num > num_of_points_shown:
            start_i = self.package_num - num_of_points_shown
        else:
            start_i = 0
        self.time_curves[0].setData(
            self.prosessing_thr.all_data[start_i:self.package_num, 0]/self.fs,
            self.prosessing_thr.all_data[start_i:self.package_num, 2]/1000)
        for i in range(self.GYRO_NUMBER):
            self.time_curves[i + 1].setData(
                self.prosessing_thr.all_data[start_i:self.package_num, 0]/self.fs,
                self.prosessing_thr.all_data[start_i:self.package_num, 1]/(-100))

    @QtCore.pyqtSlot(bool)
    def plot_fft(self, _):
        """
        Adds points to frequency graphs
        """
        self.logger.info("plot_fft")
        # ind = 3 * (self.current_cylce - 1)
        for i in range(self.GYRO_NUMBER):
            # self.amp_curves[ind + i].setData(self.prosessing_thr.amp_and_freq_for_plot[:, 0],
            #                             self.prosessing_thr.amp_and_freq_for_plot[:, 1])
            # self.phase_curves[ind + i].setData(self.prosessing_thr.amp_and_freq_for_plot[:, 0],
            #                             self.prosessing_thr.amp_and_freq_for_plot[:, 2])
            self.amp_curves[-1 - i].setData(self.prosessing_thr.amp_and_freq_for_plot[:, 0],
                                        self.prosessing_thr.amp_and_freq_for_plot[:, 1])
            self.phase_curves[-1 - i].setData(self.prosessing_thr.amp_and_freq_for_plot[:, 0],
                                        self.prosessing_thr.amp_and_freq_for_plot[:, 2])
        self.region.setRegion([self.prosessing_thr.bourder[0]/self.fs,
                               self.prosessing_thr.bourder[1]/self.fs])

    @QtCore.pyqtSlot(bool)
    def plot_fft_final(self, _):  # better recieve current_cylce instead bool
        self.logger.info("Final median plot")
        self.append_fft_plot_tab(self.current_cylce)
        self.tab_widget.setTabText(self.current_cylce + 1, "&FC")
        # self.plot_fft(True)
        # ind = 3 * self.current_cylce
        for i in range(self.GYRO_NUMBER):
#             self.amp_curves[ind + i].setData(self.prosessing_thr.amp_and_freq[:, -4],
#                                         self.prosessing_thr.amp_and_freq[:, -3])
#             self.phase_curves[ind + i].setData(self.prosessing_thr.amp_and_freq[:, -4],
#                                         self.prosessing_thr.amp_and_freq[:, -2])
            self.amp_curves[-1 - i].setData(self.prosessing_thr.amp_and_freq[:, -4],
                                        self.prosessing_thr.amp_and_freq[:, -3])
            self.phase_curves[-1 - i].setData(self.prosessing_thr.amp_and_freq[:, -4],
                                        self.prosessing_thr.amp_and_freq[:, -2])
        # app_icon = QtGui.QIcon()
        # app_icon.addFile(self.res_path('icon_24.png'), QtCore.QSize(24, 24))
        # self.tab_widget.setTabIcon(self.current_cylce + 1, app_icon)

# ----- plot change -----------------------------------------------------------

    @QtCore.pyqtSlot()
    def plot_change(self):
        """
        Switching between time plot and spectrum
        """
        if self.spectrum_button.text() == "Frequency plot":
            self.spectrum_button.setText("Time plot")
            self.time_plot_item.ctrl.fftCheck.setChecked(False)
            self.time_plot_item.setLabel(
                'bottom', 'Time', units='seconds')
            self.region.show()
        else:
            self.spectrum_button.setText("Frequency plot")
            self.time_plot_item.ctrl.fftCheck.setChecked(True)
            self.time_plot_item.setLabel(
                'bottom', 'Frequency', units='Hz')
            self.region.hide()

    def append_fft_plot_tab(self, index):
        """
        Create new tab and append amplitude and grequency graphs
        """
        self.contact_page.append(QtWidgets.QWidget(self))
        self.layout = QtWidgets.QVBoxLayout()
        self.append_phase_plot()
        self.layout.addWidget(self.phase_plot_list[index])
        self.append_amp_plot()
        self.layout.addWidget(self.amp_plot_list[index])
        self.contact_page[index].setLayout(self.layout)
        self.tab_widget.addTab(
            self.contact_page[index], f"FC &{index + 1}")

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
        for i in range(self.GYRO_NUMBER):
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
                                      units='rad', **self.LABEL_STYLE)
        # \u00b0
        self.phase_plot_item.setLabel('bottom', 'Frequency',
                                      units='Hz', **self.LABEL_STYLE)
        for i in range(self.GYRO_NUMBER):
            self.phase_curves.append(self.phase_plot_item.plot(
                pen=self.COLOR_LIST[i], name=f"gyro {i + 1}", symbol="o",
                symbolSize=6, symbolBrush=self.COLOR_LIST[i]))
        self.phase_plot_list.append(
            pg.PlotWidget(plotItem=self.phase_plot_item))

    @QtCore.pyqtSlot()
    def save_image(self):
        self.logger.info("Save image")
        pyqtgraph.exporters.ImageExporter(
            self.time_plot_item).export(self.FOLDER_NAME + '/time_plot.png')
        for i in range(self.current_cylce):
            pyqtgraph.exporters.ImageExporter(
                self.amp_plot_list[i].getPlotItem()).export(
                    self.FOLDER_NAME + f'/amp_plot_{i}.png')
            pyqtgraph.exporters.ImageExporter(
                self.phase_plot_list[i].getPlotItem()).export(
                    self.FOLDER_NAME + f'/phase_plot_{i}.png')
        self.logger.info("Saving complite")

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
            # self.progress_bar.setValue(0)

    def avaliable_butttons(self, flag_running: bool):
        self.cycle_num_widget.setDisabled(flag_running)
        self.edit_file_button.setDisabled(flag_running)
        self.save_image_button.setDisabled(flag_running)
        self.start_button.setDisabled(flag_running)
        self.stop_button.setDisabled(not flag_running)
        self.choose_file.setDisabled(flag_running)

    def combobox_changed(self, value):
        self.com_boderate_combo_box.setItemText(
            self.com_boderate_combo_box.currentIndex(), value)

    @QtCore.pyqtSlot()
    def clear_logs(self):
        self.log_text_box.widget.clear()

    def get_avaliable_com(self):
        """
        Append avaliable com ports to combo box widget
        """
        self.available_ports = QSerialPortInfo.availablePorts()
        if self.available_ports:
            for port in self.available_ports:
                self.com_list_widget.addItem(port.portName())

# ------ file name and data from file -----------------------------------------

    def check_filename(self):  # changed for three files
        if not os.path.isdir(self.FOLDER_NAME):
            os.mkdir(self.FOLDER_NAME)
        if not len(self.file_name_path.text()):
            filename = self.FOLDER_NAME + '/test'
        else:
            filename = self.FOLDER_NAME + '/' + self.file_name_path.text()

        extension = '.txt'
        new_name_1 = filename + "_1" + extension
        new_name_2 = filename + "_2" + extension
        new_name_3 = filename + "_3" + extension
        if not (os.path.exists(new_name_1) or
                os.path.exists(new_name_2) or
                os.path.exists(new_name_3)):
            self.prosessing_thr.filename = [filename, extension]
            return

        i = 0
        while (os.path.exists(new_name_1) or
                os.path.exists(new_name_2) or
                os.path.exists(new_name_3)):
            i += 1
            new_name_1 = filename + f"_1({i})" + extension
            new_name_2 = filename + f"_2({i})" + extension
            new_name_3 = filename + f"_3({i})" + extension
        self.prosessing_thr.filename = [filename, f"({i})" + extension]

    # def directory_changed(self, path):
    #     self.logger.info(f'Directory Changed: {path}')
    #     print(f'Directory Changed: {path}')

    def file_changed(self, path):
        self.logger.info(
            f'File Changed, {path}, thr run: {self.prosessing_thr.flag_start}')
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

    @QtCore.pyqtSlot()
    def open_file(self):
        os.startfile(self.filename_and_path_widget.text())

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
        self.autosave_settings.setValue("autosave",
                                        self.autosave_checkbox.checkState().value)
        if self.autosave_checkbox.checkState().value:
            self.save_all_settings()
        self.logger.warning("Saving the settings and exit")

    def save_all_settings(self):
        self.com_boderate_combo_box.save_value()
        self.com_boderate_combo_box.save_index()
        self.fs_combo_box.save_value()
        self.fs_combo_box.save_index()
        # self.file_name_and_path_widget.save_value()
        # self.file_name_and_path_widget.save_index()
        self.cycle_num_settings.setValue("cycle_num",
                                        self.cycle_num_widget.value())
        self.filename_settings.setValue("filename",
                                        self.filename_and_path_widget.text())

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