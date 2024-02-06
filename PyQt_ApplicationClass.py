import logging
import sys
import os
import re
# import json
import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo
from time import time, sleep
import PyQt_Logger
import PyQt_Thread
import PyQt_CustomTabWidget
import PyQt_CustomTable
import PyQt_CustomComboBox
from PyQt_Functions import get_icon_by_name, get_res_path, natural_keys
# import time


# путь к прошивке для 3х гироскопов
# D:\FromPrevComputer\Vibrostand\ProgramAndLoager\ARM_vibro(VibroStend_16bit)_v1.2_1000_0184_1000Hz\Debug
# d:/GyroVibroTest/venv3.6/Scripts/Activate.bat                
# C:\users\owner\appdata\local\programs\python\python36\lib\site-packages\PyQt5\Qt5\qml\QtQuick\Controls\Styles\Desktop\GroupBoxStyle.qml
# git add PyQt_ApplicationClass.py PyQt_CustomWidgets.py PyQt_Thread.py PyQt_Logger.py PyQt_Functions.py
# pyinstaller PyQt_ApplicationOnefolder.spec
# pyinstaller PyQt_Application.spec 
# pyinstaller --onefile --noconsole PyQt_Application.py
# D:\Gyro2023_Git\venv3.6\Lib\site-packages\PyQt5\Qt5\qml\QtQuick\Controls\GroupBox.qml
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class AppWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None, GYRO_NUMBER=1):
        QtWidgets.QMainWindow.__init__(self, parent)
# ------ Settings -------------------------------------------------------------
        self.settings = QtCore.QSettings(
            get_res_path('settings/config.ini'), QtCore.QSettings.Format.IniFormat)
        self.settings.setIniCodec("UTF-8")
        self.GYRO_NUMBER = self.get_settings("GYRO_NUMBER", GYRO_NUMBER)
# ------ Init vars ------------------------------------------------------------
        self.MAX_WIGTH_FIRST_COL = 315  # не расширяется
        self.PLOT_TIME_INTERVAL_SEC = 10
        self.PAUSE_INTERVAL_MS = self.get_settings("PAUSE_INTERVAL_MS", 500)
        self.READ_INTERVAL_MS = self.get_settings("READ_INTERVAL_MS", 75 * 2)  #  75 * 2  100 * 2 # 125 * 2
        self.folder_name_list = [''] * self.GYRO_NUMBER  # [os.getcwd() + '/'] 
        self.ICON_COLOR_LIST = ['red', 'green', 'blue']
        self.count: int = 0
        self.progress_value = 0  # убрать?
        self.total_cycle_num: int = 1
        self.current_cylce: int = 0
        self.flag_send = False
        self.filename_path_watcher = ""
        # STYLE_SHEETS_FILENAME = get_res_path('res\StyleSheets.css')
        STYLE_SHEETS_FILENAME = 'res\StyleSheets.css'
        FILE_LOG_FLAG = True
        # FILE_LOG_FLAG = False
        # DEBUG_ENABLE_FLAG = True
        # self.PROJECT_FILE_NAME = get_res_path('settings/projects.json')  # get_res_path не нужен по идее
        self.PROJECT_FILE_NAME = 'settings/projects.json'
        LOGGER_NAME = 'main'
# ------ Logger ---------------------------------------------------------------
        self.log_text_box = PyQt_Logger.QTextEditLogger(
            file_log=FILE_LOG_FLAG)
            # self, file_log=FILE_LOG_FLAG, debug_enable=DEBUG_ENABLE_FLAG)
        self.logger = logging.getLogger('main')
        self.logger.debug("Начало загрузки")
# ------  ---------------------------------------------------------------------
        self.serial_port = QSerialPort(dataBits=QSerialPort.DataBits.Data8,
                                       stopBits=QSerialPort.StopBits.OneStop,
                                       parity=QSerialPort.Parity.NoParity)
# ------ GUI ------------------------------------------------------------------
        QtWidgets.QApplication.setAttribute(
            QtCore.Qt.ApplicationAttribute.
            AA_UseStyleSheetPropagationInWidgetStyles,
            True)  # наследование свойств оформления потомков от родителей
        self.setWindowTitle("GyroVibroTest") # в названии номер стенда писать
        # print(QtWidgets.QStyleFactory.keys())
        QtWidgets.QApplication.setStyle('Fusion')
        # 'Fusion' 'Windows' 'windowsvista' ... QtWidgets.QStyle
# ------  ---------------------------------------------------------------------
        # widget = QtWidgets.QWidget(objectName="size16px")
        widget = QtWidgets.QWidget()
        self.main_grid_layout = QtWidgets.QGridLayout(widget, spacing=3)
        self.logger.debug(self.main_grid_layout.getContentsMargins())
        self.main_grid_layout.setContentsMargins(10, 0, 10, 10)
        self.setCentralWidget(widget)
# ------ Style ----------------------------------------------------------------
        with open(STYLE_SHEETS_FILENAME, "r") as style_sheets_css_file:
            self.setStyleSheet(style_sheets_css_file.read())
        app_icon = QtGui.QIcon()
        for i in [16, 24, 32, 48]:
            app_icon.addFile(
                get_res_path(f'res\icon_{i}.png'), QtCore.QSize(i, i))
        self.setWindowIcon(app_icon)
# ------ Timres ---------------------------------------------------------------
        self.timer_recieve = QtCore.QTimer(interval=self.READ_INTERVAL_MS)
        self.timer_recieve.timeout.connect(self.timer_read_event)
        self.timer_send_com = QtCore.QTimer(
            timerType=QtCore.Qt.TimerType.PreciseTimer)
        self.timer_send_com.timeout.connect(self.timer_event_send_com)
# ------ File watcher ---------------------------------------------------------
        self.file_watcher = QtCore.QFileSystemWatcher()
        # self.fs_watcher.directoryChanged.connect(self.directory_changed)
        self.file_watcher.fileChanged.connect(self.check_filename_and_get_data)
# ------ Thread ---------------------------------------------------------------
        self.processing_thr = PyQt_Thread.SecondThread(
            gyro_number=self.GYRO_NUMBER,
            READ_INTERVAL_MS=self.READ_INTERVAL_MS,
            logger_name=LOGGER_NAME,
            WAIT_TIME_SEC=self.get_settings("WAIT_TIME_SEC", 0.45))
        self.processing_thr.package_num_signal.connect(self.get_and_show_data_from_thread)
        self.processing_thr.fft_data_signal.connect(self.plot_fft)
        self.processing_thr.median_data_ready_signal.connect(
            self.plot_fft_final)
        self.processing_thr.info_signal.connect(
            lambda text: self.logger.info(text))
        self.processing_thr.warning_signal.connect(
            lambda text: self.logger.warning(text))
# ------ Plots in tab widget --------------------------------------------------
        # долго грузится (0.5 секунды)
        self.tab_plot_widget = PyQt_CustomTabWidget.CustomTabWidget(
            GYRO_NUMBER=self.GYRO_NUMBER, logger_name=LOGGER_NAME)  # !
        self.tab_plot_widget.info_signal.connect(
            lambda text: self.logger.info(text))
        self.tab_plot_widget.warning_signal.connect(
            lambda text: self.logger.warning(text))
        self.tab_plot_widget.get_filename_signal.connect(
            self.run_thread_for_file_processing
        )
