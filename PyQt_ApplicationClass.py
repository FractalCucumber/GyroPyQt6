import logging
import sys
# from PyQt5.QtWidgets import QFileDialog # from PyQt5.QtCore import pyqtSignal, QThread, QIODevice
import os
import re
# from datetime import datetime # from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo
# import pyqtgraph.exporters
# import pyqtgraph as pg
import numpy as np
import PyQt_Logger
import PyQt_Thread
import PyQt_CustomWidgets
from time import time
# from PyQt5_res_path import get_res_path

# pg.setConfigOption('background', '#f0f0f5')  # Установите фон в серый цвет
# pg.setConfigOption('foreground', 'd')

# d:/Gyro2023_Git/venv3.6/Scripts/Activate.bat
# git add PyQt5_ApplicationClass.py PyQt5_CustomWidgets.py PyQt5_Thread.py PyQt5_Logger.py StyleSheets.css
# pyinstaller PyQt5_ApplicationOnefolder.spec
# pyinstaller PyQt5_Application.spec 
# pyinstaller --onefile --noconsole PyQt5_Application.py
# pyinstaller --add-data "StyleSheets.css;." --add-data "icon_16.png;." --add-data "icon_24.png;." --add-data "icon_32.png;." --add-data "icon_48.png;." --onefile --windowed PyQt5_Application.py --exclude-module matplotlib --exclude-module hook --exclude-module setuptools --exclude-module DateTime --exclude-module pandas --exclude-module PyQt5.QtOpenGL --exclude-module PyQt5.QtOpenGLWidgets --exclude-module hooks --exclude-module hook --exclude-module pywintypes --exclude-module flask --exclude-module opengl32sw.dll
# pyinstaller --add-data "StyleSheets.css;." --add-data "icon_16.png;." --add-data "icon_24.png;." --add-data "icon_32.png;." --add-data "icon_48.png;." --windowed PyQt5_Application.py
# pyinstaller --add-data "StyleSheets.css;." --onefile --windowed PyQt5_Application.py
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


# class AppWindow(QtWidgets.QWidget):
class AppWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):

        QtWidgets.QMainWindow.__init__(self, parent)
        # QtWidgets.QApplication.setAttribute(
            # QtCore.Qt.ApplicationAttribute.
            # AA_UseStyleSheetPropagationInWidgetStyles,
            # True)  # наследование свойств оформления потомков от родителей
        self.setWindowTitle("GyroVibroTest")
        # print(QtWidgets.QStyleFactory.keys())
        QtWidgets.QApplication.setStyle('Fusion')  # 'Fusion' ... QtWidgets.QStyle
# ------ Init vars ------------------------------------------------------------
        self.PLOT_TIME_INTERVAL_SEC = 10
        self.PAUSE_INTERVAL_MS = 750
        self.READ_INTERVAL_MS = 100 * 2  #  125 * 2
        self.folder_name = os.getcwd() + '/'  # тоже 3 штуки сделать
        self.GYRO_NUMBER = 3
        self.folder_name_list = [os.getcwd() + '/' for _ in range(self.GYRO_NUMBER)]
        self.filename_new = ['' for _ in range(self.GYRO_NUMBER)] 
        self.filename_new_for_fft = ['' for _ in range(self.GYRO_NUMBER)] 
        self.count: int = 0
        self.progress_value = 0 # убрать?
        self.total_time: int = 0
        self.total_cycle_num: int = 1
        self.current_cylce: int = 0
        STYLE_SHEETS_FILENAME = 'res\StyleSheets.css'
        # FILE_LOG_FLAG = False
        FILE_LOG_FLAG = True
        self.filename_path_watcher = ""
        LOGGER_NAME = 'main'
        self.ICON_LIST = ['red', 'green', 'blue']
        self.Serial = QSerialPort(dataBits=QSerialPort.DataBits.Data8,
                                  stopBits=QSerialPort.StopBits.OneStop,
                                  parity=QSerialPort.Parity.NoParity)
        self.settings = QtCore.QSettings("settings")
# ------ Timres ---------------------------------------------------------------
        self.timer_recieve = QtCore.QTimer(interval=self.READ_INTERVAL_MS)
        self.timer_recieve.timeout.connect(self.timer_read_event)
        self.timer_sent_com = QtCore.QTimer(
            timerType=QtCore.Qt.TimerType.PreciseTimer)
        self.timer_sent_com.timeout.connect(self.timer_event_sent_com)
# ------ File watcher ---------------------------------------------------------
        self.fs_watcher = QtCore.QFileSystemWatcher()
        # self.fs_watcher.directoryChanged.connect(self.directory_changed)
        self.fs_watcher.fileChanged.connect(self.check_filename_and_get_data)
# ------ Thread ---------------------------------------------------------------
        self.prosessing_thr = PyQt_Thread.MyThread(
            gyro_number=self.GYRO_NUMBER, logger_name=LOGGER_NAME)
        self.prosessing_thr.package_num_signal.connect(self.plot_time_graph)
        self.prosessing_thr.fft_data_signal.connect(self.plot_fft)
        self.prosessing_thr.median_data_ready_signal.connect(
            self.plot_fft_final)
        self.logger = logging.getLogger(LOGGER_NAME)
        self.prosessing_thr.warning_signal.connect(
            lambda text: self.logger.warning(text))
        # self.custom_tab_plot_widget.filenames_list_emit.connect(
