import logging
import sys
import os
import re
import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo
from time import time, sleep
import PyQt_Logger
import PyQt_Thread
import PyQt_CustomWidgets
from PyQt_Functions import get_icon_by_name, get_res_path, natural_keys

# import time

# путь к прошивке
# D:\FromPrevComputer\Vibrostand\ProgramAndLoager\ARM_vibro(VibroStend_16bit)_v1.2_1000_0184_1000Hz\Debug
# d:/Gyro2023_Git/venv3.6/Scripts/Activate.bat
# git add PyQt_ApplicationClass.py PyQt_CustomWidgets.py PyQt_Thread.py PyQt_Logger.py PyQt_Functions.py
# pyinstaller PyQt_ApplicationOnefolder.spec
# pyinstaller PyQt_Application.spec 
# pyinstaller --onefile --noconsole PyQt_Application.py
# D:\Gyro2023_Git\venv3.6\Lib\site-packages\PyQt5\Qt5\qml\QtQuick\Controls\GroupBox.qml
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class AppWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        QtWidgets.QApplication.setAttribute(
            QtCore.Qt.ApplicationAttribute.
            AA_UseStyleSheetPropagationInWidgetStyles,
            True)  # наследование свойств оформления потомков от родителей
        self.setWindowTitle("GyroVibroTest") # в названии номер стенда писать
        # print(QtWidgets.QStyleFactory.keys())
        QtWidgets.QApplication.setStyle('Fusion')  # 'Fusion' 'Windows' 'windowsvista' ... QtWidgets.QStyle
# ------ GUI ------------------------------------------------------------------
        # widget = QtWidgets.QWidget(objectName="size16px")
        widget = QtWidgets.QWidget()
        self.main_grid_layout = QtWidgets.QGridLayout(widget, spacing=2)
        self.setCentralWidget(widget)
# ------ Init vars ------------------------------------------------------------
        self.GYRO_NUMBER = 1
        # self.GYRO_NUMBER = 3
        self.PLOT_TIME_INTERVAL_SEC = 10
        self.PAUSE_INTERVAL_MS = 750
        self.READ_INTERVAL_MS = 100 * 2  #  125 * 2
        # self.folder_name_list = [os.getcwd() + '/'] * self.GYRO_NUMBER
        self.folder_name_list = [''] * self.GYRO_NUMBER
        self.count: int = 0
        self.progress_value = 0 # убрать?
        self.total_cycle_num: int = 1
        self.current_cylce: int = 0
        self.flag_sent = False
        self.filename_path_watcher = ""
        STYLE_SHEETS_FILENAME = 'res\StyleSheets.css'
        FILE_LOG_FLAG = True
        # FILE_LOG_FLAG = False
        DEBUG_ENABLE_FLAG = True
        # DEBUG_ENABLE_FLAG = False
        LOGGER_NAME = 'main'
        self.ICON_COLOR_LIST = ['red', 'green', 'blue']
        self.serial_port = QSerialPort(dataBits=QSerialPort.DataBits.Data8,
                                       stopBits=QSerialPort.StopBits.OneStop,
                                       parity=QSerialPort.Parity.NoParity)
# ------ Logger ---------------------------------------------------------------
        self.log_text_box = PyQt_Logger.QTextEditLogger(
            self, file_log=FILE_LOG_FLAG, debug_enable=DEBUG_ENABLE_FLAG)
        self.logger = logging.getLogger('main')
        self.logger.debug("Начало загрузки")
# ------ Settings -------------------------------------------------------------
        self.settings = QtCore.QSettings(
            get_res_path('config.ini'), QtCore.QSettings.Format.IniFormat)
        self.settings.setIniCodec("UTF-8")
# ------ Style ----------------------------------------------------------------
        with open(get_res_path(STYLE_SHEETS_FILENAME),
                  "r") as style_sheets_css_file:
            self.setStyleSheet(style_sheets_css_file.read())
        app_icon = QtGui.QIcon()
        for i in [16, 24, 32, 48]:
            app_icon.addFile(
                get_res_path(f'res\icon_{i}.png'), QtCore.QSize(i, i))
        self.setWindowIcon(app_icon)

# ------ Timres ---------------------------------------------------------------
        self.timer_recieve = QtCore.QTimer(interval=self.READ_INTERVAL_MS)
        self.timer_recieve.timeout.connect(self.timer_read_event)
        self.timer_sent_com = QtCore.QTimer(
            timerType=QtCore.Qt.TimerType.PreciseTimer)
        self.timer_sent_com.timeout.connect(self.timer_event_sent_com)
# ------ File watcher ---------------------------------------------------------
        self.file_watcher = QtCore.QFileSystemWatcher()
        # self.fs_watcher.directoryChanged.connect(self.directory_changed)
        self.file_watcher.fileChanged.connect(self.check_filename_and_get_data)
# ------ Thread ---------------------------------------------------------------
        self.processing_thr = PyQt_Thread.SecondThread(
            gyro_number=self.GYRO_NUMBER,
            READ_INTERVAL_MS=self.READ_INTERVAL_MS,
            logger_name=LOGGER_NAME)
        self.processing_thr.package_num_signal.connect(self.get_and_show_data_from_thread)
        self.processing_thr.fft_data_signal.connect(self.plot_fft)
        self.processing_thr.median_data_ready_signal.connect(
            self.plot_fft_final)
        self.processing_thr.warning_signal.connect(
            lambda text: self.logger.warning(text))
        # self.custom_tab_plot_widget.filenames_list_emit.connect(
# ------ Plots in tab widget --------------------------------------------------
        # долго грузится (2.5 секунды); скорее всего, из-за сом объекта  # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        self.custom_tab_plot_widget = PyQt_CustomWidgets.CustomTabWidget(
            GYRO_NUMBER=self.GYRO_NUMBER, logger_name=LOGGER_NAME)  # !
        self.custom_tab_plot_widget.warning_signal.connect(
            lambda text: self.logger.warning(text))
        self.custom_tab_plot_widget.get_filename_signal.connect(
            self.run_thread_for_file_processing
        )
# ------ Menu -----------------------------------------------------------------
        menu_bar = self.menuBar()
        options_menu = menu_bar.addMenu("&Options")
        self.settings_autosave_action = QtWidgets.QAction(
            "&Settings autosave", self, checkable=True)
        self.settings_autosave_action.setChecked(True)
        # self.settings_autosave_action.setIcon(get_icon_by_name('ok'))
        options_menu.addAction(self.settings_autosave_action)

        self.save_settings_action = QtWidgets.QAction(
            "&Save current settings", self)
        self.save_settings_action.triggered.connect(self.save_all_settings)        
        options_menu.addAction(self.save_settings_action)   
        plots_to_png_action = QtWidgets.QAction("&Plots to .png", self)
        plots_to_png_action.setShortcut("Ctrl+P")
        plots_to_png_action.triggered.connect(self.save_image)        
        options_menu.addAction(plots_to_png_action)

        self.save_action = QtWidgets.QAction("&Save last data", self)
        # exit_action.setShortcut("Ctrl+Q")
        # exit_action.setStatusTip("Exit application")  # ???
        self.save_action.triggered.connect(self.save_results)
        options_menu.addSeparator()
        options_menu.addAction(self.save_action)

        # load_ini_action = QtWidgets.QAction("&Load ini", self)
        # # exit_action.setShortcut("Ctrl+Q")
        # # exit_action.setStatusTip("Exit application")  # ???
        # load_ini_action.triggered.connect(self.load_ini)
        # options_menu.addSeparator()
        # options_menu.addAction(load_ini_action)

        # gyro_count_action = QtWidgets.QAction("&Check gyro count", self)
        # # exit_action.setShortcut("Ctrl+Q")
        # # exit_action.setStatusTip("Exit application")  # ???
        # gyro_count_action.triggered.connect(self.get_gyro_count)
        # options_menu.addSeparator()
        # options_menu.addAction(gyro_count_action)

        self.measurement_action = QtWidgets.QAction("&Считать данные без сохранения", self)
        self.measurement_action.triggered.connect(self.measurement_start)
        options_menu.addSeparator()
        options_menu.addAction(self.measurement_action)

        exit_action = QtWidgets.QAction("&Exit", self)
        # exit_action.setShortcut("Ctrl+Q")
        # exit_action.setStatusTip("Exit application")  # ???
        exit_action.triggered.connect(self.close)
        options_menu.addSeparator()
        options_menu.addAction(exit_action)

        # меню будет видно 
        if self.GYRO_NUMBER == 1:
            mode_menu = menu_bar.addMenu("&Mode")  # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            self.gyro1_4_action = QtWidgets.QAction(
                "&Получать все данные по RboxV1", self, checkable=True)
            self.gyro1_4_action.triggered.connect(self.gyro1_4)
            # mode_menu.addSeparator()
            mode_menu.addAction(self.gyro1_4_action)
            # gyro1_2_action = QtWidgets.QAction("&Пакет из 2 значений", self)
            # gyro1_2_action.triggered.connect(self.gyro1_2)
            # mode_menu.addSeparator()
            # mode_menu.addAction(gyro1_2_action)
            # gyro3_2_action = QtWidgets.QAction("&Exit", self)
            # gyro3_2_action.triggered.connect(self.gyro3_2)
            # mode_menu.addSeparator()
            # mode_menu.addAction(gyro3_2_action)