# ------ Menu -----------------------------------------------------------------
        menu_bar = self.menuBar()
        options_menu = menu_bar.addMenu("&Options")
        self.settings_autosave_action = QtWidgets.QAction(
            "&Settings autosave", self, checkable=True)
        self.settings_autosave_action.setChecked(True)
        options_menu.addAction(self.settings_autosave_action)

        self.save_settings_action = QtWidgets.QAction(
            "&Save current settings", self)
        self.save_settings_action.triggered.connect(self.save_settings)        
        options_menu.addAction(self.save_settings_action)   
        plots_to_png_action = QtWidgets.QAction("&Plots to .png", self)
        plots_to_png_action.setShortcut("Ctrl+P")
        plots_to_png_action.triggered.connect(self.save_image)        
        options_menu.addAction(plots_to_png_action)

        self.save_action = QtWidgets.QAction("&Save last data", self)
        self.save_action.triggered.connect(self.save_results)
        options_menu.addSeparator()
        options_menu.addAction(self.save_action)

        # load_ini_action = QtWidgets.QAction("&Load ini", self)
        # # exit_action.setShortcut("Ctrl+Q")
        # # exit_action.setStatusTip("Exit application")  # ???
        # load_ini_action.triggered.connect(self.load_ini)
        # options_menu.addSeparator()
        # options_menu.addAction(load_ini_action)
        options_menu.addSeparator()

        self.start_full_measurement_action = QtWidgets.QAction("&Старт", self)
        # self.start_full_measurement_action.setShortcut("Ctrl+Return")
        self.start_full_measurement_action.setShortcuts(["Return", "Ctrl+Return"])
        self.start_full_measurement_action.triggered.connect(self.full_measurement_start)
        options_menu.addAction(self.start_full_measurement_action)

        self.stop_action = QtWidgets.QAction('Стоп', self, enabled=False)
        self.stop_action.setShortcut("Ctrl+Space+S")
        # self.stop_action.triggered.connect(self.stop_no_save)  # !
        self.stop_action.triggered.connect(self.stop)
        options_menu.addAction(self.stop_action)

        options_menu.addSeparator()

        self.measurement_action = QtWidgets.QAction("&Старт без сохранения", self)
        self.measurement_action.triggered.connect(self.measurement_start)
        options_menu.addAction(self.measurement_action)

        self.stop_with_no_save_action = QtWidgets.QAction('Стоп без сохранения',
                                                          self, enabled=False)
        # self.stop_with_no_save_action.setShortcut("Ctrl+Space")
        self.stop_with_no_save_action.setShortcuts(["Esc", "Ctrl+Space"])
        self.stop_with_no_save_action.triggered.connect(self.stop_no_save)
        options_menu.addAction(self.stop_with_no_save_action)
        exit_action = QtWidgets.QAction("&Exit", self)
        # exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("Exit application")  # ???
        exit_action.triggered.connect(self.close)
        options_menu.addSeparator()
        options_menu.addAction(exit_action)

        mode_menu = menu_bar.addMenu("&Mode")  # !!!!!!
        self.enable_crc_action = QtWidgets.QAction(
            "CRC8", self, checkable=True)
        self.enable_crc_action.triggered.connect(self.change_crc_mode)
        mode_menu.addAction(self.enable_crc_action)
        self.change_gyro_count_action = QtWidgets.QAction(
            "Изменить число гироскопов", self)
        self.change_gyro_count_action.triggered.connect(self.change_gyro_num)
        mode_menu.addAction(self.change_gyro_count_action)
        self.gyro1_4_action = QtWidgets.QAction(
            "Получать все данные по RboxV1", self, checkable=True)
        if self.GYRO_NUMBER == 1:
            self.gyro1_4_action.triggered.connect(self.gyro_full_data_or_not)
            mode_menu.addAction(self.gyro1_4_action)
# ------ Com Settings ---------------------------------------------------------
        """
        Block with COM port settings and sampling frequency selection.
        """
        self.com_param_groupbox = QtWidgets.QGroupBox(
            'Настройки COM порта', maximumWidth=self.MAX_WIGTH_FIRST_COL)
        com_param_groupbox_layout = QtWidgets.QGridLayout(spacing=15)
        com_param_groupbox_layout.setContentsMargins(5, 5, 5, 5)
        self.com_param_groupbox.setLayout(com_param_groupbox_layout)

        self.com_port_name_combobox = PyQt_CustomComboBox.CustomComboBox(
            settings=self.settings,
            settings_name=f"COM_name_settings{self.GYRO_NUMBER}",
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

        self.com_boderate_combo_box = PyQt_CustomComboBox.CustomComboBox(
            settings=self.settings,
            settings_name=f"COM_speed_settings{self.GYRO_NUMBER}",
            default_items_list=['921600', '115200', '0'])
        # com_param_groupbox_layout.addWidget(QtWidgets.QLabel('Скорость:'),
                                                #  1, 0, 1, 1)  # Speed
        com_param_groupbox_layout.addWidget(self.com_boderate_combo_box,
                                                 0, 1, 1, 1)
# ------  fs  -----------------------------------------------------
        self.fs_groupbox = QtWidgets.QGroupBox(
            'Fs, Гц', maximumWidth=self.MAX_WIGTH_FIRST_COL / 2)
        fs_groupbox_layout = QtWidgets.QHBoxLayout()
        fs_groupbox_layout.setContentsMargins(5, 5, 5, 5)
        self.fs_groupbox.setLayout(fs_groupbox_layout)
        self.fs_combo_box = PyQt_CustomComboBox.CustomComboBox(
            settings=self.settings,
            settings_name=f"fs_settings{self.GYRO_NUMBER}",
            default_items_list=['741', '1000', '2000'])
        self.fs = int(self.fs_combo_box.currentText())
        fs_groupbox_layout.addWidget(self.fs_combo_box)
# ------  cycle num  ----------------------------------------------------------
        self.cycle_number_groupbox = QtWidgets.QGroupBox(
            'Циклы:', maximumWidth=self.MAX_WIGTH_FIRST_COL / 2)
        cycle_number_groupbox_layout = QtWidgets.QHBoxLayout()
        cycle_number_groupbox_layout.setContentsMargins(5, 5, 5, 5)
        self.cycle_number_groupbox.setLayout(cycle_number_groupbox_layout)

        self.cycle_num_spinbox = QtWidgets.QSpinBox(
            minimum=1, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
        # cycle_number_groupbox_layout.addWidget(
            # QtWidgets.QLabel(''), 0, 0, 3, 2)  # Cycle number
        cycle_number_groupbox_layout.addWidget(self.cycle_num_spinbox)
# ------ Measurement File -----------------------------------------------------
        """
        Block with button to open and edit measurement file
        """
        self.measurements_groupbox = QtWidgets.QGroupBox(
            'Измерения', maximumWidth=self.MAX_WIGTH_FIRST_COL) #,objectName='small')
        measurements_groupbox_layout = QtWidgets.QGridLayout()
        measurements_groupbox_layout.setContentsMargins(5, 5, 5, 3)
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
            objectName="with_bourder", minimumHeight=22)
        self.filename_and_path_textedit.setTabChangesFocus(True)
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
            maximumWidth=self.MAX_WIGTH_FIRST_COL)
        saving_measurements_groupbox_layout = QtWidgets.QGridLayout()
        saving_measurements_groupbox_layout.setContentsMargins(5, 0, 5, 3)
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
        text_output_groupbox_layout.setContentsMargins(3, 5, 3, 3)
        self.text_output_groupbox.setLayout(text_output_groupbox_layout)

        self.table_widget = PyQt_CustomTable.CustomTableWidget()
        # self.table_widget.setTabKeyNavigation(False)
        self.table_widget.itemSelectionChanged.connect(self.show_certain_data)
        text_output_groupbox_layout.addWidget(self.table_widget)
        # print(self.table_widget.parent())
# ------ Logger ---------------------------------------------------------------

        """Logs widget"""
        self.logs_groupbox = QtWidgets.QGroupBox(
            'Лог', maximumWidth=350)  # Logs
        logs_groupbox_layout = QtWidgets.QVBoxLayout()
        logs_groupbox_layout.setContentsMargins(3, 5, 3, 5)
        self.logs_groupbox.setLayout(logs_groupbox_layout)

        logs_groupbox_layout.addWidget(self.log_text_box)

        self.logs_clear_button = QtWidgets.QPushButton('Очистить')  # Clear logs
        logs_groupbox_layout.addWidget(self.logs_clear_button)

        self.start_all_button = QtWidgets.QPushButton(
            'Старт', objectName="start_button")  # START
        self.start_all_button.installEventFilter(self)
        self.stop_button = QtWidgets.QPushButton(
            'Стоп', enabled=False, objectName="stop_button")  # STOP
        self.stop_button.installEventFilter(self)