# ------ Plots in tab widget --------------------------------------------------
        self.custom_tab_plot_widget = PyQt_CustomWidgets.CustomTabWidget(
            GYRO_NUMBER=self.GYRO_NUMBER, logger_name=LOGGER_NAME)  # !
        self.custom_tab_plot_widget.warning_signal.connect(
            lambda text: self.logger.warning(text))
        self.custom_tab_plot_widget.get_filename_signal.connect(
            self.run_thread_for_file_prosessing
        )
# ------ GUI ------------------------------------------------------------------
        # self.main_grid_layout = QtWidgets.QGridLayout(self)
        # self.win_widget = WinWidget(self)
        # widget = QtWidgets.QWidget(objectName="size16px")
        widget = QtWidgets.QWidget()
        self.main_grid_layout = QtWidgets.QGridLayout(widget)
        # layout.addWidget(self.win_widget)
        self.setCentralWidget(widget)
# ------ menu -----------------------------------------------------------------
        # self.menu_bar = QtWidgets.QMenuBar(self)
        # from PyQt5.QtWidgets import QMainWindow, QAction, qApp, QApplication
        menu_bar = self.menuBar()
        # self.menuBar.setGeometry(0,0, 500, 25)
        menu_1 = menu_bar.addMenu("&Options")
        # menu_1.addAction('New')
        # menu_1.addAction('Open')
        # menu_1.addAction('Save')
        settings_autosave_action = QtWidgets.QAction(
            "&Settings autosave", self, checkable=True)
        # settings_autosave_action.setIcon(QtGui.QIcon(self.get_res_path('res//ok.png')))
        # save_settings_action.triggered.connect(self.save_all_settings)        
        settings_autosave_action.triggered.connect(lambda: print("Settings autosave"))        
        menu_1.addAction(settings_autosave_action)
        save_settings_action = QtWidgets.QAction("&Save current settings", self)
        save_settings_action.triggered.connect(self.save_all_settings)        
        menu_1.addAction(save_settings_action)   
        plots_to_png_action = QtWidgets.QAction("&Plots to .png", self)
        plots_to_png_action.setShortcut("Ctrl+P")
        plots_to_png_action.triggered.connect(self.save_image)        
        menu_1.addAction(plots_to_png_action)        
        exit_action = QtWidgets.QAction("&Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        # exit_action.setStatusTip("Exit application")  # ???
        exit_action.triggered.connect(self.close)
        menu_1.addAction(exit_action)
        menu_2 = menu_bar.addMenu("&Mode")
        menu_2.addAction('1')
        menu_2.addAction('2')
        # self.statusBar()
# ------ Com Settings ---------------------------------------------------------
        """
        Block with COM port settings and sampling frequency selection
        """
        self.com_param_groupbox = QtWidgets.QGroupBox(
            'Настройки COM порта', maximumWidth=300)
        self.com_param_groupbox_layout = QtWidgets.QGridLayout()
        self.com_param_groupbox.setLayout(self.com_param_groupbox_layout)

        self.combo_box_name = PyQt_CustomWidgets.CustomComboBox(
            settings=self.settings,
            settings_name="COM_name_settings",
            editable_flag=False, uint_validator_enable=False)

        self.get_avaliable_com()
        # self.com_param_groupbox_layout.addWidget(QtWidgets.QLabel('COM:'),
                                                #  0, 0, 1, 1)
        self.com_param_groupbox_layout.addWidget(self.combo_box_name,
                                                 0, 0, 1, 1)

        self.com_boderate_combo_box = PyQt_CustomWidgets.CustomComboBox(
            settings=self.settings,
            settings_name="COM_speed_settings",
            default_items_list=['921600', '115200', '0'])
        # self.com_param_groupbox_layout.addWidget(QtWidgets.QLabel('Скорость:'),
                                                #  1, 0, 1, 1)  # Speed
        self.com_param_groupbox_layout.addWidget(self.com_boderate_combo_box,
                                                 0, 1, 1, 1)
# ------   -----------------------------------------------------

        self.fs_groupbox = QtWidgets.QGroupBox(
            'FS', maximumWidth=300)
        self.fs_groupbox_layout = QtWidgets.QGridLayout()
        self.fs_groupbox.setLayout(self.fs_groupbox_layout)
        self.fs_combo_box = PyQt_CustomWidgets.CustomComboBox(
            settings=self.settings,
            settings_name="fs_settings",
            default_items_list=['1000', '2000', '741'])
        self.fs = int(self.fs_combo_box.currentText())
        self.fs_groupbox_layout.addWidget(self.fs_combo_box,
                                                 0, 0, 1, 1)
# ------   -----------------------------------------------------
        self.cycle_number_groupbox = QtWidgets.QGroupBox(
            'Циклы:', maximumWidth=300)
        self.cycle_number_groupbox_layout = QtWidgets.QGridLayout()
        self.cycle_number_groupbox.setLayout(self.cycle_number_groupbox_layout)

        self.cycle_num_widget = QtWidgets.QSpinBox(
            minimum=1, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
        # self.cycle_number_groupbox_layout.addWidget(
            # QtWidgets.QLabel(''), 0, 0, 3, 2)  # Cycle number
        self.cycle_number_groupbox_layout.addWidget(self.cycle_num_widget)#,
                                                    # 0, 2, 3, 2)
        # self.fs_combo_box = PyQt_CustomWidgets.CustomComboBox(
            # settings=self.settings,
            # settings_name="fs_settings",
            # default_items_list=['1000', '2000', '741'])
        # self.fs = int(self.fs_combo_box.currentText())
        # self.cycle_number_groupbox_layout.addWidget(self.fs_combo_box,
                                                #  0, 0, 1, 1)
# ------ Measurement File -----------------------------------------------------
        """
        Block with button to open and edit measurement file
        """
        self.measurements_groupbox = QtWidgets.QGroupBox(
            'Измерения', maximumWidth=300)
        self.measurements_groupbox_layout = QtWidgets.QGridLayout()
        self.measurements_groupbox.setLayout(self.measurements_groupbox_layout)

        # self.measurements_groupbox_layout.addWidget(
        #     QtWidgets.QLabel('Measurement\ncycle file:'), 1, 0, 1, 1)
        self.choose_file = QtWidgets.QPushButton(
            'Выбрать файл',
            icon=QtGui.QIcon(self.get_res_path('res/open_folder.png')))  # &Choose file
        self.measurements_groupbox_layout.addWidget(self.choose_file,
                                                    0, 0, 3, 4)

        self.edit_file_button = QtWidgets.QPushButton('Открыть файл')  # &Open file
        self.measurements_groupbox_layout.addWidget(self.edit_file_button,
                                                    6, 0, 3, 4)

        self.measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel('Путь:'), 3, 0, 3, 1)  # Filepath
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
            self.filename_and_path_widget, 3, 1, 3, 3)
        # self.measurements_groupbox_layout.setSizeConstraint(
        # QtWidgets.QLayout.SizeConstraint.SetNoConstraint)