# ------ Com Settings ---------------------------------------------------------
        """
        Block with COM port settings and sampling frequency selection
        """
        self.com_param_groupbox = QtWidgets.QGroupBox(
            'Настройки COM порта', maximumWidth=320)
        com_param_groupbox_layout = QtWidgets.QGridLayout()
        self.com_param_groupbox.setLayout(com_param_groupbox_layout)

        self.com_port_name_combobox = PyQt_CustomWidgets.CustomComboBox(
            settings=self.settings,
            # default_items_list=['222', '4444', '000'],
            settings_name="COM_name_settings",
            editable_flag=False, uint_validator_enable=False)
        self.get_avaliable_com()
        self.com_port_name_combobox.get_ind()
        self.com_port_name_combobox.setContextMenuPolicy(
            QtCore.Qt.CustomContextMenu)
        self.com_port_name_combobox.customContextMenuRequested.connect(
            self.__contextMenu)
        # com_param_groupbox_layout.addWidget(QtWidgets.QLabel('COM:'),
                                                #  0, 0, 1, 1)
        com_param_groupbox_layout.addWidget(self.com_port_name_combobox,
                                                 0, 0, 1, 1)

        self.com_boderate_combo_box = PyQt_CustomWidgets.CustomComboBox(
            settings=self.settings,
            settings_name="COM_speed_settings",
            default_items_list=['921600', '115200', '0'])
        # com_param_groupbox_layout.addWidget(QtWidgets.QLabel('Скорость:'),
                                                #  1, 0, 1, 1)  # Speed
        com_param_groupbox_layout.addWidget(self.com_boderate_combo_box,
                                                 0, 1, 1, 1)
# ------  fs  -----------------------------------------------------
        self.fs_groupbox = QtWidgets.QGroupBox(
            'Fs, Гц', maximumWidth=160)
        fs_groupbox_layout = QtWidgets.QHBoxLayout()
        self.fs_groupbox.setLayout(fs_groupbox_layout)
        self.fs_combo_box = PyQt_CustomWidgets.CustomComboBox(
            settings=self.settings,
            settings_name="fs_settings",
            default_items_list=['1000', '2000', '741'])
        self.fs = int(self.fs_combo_box.currentText())
        fs_groupbox_layout.addWidget(self.fs_combo_box)
# ------  cycle num  ----------------------------------------------------------
        self.cycle_number_groupbox = QtWidgets.QGroupBox(
            'Циклы:', maximumWidth=160)
        self.cycle_number_groupbox_layout = QtWidgets.QHBoxLayout()
        self.cycle_number_groupbox.setLayout(self.cycle_number_groupbox_layout)

        self.cycle_num_spinbox = QtWidgets.QSpinBox(
            minimum=1, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
        # self.cycle_number_groupbox_layout.addWidget(
            # QtWidgets.QLabel(''), 0, 0, 3, 2)  # Cycle number
        self.cycle_number_groupbox_layout.addWidget(self.cycle_num_spinbox)
# ------ Measurement File -----------------------------------------------------
        """
        Block with button to open and edit measurement file
        """
        self.measurements_groupbox = QtWidgets.QGroupBox(
            'Измерения', maximumWidth=320)
        measurements_groupbox_layout = QtWidgets.QGridLayout()
        self.measurements_groupbox.setLayout(measurements_groupbox_layout)

        # measurements_groupbox_layout.addWidget(
        #     QtWidgets.QLabel('Measurement\ncycle file:'), 1, 0, 1, 1)
        self.choose_file = QtWidgets.QPushButton(
            'Выбрать',
            icon=get_icon_by_name('open_folder'))  # &Choose file
        measurements_groupbox_layout.addWidget(self.choose_file,
                                                    3, 0, 1, 2)

        self.edit_file_button = QtWidgets.QPushButton('Открыть')  # &Open file
        measurements_groupbox_layout.addWidget(self.edit_file_button,
                                                    3, 2, 1, 2)

        measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel('Путь:'), 0, 0, 3, 1)  # Filepath

        self.filename_and_path_textedit = QtWidgets.QTextEdit(
            objectName="with_bourder")
        self.filename_and_path_textedit.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff) 
        self.filename_and_path_textedit.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored,
            QtWidgets.QSizePolicy.Policy.Ignored)
        measurements_groupbox_layout.addWidget(
            self.filename_and_path_textedit, 0, 1, 3, 3)
        # measurements_groupbox_layout.setSizeConstraint(
        # QtWidgets.QLayout.SizeConstraint.SetNoConstraint)

# ------ Saving results -------------------------------------------------------
      
        self.saving_measurements_groupbox_list: list[QtWidgets.QGroupBox] = []
        self.saving_result_folder_label_list: list[QtWidgets.QTextEdit] = []
        self.create_folder_checkbox_list: list[QtWidgets.QCheckBox] = []
        self.file_name_line_edit_list: list[QtWidgets.QLineEdit] = []
        self.choose_path_button_list: list[QtWidgets.QPushButton] = []

        self.saving_measurements_groupbox = QtWidgets.QGroupBox(
            maximumWidth=320) # , minimumHeight=110)
        saving_measurements_groupbox_layout = QtWidgets.QGridLayout()
        self.saving_measurements_groupbox.setLayout(
            saving_measurements_groupbox_layout)
        
        for i in range(self.GYRO_NUMBER):
            self.append_gyro_widgets()
            saving_measurements_groupbox_layout.addWidget(
                self.saving_measurements_groupbox_list[i], i, 0, 1, 1)
# ------ Output logs and data from file ---------------------------------------

        self.text_output_groupbox = QtWidgets.QGroupBox(
            'Содержимое файла', maximumWidth=350, minimumWidth=150)
        text_output_groupbox_layout = QtWidgets.QGridLayout()
        self.text_output_groupbox.setLayout(text_output_groupbox_layout)

        self.table_widget = PyQt_CustomWidgets.CustomTableWidget()
        text_output_groupbox_layout.addWidget(self.table_widget)
# ------ Logger ---------------------------------------------------------------

        """Logs widget"""
        self.logs_groupbox = QtWidgets.QGroupBox(
            'Лог', maximumWidth=350)  # Logs
        logs_groupbox_layout = QtWidgets.QVBoxLayout()
        self.logs_groupbox.setLayout(logs_groupbox_layout)

        logs_groupbox_layout.addWidget(self.log_text_box.widget)

        self.logs_clear_button = QtWidgets.QPushButton('Очистить')  # Clear logs
        logs_groupbox_layout.addWidget(self.logs_clear_button)

        self.start_all_button = QtWidgets.QPushButton(
            'Старт', objectName="start_button")  # START
        self.start_all_button.installEventFilter(self)
        self.stop_button = QtWidgets.QPushButton(
            'Стоп', enabled=False, objectName="stop_button")  # STOP
        self.stop_button.installEventFilter(self)