# ------ Others ------------------------------------------------------------
        self.plot_groupbox = QtWidgets.QGroupBox(minimumWidth=180)
        plot_groupbox_layout = QtWidgets.QGridLayout()
        plot_groupbox_layout.setContentsMargins(10, 10, 10, 10)
        self.plot_groupbox.setLayout(plot_groupbox_layout)

        for i in range(self.GYRO_NUMBER + 1):
            plot_groupbox_layout.addWidget(
                self.tab_plot_widget.plot_check_box_list[i], 0, 5 * i, 1, 4)

        self.progress_bar = QtWidgets.QProgressBar(
            format='%v/%m сек', maximum=1, value=self.progress_value)  # sec
        plot_groupbox_layout.addWidget(self.progress_bar,
                                            1, 0, 1, 15)

        package_number_label = QtWidgets.QLabel('Пакеты:')  # Package number
        plot_groupbox_layout.addWidget(package_number_label,
                                            1, 15, 1, 4)
        self.package_num_label = QtWidgets.QLabel('0')
        plot_groupbox_layout.addWidget(self.package_num_label,
                                            1, 19, 1, 2)
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

        self.main_grid_layout.addWidget(self.tab_plot_widget,
                                        0, 3, 17, 1)
        self.main_grid_layout.addWidget(self.plot_groupbox,
                                        17, 3, 3, 2)

# ------ Set settings --------------------------------------------------------------------------
        self.load_previous_settings(self.settings)
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
        self.logs_clear_button.clicked.connect(
            lambda: self.log_text_box.clear())
        for i in range(self.GYRO_NUMBER):
            self.choose_path_button_list[i].clicked.connect(
                self.choose_result_saving_path)
            self.saving_result_folder_label_list[i].textChanged.connect(
                self.folder_change_event)

        
        self.tab_plot_widget.create_excel_com_object()  # !
        self.show()
        self.logger.debug("Программа запущена")
        # os.system(r'start D:/')  # так можно открывать папку
        # print(self.palette().window().color().name())
        # win32api.ShellExecute()  # вроде так можно проводник открывать
        # self.saving_result_folder_label_list[0].menu.setShortcut(QtGui.QKeySequence('Ctrl+O'), self)
        # self.shortcut.activated.connect(self.on_open)
        self.open_folder_action = QtWidgets.QAction("Open folder", self)
        self.open_folder_action.setShortcut('Ctrl+O')
        for label in self.saving_result_folder_label_list:
            label.addAction(self.open_folder_action)
            # print(self.open_folder_action.parent())
        # self.open_folder_actionsetShortcut = QtWidgets.QShortcut(QtGui.QKeySequence('Ctrl+O'), self.saving_result_folder_label_list[0])
        # self.open_folder_actionsetShortcut.activated.connect(self.open_folder)
        self.open_folder_action.triggered.connect(self.open_folder) 
        # print(self.findChild(QtWidgets.QTextEdit, 'with_bourder').setText('fffffff'))
        self.check_time = 0
# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------
#
        
    def gyro_full_data_or_not(self):
        self.processing_thr.pack_len = (4 if self.gyro1_4_action.isChecked() else 2)  # !
        if self.processing_thr.pack_len == 2 and self.GYRO_NUMBER == 1:
            self.enable_crc_action.setChecked(False)
            self.processing_thr.crc_flag = False
            self.enable_crc_action.setDisabled(True)
        else:
            self.enable_crc_action.setDisabled(False)
        # self.GYRO_NUMBER = 1
        #     self.processing_thr.package_len = 4
        # else:
        #     self.processing_thr.package_len = 2
        # self.processing_thr.GYRO_NUMBER = 1
        # self.custom_tab_plot_widget.GYRO_NUMBER = 1

    def change_crc_mode(self):
        if self.processing_thr.pack_len == 2 and self.GYRO_NUMBER == 1:
            self.enable_crc_action.setChecked(False)
        self.processing_thr.crc_flag = self.enable_crc_action.isChecked()

    @QtCore.pyqtSlot()
    def change_gyro_num(self):
        msg = QtWidgets.QMessageBox(parent=self, text="Перезапустить программу?")
        msg.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        if msg.exec() == msg.Ok:
            # self.save_settings()
            # QtCore.QCoreApplication.quit()
            # self.restart()
            self.settings.setValue("GYRO_NUMBER", (3 if self.GYRO_NUMBER == 1 else 1))
            self.close()
            status = QtCore.QProcess.startDetached(sys.executable, sys.argv)
            self.logger.debug(status)

    @QtCore.pyqtSlot()
    def __contextMenu(self):
        self._normalMenu = self.com_port_name_combobox.lineEdit().createStandardContextMenu()
        # self._normalMenu = QtWidgets.QMenu()
        # self._normalMenu = self.combo_box_name.visibleRegion().createStandardContextMenu()
        # self._normalMenu = self.combo_box_name.layoutDirection().createStandardContextMenu()
        self._addCustomMenuItems(self._normalMenu)
        self._normalMenu.exec_(QtGui.QCursor.pos())

    # def resizeEvent(self, e):
    #     # print(list(e.size()))
    #     # print((e.size().boundedTo()))
    #     print((e.size().width()))
    #     if e.size().width() < 750:
    #         self.saving_measurements_groupbox.layout().setContentsMargins(0, 0, 0, 0)
    #         self.plot_groupbox.layout().setContentsMargins(0, 0, 0, 0)
    #         self.logs_groupbox.layout().setContentsMargins(0, 0, 0, 0)
    #         self.text_output_groupbox.layout().setContentsMargins(0, 0, 0, 0)
    #         self.saving_measurements_groupbox.layout().setContentsMargins(0, 0, 0, 0)
    #         self.main_grid_layout.setContentsMargins(0, 0, 0, 0)
    #         self.main_grid_layout.setSpacing(0)
    #         for groupbox in self.saving_measurements_groupbox_list:
    #             groupbox.layout().setContentsMargins(0, 0, 0, 0)
    #     else:
    #         self.saving_measurements_groupbox.layout().setContentsMargins(5, 5, 5, 2)
    #         self.plot_groupbox.layout().setContentsMargins(10, 10, 10, 10)
    #         self.logs_groupbox.layout().setContentsMargins(3, 5, 3, 5)
    #         self.text_output_groupbox.layout().setContentsMargins(3, 5, 3, 3)
    #         self.saving_measurements_groupbox.layout().setContentsMargins(5, 0, 5, 3)
    #         self.main_grid_layout.setSpacing(3)
    #         self.main_grid_layout.setContentsMargins(10, 0, 10, 10)
    #         for groupbox in self.saving_measurements_groupbox_list:
    #             groupbox.layout().setContentsMargins(5, 5, 5, 2)
        # QtGui.QResizeEvent.size()
        # list(QtCore.QSize.boundedTo)

    def _addCustomMenuItems(self, menu: QtWidgets.QMenu):
        menu.addSeparator()
        # action = QtWidgets.QAction("Обновить", self, shortcut="Ctrl+U")
        # action.setShortcut("Ctrl+U")
        # menu.addAction(action)
        menu.addAction('Обновить', self.get_avaliable_com)

    @QtCore.pyqtSlot()
    def __textEditContextMenu(self):
        # if not self.sender().isWidgetType == QtWidgets.QTextEdit:
        _normalMenu = self.sender().createStandardContextMenu()
        _normalMenu.addSeparator()
        _normalMenu.addAction(self.open_folder_action)
        _normalMenu.exec_(QtGui.QCursor.pos())

    @QtCore.pyqtSlot()
    def open_folder(self):  # не открываются папки с пробелами!
        self.logger.debug(f"open folder event")
        # правильнее было бы определить родителя и по нему обратиться к нужному виджету
        for i in range(len(self.saving_result_folder_label_list)):
            # if self.saving_result_folder_label_list[i] == self.sender().parent():
            if self.saving_result_folder_label_list[i].hasFocus() or self.file_name_line_edit_list[i].hasFocus():
                # только если есть галочка создавать папку
                path_to_sensor = os.path.realpath(
                    self.saving_result_folder_label_list[i].toPlainText())
                if not (path_to_sensor.find(' ') == -1):
                    self.logger.warning("Path contain space and cannot be open!")
                    return False
                if self.create_folder_checkbox_list[i].isChecked(): # re.split("_", self.file_name_line_edit_list[i].text())[0]
                    if os.path.isdir(path_to_sensor + '/' + re.split("_", self.file_name_line_edit_list[i].text())[0]):
                        path_to_sensor = path_to_sensor + '/' + re.split("_", self.file_name_line_edit_list[i].text())[0]
                    else:
                        self.logger.warning("Sensor folder doesn't exist!")
                # path_to_sensor = path_to_sensor.replace(' ', '\\ ')
                # print(path_to_sensor)
                # path_to_sensor = path_to_sensor.replace('\\', '//')
                # path_to_sensor = path_to_sensor[2:]
                # print(path_to_sensor)
                # print(path_to_sensor[2:])
                # print(repr(path_to_sensor))
                # print(path_to_sensor.find(' '))
                parent_text = r'start ' + path_to_sensor
                # parent_text = path_to_sensor
                # print(parent_text)
                # print("repr(parent_text)")
                # print(repr(parent_text))
                os.system((parent_text))
                return True
                # os.system(repr(parent_text))
                # pypath = sys.executable # "E:\program files\python\python.exe"
                # cmdline = path_to_sensor
                # os.system(pypath + ' ' + cmdline)
                # os.popen('%s %s' % (pypath, cmdline))
                # os.system(repr(parent_text))
        self.logger.warning("Select widget with path")
        return False
        # print(self.sender().parent().parent())
        # path = os.path.realpath(self.sender().parent().parent().toPlainText())
        # parent_text = r"start " + path
        # print(self.sender().parent().parent().toPlainText())
        # print(self.sender().objectName())

    def append_gyro_widgets(self):
        """Append groupbox with widgets for gyroscope."""
        ind = len(self.saving_measurements_groupbox_list)
        self.saving_measurements_groupbox_list.append(QtWidgets.QGroupBox(
            f'Сохранение для gyro{ind + 1}',
            minimumWidth=self.MAX_WIGTH_FIRST_COL / 1.7,
            maximumHeight=175, objectName='small'))
        saving_measurements_groupbox_layout = QtWidgets.QGridLayout(
            spacing=int(9 / self.GYRO_NUMBER))
        saving_measurements_groupbox_layout.setContentsMargins(5, 5, 5, 2)
        self.saving_measurements_groupbox_list[-1].setLayout(
            saving_measurements_groupbox_layout)
        # self.saving_measurements_groupbox_list[-1].installEventFilter(self)

        saving_measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel('Папка:'), 0, 0, 3, 1)
            # QtWidgets.QLabel('<b>Папка:</b>'), 0, 0, 3, 1)
        self.saving_result_folder_label_list.append(QtWidgets.QTextEdit(
            self.folder_name_list[ind],
            objectName="with_bourder"))
        self.saving_result_folder_label_list[-1].setTabChangesFocus(True)
        self.saving_result_folder_label_list[-1].setContextMenuPolicy(
            QtCore.Qt.CustomContextMenu)
        self.saving_result_folder_label_list[-1].customContextMenuRequested.connect(
            self.__textEditContextMenu)
        # self.current_folder_label.setMinimumHeight(20)
        self.saving_result_folder_label_list[-1].setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff) 
        self.saving_result_folder_label_list[-1].setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored,
            QtWidgets.QSizePolicy.Policy.Ignored)
        saving_measurements_groupbox_layout.addWidget(
            self.saving_result_folder_label_list[-1], 0, 1, 3, 4)

        saving_measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel('Имя:'), 3, 0, 1, 1)
        self.file_name_line_edit_list.append(QtWidgets.QLineEdit(f'test{ind + 1}'))
        saving_measurements_groupbox_layout.addWidget(
            self.file_name_line_edit_list[-1], 3, 1, 1, 4)
        self.choose_path_button_list.append(QtWidgets.QPushButton(
            # 'Выбрать папку\nсохранения',
            icon=get_icon_by_name(f'open_folder_{self.ICON_COLOR_LIST[ind]}')))
        saving_measurements_groupbox_layout.addWidget(
            # self.choose_path_button_list[-1], 0, 3, 1, 1)
            self.choose_path_button_list[-1], 4, 0, 1, 2)
        self.create_folder_checkbox_list.append(
            QtWidgets.QCheckBox('папка'))
        saving_measurements_groupbox_layout.addWidget(
            # self.create_folder_checkbox_list[-1], 3, 3, 1, 1)  #
            self.create_folder_checkbox_list[-1], 4, 3, 1, 2)  #

    @QtCore.pyqtSlot()
    def eventFilter(self, obj, event):
        # print(time())
        if event.type() == QtCore.QEvent.ContextMenu:
            if obj is self.stop_button:
                if not self.processing_thr.isRunning():
                    return True
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

    @QtCore.pyqtSlot()
    def stop_no_save(self):
        self.processing_thr.flag_do_not_save = True
        self.stop()

    def get_gyro_count(self):
        if not self.serial_port.open(QtCore.QIODevice.OpenModeFlag.ReadWrite):
            self.logger.warning(
                f"Can't open {self.com_port_name_combobox.currentText()}")
            return False
        self.serial_port.readLine()
        length = len(self.serial_port.readLine())
        length = 20
        self.logger.debug(f"data_len: {length}")
        flag = (length == 20)
        if flag:
            self.GYRO_NUMBER = 3
            self.processing_thr.GYRO_NUMBER = 3
            self.tab_plot_widget.GYRO_NUMBER = 3
        else:
            self.GYRO_NUMBER = 1
            self.processing_thr.GYRO_NUMBER = 1
            self.tab_plot_widget.GYRO_NUMBER = 1
            for i in range(1, len(self.tab_plot_widget.plot_check_box_list)-1):
                self.file_name_line_edit_list[i].setText('')
                self.processing_thr.save_file_name[i] = ''
        for i in range(1, len(self.tab_plot_widget.plot_check_box_list)-1):
            self.saving_measurements_groupbox_list[i].setVisible(flag)
            self.tab_plot_widget.plot_check_box_list[i + 1].setVisible(flag)
            self.tab_plot_widget.groupbox_list[i].setVisible(flag)
        self.serial_port.close()
################################################################################################
#
# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------
#
################################################################################################

    @QtCore.pyqtSlot()
    def save_results(self):
        if self.processing_thr.isRunning():
            self.logger.warning("Thread still work")
            self.logger.debug(
                f"data_recieved_event {self.processing_thr.data_recieved_event.is_set()}")
            # self.processing_thr.data_recieved_event.set()
            # self.processing_thr.flag_full_measurement_start = False
            # self.processing_thr.flag_measurement_start = False
            return False
        # Check filenames
        for i in range(self.GYRO_NUMBER):  # !
            if self.processing_thr.pack_num and not self.processing_thr.flag_by_name_:
                self.make_filename(i)  # !  # без создания имени не получится
            self.processing_thr.start()
        return True

    @QtCore.pyqtSlot(bool)
    def run_thread_for_file_processing(self, _):  ################### изменить для трех, изменить имена
        """Process files to create medial frequency plot."""
        self.logger.debug(
            f"files: {self.tab_plot_widget.selected_files_to_fft}")
        if self.processing_thr.isRunning():
            self.logger.warning("Thread still work")
            return False
        self.tab_plot_widget.clear_plots()
        self.fs = int(self.fs_combo_box.currentText())
        # Copy variables to another classes and start thread
        self.tab_plot_widget.fs = self.fs
        self.processing_thr.fs = self.fs

        self.processing_thr.flag_by_name = True
        self.processing_thr.selected_files_to_fft = self.tab_plot_widget.selected_files_to_fft
        self.processing_thr.start()
        return True