# ------ Saving results -------------------------------------------------------
      
        self.saving_measurements_groupbox_list: list[QtWidgets.QGroupBox] = []
        self.saving_result_folder_label_list: list[QtWidgets.QTextEdit] = []
        self.create_folder_checkbox_list: list[QtWidgets.QCheckBox] = []
        self.file_name_line_edit_list: list[QtWidgets.QLineEdit] = []
        self.choose_path_button_list: list[QtWidgets.QPushButton] = []

        for i in range(self.GYRO_NUMBER):
            self.append_gyro_widgets()

# ------ Output logs and data from file ---------------------------------------

        self.text_output_groupbox = QtWidgets.QGroupBox(
            'Содержимое файла', maximumWidth=315, minimumWidth=215)
        self.text_output_groupbox_layout = QtWidgets.QGridLayout()
        self.text_output_groupbox.setLayout(self.text_output_groupbox_layout)

        self.table_widget = PyQt_CustomWidgets.CustomTableWidget()

        self.text_output_groupbox_layout.addWidget(self.table_widget)

# ------ Logger ---------------------------------------------------------------
        """Logs widget"""
        self.logs_groupbox = QtWidgets.QGroupBox(
            'Лог', maximumWidth=315)  # Logs
        self.logs_groupbox_layout = QtWidgets.QVBoxLayout()
        self.logs_groupbox.setLayout(self.logs_groupbox_layout)

        self.log_text_box = PyQt_Logger.QTextEditLogger(
            self, file_log=FILE_LOG_FLAG)

        self.logs_groupbox_layout.addWidget(self.log_text_box.widget)

        self.clear_button = QtWidgets.QPushButton('Очистить')  # Clear logs
        self.logs_groupbox_layout.addWidget(self.clear_button)

        self.start_button = QtWidgets.QPushButton(
            'Старт', objectName="start_button")  # START
        self.stop_button = QtWidgets.QPushButton(
            'Стоп', enabled=False, objectName="stop_button")  # STOP

# ------ Others ------------------------------------------------------------
        # self.plot_groupbox = QtWidgets.QGroupBox('График', minimumWidth=395)
        self.plot_groupbox = QtWidgets.QGroupBox(minimumWidth=395)
        self.plot_groupbox_layout = QtWidgets.QGridLayout()
        self.plot_groupbox.setLayout(self.plot_groupbox_layout)

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
        self.plot_groupbox_layout.addWidget(
            self.save_image_button, 2, 0, 1, 6)
        self.save_settings_button = QtWidgets.QPushButton(
            'Сохранить\nнастройки')  # Save settings
        self.plot_groupbox_layout.addWidget(
            self.save_settings_button, 2, 6, 1, 6)
        # QToolButton # есть wordWrap
        self.autosave_checkbox = QtWidgets.QCheckBox(
            'Автосохранение\n     настроек')  # Autosave
        self.plot_groupbox_layout.addWidget(
            self.autosave_checkbox, 2, 12, 1, 6)

        self.check_box_list: list[QtWidgets.QCheckBox] = []
        self.check_box_list.append(
            QtWidgets.QCheckBox("encoder",
                                objectName="0", checked=True,
                                icon=QtGui.QIcon(self.get_res_path('res//white.png'))))
        for i in range(self.GYRO_NUMBER):
            self.check_box_list.append(
                QtWidgets.QCheckBox(
                    f"gyro {i + 1}", objectName=f"{i + 1}", checked=True,
                    icon=QtGui.QIcon(self.get_res_path(f'res//{self.ICON_LIST[i]}.png'))))
        for i in range(self.GYRO_NUMBER + 1):
            self.plot_groupbox_layout.addWidget(self.check_box_list[i],
                                            0, 5 * i, 1, 4)
                                            # 0, 5 * i, 1, 5 * (i + 1))