# ------ Others ------------------------------------------------------------
        self.plot_groupbox = QtWidgets.QGroupBox(minimumWidth=160)
        plot_groupbox_layout = QtWidgets.QGridLayout()
        self.plot_groupbox.setLayout(plot_groupbox_layout)

        self.check_box_list: list[QtWidgets.QCheckBox] = []
        self.check_box_list.append(
            QtWidgets.QCheckBox("encoder",
                                objectName="0", checked=True,
                                icon=get_icon_by_name('white')))
        for i in range(self.GYRO_NUMBER):
            self.check_box_list.append(
                QtWidgets.QCheckBox(
                    f"gyro {i + 1}", objectName=f"{i + 1}", checked=True,
                    icon=get_icon_by_name(self.ICON_COLOR_LIST[i])))
        for i in range(self.GYRO_NUMBER + 1):
            plot_groupbox_layout.addWidget(self.check_box_list[i],
                                                0, 5 * i, 1, 4)

        self.progress_bar = QtWidgets.QProgressBar(
            format='%v/%m сек', maximum=1, value=self.progress_value)  # sec
        plot_groupbox_layout.addWidget(self.progress_bar,
                                            1, 0, 1, 13)

        package_number_label = QtWidgets.QLabel('Пакеты:')  # Package number
        plot_groupbox_layout.addWidget(package_number_label,
                                            1, 13, 1, 4)
        self.package_num_label = QtWidgets.QLabel('0')
        plot_groupbox_layout.addWidget(self.package_num_label,
                                            1, 17, 1, 1)
        # QToolButton # есть wordWrap

# ------ Set main grid --------------------------------------------------------
        self.main_grid_layout.addWidget(self.com_param_groupbox,
                                        0, 0, 1, 2)
        self.main_grid_layout.addWidget(self.fs_groupbox,
                                        1, 0, 1, 1)
        self.main_grid_layout.addWidget(self.cycle_number_groupbox,
                                        1, 1, 1, 1)
        self.main_grid_layout.addWidget(self.saving_measurements_groupbox,
                                        7, 0, 13, 2)
        self.main_grid_layout.addWidget(self.measurements_groupbox,
                                        2, 0, 5, 2)
        self.main_grid_layout.addWidget(self.text_output_groupbox,
                                        0, 2, 9, 1)
        self.main_grid_layout.addWidget(self.logs_groupbox,
                                        9, 2, 9, 1)
        self.main_grid_layout.addWidget(self.start_all_button,
                                        18, 2, 1, 1)
        self.main_grid_layout.addWidget(self.stop_button,
                                        19, 2, 1, 1)

        self.main_grid_layout.addWidget(self.custom_tab_plot_widget,
                                        0, 3, 17, 1)
        self.main_grid_layout.addWidget(self.plot_groupbox,
                                        17, 3, 3, 2)

# ------ Set settings --------------------------------------------------------------------------
        self.load_previous_settings(self.settings)
        # print(self.findChild(QtWidgets.QTextEdit, 'with_bourder').setText('fffffff'))
# ------ Signal Connect --------------------------------------------------------------------
        self.start_all_button.clicked.connect(self.full_measurement_start)
        self.stop_button.clicked.connect(self.stop)
        self.choose_file.clicked.connect(self.choose_and_load_file)
        self.cycle_num_spinbox.valueChanged.connect(self.cycle_num_value_change)
        self.cycle_num_spinbox.valueChanged.connect(self.progress_bar_set_max)
        # self.choose_path_button.clicked.connect(
        #     self.choose_result_saving_path)
        self.filename_and_path_textedit.textChanged.connect(
            self.filename_and_path_text_change)
        self.edit_file_button.clicked.connect(self.open_file)
            # lambda: os.startfile(self.filename_and_path_textedit.toPlainText()))
        self.logs_clear_button.clicked.connect(
            lambda: self.log_text_box.widget.clear())
        for i in range(self.GYRO_NUMBER):
            self.choose_path_button_list[i].clicked.connect(
                self.choose_result_saving_path)
            self.saving_result_folder_label_list[i].textChanged.connect(
                self.folder_chage_event)
        for i in range(self.GYRO_NUMBER + 1):
            self.check_box_list[i].stateChanged.connect(
                self.custom_tab_plot_widget.change_curve_visibility)
        
        self.show()
        self.custom_tab_plot_widget.create_excel_com_object()  # !
        self.logger.debug("Программа запущена")
        # os.system(r'start D:/')  # так можно открывать папку
        # print(self.palette().window().color().name())
        # win32api.ShellExecute()
# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------
#
        
    def gyro1_4(self):
        self.processing_thr.pack_len = (4 if self.gyro1_4_action.isChecked() else 2)  # !
        # self.GYRO_NUMBER = 1
        #     self.processing_thr.package_len = 4
        # else:
        #     self.processing_thr.package_len = 2
        # self.processing_thr.GYRO_NUMBER = 1
        # self.custom_tab_plot_widget.GYRO_NUMBER = 1

    def gyro1_2(self):
        self.GYRO_NUMBER = 1
        self.processing_thr.pack_len = 2
        self.processing_thr.GYRO_NUMBER = 1 
        self.custom_tab_plot_widget.GYRO_NUMBER = 1

    def gyro3_2(self):
        self.GYRO_NUMBER = 3
        self.processing_thr.pack_len = 2
        self.processing_thr.GYRO_NUMBER = 3
        self.custom_tab_plot_widget.GYRO_NUMBER = 3
        # self.

    def __contextMenu(self):
        self._normalMenu = self.com_port_name_combobox.lineEdit().createStandardContextMenu()
        # self._normalMenu = QtWidgets.QMenu()
        # self._normalMenu = self.combo_box_name.visibleRegion().createStandardContextMenu()
        # self._normalMenu = self.combo_box_name.layoutDirection().createStandardContextMenu()
        self._addCustomMenuItems(self._normalMenu)
        self._normalMenu.exec_(QtGui.QCursor.pos())

    def _addCustomMenuItems(self, menu: QtWidgets.QMenu):
        menu.addSeparator()
        # action = QtWidgets.QAction("Обновить", self, shortcut="Ctrl+U")
        # action.setShortcut("Ctrl+U")
        # menu.addAction(action)
        menu.addAction('Обновить', self.get_avaliable_com)

    def append_gyro_widgets(self):
        ind = len(self.saving_measurements_groupbox_list)
        self.saving_measurements_groupbox_list.append(QtWidgets.QGroupBox(
            f'Сохранение измерений gyro{ind + 1}',
            maximumWidth=310, maximumHeight=175,
            objectName='gyro_save_groupbox'))
        saving_measurements_groupbox_layout = QtWidgets.QGridLayout()
        self.saving_measurements_groupbox_list[-1].setLayout(
            saving_measurements_groupbox_layout)
        # self.saving_measurements_groupbox_list[-1].installEventFilter(self)

        saving_measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel('Папка:'), 0, 0, 3, 1)
            # QtWidgets.QLabel('<b>Папка:</b>'), 0, 0, 3, 1)
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
            QtWidgets.QLabel('Имя:'), 3, 0, 1, 1)
        self.file_name_line_edit_list.append(QtWidgets.QLineEdit(f'test{ind + 1}'))
        saving_measurements_groupbox_layout.addWidget(
            self.file_name_line_edit_list[-1], 3, 1, 1, 2)
        self.choose_path_button_list.append(QtWidgets.QPushButton(
            # 'Выбрать папку\nсохранения',
            icon=get_icon_by_name(f'open_folder_{self.ICON_COLOR_LIST[ind]}'))) ##QtGui.QIcon(
        saving_measurements_groupbox_layout.addWidget(
            # self.choose_path_button_list[-1], 0, 3, 1, 1)
            self.choose_path_button_list[-1], 4, 0, 1, 2)
        self.create_folder_checkbox_list.append(
            QtWidgets.QCheckBox('папка'))
        saving_measurements_groupbox_layout.addWidget(
            # self.create_folder_checkbox_list[-1], 3, 3, 1, 1)  #
            self.create_folder_checkbox_list[-1], 4, 2, 1, 1)  #

    def eventFilter(self, obj, event):
        # print(time())
        if event.type() == QtCore.QEvent.ContextMenu:
            if obj is self.stop_button:
                if not self.processing_thr.isRunning():
                    return True
                print(1)
                menu = QtWidgets.QMenu(self)
                action = QtWidgets.QAction('Стоп без сохранения', self)
                action.triggered.connect(self.stop_no_save)
                menu.addAction(action)
                menu.exec_(event.globalPos())
            elif obj is self.start_all_button:
                if self.processing_thr.isRunning():
                    return True
                menu = QtWidgets.QMenu(self)
                action = QtWidgets.QAction('Старт без сохранения', self)
                action.triggered.connect(self.measurement_start)
                menu.addAction(action)                
                menu.exec_(event.globalPos())
                    # action.setDisabled(True)
    #         if obj is self.saving_measurements_groupbox_list[0]:
    #             print(0)
    #         else:
    #             print(1)
    #         menu = QtWidgets.QMenu(self)
    #         action = QtWidgets.QAction('Изменить проект', self)
    #         # action.triggered.connect(self.change_current_xlsx_item)
    #         menu.addAction(action)
    #         action = QtWidgets.QAction('Добавить проект', self)
    #         # action.triggered.connect(self.add_xlsx_item)
    #         menu.addAction(action)
    #         action = QtWidgets.QAction('Удалить текущий проект', self)
    #         # action.triggered.connect(self.delete_xlsx_item)
    #         menu.addAction(action)
                # menu.exec_(event.globalPos())
            return True
        return False

    def stop_no_save(self):
        self.processing_thr.flag_do_not_save = True
        self.stop()

    def get_gyro_count(self):
        if not self.serial_port.open(QtCore.QIODevice.OpenModeFlag.ReadWrite):
            self.logger.warning(
                f"Can't open {self.com_port_name_combobox.currentText()}")
            return
        self.serial_port.readLine()
        length = len(self.serial_port.readLine())
        length = 20
        self.logger.debug(f"data_len: {length}")
        flag = (length == 20)
        if flag:
            self.GYRO_NUMBER = 3
            self.processing_thr.GYRO_NUMBER = 3
            self.custom_tab_plot_widget.GYRO_NUMBER = 3
        else:
            self.GYRO_NUMBER = 1
            self.processing_thr.GYRO_NUMBER = 1
            self.custom_tab_plot_widget.GYRO_NUMBER = 1
            for i in range(1, len(self.check_box_list)-1):
                self.file_name_line_edit_list[i].setText('')
                self.processing_thr.save_file_name[i] = ''
        for i in range(1, len(self.check_box_list)-1):
            self.saving_measurements_groupbox_list[i].setVisible(flag)
            self.check_box_list[i + 1].setVisible(flag)
            self.custom_tab_plot_widget.groupbox_list[i].setVisible(flag)
        self.serial_port.close()
################################################################################################
#
# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------
#
################################################################################################
    def save_results(self):
        if self.processing_thr.isRunning():
            self.logger.warning("Thread still work")
            self.logger.debug(f"data_recieved_event {self.processing_thr.data_recieved_event.is_set()}")
            self.processing_thr.data_recieved_event.set()
            return
        # Check filenames
        for i in range(self.GYRO_NUMBER):  # !
            if self.processing_thr.pack_num:
                self.make_filename(i)  # !  # без создания имени не получится
            self.processing_thr.start()

    @QtCore.pyqtSlot(bool)
    def run_thread_for_file_processing(self, _):  ################### изменить для трех, изменить имена
        self.logger.debug(
            f"files: {self.custom_tab_plot_widget.selected_files_to_fft}")
        if self.processing_thr.isRunning():
            self.logger.warning("Thread still work")
            return
        self.custom_tab_plot_widget.clear_plots()
        self.fs = int(self.fs_combo_box.currentText())
        # Copy variables to another classes and start thread
        self.custom_tab_plot_widget.fs = self.fs
        self.processing_thr.fs = self.fs
        # self.processing_thr.folder = self.folder_name_list[0] ###################################################

        self.processing_thr.flag_by_name = True
        self.processing_thr.selected_files_to_fft = self.custom_tab_plot_widget.selected_files_to_fft
        self.processing_thr.start()
        if False:
            path = 'sencors_nums.txt'
            self.processing_thr.flag_do_not_save = True