# ----------------------------------------------------------------------------------------------
            
    @QtCore.pyqtSlot()
    def measurement_start(self):
        """Try to start measurement without sending command and saving results."""
        self.tab_plot_widget.time_plot.autoRange()
        self.tab_plot_widget.time_plot.enableAutoRange()
        self.tab_plot_widget.region.setVisible(False)
        self.tab_plot_widget.setCurrentIndex(0)
        self.progress_value = 0  # не создавать эту переменную
        self.progress_bar.setValue(0)
        self.package_num_label.setText('0')
        self.count = 0
        self.current_cylce = 1

        if self.processing_thr.isRunning():
            self.logger.warning("Thread still work")
            return False
        # Check COM port
        self.logger.debug(F"\nPORT: {self.com_port_name_combobox.currentText()}\n")
        if not len(self.com_port_name_combobox.currentText()):
            # self.logger.warning(
                # "Can't find avaliable COM port")
            QtWidgets.QMessageBox.critical(
                self, "Error", "Can't find avaliable COM port")
            self.get_avaliable_com()
            return False
        self.serial_port.setBaudRate(
            int(self.com_boderate_combo_box.currentText()))
        self.serial_port.setPortName(
            self.com_port_name_combobox.currentText())
        self.logger.debug("Set COM settings")

        # self.get_gyro_count()  # !!!!!!!!!!!

        # Open COM
        if not self.serial_port.open(QtCore.QIODevice.OpenModeFlag.ReadWrite):
            self.logger.warning(
                f"Can't open {self.com_port_name_combobox.currentText()}")
            QtWidgets.QMessageBox.critical(
                self, "Error",
                f"Can't open {self.com_port_name_combobox.currentText()}")
            return False
        self.start_all_button.setDisabled(True)
        # надо понять, можно ли 2 раза нажать на старт
        # или нажать на стоп, пока еще запуск не произошел

        self.progress_bar.setMaximum(999)
        self.tab_plot_widget.clear_plots()

        self.logger.debug(f"{self.com_port_name_combobox.currentText()} open")
        self.log_text_box.insertHtml('<br />')
        self.logger.info("Start without saving results")
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
        self.tab_plot_widget.fs = self.fs
        self.processing_thr.fs = self.fs
        self.processing_thr.flag_measurement_start = True
        self.processing_thr.flag_do_not_save = True
        self.processing_thr.total_time = self.table_widget.total_time
        self.processing_thr.start()
        self.set_avaliable_butttons(flag_running=True)  # disable widgets
        return True

    @QtCore.pyqtSlot()
    def full_measurement_start(self):
        self.tab_plot_widget.time_plot.autoRange()
        self.tab_plot_widget.time_plot.enableAutoRange()
        self.tab_plot_widget.setCurrentIndex(0)
        self.time_error = 0  # !
        self.tab_plot_widget.region.setVisible(True)
        self.progress_value = 0  # не создавать эту переменную
        self.progress_bar.setValue(self.progress_value)
        self.package_num_label.setText('0')
        self.count = 0
        self.current_cylce = 1

        if self.processing_thr.isRunning():
            self.logger.warning("Thread still work")
            self.processing_thr.flag_full_measurement_start = False
            self.processing_thr.flag_measurement_start = False
            return False
        # Check COM port
        self.logger.debug(F"PORT: {self.com_port_name_combobox.currentText()}\n")
        if not len(self.com_port_name_combobox.currentText()):
            QtWidgets.QMessageBox.critical(
                self, "Error", "Can't find COM port!")
            self.get_avaliable_com()
            return False
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
                return False
        self.logger.debug("Data from file was loaded")
        # self.get_gyro_count()  # !!!!!!!!!!!
        # Open COM
        if not self.serial_port.open(QtCore.QIODevice.OpenModeFlag.ReadWrite):
            self.logger.warning(
                f"Can't open {self.com_port_name_combobox.currentText()}")
            QtWidgets.QMessageBox.critical(
                self, "Error",
                f"Can't open {self.com_port_name_combobox.currentText()}")
            return False
        self.progress_bar.setFormat('%v/%m сек (определение смещения)')
        self.start_all_button.setDisabled(True)
        # надо понять, можно ли 2 раза нажать на старт или нажать на стоп, пока еще запуск не произошел

        self.tab_plot_widget.clear_plots()
        self.tab_plot_widget.append_fft_plot_tab()

        self.cycle_num_value_change()
        self.progress_bar_set_max()

        self.logger.debug(f"{self.com_port_name_combobox.currentText()} open " +
                         f"self.cycle_num = {self.total_cycle_num}")

        self.serial_port.clear()
        # Start timers
        self.start_time = time()  # !!!!!
        self.timer_recieve.start()
        self.fs = int(self.fs_combo_box.currentText())
        # Copy variables to another classes and start thread
        self.tab_plot_widget.fs = self.fs
        self.processing_thr.fs = self.fs
        self.processing_thr.flag_measurement_start = True  # !!!!!
        self.processing_thr.total_time = self.table_widget.total_time
        self.processing_thr.num_measurement_rows = self.table_widget.rowCount()
        self.processing_thr.flag_do_not_save = True
        self.processing_thr.total_cycle_num = self.total_cycle_num
        self.processing_thr.start()
        QtCore.QTimer.singleShot(1500, self.end_start)
        self.set_avaliable_butttons(flag_running=True)  # disable widgets
        self.log_text_box.insertHtml('<br />')
        self.logger.info("Start")
        return True

    @QtCore.pyqtSlot()
    def end_start(self):
        """Start measurement with FFT processing."""
        self.progress_bar.setFormat('%v/%m сек')
        if self.processing_thr.flag_measurement_start:
            self.serial_port.clear()
            self.processing_thr.flag_do_not_save = False
            # self.timer_recieve.setInterval(0)
            # self.timer_send_com.setInterval(0)
            self.processing_thr.flag_full_measurement_start = True
            self.processing_thr.flag_measurement_start = False
            # self.processing_thr.data_recieved_event.set()
            # Start timer
            self.start_time = time()
            self.table_widget.selectRow(0)
            self.check_time = time() - self.table_widget.get_current_T() / 1000
            # self.check_time = time() - 0.75
            # self.flag_send = False
            self.flag_send = True
            # self.timer_event_send_com()
            self.timer_send_com.setInterval(self.PAUSE_INTERVAL_MS)
            # print(f"timer_event_send_com {self.timer_send_com.interval()}") # +
            self.timer_send_com.start()
            # print(f"timer_event_send_com {self.timer_send_com.interval()}") # +
            self.logger.debug('start full measurements')
            # self.logger.warning(f"Shift: {self.processing_thr.amp_shift}")
# ------ Timer Recieve --------------------------------------------------------

    @QtCore.pyqtSlot()
    def timer_read_event(self):
        """Connect COM port readyread signal to read function.
        Generate warning if avaliable less than 14 bytes."""
        if not self.serial_port.receivers(self.serial_port.readyRead):
            self.serial_port.readyRead.connect(self.read_serial)
        else:
            if 0 < self.serial_port.bytesAvailable() <= 20 * 2:
                self.logger.warning(
                    f"Not enough data from {self.com_port_name_combobox.currentText()}")
            else:
                self.logger.warning(
                    f"No data from {self.com_port_name_combobox.currentText()}!")
        # self.read_serial()

    @QtCore.pyqtSlot()
    def read_serial(self):
        """Read data from COM port."""
        self.logger.debug(
            f"ready to read, bytes num = {self.serial_port.bytesAvailable()}")  # +
        if self.serial_port.bytesAvailable() <= 20 * 2:
            return False
        self.serial_port.readyRead.disconnect(self.read_serial)
        if self.processing_thr.data_recieved_event.is_set():
            self.logger.warning("Thread still work with previous data")
            return False
        self.copy_variables_to_thread()
        self.logger.debug(f"command thr to start, count = {self.count}")

    def copy_variables_to_thread(self):
        self.processing_thr.rx += self.serial_port.readAll().data() # частичное обнуление в потоке
        self.processing_thr.count_fft_frame = self.count
        # self.processing_thr.flag_send = self.flag_send  # !!!!!!!!!!!!!!!
        # --- в конце выставляем флаг обработки данных ---
        self.processing_thr.data_recieved_event.set()

        # self.show_bytes_flag = True  # чтение байтов!
        # temp = np.copy(self.processing_thr.rx)
        # if self.show_bytes_flag:
        #     self.stop_no_save()
        #     self.show_bytes_flag = False
        #     self.tab_plot_widget.time_plot.setVisible(False)
        #     self.tab_plot_widget.spectrum_button.setVisible(False)
        #     self.tab_plot_widget.bytes_widget.setVisible(True)
        #     if True:
        #         opt = np.get_printoptions()
        #         # np.set_printoptions(threshold=np.inf, linewidth=60)
        #         # np.set_printoptions(threshold=np.inf, linewidth=118)
        #         np.set_printoptions(threshold=np.inf)
        #         self.tab_plot_widget.bytes_widget.insertPlainText(
        #             str(np.frombuffer(temp, dtype=np.uint8)))
        #         np.set_printoptions(**opt)
        #         # threshold=None, edgeitems=10 , linewidth=200
        #     else:
        #         self.custom_tab_plot_widget.bytes_widget.insertPlainText(
        #             str(self.serial_port.readAll().data()))
        #         self.custom_tab_plot_widget.bytes_widget.insertPlainText('\n\n')