# ------ Set main grid --------------------------------------------------------
        self.main_grid_layout.addWidget(self.com_param_groupbox,
                                        0, 0, 1, 2)
        self.main_grid_layout.addWidget(self.fs_groupbox,
                                        1, 0, 1, 1)
        self.main_grid_layout.addWidget(self.cycle_number_groupbox,
                                        1, 1, 1, 1)
        self.main_grid_layout.addWidget(self.saving_measurements_groupbox_list[0],
                                        2, 0, 5, 2)
        self.main_grid_layout.addWidget(self.saving_measurements_groupbox_list[1],
                                        7, 0, 5, 2)
        self.main_grid_layout.addWidget(self.saving_measurements_groupbox_list[2],
                                        12, 0, 5, 2)
    
        self.main_grid_layout.addWidget(self.measurements_groupbox,
                                        6, 2, 4, 1)
        self.main_grid_layout.addWidget(self.text_output_groupbox,
                                        0, 2, 6, 1)
        self.main_grid_layout.addWidget(self.logs_groupbox,
                                        10, 2, 8, 1)
        self.main_grid_layout.addWidget(self.start_button,
                                        18, 2, 1, 1)
        self.main_grid_layout.addWidget(self.stop_button,
                                        19, 2, 1, 1)

        self.main_grid_layout.addWidget(self.custom_tab_plot_widget,
                                        0, 3, 16, 1)
        self.main_grid_layout.addWidget(self.plot_groupbox,
                                        16, 3, 4, 2)
        # self.setLayout(self.main_grid_layout)
        # self.layout = self.main_grid_layout

# ------ Style ----------------------------------------------------------------
        with open(self.get_res_path(STYLE_SHEETS_FILENAME), "r") as style_sheets:
            self.setStyleSheet(style_sheets.read())
        app_icon = QtGui.QIcon()
        for i in [16, 24, 32, 48]:
            app_icon.addFile(
                self.get_res_path(f'res\icon_{i}.png'), QtCore.QSize(i, i))
        self.setWindowIcon(app_icon)

# ------ Set settings --------------------------------------------------------------------------
        self.load_previous_settings(self.settings)

# ------ Signal Connect --------------------------------------------------------------------
        self.start_button.clicked.connect(self.measurement_start)
        self.stop_button.clicked.connect(self.stop)
        self.choose_file.clicked.connect(self.choose_and_load_file)
        self.cycle_num_widget.valueChanged.connect(self.cycle_num_value_change)
        self.cycle_num_widget.valueChanged.connect(self.progress_bar_set_max)
        self.save_image_button.clicked.connect(self.save_image)
        self.save_settings_button.clicked.connect(self.save_all_settings)
        # self.choose_path_button.clicked.connect(
        #     self.choose_result_saving_path)
        self.filename_and_path_widget.textChanged.connect(
            self.filename_and_path_text_change)
        self.clear_button.clicked.connect(
            lambda: self.log_text_box.widget.clear())
        self.edit_file_button.clicked.connect(
            lambda: os.startfile(self.filename_and_path_widget.toPlainText()))
        for i in range(self.GYRO_NUMBER):
            self.choose_path_button_list[i].clicked.connect(
                self.choose_result_saving_path)
        for i in range(self.GYRO_NUMBER + 1):
            self.check_box_list[i].stateChanged.connect(
                self.custom_tab_plot_widget.change_curve_visibility)
        
        # self.prosessing_thr.fft_for_file('', 1000)
        # print(list(filter(None, re.split("_|_|_|.|\n", "6021_135_4.4_1.txt"))))  D:\Gyro2023_Git
        # print(list(filter(None, re.split("_", f[-1])))[0])
        
        # from pandas import read_csv
        # time_data = np.array(read_csv("//fs/Projects/АФЧХ/6231/6231_165_7_2.txt", delimiter='\t',
                                    #   dtype=np.int32, header=None))
        self.show()
# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------
#
    def append_gyro_widgets(self):
        ind = len(self.saving_measurements_groupbox_list)
        self.saving_measurements_groupbox_list.append(QtWidgets.QGroupBox(
            f'Сохранение измерений gyro{ind + 1}',
            maximumWidth=300))
        saving_measurements_groupbox_layout = QtWidgets.QGridLayout()
        self.saving_measurements_groupbox_list[-1].setLayout(
            saving_measurements_groupbox_layout)

        saving_measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel('<b>Папка:</b>'), 0, 0, 3, 1)
        self.saving_result_folder_label_list.append(QtWidgets.QTextEdit(
            self.folder_name_list[ind],
            objectName="with_bourder"))
        # self.current_folder_label.setMinimumHeight(20)
        self.saving_result_folder_label_list[-1].setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff) 
        self.saving_result_folder_label_list[-1].setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored,
            QtWidgets.QSizePolicy.Policy.Ignored)
        saving_measurements_groupbox_layout.addWidget(
            self.saving_result_folder_label_list[-1], 0, 1, 3, 2)

        saving_measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel('Имя:'), 3, 0, 2, 1)
        self.file_name_line_edit_list.append(QtWidgets.QLineEdit(f'test{ind + 1}'))
        saving_measurements_groupbox_layout.addWidget(
            self.file_name_line_edit_list[-1], 3, 1, 2, 2)
        self.choose_path_button_list.append(QtWidgets.QPushButton(
            # 'Выбрать папку\nсохранения',
            icon=QtGui.QIcon(
                self.get_res_path(
                    f'res/open_folder_{self.ICON_LIST[ind]}.png'))))
        saving_measurements_groupbox_layout.addWidget(
            self.choose_path_button_list[-1], 5, 0, 1, 2)
        self.create_folder_checkbox_list.append(
            QtWidgets.QCheckBox('Cоздавать папку'))
        saving_measurements_groupbox_layout.addWidget(
            self.create_folder_checkbox_list[-1], 5, 2, 1, 1)  #