# ----------------------------------------------------------------------------------------------
            
    @QtCore.pyqtSlot()
    def measurement_start(self):
        self.custom_tab_plot_widget.region.setVisible(False)
        self.progress_value = 0  # не создавать эту переменную
        self.progress_bar.setValue(0)
        self.package_num_label.setText('0')
        self.count = 0
        self.current_cylce = 1

        if self.processing_thr.isRunning():
            self.logger.warning("Thread still work")
            return
        # Check COM port
        self.logger.debug(F"\nPORT: {self.com_port_name_combobox.currentText()}\n")
        if not len(self.com_port_name_combobox.currentText()):
            self.get_avaliable_com()
            self.logger.debug(
                f"PORT: {(self.com_port_name_combobox.currentText())}\n")
            QtWidgets.QMessageBox.critical(
                None, "Error", "Can't find COM port")
            return
        self.serial_port.setBaudRate(
            int(self.com_boderate_combo_box.currentText()))
        self.serial_port.setPortName(
            self.com_port_name_combobox.currentText())
        self.logger.debug("Set COM settings")

        # self.get_gyro_count()  # !!!!!!!!!!! #################################################

        # Open COM
        if not self.serial_port.open(QtCore.QIODevice.OpenModeFlag.ReadWrite):
            self.logger.warning(
                f"Can't open {self.com_port_name_combobox.currentText()}")
            return
        self.start_all_button.setDisabled(True)
        # надо понять, можно ли 2 раза нажать на старт
        # или нажать на стоп, пока еще запуск не произошел

        self.progress_bar.setMaximum(999)
        self.custom_tab_plot_widget.clear_plots()

        self.logger.debug(f"{self.com_port_name_combobox.currentText()} open")
        self.logger.warning("Start")
        # self.serial_port.clear()
        # sleep(0.1)
        # # self.serial_port.readLine()
        # if self.serial_port.bytesAvailable() > 35:
        #     test_data = self.serial_port.read(35)
        #     self.logger.debug(f"test_data: {test_data}")
        #     test_data = np.frombuffer(test_data, dtype=np.uint8)
        #     check = (test_data[:-13] == 0x72) & (test_data[13:] == 0x27)[0]
        #     if check.size:
        #         # self.logger.debug(f"data_len: {check.size}")
        #         pass
        #     self.logger.debug(f"check.size: {check.size}")
        # else:
        #     self.logger.debug(
        #         f"self.serial_port.bytesAvailable(): {self.serial_port.bytesAvailable()}")
        self.serial_port.clear()
        # Start timers
        self.start_time = time()
        self.timer_recieve.start()
        self.fs = int(self.fs_combo_box.currentText())
        # Copy variables to another classes and start thread
        self.custom_tab_plot_widget.fs = self.fs
        self.processing_thr.fs = self.fs
        self.processing_thr.flag_measurement_start = True
        self.processing_thr.flag_do_not_save = True
        self.processing_thr.total_time = self.table_widget.total_time
        self.processing_thr.start()
        self.set_avaliable_butttons(flag_running=True)  # disable widgets
            
    @QtCore.pyqtSlot()
    def full_measurement_start(self):
        self.custom_tab_plot_widget.region.setVisible(True)
        self.progress_value = 0  # не создавать эту переменную
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat('%v/%m сек (определение смещения)')
        self.package_num_label.setText('0')
        self.count = 0
        self.current_cylce = 1

        if self.processing_thr.isRunning():
            self.logger.warning("Thread still work")
            return
        # Check COM port
        self.logger.debug(F"PORT: {self.com_port_name_combobox.currentText()}\n")
        if not len(self.com_port_name_combobox.currentText()):
            self.get_avaliable_com()
            self.logger.debug(
                f"PORT: {(self.com_port_name_combobox.currentText())}\n")
            QtWidgets.QMessageBox.critical(
                None, "Error", "Can't find COM port")
            return
        self.serial_port.setBaudRate(
            int(self.com_boderate_combo_box.currentText()))
        self.serial_port.setPortName(
            self.com_port_name_combobox.currentText())
        self.logger.debug("Set COM settings")

        # Check measurement file
        if not self.table_widget.total_time:
            self.cycle_num_value_change()
            if not self.choose_and_load_file():
                self.logger.debug("No data from file")
                return
        self.logger.debug("Data from file was loaded")

        # self.get_gyro_count()  # !!!!!!!!!!! #################################################

        # Open COM
        if not self.serial_port.open(QtCore.QIODevice.OpenModeFlag.ReadWrite):
            self.logger.warning(
                f"Can't open {self.com_port_name_combobox.currentText()}")
            return
        self.start_all_button.setDisabled(True)
        # надо понять, можно ли 2 раза нажать на старт
        # или нажать на стоп, пока еще запуск не произошел

        self.custom_tab_plot_widget.clear_plots()
        self.custom_tab_plot_widget.append_fft_plot_tab()

        self.cycle_num_value_change()
        self.progress_bar_set_max()

        self.logger.debug(f"{self.com_port_name_combobox.currentText()} open " +
                         f"self.cycle_num = {self.total_cycle_num}")

        self.serial_port.clear()
        # Start timers
        self.flag_sent = False
        self.start_time = time()  # !!!!!
        self.timer_recieve.start()
        self.fs = int(self.fs_combo_box.currentText())
        # Copy variables to another classes and start thread
        self.custom_tab_plot_widget.fs = self.fs
        self.processing_thr.fs = self.fs
        self.processing_thr.flag_measurement_start = True  # !!!!!
        self.processing_thr.total_time = self.table_widget.total_time
        self.processing_thr.num_measurement_rows = self.table_widget.rowCount()
        self.processing_thr.flag_do_not_save = True
        self.processing_thr.total_cycle_num = self.total_cycle_num
        self.processing_thr.start()
        QtCore.QTimer.singleShot(1500, self.end_start)
        self.set_avaliable_butttons(flag_running=True)  # disable widgets
        self.logger.warning("Start")

    @QtCore.pyqtSlot()
    def end_start(self):
        self.progress_bar.setFormat('%v/%m сек')
        if self.processing_thr.flag_measurement_start:
            self.serial_port.clear()
            self.processing_thr.flag_do_not_save = False
            # self.timer_recieve.setInterval(0)
            # self.timer_sent_com.setInterval(0)
            self.processing_thr.flag_full_measurement_start = True
            self.processing_thr.flag_measurement_start = False
            # self.processing_thr.data_recieved_event.set()
            # Start timer
            self.start_time = time()
            self.check_time = time()
            self.timer_event_sent_com()
            self.timer_sent_com.start()
            self.logger.debug('start full measurements')
            # self.logger.warning(f"Shift: {self.processing_thr.amp_shift}")
# ------ Timer Recieve --------------------------------------------------------

    @QtCore.pyqtSlot()
    def timer_read_event(self):
        """Read data from COM port using readyRead signal.
        Generate warning if avaliable less than 14 bytes"""
        if not self.serial_port.receivers(self.serial_port.readyRead):
            self.serial_port.readyRead.connect(self.read_serial)
        else:
            if self.serial_port.bytesAvailable() <= 14:
                self.logger.warning(
                    f"Not enough data from {self.com_port_name_combobox.currentText()}")
            else:
                self.logger.warning(
                    f"No data from {self.com_port_name_combobox.currentText()}!")
        # self.read_serial()

    @QtCore.pyqtSlot()
    def read_serial(self):
        self.logger.debug(
            f"ready to read, bytes num = {self.serial_port.bytesAvailable()}")  # +
        if self.serial_port.bytesAvailable() <= 14:
            return
        self.serial_port.readyRead.disconnect(self.read_serial)
        if self.processing_thr.data_recieved_event.is_set():
            self.logger.warning("Thread still work with previous data")
            return
        self.copy_variables_to_thread()
        self.logger.debug(f"command thr to start, count = {self.count}")

    def copy_variables_to_thread(self):
        self.processing_thr.rx = self.serial_port.readAll().data()
        self.processing_thr.count_fft_frame = self.count
        self.processing_thr.flag_sent = self.flag_sent
        self.processing_thr.data_recieved_event.set()  # в конце запускаем поток
# ------- Timer Sent ----------------------------------------------------------

    @QtCore.pyqtSlot()
    def timer_event_sent_com(self):
        """
        Sent command with frequency and amplitude or stop vibration
        """
        if self.flag_sent:
            if self.count >= self.table_widget.rowCount():
                self.logger.debug(
                    f"end cycle = {self.count}")
                if self.current_cylce < self.total_cycle_num:
                    self.new_cycle_event()
                    self.sent_stop_vibro_command()
                else:
                    self.stop()
                return
        # if self.flag_sent:
            self.sent_vibro_command()
        else:
            self.sent_stop_vibro_command()
        self.flag_sent = not self.flag_sent
        self.check_time = time()

    def sent_stop_vibro_command(self):
        self.timer_sent_com.setInterval(self.PAUSE_INTERVAL_MS)
        # self.timer_sent_com.setInterval(2 * self.PAUSE_INTERVAL_MS - time() - self.check_time)  # компенсация
        self.serial_port.write(bytes([0, 0, 0, 0, 0, 0, 0, 0]))
        self.logger.debug(f"---stop vibro command was sent, time: {time() - self.check_time}")

    def sent_vibro_command(self):
        self.table_widget.selectRow(self.count)
        self.timer_sent_com.setInterval(self.table_widget.get_current_T())
        F = int.to_bytes(self.table_widget.get_current_F(),
                         length=2, byteorder='little', signed=False)
        A = int.to_bytes(self.table_widget.get_current_A(),
                         length=2, byteorder='little', signed=False)
        self.serial_port.write(
            bytes([77, 0, F[0], F[1], A[0], A[1], 0, 0]))
        self.logger.debug(
            f"--- vibro command {self.count} was sent, time: {time() - self.check_time}")
        self.count += 1

# ----- End cycle, stop, etc --------------------------------------------------
    def new_cycle_event(self):
        self.logger.warning(
            f"End of cycle {self.current_cylce} of {self.total_cycle_num}")
        self.current_cylce += 1
        self.count = 0
        self.processing_thr.new_measurement_cycle()
        self.logger.debug("append tab")
        self.custom_tab_plot_widget.append_fft_plot_tab()
        self.logger.debug("end append tab")

    @QtCore.pyqtSlot()
    def stop(self):
        if self.timer_sent_com.isActive():
            self.logger.debug("Stop timer_sent_com")
            self.timer_sent_com.stop()
        if self.timer_recieve.isActive():
            self.logger.debug("Stop timer_recieve")
            self.timer_recieve.stop()

        if self.serial_port.isOpen():
            if self.processing_thr.flag_full_measurement_start:
                self.serial_port.write(bytes([0, 0, 0, 0, 0, 0, 0, 0]))
                sleep(0.01)
                self.logger.debug("COM close? " +
                                 str(self.serial_port.waitForBytesWritten(250)))
            self.serial_port.close()
            self.logger.warning("End of measurements\n")
            if self.progress_value > 3:
                check = int(int(self.package_num_label.text()) / self.progress_value)
                if not (0.95 * self.fs < check < 1.05 * self.fs):
                    QtWidgets.QMessageBox.critical(
                        None, "Warning",
                        f"You set fs = {self.fs} Hz," +
                        f"but in fact it's close to {check} Hz")
            # Check filenames
            for i in range(self.GYRO_NUMBER):
                self.make_filename(i)
        self.processing_thr.flag_full_measurement_start = False
        self.processing_thr.flag_measurement_start = False
        self.processing_thr.data_recieved_event.set()
        self.flag_sent = False
        self.set_avaliable_butttons(False)

        total_time = self.total_cycle_num * (self.table_widget.total_time +
                (self.table_widget.rowCount() + 1) * self.PAUSE_INTERVAL_MS / 1000)
        self.logger.debug(
            f"time = {self.progress_value}, " +
            f"total time = {self.progress_bar.maximum()} ({total_time})")