# ------- Timer Send ----------------------------------------------------------

    @QtCore.pyqtSlot()
    def timer_event_send_com(self):
        """Send command with frequency and amplitude or stop vibration."""
        if self.flag_send:
            if self.count >= self.table_widget.rowCount():
                self.logger.debug(
                    f"end cycle = {self.current_cylce}")
                if self.current_cylce < self.total_cycle_num:
                    self.new_cycle_event()
                    self.send_stop_vibro_command()
                else:
                    self.stop()
                return
            self.send_vibro_command()
        else:
            self.send_stop_vibro_command()
        self.flag_send = not self.flag_send
        self.processing_thr.flag_send = self.flag_send  # так все-таки лучше 
        self.processing_thr.data_recieved_event.set()
        # self.check_time = time()

    def send_stop_vibro_command(self):
        """Send command with frequency and amplitude."""
        if self.time_error > 250 or self.time_error < -250:
            control = 75 * self.time_error / abs(self.time_error)
        else:
            control = 0.3 * self.time_error
        self.timer_send_com.setInterval(self.PAUSE_INTERVAL_MS - control)
        self.serial_port.write(bytes([0, 0, 0, 0, 0, 0, 0, 0]))
        # self.timer_send_com.setInterval(self.PAUSE_INTERVAL_MS)
        self.logger.debug("---stop vibro command was send") # +

    def send_vibro_command(self):
        """Send command to stop vibration."""
        # --- time regulator ---
        self.time_error += ((time() - self.check_time) * 1000 - \
            (self.table_widget.get_current_T() + self.PAUSE_INTERVAL_MS))
        # ---  ---

        self.table_widget.selectRow(self.count)
        self.timer_send_com.setInterval(self.table_widget.get_current_T())
        F = int.to_bytes(self.table_widget.get_current_F(),
                         length=2, byteorder='little', signed=False)
        A = int.to_bytes(self.table_widget.get_current_A(),
                         length=2, byteorder='little', signed=False)
        # import subprocess
        # FNULL = open(os.devnull, 'w')    #use this if you want to suppress output to stdout from the subprocess
        # filename = r'send.exe'
        # args = filename + "1 111"
        # # print(subprocess.call(args, stdout=FNULL, stderr=FNULL, shell=False))
        # self.serial_port.close()
        # sleep(0.01)
        # t = time()
        # # subprocess.call([filename, "SetVel", "1", "100"], stdout=FNULL)
        # subprocess.Popen([filename, "SetVel", "1", "100"], stdout=FNULL)
        # print(time()-t)
        # sleep(0.01)
        # self.serial_port.open(QtCore.QIODevice.OpenModeFlag.ReadWrite)
        self.serial_port.write(
            bytes([77, 0, F[0], F[1], A[0], A[1], 0, 0]))
        self.logger.debug(
            f"--- vibro command {self.count} was send, time: {time() - self.check_time}")
        self.count += 1

        # --- time regulator ---
        # self.time_error += 1 * ((time() - self.check_time) * 1000 - \
        #     (self.table_widget.get_current_T() + self.PAUSE_INTERVAL_MS))
        self.logger.debug(
            f"time_error: {self.time_error}")
        self.check_time = time()
        # ---  ---

# ----- End cycle, stop, etc --------------------------------------------------
    def new_cycle_event(self):
        self.logger.info(
            f"End of cycle {self.current_cylce} of {self.total_cycle_num}")
        self.current_cylce += 1
        self.count = 0
        self.processing_thr.new_measurement_cycle()
        self.logger.debug("append tab")
        self.tab_plot_widget.append_fft_plot_tab()
        self.logger.debug("end append tab")

    @QtCore.pyqtSlot()
    def stop(self):
        """Stop timers, stop measurement processing in thread,
        send filenames to thread and stop command to vibrostand."""
        if self.timer_send_com.isActive():
            self.logger.debug("Stop timer_send_com")
            self.timer_send_com.stop()
        if self.timer_recieve.isActive():
            self.logger.debug("Stop timer_recieve")
            self.timer_recieve.stop()
        if self.processing_thr.isRunning():
            # --- Check filenames ---
            for i in range(self.GYRO_NUMBER):
                self.make_filename(i)
            if self.processing_thr.flag_do_not_save:
                self.logger.info("No saving")
        self.processing_thr.flag_full_measurement_start = False
        self.processing_thr.flag_measurement_start = False
        self.processing_thr.data_recieved_event.set()
        self.flag_send = False
        if self.serial_port.isOpen():
            # if self.processing_thr.flag_full_measurement_start:
            self.serial_port.write(bytes([0, 0, 0, 0, 0, 0, 0, 0]))
            self.logger.debug("COM close? " +
                              str(self.serial_port.waitForBytesWritten(50)))
            sleep(0.05)
            self.logger.info("End of measurements\n")
            self.serial_port.close()
            if self.progress_value > 3:
                check = int(int(self.package_num_label.text()) / self.progress_value)
                if not (0.95 * self.fs < check < 1.05 * self.fs):
                    QtWidgets.QMessageBox.critical(
                        self, "Warning",
                        f"You set fs = {self.fs} Hz," +
                        f"but in fact it's close to {check} Hz")
        self.set_avaliable_butttons(False)

        total_time = self.total_cycle_num * (self.table_widget.total_time +
                (self.table_widget.rowCount() + 1) * self.PAUSE_INTERVAL_MS / 1000)
        self.logger.debug(
            f"real progress time = {self.progress_value}, " +
            f"progress_bar.maximum = {self.progress_bar.maximum()}, total time (not rounded) =  ({total_time})")