###############################################################################
#
# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------
    def measurement_start_test(self):
        for i in range(self.GYRO_NUMBER):
            self.make_filename(i)

        self.exp_package_num = 0
        self.progress_bar.setValue(0)
        self.progress_value = 0
        self.count = 0
        self.current_cylce = 1
        self.package_num = 0
        self.flag_sent = False
        if not self.check_filename():
            return
        if not self.total_time:
            self.cycle_num_value_change()
            if not self.choose_and_load_file():
                self.logger.info("No data from file")
                return
        self.logger.info("Data from file was loaded")
        self.cycle_num_value_change()
        self.progress_bar_set_max()
        self.set_avaliable_butttons(True)  # disable widgets
        self.logger.info(f"self.cycle_num = {self.total_cycle_num}")
        self.logger.warning("Start")
        self.custom_tab_plot_widget.clear_plots()
        self.custom_tab_plot_widget.append_fft_plot_tab() 
        from pandas import read_csv
        filename = 'all_prev/6884_139_6.2_4.txt'
        self.time_data_test = np.array(read_csv(filename, delimiter='\t',
                                      dtype=np.int32, header=None,  #,
                                      keep_default_na=False,
                                      na_filter=False,
                                      index_col=False,
                                      usecols=[1, 2, 3, 4],
                                      skiprows=2000))
        self.timer_sent_com.timeout.connect(self.timer_event_sent_com_test)
        self.timer_sent_com.timeout.disconnect(self.timer_event_sent_com)
        self.timer_recieve.timeout.connect(self.timer_read_event_test)
        self.timer_recieve.timeout.disconnect(self.timer_read_event)
        self.PLOT_TIME_INTERVAL_SEC = 20
        self.PAUSE_INTERVAL_MS = 4000
        self.start_time = time()
        self.timer_event_sent_com()
        self.timer_sent_com.start()
        self.timer_recieve.start()
        self.fs = int(self.fs_combo_box.currentText())
        self.custom_tab_plot_widget.fs = self.fs
        self.prosessing_thr.fs = self.fs
        self.prosessing_thr.flag_measurement_start = True
        self.prosessing_thr.TIMER_INTERVAL = self.READ_INTERVAL_MS
        self.prosessing_thr.num_measurement_rows = self.num_rows
        self.prosessing_thr.total_cycle_num = self.total_cycle_num
        self.prosessing_thr.start()

    @QtCore.pyqtSlot()
    def timer_read_event_test(self):
        self.read_serial_test()

    def read_serial_test(self):
        self.progress_value = time() - self.start_time
        self.progress_bar.setValue(int(round(self.progress_value)))
        data: bytearray = b""
        for i in range(200):
            data += int.to_bytes(0x72, length=1, byteorder='big')
            data += int.to_bytes(int(self.time_data_test[self.package_num + i, 0]), length=3, byteorder='big', signed=True)
            data += int.to_bytes(int(self.time_data_test[self.package_num + i, 1]), length=3, byteorder='big', signed=True)
            data += int.to_bytes(int(self.time_data_test[self.package_num + i, 2]), length=3, byteorder='big', signed=True)
            data += int.to_bytes(int(self.time_data_test[self.package_num + i, 3]), length=3, byteorder='big', signed=True)
            data += int.to_bytes(0x27, length=1, byteorder='big')
        self.prosessing_thr.rx = data
        self.prosessing_thr.flag_recieve = True
        self.prosessing_thr.count_fft_frame = self.count
        self.prosessing_thr.flag_sent = self.flag_sent
        self.logger.info(f"thr_start, count = {self.count}")

    @QtCore.pyqtSlot()
    def timer_event_sent_com_test(self):
        if self.flag_sent:
            self.logger.info(f"count = {self.count}, num_rows={self.num_rows}")
            if self.count >= self.num_rows:
                if self.current_cylce < self.total_cycle_num:
                    self.new_cycle_event()
                    # self.timer_sent_com.setInterval(self.PAUSE_INTERVAL_MS)
                else:
                    self.stop()
                return
        if self.flag_sent:
            self.sent_vibro_command_test()
        else:
            self.timer_sent_com.setInterval(self.PAUSE_INTERVAL_MS)
        self.flag_sent = not self.flag_sent
        self.logger.info("---end_sent_command")

    def sent_vibro_command_test(self):
        self.table_widget.selectRow(self.count)
        self.timer_sent_com.setInterval(self.table_widget.get_T())
        self.count += 1

###########################################################################################
#
###########################################################################################
#
###########################################################################################

    @QtCore.pyqtSlot(bool)
    def run_thread_for_file_prosessing(self, _):
        self.logger.info(f"files: {self.custom_tab_plot_widget.filenames_to_fft}")
        if self.prosessing_thr.isRunning():
            return
        # self.prosessing_thr.TIMER_INTERVAL = self.READ_INTERVAL_MS
        # self.prosessing_thr.num_measurement_rows = self.num_rows
        # self.prosessing_thr.total_cycle_num = self.total_cycle_num
        # self.prosessing_thr.fs = 1000
        if len(self.custom_tab_plot_widget.filenames_to_fft):
            self.custom_tab_plot_widget.clear_plots()
            self.check_filename()
            self.fs = int(self.fs_combo_box.currentText())
            # Copy variables to another classes and start thread
            self.custom_tab_plot_widget.fs = self.fs
            self.prosessing_thr.fs = self.fs
            self.prosessing_thr.folder = self.folder_name ###################################################

            self.prosessing_thr.flag_by_name = True
            # self.prosessing_thr.flag_all = True
            self.prosessing_thr.filenames_to_fft = self.custom_tab_plot_widget.filenames_to_fft
            self.prosessing_thr.start()
        if False:
            path = 'sencors_nums.txt'
            self.prosessing_thr.folder = self.folder_name
            self.prosessing_thr.flag_all = True

    @QtCore.pyqtSlot()
    def measurement_start(self):
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
        # if not self.check_filename():
            # return
        for i in range(self.GYRO_NUMBER):
            self.make_filename(i)

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
        self.set_avaliable_butttons(True)  # disable widgets

        self.logger.info(f"{self.combo_box_name.currentText()} open")
        self.logger.info(f"self.cycle_num = {self.total_cycle_num}")
        self.logger.warning("Start")

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
        self.prosessing_thr.flag_measurement_start = True
        self.prosessing_thr.TIMER_INTERVAL = self.READ_INTERVAL_MS
        self.prosessing_thr.num_measurement_rows = self.num_rows
        self.prosessing_thr.total_cycle_num = self.total_cycle_num
        self.prosessing_thr.start()

        self.custom_tab_plot_widget.clear_plots()
        self.custom_tab_plot_widget.append_fft_plot_tab() 