###############################################################################
# ----- plotting --------------------------------------------------------------

    @QtCore.pyqtSlot(int, np.ndarray)
    def get_and_show_data_from_thread(self, package_num_signal, plot_data):
        """Receiving the processed measurement data
            (package num, time data to graph)"""
        self.package_num_label.setText(str(package_num_signal))
        self.progress_value = time() - self.start_time
        self.progress_bar.setValue(int(round(self.progress_value)))
        self.logger.debug(f"Progress: {self.progress_value} " +
                         f"thr_stop, count = {self.count}, " +
                         f"package_num = {package_num_signal} ")
        self.custom_tab_plot_widget.plot_time_graph(
            plot_data[:, 0], plot_data[:, 2], plot_data[:, 1::self.processing_thr.pack_len])
            # plot_data[:, 0], plot_data[:, 2], plot_data[:, 1::4])

    @QtCore.pyqtSlot(bool)
    def plot_fft(self, _):
        """Adds points to frequency graphs"""
        self.custom_tab_plot_widget.set_fft_data(
            self.processing_thr.all_fft_data[:, (self.current_cylce-1)*4:self.current_cylce*4, :],
            self.processing_thr.bourder)
        self.logger.debug("end plot_fft")

    # @QtCore.pyqtSlot(str)
    @QtCore.pyqtSlot(list)
    def plot_fft_final(self, name: list):
        self.logger.debug(f"Final median plot {name}")
        self.custom_tab_plot_widget.set_fft_median_data(
            self.processing_thr.all_fft_data[:, -4:],
            self.processing_thr.special_points, name)

    @QtCore.pyqtSlot()
    def save_image(self):
        self.logger.debug("Save image")
        for i in range(self.GYRO_NUMBER):
            if (len(self.processing_thr.save_file_name[i])
                and self.check_box_list[i].isChecked()):
                if self.processing_thr.flag_full_measurement_start:  # !
                    self.make_filename(i)  # !
                self.custom_tab_plot_widget.save_plot_image(
                    self.processing_thr.save_file_name[i])
        self.logger.debug("Saving complite")

# ------ Widgets events -------------------------------------------------------

    def cycle_num_value_change(self):
        # if not self.timer_recieve.isActive():  # is this required?
        self.total_cycle_num = self.cycle_num_spinbox.value()

    def progress_bar_set_max(self):
        if self.table_widget.total_time and not self.timer_recieve.isActive():  # is this required?
            self.total_cycle_num = self.cycle_num_spinbox.value()
            self.progress_bar.setMaximum(int(
                self.total_cycle_num * 
                (self.table_widget.total_time +
                 (self.table_widget.rowCount() + 1) * self.PAUSE_INTERVAL_MS / 1000)))
            # self.progress_bar.setValue(0)

    def set_avaliable_butttons(self, flag_running: bool):
        """Enable or disable widgets"""
        self.cycle_num_spinbox.setDisabled(flag_running)
        self.edit_file_button.setDisabled(flag_running)
        # self.save_image_button.setDisabled(flag_running)
        self.start_all_button.setDisabled(flag_running)
        self.stop_button.setDisabled(not flag_running)
        self.choose_file.setDisabled(flag_running)
        self.measurement_action.setDisabled(flag_running)
        self.save_action.setDisabled(flag_running)
        if self.GYRO_NUMBER == 1:
            self.gyro1_4_action.setDisabled(flag_running)  # !
        # for groupbox in self.saving_measurements_groupbox_list:
            # groupbox.setDisabled(flag_running)
        # saving_measurements_groupbox_list можно редактировать,
        # т.к. путь отправляется в поток перед окончанием цикла

    def get_avaliable_com(self):
        """Append avaliable com ports to combo box widget"""
        port_name_list = [ports.portName() 
               for ports in QSerialPortInfo.availablePorts()]
        if len(port_name_list):
            # for _ in range(self.com_port_name_combobox.count()):
            while(self.com_port_name_combobox.count()):  # !
                self.com_port_name_combobox.removeItem(0)
            self.com_port_name_combobox.addItems(
                sorted(port_name_list, key=natural_keys))
        self.logger.warning('Update avaliable COM port list')

# ------ file name and data from file -----------------------------------------
    def make_filename(self, i: int):
        # подправить if
        if not len(self.file_name_line_edit_list[i].text()) or not len(self.folder_name_list[i]): # or not len():
            self.processing_thr.save_file_name[i] = ''
            return
        if not os.path.isdir(self.folder_name_list[i]):
            self.processing_thr.save_file_name[i] = ''
            self.logger.warning(f"Path {self.folder_name_list[i]} doesn't exist!")
            return
        if self.create_folder_checkbox_list[i].isChecked():
            folder = re.split("_", self.file_name_line_edit_list[i].text())[0]
            if not os.path.isdir(self.folder_name_list[i] + folder):
                os.mkdir(self.folder_name_list[i] + folder)
            folder += '/'
        else:
            folder = ''
        self.processing_thr.save_file_name[i] = \
            self.folder_name_list[i] + folder + self.file_name_line_edit_list[i].text()
        self.logger.debug(f"name {self.processing_thr.save_file_name[i]}")

    # def directory_changed(self, path):
    #     self.logger.debug(f'Directory Changed: {path}')
    #     print(f'Directory Changed: {path}')

    def folder_chage_event(self):
        for i in range(len(self.saving_result_folder_label_list)):
            if self.sender() == self.saving_result_folder_label_list[i]:
                break
        else:
            return
        self.folder_name_list[i] = self.saving_result_folder_label_list[i].toPlainText()   

    @QtCore.pyqtSlot()
    def choose_result_saving_path(self):
        for i in range(len(self.choose_path_button_list)):
            if self.sender() == self.choose_path_button_list[i]:
                break
        else:
            return
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Выбрать папку", self.folder_name_list[i])
        if not len(folder):
            return
        self.folder_name_list[i] = folder + '/'
        self.saving_result_folder_label_list[i].setText(
            self.folder_name_list[i])

    @QtCore.pyqtSlot()
    def filename_and_path_text_change(self):
        if not os.path.exists(self.filename_and_path_textedit.toPlainText()):  # text
            # QtCore.QTimer.singleShot(1500, self.check2)
            # можно вместо уведомлений делать серым шрифт, например
            self.logger.warning("The file path does not exist!")
            # доработать, чтобы человек не получал кучу таких уведомлений
            return False
        if len(self.filename_and_path_textedit.toPlainText()):
            self.file_watcher.removePath(self.filename_path_watcher)
        self.filename_path_watcher = self.filename_and_path_textedit.toPlainText()  # os.path.basename(filename)
        self.file_watcher.addPath(self.filename_path_watcher)
        return self.get_data_from_file(self.filename_path_watcher)

    # @QtCore.pyqtSlot()
    # def check2(self):
    #     print(1)

    @QtCore.pyqtSlot(str)
    def check_filename_and_get_data(self, path: str):
        """Вызывается при изменении файла"""
        self.logger.debug(
            f'File Changed, {path},' +
            f'thr run? {self.processing_thr.flag_full_measurement_start}')
        if not self.processing_thr.flag_full_measurement_start and os.path.exists(path):
            self.get_data_from_file(path)

    @QtCore.pyqtSlot()
    def choose_and_load_file(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Выберите методику измерений",
            os.path.dirname(self.filename_path_watcher),
            "Text Files(*.txt)")
        if not filename:
            return False
        self.logger.debug(
            f"filename: {filename}, basebame: {os.path.basename(filename)}")
        if len(self.filename_path_watcher):
            self.file_watcher.removePath(self.filename_path_watcher)
        self.file_watcher.addPath(filename)
        self.filename_and_path_textedit.setText(filename)
        self.filename_path_watcher = filename  # os.path.basename(filename)
        return self.get_data_from_file(self.filename_path_watcher)

    def get_data_from_file(self, filename_path_watcher: str):
        """Get data from file and put it in table"""
        with open(filename_path_watcher, 'r') as file:
            self.table_widget.set_table(file)
            self.progress_bar_set_max()
        return self.table_widget.total_time > 0

    @QtCore.pyqtSlot()
    def open_file(self):
        self.logger.debug('startfile')
        os.startfile(self.filename_and_path_textedit.toPlainText())

    @QtCore.pyqtSlot()
    def closeEvent(self, _):
        """Sending stop command to the vibrostand and saving user settings"""
        self.logger.warning("Saving the settings and exit")
        self.stop()
        self.settings.setValue("autosave",
                               int(self.settings_autosave_action.isChecked()))
        if self.settings_autosave_action.isChecked():
            self.save_all_settings()
        try:
            self.logger.warning("Wait Excel to close...")
            self.custom_tab_plot_widget.close_excel_com_object()  # !
            self.logger.debug("Close COM object")
        except Exception:
            self.logger.debug("Can't close COM object!")