###############################################################################
# ----- plotting --------------------------------------------------------------

    @QtCore.pyqtSlot(int, np.ndarray)
    def get_and_show_data_from_thread(self, package_num_signal, plot_data):
        """Receiving the processed measurement data
            (package num, time data to graph)."""
        self.logger.debug("start plot")
        self.package_num_label.setText(str(package_num_signal))
        self.progress_value = time() - self.start_time
        self.progress_bar.setValue(int(round(self.progress_value)))
        self.logger.debug(f"real progress_value: {self.progress_value}," +
                          f"thr_stop, count = {self.count}, " +
                          f"package_num = {package_num_signal} ")
        # if self.count == 0:
        #     self.custom_tab_plot_widget.plot_time_graph(
        #         self.processing_thr.to_plot[:, 0],
        #         self.processing_thr.to_plot[:, 2],
        #         self.processing_thr.to_plot[:, 1::self.processing_thr.pack_len])
        self.tab_plot_widget.plot_time_graph(
            plot_data[:, 0], plot_data[:, 2], plot_data[:, 1::self.processing_thr.pack_len])
            # plot_data[:, 0], plot_data[:, 2], plot_data[:, 1::4])
        self.logger.debug("end plot")

    @QtCore.pyqtSlot()
    def show_certain_data(self):  # работает
        """Show part of time plot when you select row in table."""
        # возможно, лучше часть этих вычислений делать в функции потока
        if self.processing_thr.isRunning():
            # self.logger.warning("You can see previous results only after stop")
            return False
        if int(self.package_num_label.text()):
            time = 0
            # time += self.PAUSE_INTERVAL_MS / 1000
            for i in range(self.table_widget.currentRow()):
                time += int(self.table_widget.item(i, 2).data(
                    QtCore.Qt.ItemDataRole.EditRole)) + self.PAUSE_INTERVAL_MS / 1000
            self.logger.debug(f"{self.table_widget.currentRow()} {self.current_cylce} {time}")
            start = time * self.fs #- self.processing_thr.points_shown / 4
            start += self.processing_thr.package_num_list[-2]
            self.logger.debug(f"package_num_list: {self.processing_thr.package_num_list} {start}")
            if start > int(self.package_num_label.text()) or start > self.processing_thr.time_data.shape[0]:
                self.logger.warning("Out of range")
                return False
            # if start < 0:  # start = 0
            start = int(start)
            end = start + self.processing_thr.to_plot.shape[0]
            if end > int(self.package_num_label.text()):
                end = int(self.package_num_label.text())
            else:
                end = int(end)
            self.logger.debug(f"start={start}, end={end}")
            self.tab_plot_widget.plot_time_graph(
                self.processing_thr.time_data[start:end, 0] / self.fs,
                self.processing_thr.time_data[start:end, 2] / 1000,
                self.processing_thr.time_data[start:end, 1::self.processing_thr.pack_len] / 1000 / self.processing_thr.k_amp)
            self.tab_plot_widget.region.setVisible(False)
            self.tab_plot_widget.time_plot.autoRange()
            self.tab_plot_widget.region.setVisible(True)

    @QtCore.pyqtSlot(bool)
    def plot_fft(self, _):
        """Adds points to frequency graphs."""
        self.logger.debug("start plot_fft")
        # if self.count == 1:  # можно установить ссылку на массив, тогда при его заполнении график будет меняться автоматически (не будет)
        # print(self.processing_thr.all_fft_data[:, (self.current_cylce-1)*4:self.current_cylce*4, :])
        self.tab_plot_widget.set_fft_data(
            self.processing_thr.all_fft_data[:, (self.current_cylce-1)*4:self.current_cylce*4, :],
            self.processing_thr.bourder)
        self.logger.debug("end plot_fft")

    @QtCore.pyqtSlot(list)
    def plot_fft_final(self, name: list):
        self.package_num_label.setText(str(self.processing_thr.pack_num))
        # здесь число пакетов получать, чтобы можно было прежние записи просматривать
        self.logger.debug(f"Final median plot {name}")
        self.tab_plot_widget.set_fft_median_data(
            self.processing_thr.all_fft_data[:, -4:],
            self.processing_thr.special_points, name)

    @QtCore.pyqtSlot()
    def save_image(self):
        self.logger.debug("Save image")
        for i in range(self.GYRO_NUMBER):
            # if (len(self.processing_thr.save_file_name[i])
                # and self.plot_check_box_list[i].isChecked()):
            if self.tab_plot_widget.plot_check_box_list[i].isChecked():
                # if self.processing_thr.flag_full_measurement_start:  # !
                self.make_filename(i)  # !
                self.tab_plot_widget.save_plot_image(
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
        """Enable or disable widgets."""
        self.cycle_num_spinbox.setDisabled(flag_running)
        self.edit_file_button.setDisabled(flag_running)
        self.start_all_button.setDisabled(flag_running)
        self.stop_button.setDisabled(not flag_running)
        self.choose_file.setDisabled(flag_running)
        self.start_full_measurement_action.setDisabled(flag_running)
        self.stop_action.setDisabled(not flag_running)
        self.measurement_action.setDisabled(flag_running)
        self.stop_with_no_save_action.setDisabled(not flag_running) 
        self.save_action.setDisabled(flag_running)
        self.com_param_groupbox.setDisabled(flag_running)
        self.fs_groupbox.setDisabled(flag_running)
        self.enable_crc_action.setDisabled(flag_running)
        self.change_gyro_count_action.setDisabled(flag_running)
        for button in self.choose_path_button_list:
            button.setDisabled(flag_running)
        # self.table_widget.horizontalHeader().setSectionsClickable(False)
        # self.table_widget.verticalHeader().setSectionsClickable(False)
        # self.table_widget.horizontalHeader().sectionPressed.disconnect()
        # self.table_widget.itemClicked.disconnect(self.table_widget.selectColumn) 
        # self.table_widget.itemPressed.disconnect(self.table_widget.selectColumn)
        # self.table_widget.itemClicked.connect(self.check_table) 
        # self.table_widget.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        if self.GYRO_NUMBER == 1:
            self.gyro1_4_action.setDisabled(flag_running)  # !
        # for groupbox in self.saving_measurements_groupbox_list:
            # groupbox.setDisabled(flag_running)
        # saving_measurements_groupbox_list можно редактировать,
        # т.к. путь отправляется в поток перед окончанием цикла

    # def check_table(self):
    #     if self.processing_thr.flag_full_measurement_start:
    #         self.table_widget.selectRow(self.count)
            
    def get_avaliable_com(self):
        """Append avaliable COM ports names to combo box widget."""
        port_name_list = [ports.portName() 
               for ports in QSerialPortInfo.availablePorts()]
        if len(port_name_list):
            while(self.com_port_name_combobox.count()):  # !
                self.com_port_name_combobox.removeItem(0)
            self.com_port_name_combobox.addItems(
                sorted(port_name_list, key=natural_keys))
            self.logger.info('Update avaliable COM port list')
        else:
            self.logger.warning('No COM ports available')

# ------ file name and data from file -----------------------------------------
    def make_filename(self, i: int):
        """Check conditions and create filename and path."""
        # подправить if
        if (not len(self.file_name_line_edit_list[i].text()) or
            not len(self.folder_name_list[i]) or
            not len(self.saving_result_folder_label_list[i].toPlainText())): # or not len():
            self.processing_thr.save_file_name[i] = ''
            return False
        if not os.path.isdir(self.folder_name_list[i]):
            self.processing_thr.save_file_name[i] = ''
            self.logger.warning(f"Path {self.folder_name_list[i]} doesn't exist!")
            return False
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
        return True

    # @QtCore.pyqtSlot()
    # def directory_changed(self, path):
    #     self.logger.debug(f'Directory Changed: {path}')
    #     print(f'Directory Changed: {path}')

    @QtCore.pyqtSlot()
    def folder_change_event(self):
        for i in range(len(self.saving_result_folder_label_list)):
            if self.sender() == self.saving_result_folder_label_list[i]:
                break
        else:
            return
        if not os.path.exists(self.saving_result_folder_label_list[i].toPlainText()):
            self.saving_result_folder_label_list[i].setStyleSheet("color: grey;")
        else:
            self.saving_result_folder_label_list[i].setStyleSheet("color: #FFFFF1;")
        self.folder_name_list[i] = self.saving_result_folder_label_list[i].toPlainText() + '/'   

    @QtCore.pyqtSlot()
    def choose_result_saving_path(self):
        """Folder selection dialog."""
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
        """Вызывается при изменении пути к файлу измерений."""
        if not os.path.isfile(self.filename_and_path_textedit.toPlainText()):  # text
            # self.logger.debug("The file path does not exist!")  # !
            self.filename_and_path_textedit.setStyleSheet("color: grey;")
            return False
        if len(self.filename_and_path_textedit.toPlainText()):
            self.file_watcher.removePath(self.filename_path_watcher)
        self.filename_and_path_textedit.setStyleSheet("color: #FFFFF1;")
        self.filename_path_watcher = self.filename_and_path_textedit.toPlainText()  # os.path.basename(filename)
        self.file_watcher.addPath(self.filename_path_watcher)
        return self.get_data_from_file(self.filename_path_watcher)

    @QtCore.pyqtSlot(str)
    def check_filename_and_get_data(self, path: str):
        """Reload measurenet file."""
        self.logger.debug(
            f'measurement File Changed, {path},' +
            f'thr run? {self.processing_thr.flag_full_measurement_start}')
        if not self.processing_thr.flag_full_measurement_start and os.path.exists(path):
            self.get_data_from_file(path)

    @QtCore.pyqtSlot()
    def choose_and_load_file(self):
        """Open file selection dialog and load selected measurement file."""
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
        """Get data from file and put it in table."""
        with open(filename_path_watcher, 'r') as file:
            self.table_widget.set_table(file)
            self.progress_bar_set_max()
        return self.table_widget.total_time > 0

    @QtCore.pyqtSlot()
    def open_file(self):
        """Open .txt file."""
        self.logger.debug('startfile')
        if os.path.isfile(self.filename_and_path_textedit.toPlainText()):
            os.startfile(self.filename_and_path_textedit.toPlainText())
        else:
            self.logger.warning('Wrong filename!')

    @QtCore.pyqtSlot()
    def closeEvent(self, _):
        """Sending stop command to the vibrostand and saving user settings."""
        self.logger.info("Saving the settings and exit")
        self.stop()
        for i in range(self.tab_plot_widget.count()):
            self.tab_plot_widget.widget(i).deleteLater() # во избежание Warning: ViewBox should be closed before application exit.
        self.save_settings()
        self.logger.info("Wait Excel to close...")
        try:
            self.tab_plot_widget.close_excel_com_object()  # !
            self.logger.debug("Close COM object\n")
        except Exception as e:
            self.logger.debug(f"Can't close COM object! {e}\n")

# ------ settings --------------------------------------------------------------------
    def save_settings(self):
        """Check condition and write settings in .ini and .json files."""
        self.tab_plot_widget.projects_combo_box.save_json(self.PROJECT_FILE_NAME)
        self.settings.setValue(f'GYRO_NUMBER{self.GYRO_NUMBER}',
                               self.GYRO_NUMBER)
        # --- ---
        self.settings.setValue(f'autosave{self.GYRO_NUMBER}',
                               int(self.settings_autosave_action.isChecked()))
        if self.settings_autosave_action.isChecked():
            self.save_all_settings()

    def save_all_settings(self):
        """Write settings in .ini file."""
        self.com_boderate_combo_box.save_all()
        self.fs_combo_box.save_all()
        self.com_port_name_combobox.save_current_text()
        self.settings.setValue(f'cycle_num{self.GYRO_NUMBER}',
                                self.cycle_num_spinbox.value())
        self.settings.setValue(f'filename{self.GYRO_NUMBER}',
                                self.filename_and_path_textedit.toPlainText())
        self.settings.setValue(f'current_folders{self.GYRO_NUMBER}',
                               self.folder_name_list)
        self.settings.setValue(f'create_folder_flag{self.GYRO_NUMBER}',
                               [int(checkbox.isChecked()) 
                                for checkbox in self.create_folder_checkbox_list])
        self.settings.setValue(f'enable_debug_in_file{self.GYRO_NUMBER}',
                               int(self.log_text_box.enable_debug_in_file.isChecked()))
        # лучше сохранять и распаковывать эти настройки в отдельном файле в классе комбобокса
        # или, как максимум, одну функцию оставить
        # self.settings.setValue(self.enable_crc_action
            # 'dict', self.custom_tab_plot_widget.projects_combo_box.projects_dict)
        self.settings.setValue(
            f'dict_curr_project{self.GYRO_NUMBER}',
            self.tab_plot_widget.projects_combo_box.currentText())
        self.settings.setValue(f'crc_enable{self.GYRO_NUMBER}',
                               int(self.enable_crc_action.isChecked()))
        if self.GYRO_NUMBER == 1:
            self.settings.setValue(
                'full_data_flag', int(self.gyro1_4_action.isChecked()))

    def load_previous_settings(self, settings: QtCore.QSettings):
        """Get previous settings from .ini and .json files."""
        self.log_text_box.enable_debug_in_file.setChecked(
            self.get_settings("enable_debug_in_file" + str(self.GYRO_NUMBER), True))
        self.enable_crc_action.setChecked(
            self.get_settings("crc_enable" + str(self.GYRO_NUMBER),
                              (False if self.GYRO_NUMBER == 1 else True)))
        self.settings_autosave_action.setChecked(
            self.get_settings("autosave" + str(self.GYRO_NUMBER), True))
        self.cycle_num_spinbox.setValue(
            self.get_settings("cycle_num" + str(self.GYRO_NUMBER), 1))
        self.change_crc_mode()
        if self.settings.contains("full_data_flag") and self.GYRO_NUMBER == 1:
            self.gyro1_4_action.setChecked(int(self.settings.value("full_data_flag")))
            self.gyro_full_data_or_not()
        if settings.contains("filename" + str(self.GYRO_NUMBER)):
            name = settings.value("filename" + str(self.GYRO_NUMBER))
            if os.path.exists(name):
                self.filename_and_path_textedit.setText(name)
                if self.get_data_from_file(name):
                    self.logger.info("The previous file is loaded")
                self.filename_path_watcher = self.filename_and_path_textedit.toPlainText()  # os.path.basename(filename)
                self.file_watcher.addPath(self.filename_path_watcher)
        if settings.contains("create_folder_flag" + str(self.GYRO_NUMBER)):
            for i in range(min(len(settings.value("create_folder_flag" + str(self.GYRO_NUMBER))),
                               len(self.create_folder_checkbox_list))):
                self.create_folder_checkbox_list[i].setChecked(
                    int(settings.value("create_folder_flag" + str(self.GYRO_NUMBER))[i]))
        if settings.contains("current_folders" + str(self.GYRO_NUMBER)):
            for i in range(min(len(settings.value("current_folders" + str(self.GYRO_NUMBER))),
                               len(self.saving_result_folder_label_list))):
                if (os.path.isdir(settings.value("current_folders" + str(self.GYRO_NUMBER))[i])
                    or len(settings.value("current_folders" + str(self.GYRO_NUMBER))[i]) == 0):
                    self.saving_result_folder_label_list[i].setText(
                        settings.value("current_folders" + str(self.GYRO_NUMBER))[i])
                    self.folder_name_list[i] = settings.value(
                        "current_folders" + str(self.GYRO_NUMBER))[i]
        # попробовать сохранить в json или вместо словаря использовать dataFrame pandas
        # можно будет добавить пункт открыть исходник, чтобы вручную редактировать
        if not os.path.isfile(self.PROJECT_FILE_NAME):
            self.logger.warning(f"No json file:\n{self.PROJECT_FILE_NAME}")
            return
        self.tab_plot_widget.projects_combo_box.load_json(self.PROJECT_FILE_NAME)
        # try:
        #     with open(self.PROJECT_FILE_NAME, 'r', encoding='utf-8') as f:  # оставить чтение json
        #         projects_dict = json.load(f)
        # except FileNotFoundError:
        #     self.logger.warning(f"No json file:\n{self.PROJECT_FILE_NAME}!")
        #     return
        if self.settings.contains('dict_curr_project' + str(self.GYRO_NUMBER)):
            for i in range(self.tab_plot_widget.projects_combo_box.count()):
                if self.tab_plot_widget.projects_combo_box.itemText(i) == \
                    self.settings.value('dict_curr_project' + str(self.GYRO_NUMBER)):
                    self.tab_plot_widget.projects_combo_box.setCurrentIndex(i)

    def get_settings(self, name, otherwise_val):
        """Get settings or set deafault value"""
        if self.settings.contains(name):
            return int(self.settings.value(name))
        else:
            return otherwise_val
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
#
###############################################################################
###############################################################################
#
###############################################################################
###############################################################################
#
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    splash = QtWidgets.QSplashScreen(QtGui.QPixmap(get_res_path('res/load_icon.png')))
    splash.show()
    app.processEvents()
    window = AppWindow()
    splash.finish(window)
    sys.exit(app.exec())