# ------ Timer Recieve --------------------------------------------------------
    @QtCore.pyqtSlot()
    def timer_read_event(self):
        """Read data from COM port.
        Generate warning if avaliable less than 14 bytes"""
        self.read_serial()
        # self.progress_value += self.READ_INTERVAL_MS/1000
        # self.progress_value = time() - self.start_time
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
        self.progress_bar.setValue(int(round(self.progress_value)))
        self.logger.info(f"Progress: {self.progress_value}")
        # !!!
        self.exp_package_num += int(bytes_num/14)
        self.logger.info(
            f"ready to read, bytes num = {bytes_num}," +
            f"expected package num {self.exp_package_num}")
        self.copy_variables_to_thread()
        self.logger.info(f"command thr to start, count = {self.count}")

    def copy_variables_to_thread(self):
        self.prosessing_thr.rx = self.Serial.readAll().data()
        self.prosessing_thr.flag_recieve = True
        self.prosessing_thr.count_fft_frame = self.count
        self.prosessing_thr.flag_sent = self.flag_sent

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
                    self.new_cycle_event()
                    self.sent_stop_vibro_command()
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
        # self.table_widget.selectRow(self.count)
        self.table_widget.select_row(self.count)
        F = int.to_bytes(self.table_widget.get_F(),
                         length=2, byteorder='little', signed=False)
        A = int.to_bytes(self.table_widget.get_A(),
                         length=2, byteorder='little', signed=False)
        # F = int.to_bytes(int(self.table_widget.item(self.count, 0).data(
        #     QtCore.Qt.ItemDataRole.EditRole)),
        #                  length=2, byteorder='little', signed=False)
        # A = int.to_bytes(int(self.table_widget.item(self.count, 1).data(
        #     QtCore.Qt.ItemDataRole.EditRole)),
        #                  length=2, byteorder='little', signed=False)
        self.Serial.write(
            bytes([77, 0, F[0], F[1], A[0], A[1], 0, 0]))
        
        self.timer_sent_com.setInterval(self.table_widget.get_T())
        # self.timer_sent_com.setInterval(
            # int(self.table_widget.item(
                # self.count, 2).data(QtCore.Qt.ItemDataRole.EditRole)) * 1000)
        self.count += 1
        self.logger.info("- Command was sent -")

# ----- End cycle, stop, etc --------------------------------------------------
    def new_cycle_event(self):
        self.logger.warning(
            f"End of cycle {self.current_cylce} of {self.total_cycle_num}")
        self.current_cylce += 1
        self.count = 0
        self.custom_tab_plot_widget.append_fft_plot_tab()
        self.prosessing_thr.new_cycle()

    def stop(self):
        self.set_avaliable_butttons(False)
        if self.timer_sent_com.isActive():
            self.timer_sent_com.stop()

        if self.timer_recieve.isActive():
            self.timer_recieve.stop()

        self.logger.info(
            f"% = {self.progress_value}, " +
            f"total time = {self.progress_bar.maximum()}")

        if self.Serial.isOpen():
            self.Serial.write(bytes([0, 0, 0, 0, 0, 0, 0, 0]))
            self.logger.info("COM close? " +
                             str(self.Serial.waitForBytesWritten(250)))
            self.Serial.close()
            self.logger.warning("End of measurements\n")
            if self.progress_value > 2:
                check = int(self.package_num / self.progress_value)
                if not (0.95 * self.fs < check < 1.05 * self.fs):
                    QtWidgets.QMessageBox.critical(
                        None, "Warning",
                        f"You set fs = {self.fs} Hz," +
                        f"but in fact it's close to {check} Hz")
        self.prosessing_thr.flag_measurement_start = False