# ------ settings --------------------------------------------------------------------
    def save_all_settings(self):
        self.com_boderate_combo_box.save_all()
        self.fs_combo_box.save_all()
        self.com_port_name_combobox.save_current_text()
        self.settings.setValue("cycle_num",
                                self.cycle_num_spinbox.value())
        self.settings.setValue("filename",
                                self.filename_and_path_textedit.toPlainText())
        self.settings.setValue("current_folders", self.folder_name_list)
        self.settings.setValue('create_folder_flag',
                               [int(checkbox.isChecked()) 
                                for checkbox in self.create_folder_checkbox_list])
        # лучше сохранять и распаковывать эти настройки в отдельном файле в классе комбобокса
        # или, как максимум, одну функцию оставить
        self.settings.setValue(
            'dict', self.custom_tab_plot_widget.projects_combo_box.projects_dict)
        self.settings.setValue(
            'dict_curr_project',
            self.custom_tab_plot_widget.projects_combo_box.currentText())
        # import json
        # with open('projects_dict.json', 'w', encoding='utf-8') as f:
        #     json.dump(
        #         self.custom_tab_plot_widget.projects_combo_box.projects_dict,
        #         f, ensure_ascii=False, indent=4)

    def load_previous_settings(self, settings: QtCore.QSettings):
        if self.settings.contains("autosave"):
            self.settings_autosave_action.setChecked(
                int(self.settings.value("autosave")))
        if settings.contains("cycle_num"):
            self.cycle_num_spinbox.setValue(
                int(settings.value("cycle_num")))
        if settings.contains("filename"):
            name = settings.value("filename")
            if os.path.exists(name):
                self.filename_and_path_textedit.setText(name)
                if self.get_data_from_file(name):
                    self.logger.warning("The previous file is loaded")
                self.filename_path_watcher = self.filename_and_path_textedit.toPlainText()  # os.path.basename(filename)
                self.file_watcher.addPath(self.filename_path_watcher)
        if settings.contains("create_folder_flag"):
            for i in range(min(len(settings.value("create_folder_flag")),
                               len(self.create_folder_checkbox_list))):
                self.create_folder_checkbox_list[i].setChecked(
                    int(settings.value("create_folder_flag")[i]))
        if settings.contains("current_folders"):
            for i in range(min(len(settings.value("current_folders")),
                               len(self.saving_result_folder_label_list))):
                if (os.path.isdir(settings.value("current_folders")[i])
                    or len(settings.value("current_folders")[i]) == 0):
                    self.saving_result_folder_label_list[i].setText(
                        settings.value("current_folders")[i])
                    self.folder_name_list[i] = settings.value("current_folders")[i]
        # лучше сохранять и распаковывать эти настройки в отдельном файле в классе комбобокса
        # попробовать сохранить в json или вместо словаря использовать dataFrame pandas
        # можно будет добавить пункт открыть исходник, чтобы вручную редактировать
        if not self.settings.contains('dict'):  
            return
        self.custom_tab_plot_widget.projects_combo_box.projects_dict = \
            self.settings.value('dict')
        if self.custom_tab_plot_widget.projects_combo_box.projects_dict:
            # keys сортируются автоматически
            self.custom_tab_plot_widget.projects_combo_box.addItems(
                self.custom_tab_plot_widget.projects_combo_box.projects_dict.keys())
            for i in range(self.custom_tab_plot_widget.projects_combo_box.count()):
                self.custom_tab_plot_widget.projects_combo_box.setItemData(
                    i, self.custom_tab_plot_widget.projects_combo_box.projects_dict.get(
                        self.custom_tab_plot_widget.projects_combo_box.itemText(i)),
                    QtCore.Qt.ItemDataRole.ToolTipRole)
            if self.settings.contains('dict_curr_project'):
                for i in range(self.custom_tab_plot_widget.projects_combo_box.count()):
                    if self.custom_tab_plot_widget.projects_combo_box.itemText(i) == \
                        self.settings.value('dict_curr_project'):
                        self.custom_tab_plot_widget.projects_combo_box.setCurrentIndex(i)

        # import json
        # with open('projects_dict.json', 'r', encoding='utf-8') as f:
        #     res = json.load(f)
        #     print(res)
        #     print(type(res))
            # self.fs_combo_box.addItems(None)
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
#
###############################################################################
###############################################################################
#
###############################################################################
#
###############################################################################
###############################################################################
#
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class AppWindowTest(AppWindow):
    def __init__(self, parent=None):
        AppWindow.__init__(self, parent)

    @QtCore.pyqtSlot()
    def measurement_start(self):
        self.progress_value = 0  # не создавать эту переменную
        self.progress_bar.setValue(0)
        self.package_num_label.setText('0')
        self.count = 0
        self.current_cylce = 1
        if self.processing_thr.isRunning():
            self.logger.warning("Thread still work")
            return
        # Check COM port
        self.logger.debug(F"\nPORT: {self.com_port_name_combobox.currentText()}\n")
        from pandas import read_csv, DataFrame
        # filename = 'прежнее/6884_139_6.2_4.txt'
        filename = 'прежнее/6884_139_6.2_4.txt'
        self.time_data_test = np.array(
            read_csv(filename, delimiter='\t', 
                     dtype=np.int32, header=None,  #,
                     keep_default_na=False, na_filter=False,
                     index_col=False, usecols=[1, 2, 3, 4], 
                     skiprows=2000))
        # self.get_gyro_count()  # !!!!!!!!!!! #################################################
        self.progress_bar.setMaximum(-1)
        self.custom_tab_plot_widget.clear_plots()
        self.set_avaliable_butttons(flag_running=True)  # disable widgets

        self.logger.debug(f"{self.com_port_name_combobox.currentText()} open")
        self.logger.warning("Start")
        # Start timers
        self.start_time = time()
        self.timer_recieve.start()
        self.fs = int(self.fs_combo_box.currentText())
        # Copy variables to another classes and start thread
        self.custom_tab_plot_widget.fs = self.fs
        self.processing_thr.fs = self.fs
        self.processing_thr.flag_measurement_start = True
        self.processing_thr.flag_do_not_save = True
        self.processing_thr.total_time = self.table_widget.total_time
        self.processing_thr.start()

    def full_measurement_start(self):
        self.progress_bar.setValue(0)
        self.progress_value = 0
        self.count = 0
        self.current_cylce = 1
        self.package_num_label.setText('0')
        self.flag_sent = False
        if not self.table_widget.total_time:
            self.cycle_num_value_change()
            if not self.choose_and_load_file():
                self.logger.debug("No data from file")
                return
        self.logger.debug("Data from file was loaded")
        self.cycle_num_value_change()
        self.progress_bar_set_max()
        self.set_avaliable_butttons(True)  # disable widgets
        self.logger.debug(f"self.cycle_num = {self.total_cycle_num}")
        self.logger.warning("Start")
        self.custom_tab_plot_widget.clear_plots()
        self.custom_tab_plot_widget.append_fft_plot_tab() 
        from pandas import read_csv, DataFrame
        # filename = 'прежнее/6884_139_6.2_4.txt'
        filename = 'прежнее/6884_139_6.2_4.txt'
        self.time_data_test = np.array(
            read_csv(filename, delimiter='\t', 
                     dtype=np.int32, header=None,  #,
                     keep_default_na=False, na_filter=False,
                     index_col=False, usecols=[1, 2, 3, 4], 
                     skiprows=2000))
        # self.logger.debug("1")
        # DataFrame(self.time_data_test).to_csv(
        #     "ddddddd.txt", header=None, index=None,
        #     sep='\t', mode='w', date_format='%d', decimal=',')
        # self.logger.debug("2")
        # from PyQt_Functions import get_fft_data  # ! показательно !
        # print(get_fft_data(self.time_data_test[2_400:11_400, 0], self.time_data_test[2_400:11_400, 1], 1000))
        # # print(get_fft_data(self.time_data_test[4_400:9_400, 0], self.time_data_test[4_400:9_400, 1], 1000))
        # print(get_fft_data(self.time_data_test[6_400:8_400, 0], self.time_data_test[6_400:8_400, 1], 1000))
        # print(get_fft_data(self.time_data_test[4_400:5_400, 0], self.time_data_test[4_400:5_400, 1], 1000))
        # print(get_fft_data(self.time_data_test[4_900:5_900, 0], self.time_data_test[4_900:5_900, 1], 1000))
        # print(get_fft_data(self.time_data_test[4_700:5_900, 0], self.time_data_test[4_700:5_900, 1], 1000))
        # print(get_fft_data(self.time_data_test[4_200:5_900, 0], self.time_data_test[4_200:5_900, 1], 1000))
        # print(get_fft_data(self.time_data_test[6_200:7_200, 0], self.time_data_test[6_200:7_200, 1], 1000))
        # print(get_fft_data(self.time_data_test[3_200:4_900, 0], self.time_data_test[3_200:4_900, 1], 1000))
        # print(get_fft_data(self.time_data_test[10_400:11_400, 0], self.time_data_test[10_400:11_400, 1], 1000))
        # return
        self.PLOT_TIME_INTERVAL_SEC = 20
        self.PAUSE_INTERVAL_MS = 4000
        self.start_time = time()
        self.timer_event_sent_com()
        self.timer_sent_com.start()
        self.timer_recieve.start()
        self.fs = int(self.fs_combo_box.currentText())
        self.custom_tab_plot_widget.fs = self.fs
        self.processing_thr.fs = self.fs
        self.processing_thr.flag_full_measurement_start = True
        self.processing_thr.total_time = self.table_widget.total_time * 5 # !!!
        self.processing_thr.num_measurement_rows = self.table_widget.rowCount()
        self.processing_thr.total_cycle_num = self.total_cycle_num
        self.processing_thr.start()
        # print(np.mean(self.time_data_test[:, 0]))
        print(np.mean(self.time_data_test[:100, 0]))
        print(np.mean(self.time_data_test[:500, 0]))
        print(np.mean(self.time_data_test[:750, 0]))
        print(np.mean(self.time_data_test[:2500, 0]))
        print(np.mean(self.time_data_test[:4000, 0]))
        print("enc " + str(np.mean(self.time_data_test[:4000, 1])))

    @QtCore.pyqtSlot()
    def timer_read_event(self):
        self.read_serial()

    def read_serial(self):
        self.progress_value = time() - self.start_time
        self.progress_bar.setValue(int(round(self.progress_value)))
        # data = b'\x72\xFF\xFF\xFF\x00\x00\x03\xF0\xF0\xF0\x00\x00\x04\x0F\x0F\x0F\x00\x00\x05\x27\x72\xFF\xFF\xFF\x00\x00\x06\xFF\xFF\xFF\x00\x00\x07\xFF\xFF\xFF\x00\x00\x08\x27'
        data: bytearray = b""
        package_num = int(self.package_num_label.text())
        if self.GYRO_NUMBER == 1:
            for i in range(200):
                data += int.to_bytes(0x72, length=1, byteorder='big')
                for j in range(4):
                    data += int.to_bytes(int(self.time_data_test[package_num + i, j]),
                                        length=3, byteorder='big', signed=True)
                data += int.to_bytes(0x27, length=1, byteorder='big')
        if self.GYRO_NUMBER == 3:
            for i in range(200):
                data += int.to_bytes(0x72, length=1, byteorder='big')
                for j in range(3):
                    data += int.to_bytes(int((j+1)*self.time_data_test[package_num + i, 0]),
                                        length=3, byteorder='big', signed=True)
                    data += int.to_bytes(int((j+1)*self.time_data_test[package_num + i, 1]),
                                        length=3, byteorder='big', signed=True)
                data += int.to_bytes(0x27, length=1, byteorder='big')
        self.processing_thr.rx = data
        self.processing_thr.data_recieved_event.set()
        self.processing_thr.count_fft_frame = self.count
        self.processing_thr.flag_sent = self.flag_sent
        self.logger.debug(f"thr_start, count = {self.count}")

    @QtCore.pyqtSlot()
    def timer_event_sent_com(self):
        if self.flag_sent:
            self.logger.debug(
                f"count = {self.count}, num_rows={self.table_widget.rowCount()}")
            if self.count >= self.table_widget.rowCount():
                if self.current_cylce < self.total_cycle_num:
                    self.new_cycle_event()
                else:
                    self.stop()
                return
            self.sent_vibro_command()
        else:
            self.timer_sent_com.setInterval(self.PAUSE_INTERVAL_MS)
        self.flag_sent = not self.flag_sent
        self.logger.debug("---end_sent_command")

    def sent_vibro_command(self):
        self.table_widget.selectRow(self.count)
        self.timer_sent_com.setInterval(self.table_widget.get_current_T())
        self.count += 1

    @QtCore.pyqtSlot()
    def stop(self):
        self.set_avaliable_butttons(False)
        if self.timer_sent_com.isActive():
            self.timer_sent_com.stop()
        if self.timer_recieve.isActive():
            self.timer_recieve.stop()
        self.logger.debug(
            f"time = {self.progress_value}, " +
            f"total time = {self.progress_bar.maximum()}")

        if self.processing_thr.isRunning():
            self.logger.warning("End of measurements\n")
            if self.progress_value > 5:
                check = int(int(self.package_num_label.text()) / self.progress_value)
                if not (0.95 * self.fs < check < 1.05 * self.fs):
                    QtWidgets.QMessageBox.critical(
                        None, "Warning",
                        f"You set fs = {self.fs} Hz," +
                        f"but in fact it's close to {check} Hz")
            # Check filenames
            for i in range(self.GYRO_NUMBER):
                self.make_filename(i)
        self.processing_thr.flag_full_measurement_start = False
        self.processing_thr.flag_measurement_start = False
        self.processing_thr.data_recieved_event.set()


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
###############################################################################
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    
    app = QtWidgets.QApplication(sys.argv)
    splash = QtWidgets.QSplashScreen(QtGui.QPixmap(get_res_path('res/G.png')))
    splash.show()
    app.processEvents()

    test = True
    # test = False
    if test:
        window = AppWindowTest()
    else:
        window = AppWindow()
    splash.finish(window)
    sys.exit(app.exec())
    # можно перезапуск приложения добавить для случая, если пользователь меняет число гироскопов