###############################################################################
# ----- plotting --------------------------------------------------------------

    @QtCore.pyqtSlot(int)  # почему-то плохо работает, только через 10 секунд начинает выводить график
    def plot_time_graph(self, s):
        self.package_num = s
        self.package_num_label.setText(str(self.package_num))

        points_shown = self.PLOT_TIME_INTERVAL_SEC * self.fs
        start_i = (self.package_num - points_shown
                   if self.package_num > points_shown else 0)
        self.logger.info(f"thr_stop, count = {self.count}\n" +
                         f"package_num = {self.package_num} ")
        self.custom_tab_plot_widget.plot_time_graph(
            self.prosessing_thr.time_data[start_i:self.package_num, 0] / self.fs,
            self.prosessing_thr.time_data[start_i:self.package_num, 2] / 1000,
            self.prosessing_thr.time_data[start_i:self.package_num, 1]
            / self.prosessing_thr.k_amp / 1000)

    @QtCore.pyqtSlot(bool)
    def plot_fft(self, _):
        """Adds points to frequency graphs"""
        self.custom_tab_plot_widget.set_fft_data(
            self.prosessing_thr.amp_and_freq_for_plot,
            self.prosessing_thr.bourder, self.fs)
        self.logger.info("plot_fft")

    @QtCore.pyqtSlot(str)
    def plot_fft_final(self, name):
        self.logger.info("Final median plot")
        self.custom_tab_plot_widget.set_fft_median_data(
            self.prosessing_thr.amp_and_freq[:, -4:],
            self.prosessing_thr.special_points, name)

    @QtCore.pyqtSlot()
    def save_image(self):  # ???
        self.logger.info("Save image")
        # if self.check_filename():
        # if self.check_filename():
        self.custom_tab_plot_widget.save_plot_image(
            self.prosessing_thr.filename_new[0])
        self.custom_tab_plot_widget.save_plot_image(
            self.prosessing_thr.filename_new[1])
        self.custom_tab_plot_widget.save_plot_image(
            self.prosessing_thr.filename_new[2])
        self.logger.info("Saving complite")

# ------ Widgets events -------------------------------------------------------

    def cycle_num_value_change(self):
        # if not self.timer_recieve.isActive():  # is this required?
        self.total_cycle_num = self.cycle_num_widget.value()

    def progress_bar_set_max(self):
        if self.total_time and not self.timer_recieve.isActive():  # is this required?
            self.total_cycle_num = self.cycle_num_widget.value()
            self.progress_bar.setMaximum(int(
                self.total_cycle_num * (self.total_time +
                 self.num_rows * self.PAUSE_INTERVAL_MS / 1000 +
                 self.PAUSE_INTERVAL_MS / 1000)))
            # self.progress_bar.setValue(0)

    def set_avaliable_butttons(self, flag_running: bool):
        """Enable or disable widgets"""
        self.cycle_num_widget.setDisabled(flag_running)
        self.edit_file_button.setDisabled(flag_running)
        self.save_image_button.setDisabled(flag_running)
        self.start_button.setDisabled(flag_running)
        self.stop_button.setDisabled(not flag_running)
        self.choose_file.setDisabled(flag_running)

    def get_avaliable_com(self):
        """Append avaliable com ports to combo box widget"""
        self.combo_box_name.addItems(
              [ports.portName() 
               for ports in QSerialPortInfo.availablePorts()])

# ------ file name and data from file -----------------------------------------
    # по идее надо сразу при постановке
    def make_filename(self, i):
        if not len(self.file_name_line_edit_list[i].text()):
            return ''

        folder = ''
        if self.create_folder_checkbox_list[i].isChecked():
            folder = re.split("_", self.file_name_line_edit_list[i].text())[0]
            # if not os.path.isdir(folder):  # ? будет ли это работать, надо ведь путь добавить
            if not os.path.isdir(self.folder_name_list[i] + folder):  # ? будет ли это работать, надо ведь путь добавить
                os.mkdir(self.folder_name_list[i] + folder)
                # os.mkdir(folder)
            folder += '/'
        # self.filename_new[i] = self.folder_name_list[i] + folder + self.file_name_line_edit_list[i].text()
        self.prosessing_thr.filename_new[i] = \
            self.folder_name_list[i] + folder + self.file_name_line_edit_list[i].text()
        # self.filename_new_for_fft[i] = self.filename_new[i] + f'%_{self.total_cycle_num}%.txt_FRQ_AMP_dPh_{self.fs}Hz.txt'
        self.prosessing_thr.filename_new_for_fft[i] = \
            self.filename_new[i] + f'%_{self.total_cycle_num}%.txt_FRQ_AMP_dPh_{self.fs}Hz.txt'
        # self.saving_result_folder_label_list[i].setText(self.folder_name + folder)
        # self.saving_result_folder_label_list[i].setText(self.folder_name)
        # return filename
        
    def check_filename(self):  # changed for three files
        i = 0
        # print( os.path.exists(self.current_folder_label.())) 
        if not os.path.exists(self.saving_result_folder_label_list[-1].toPlainText()):  # text
            QtWidgets.QMessageBox.critical(
                None, "Error", "The file path does not exist!")
            return False
        if not len(self.file_name_line_edit_list[i].text()):
            filename = self.folder_name_list[i] + 'test'
        else:
            filename = self.folder_name_list[i] + self.file_name_line_edit_list[i].text()

        self.prosessing_thr.fft_filename = filename + \
            f'%_{self.total_cycle_num}%.txt_FRQ_AMP_dPh_{self.fs}Hz.txt'

        extension = '.txt'
        if self.create_folder_checkbox_list[i].isChecked():
            folder = re.split("_", self.file_name_line_edit_list[i].text())[0]
            if not os.path.isdir(folder):
                os.mkdir(folder)
            filename = self.folder_name_list[i] + folder + '/' + self.file_name_line_edit_list[i].text()
            self.saving_result_folder_label_list[-1].setText(self.folder_name_list[i] + folder + '/')

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
    
    # @staticmethod
    # def check_name_simple(name):
    #     basename = os.path.splitext(name)[0]
    #     extension = os.path.splitext(name)[1]
    #     i = 0
    #     while os.path.exists(name):
    #         i += 1
    #         name = basename + f"({i})" + extension
    #     return name

    # def directory_changed(self, path):
    #     self.logger.info(f'Directory Changed: {path}')
    #     print(f'Directory Changed: {path}')

    @QtCore.pyqtSlot()
    def choose_result_saving_path(self):
        for i in range(3):
            if self.sender() == self.choose_path_button_list[i]:
                break
        else:
            return
        temp = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Выбрать папку", ".")
        if not len(temp):
            return
        self.folder_name_list[i] = temp + '/'
        self.saving_result_folder_label_list[i].setText(
            self.folder_name_list[i])

    @QtCore.pyqtSlot(str)
    def check_filename_and_get_data(self, path):
        """Вызывается при изменении файла"""
        self.logger.info(
            f'File Changed, {path},' +
            f'thr run: {self.prosessing_thr.flag_measurement_start}')
        if not self.prosessing_thr.flag_measurement_start and os.path.exists(path):
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
            self.table_widget.setRowCount(0)
            for line in file:
                f_a_t = list(filter(None, re.split("F|A|T|\n", line)))
                if (len(f_a_t) == 3 and f_a_t[0].isdecimal() and
                    f_a_t[1].isdecimal() and f_a_t[2].isdecimal()):

                    self.table_widget.add_and_fill_row(f_a_t)
            self.total_time = self.table_widget.total_time
            self.num_rows = self.table_widget.rowCount()
            self.progress_bar_set_max()
        return self.total_time > 0

    # @QtCore.pyqtSlot()
    # def open_file(self):
    #     os.startfile(self.filename_and_path_widget.toPlainText())

    @staticmethod
    def get_res_path(relative_path):
        """
        Get absolute path to resource, works with PyInstaller
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

# ------ settings --------------------------------------------------------------------

    def save_all_settings(self):
        self.com_boderate_combo_box.save_all()
        self.fs_combo_box.save_all()
        self.combo_box_name.save_current_text()
        self.settings.setValue("cycle_num",
                                self.cycle_num_widget.value())
        self.settings.setValue("filename",
                                self.filename_and_path_widget.toPlainText())
        # self.settings.setValue("current_folder", self.folder_name) ###############################################
        self.settings.setValue("current_folders", self.folder_name_list)
                            #    self.saving_result_folder_label.toPlainText())  # text
        # print('save' + str(self.custom_tab_plot_widget.dict))
        self.settings.setValue('dict', self.custom_tab_plot_widget.dict)
        # print([checkbox.isChecked() 
                                # for checkbox in self.create_folder_checkbox_list])
        self.settings.setValue('create_folder_flag',
                               [int(checkbox.isChecked()) 
                                for checkbox in self.create_folder_checkbox_list])

    def load_previous_settings(self, settings: QtCore.QSettings):
        if settings.contains("cycle_num"):
            self.cycle_num_widget.setValue(
                settings.value("cycle_num"))
        if settings.contains("autosave"):
            self.autosave_checkbox.setChecked(
                settings.value("autosave"))
        if settings.contains("filename"):
            name = settings.value("filename")
            if os.path.exists(name):
                self.filename_and_path_widget.setText(name)
                if self.get_data_from_file(name):
                    self.logger.warning("The previous file is loaded")
                self.filename_path_watcher = self.filename_and_path_widget.toPlainText()  # os.path.basename(filename)
                self.fs_watcher.addPath(self.filename_path_watcher)
        # if settings.contains("current_folder"):
        #     if os.path.isdir(settings.value("current_folder")):
        #         # self.saving_result_folder_label.setText(
        #         self.saving_result_folder_label_list[-1].setText(  #########################################################
        #             settings.value("current_folder"))
        #         self.folder_name = settings.value("current_folder")
        if settings.contains("create_folder_flag"):
            # print(settings.value("create_folder_flag"))
            # print(settings.value("create_folder_flag")[1])
            for i in range(self.GYRO_NUMBER):
                self.create_folder_checkbox_list[i].setChecked(
                    int(settings.value("create_folder_flag")[i]))
            
        if settings.contains("current_folders"):
            i = 0
            # for folder in settings.value("current_folders"):
            for i in range(self.GYRO_NUMBER):
                if os.path.isdir(settings.value("current_folders")[i]):
                    # self.saving_result_folder_label.setText(
                    self.saving_result_folder_label_list[i].setText(  #########################################################
                        settings.value("current_folders")[i])
                    self.folder_name_list[i] = settings.value("current_folders")[i]
                    i += 1
        if self.settings.contains('dict'):
            # self.settings.setValue('dict', self.custom_tab_plot_widget.dict)
            self.custom_tab_plot_widget.dict = self.settings.value('dict')
            # self.custom_tab_plot_widget.test_combo_box.addItems(self.custom_tab_plot_widget.dict.keys())
            if self.custom_tab_plot_widget.dict:
                self.custom_tab_plot_widget.projects_combo_box.addItems(self.custom_tab_plot_widget.dict.keys())
                for i in range(self.custom_tab_plot_widget.projects_combo_box.count()):
                    self.custom_tab_plot_widget.projects_combo_box.setItemData(
                        i, self.custom_tab_plot_widget.dict.get(
                            self.custom_tab_plot_widget.projects_combo_box.itemText(i)),
                        QtCore.Qt.ItemDataRole.ToolTipRole)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
#
###############################################################################
#
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

test = True
test = False
if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)
    window = AppWindow()
    # window.resize(850, 500)
    # здесь добавляю событие таймера 2,
    # в котором происходит запись считанной из файла информации в поток, 
    # как если бы данные реально шли
    if test:
        window.start_button.clicked.disconnect(window.measurement_start)
        window.start_button.clicked.connect(window.measurement_start_test)
    sys.exit(app.exec())