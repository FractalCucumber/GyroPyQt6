import logging
import sys
import os
import re
import numpy as np
# from datetime import datetime # from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo
from time import time
import PyQt_Logger
import PyQt_Thread
import PyQt_CustomWidgets
from PyQt_Functions import get_icon_by_name, get_res_path
# from PyQt5_res_path import get_res_path

# pg.setConfigOption('background', '#f0f0f5')  # Установите фон в серый цвет
# pg.setConfigOption('foreground', 'd')

# d:/Gyro2023_Git/venv3.6/Scripts/Activate.bat
# git add PyQt_ApplicationClass.py PyQt_CustomWidgets.py PyQt_Thread.py PyQt_Logger.py PyQt_Functions.py
# pyinstaller PyQt_ApplicationOnefolder.spec
# pyinstaller PyQt5_Application.spec 
# pyinstaller --onefile --noconsole PyQt5_Application.py
# pyinstaller --add-data "StyleSheets.css;." --add-data "icon_16.png;." --add-data "icon_24.png;." --add-data "icon_32.png;." --add-data "icon_48.png;." --onefile --windowed PyQt5_Application.py --exclude-module matplotlib --exclude-module hook --exclude-module setuptools --exclude-module DateTime --exclude-module pandas --exclude-module PyQt5.QtOpenGL --exclude-module PyQt5.QtOpenGLWidgets --exclude-module hooks --exclude-module hook --exclude-module pywintypes --exclude-module flask --exclude-module opengl32sw.dll
# pyinstaller --add-data "StyleSheets.css;." --add-data "icon_16.png;." --add-data "icon_24.png;." --add-data "icon_32.png;." --add-data "icon_48.png;." --windowed PyQt5_Application.py
# pyinstaller --add-data "StyleSheets.css;." --onefile --windowed PyQt5_Application.py
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class AppWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):

        QtWidgets.QMainWindow.__init__(self, parent)
        QtWidgets.QApplication.setAttribute(
            QtCore.Qt.ApplicationAttribute.
            AA_UseStyleSheetPropagationInWidgetStyles,
            True)  # наследование свойств оформления потомков от родителей
        self.setWindowTitle("GyroVibroTest")
        # print(QtWidgets.QStyleFactory.keys())
        QtWidgets.QApplication.setStyle('Fusion')  # 'Fusion' 'Windows' 'windowsvista' ... QtWidgets.QStyle
# ------ GUI ------------------------------------------------------------------
        # widget = QtWidgets.QWidget(objectName="size16px")
        widget = QtWidgets.QWidget()
        self.main_grid_layout = QtWidgets.QGridLayout(widget, spacing=5)
        self.setCentralWidget(widget)
# ------ Init vars ------------------------------------------------------------
        self.GYRO_NUMBER = 3  #1
        self.PLOT_TIME_INTERVAL_SEC = 10
        self.PAUSE_INTERVAL_MS = 750
        self.READ_INTERVAL_MS = 100 * 2  #  125 * 2
        # self.folder_name_list = [os.getcwd() + '/'] * self.GYRO_NUMBER
        self.folder_name_list = [''] * self.GYRO_NUMBER
        self.count: int = 0
        self.progress_value = 0 # убрать?
        self.total_cycle_num: int = 1
        self.current_cylce: int = 0
        self.filename_path_watcher = ""
        STYLE_SHEETS_FILENAME = 'res\StyleSheets.css'
        # FILE_LOG_FLAG = False
        FILE_LOG_FLAG = True
        LOGGER_NAME = 'main'
        self.ICON_COLOR_LIST = ['red', 'green', 'blue']
        self.serial_port = QSerialPort(dataBits=QSerialPort.DataBits.Data8,
                                  stopBits=QSerialPort.StopBits.OneStop,
                                  parity=QSerialPort.Parity.NoParity)
        self.settings = QtCore.QSettings("settings")

# ------ Style ----------------------------------------------------------------
        # with open(self.get_res_path(STYLE_SHEETS_FILENAME),
        #           "r") as style_sheets_css_file:
        with open(get_res_path(STYLE_SHEETS_FILENAME),
                  "r") as style_sheets_css_file:
            self.setStyleSheet(style_sheets_css_file.read())
        app_icon = QtGui.QIcon()
        for i in [16, 24, 32, 48]:
            app_icon.addFile(
                get_res_path(f'res\icon_{i}.png'), QtCore.QSize(i, i))
                # self.get_res_path(f'res\icon_{i}.png'), QtCore.QSize(i, i))
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
# ------ Logger ---------------------------------------------------------------
        self.log_text_box = PyQt_Logger.QTextEditLogger(
            self, file_log=FILE_LOG_FLAG)
# ------ Thread ---------------------------------------------------------------
        self.processing_thr = PyQt_Thread.SecondThread(
            gyro_number=self.GYRO_NUMBER,
            READ_INTERVAL_MS=self.READ_INTERVAL_MS,
            logger_name=LOGGER_NAME)
        self.processing_thr.package_num_signal.connect(self.plot_time_graph)
        self.processing_thr.fft_data_signal.connect(self.plot_fft)
        self.processing_thr.median_data_ready_signal.connect(
            self.plot_fft_final)
        self.logger = logging.getLogger(LOGGER_NAME)
        self.processing_thr.warning_signal.connect(
            lambda text: self.logger.warning(text))
        # self.custom_tab_plot_widget.filenames_list_emit.connect(
# ------ Plots in tab widget --------------------------------------------------
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
        # menu_1.addAction('New')
        # menu_1.addAction('Open')
        # menu_1.addAction('Save')
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
        save_action = QtWidgets.QAction("&Save data", self)
        # exit_action.setShortcut("Ctrl+Q")
        # exit_action.setStatusTip("Exit application")  # ???
        save_action.triggered.connect(self.save_results)
        options_menu.addSeparator()
        options_menu.addAction(save_action)
        exit_action = QtWidgets.QAction("&Exit", self)
        # exit_action.setShortcut("Ctrl+Q")
        # exit_action.setStatusTip("Exit application")  # ???
        exit_action.triggered.connect(self.close)
        options_menu.addSeparator()
        options_menu.addAction(exit_action)

# ------ Com Settings ---------------------------------------------------------
        """
        Block with COM port settings and sampling frequency selection
        """
        self.com_param_groupbox = QtWidgets.QGroupBox(
            'Настройки COM порта', maximumWidth=310)
        self.com_param_groupbox_layout = QtWidgets.QGridLayout()
        self.com_param_groupbox.setLayout(self.com_param_groupbox_layout)

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
        # self.com_param_groupbox_layout.addWidget(QtWidgets.QLabel('COM:'),
                                                #  0, 0, 1, 1)
        self.com_param_groupbox_layout.addWidget(self.com_port_name_combobox,
                                                 0, 0, 1, 1)

        self.com_boderate_combo_box = PyQt_CustomWidgets.CustomComboBox(
            settings=self.settings,
            settings_name="COM_speed_settings",
            default_items_list=['921600', '115200', '0'])
        # self.com_param_groupbox_layout.addWidget(QtWidgets.QLabel('Скорость:'),
                                                #  1, 0, 1, 1)  # Speed
        self.com_param_groupbox_layout.addWidget(self.com_boderate_combo_box,
                                                 0, 1, 1, 1)
# ------  fs  -----------------------------------------------------

        self.fs_groupbox = QtWidgets.QGroupBox(
            'FS, Гц', maximumWidth=155)
        self.fs_groupbox_layout = QtWidgets.QGridLayout()
        self.fs_groupbox.setLayout(self.fs_groupbox_layout)
        self.fs_combo_box = PyQt_CustomWidgets.CustomComboBox(
            settings=self.settings,
            settings_name="fs_settings",
            default_items_list=['1000', '2000', '741'])
        self.fs = int(self.fs_combo_box.currentText())
        self.fs_groupbox_layout.addWidget(self.fs_combo_box,
                                                 0, 0, 1, 1)
# ------  cycle num  -----------------------------------------------------
        self.cycle_number_groupbox = QtWidgets.QGroupBox(
            'Циклы:', maximumWidth=155)
        self.cycle_number_groupbox_layout = QtWidgets.QGridLayout()
        self.cycle_number_groupbox.setLayout(self.cycle_number_groupbox_layout)

        self.cycle_num_widget = QtWidgets.QSpinBox(
            minimum=1, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
        # self.cycle_number_groupbox_layout.addWidget(
            # QtWidgets.QLabel(''), 0, 0, 3, 2)  # Cycle number
        self.cycle_number_groupbox_layout.addWidget(self.cycle_num_widget)#,
                                                    # 0, 2, 3, 2)
# ------ Measurement File -----------------------------------------------------
        """
        Block with button to open and edit measurement file
        """
        self.measurements_groupbox = QtWidgets.QGroupBox(
            'Измерения', maximumWidth=310)
        self.measurements_groupbox_layout = QtWidgets.QGridLayout()
        self.measurements_groupbox.setLayout(self.measurements_groupbox_layout)

        # self.measurements_groupbox_layout.addWidget(
        #     QtWidgets.QLabel('Measurement\ncycle file:'), 1, 0, 1, 1)
        self.choose_file = QtWidgets.QPushButton(
            'Выбрать',
            icon=get_icon_by_name('open_folder'))  # &Choose file
        self.measurements_groupbox_layout.addWidget(self.choose_file,
                                                    3, 0, 1, 2)

        self.edit_file_button = QtWidgets.QPushButton('Открыть')  # &Open file
        self.measurements_groupbox_layout.addWidget(self.edit_file_button,
                                                    3, 2, 1, 2)

        self.measurements_groupbox_layout.addWidget(
            QtWidgets.QLabel('Путь:'), 0, 0, 3, 1)  # Filepath

        self.filename_and_path_widget = QtWidgets.QTextEdit(
            objectName="with_bourder")
        self.filename_and_path_widget.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff) 
        self.filename_and_path_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored,
            QtWidgets.QSizePolicy.Policy.Ignored)
        self.measurements_groupbox_layout.addWidget(
            self.filename_and_path_widget, 0, 1, 3, 3)
        # self.measurements_groupbox_layout.setSizeConstraint(
        # QtWidgets.QLayout.SizeConstraint.SetNoConstraint)

# ------ Saving results -------------------------------------------------------
      
        self.saving_measurements_groupbox_list: list[QtWidgets.QGroupBox] = []
        self.saving_result_folder_label_list: list[QtWidgets.QTextEdit] = []
        self.create_folder_checkbox_list: list[QtWidgets.QCheckBox] = []
        self.file_name_line_edit_list: list[QtWidgets.QLineEdit] = []
        self.choose_path_button_list: list[QtWidgets.QPushButton] = []

        self.saving_measurements_groupbox = QtWidgets.QGroupBox(
            maximumWidth=310)
        saving_measurements_groupbox_layout = QtWidgets.QGridLayout()
        self.saving_measurements_groupbox.setLayout(
            saving_measurements_groupbox_layout)
        
        for i in range(self.GYRO_NUMBER):
            self.append_gyro_widgets()
            saving_measurements_groupbox_layout.addWidget(
                self.saving_measurements_groupbox_list[i], i, 0, 1, 1)
# ------ Output logs and data from file ---------------------------------------

        self.text_output_groupbox = QtWidgets.QGroupBox(
            'Содержимое файла', maximumWidth=350, minimumWidth=215)
        self.text_output_groupbox_layout = QtWidgets.QGridLayout()
        self.text_output_groupbox.setLayout(self.text_output_groupbox_layout)

        self.table_widget = PyQt_CustomWidgets.CustomTableWidget()
        self.text_output_groupbox_layout.addWidget(self.table_widget)

# ------ Logger ---------------------------------------------------------------
        """Logs widget"""
        self.logs_groupbox = QtWidgets.QGroupBox(
            'Лог', maximumWidth=350)  # Logs
        self.logs_groupbox_layout = QtWidgets.QVBoxLayout()
        self.logs_groupbox.setLayout(self.logs_groupbox_layout)

        self.logs_groupbox_layout.addWidget(self.log_text_box.widget)

        self.logs_clear_button = QtWidgets.QPushButton('Очистить')  # Clear logs
        self.logs_groupbox_layout.addWidget(self.logs_clear_button)

        self.start_button = QtWidgets.QPushButton(
            'Старт', objectName="start_button")  # START
        self.stop_button = QtWidgets.QPushButton(
            'Стоп', enabled=False, objectName="stop_button")  # STOP

# ------ Others ------------------------------------------------------------
        self.plot_groupbox = QtWidgets.QGroupBox(minimumWidth=395)
        self.plot_groupbox_layout = QtWidgets.QGridLayout()
        self.plot_groupbox.setLayout(self.plot_groupbox_layout)

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
            self.plot_groupbox_layout.addWidget(self.check_box_list[i],
                                            0, 5 * i, 1, 4)

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
        self.main_grid_layout.addWidget(self.start_button,
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
        self.start_button.clicked.connect(self.measurement_start)
        self.stop_button.clicked.connect(self.stop)
        self.choose_file.clicked.connect(self.choose_and_load_file)
        self.cycle_num_widget.valueChanged.connect(self.cycle_num_value_change)
        self.cycle_num_widget.valueChanged.connect(self.progress_bar_set_max)
        # self.choose_path_button.clicked.connect(
        #     self.choose_result_saving_path)
        self.filename_and_path_widget.textChanged.connect(
            self.filename_and_path_text_change)
        self.logs_clear_button.clicked.connect(
            lambda: self.log_text_box.widget.clear())
        self.edit_file_button.clicked.connect(
            lambda: os.startfile(self.filename_and_path_widget.toPlainText()))
        for i in range(self.GYRO_NUMBER):
            self.choose_path_button_list[i].clicked.connect(
                self.choose_result_saving_path)
            self.saving_result_folder_label_list[i].textChanged.connect(
                self.folder_chage_event)
        for i in range(self.GYRO_NUMBER + 1):
            self.check_box_list[i].stateChanged.connect(
                self.custom_tab_plot_widget.change_curve_visibility)
        
        self.show()
        # print(self.custom_tab_plot_widget.amp_plot_list[0].getPlotItem().curves[0].objectName())
        # print(self.custom_tab_plot_widget.amp_curves[0].objectName())
        # print(self.custom_tab_plot_widget.amp_plot_list[0].objectName())
        # print(self.palette().window().color().name())
        # print(sys.getsizeof((self.GYRO_NUMBER)))
# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------
#

    def __contextMenu(self):
        # self._normalMenu = self.combo_box_name.layout().createStandardContextMenu()
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
        # action.triggered.connect(self.get_avaliable_com)        
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

    # def eventFilter(self, obj, event):
    #     if event.type() == QtCore.QEvent.ContextMenu:
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
    #         menu.exec_(event.globalPos())
    #         return True
    #     return False
################################################################################################
#
# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------
#
################################################################################################
    def save_results(self):
        if self.processing_thr.isRunning():
            self.logger.warning("Thread still work with previous data")
            self.logger.info(f"data_recieved_event {self.processing_thr.data_recieved_event.is_set()}")
            self.processing_thr.data_recieved_event.set()
            return
        # Check filenames
        for i in range(self.GYRO_NUMBER):  # !
            self.make_filename(i)  # !
            self.processing_thr.start()

    @QtCore.pyqtSlot(bool)
    def run_thread_for_file_processing(self, _):  ################### изменить для трех, изменить имена
        self.logger.info(
            f"files: {self.custom_tab_plot_widget.selected_files_to_fft}")
        if self.processing_thr.isRunning():
            self.logger.warning("Thread still work with previous data")
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
            self.processing_thr.flag_all = True

    @QtCore.pyqtSlot()
    def measurement_start(self):
        self.package_num = 0  # не создавать эту переменную, а брать из виджета значения
        self.progress_value = 0  # не создавать эту переменную
        self.progress_bar.setValue(0)
        self.count = 0
        self.current_cylce = 1
        self.flag_sent = False

        if self.processing_thr.isRunning():
            self.logger.warning("Thread still work with previous data")
            return
        # Check COM port
        self.logger.info(F"\nPORT: {self.com_port_name_combobox.currentText()}\n")
        if not len(self.com_port_name_combobox.currentText()):
            self.get_avaliable_com()
            self.logger.info(
                f"PORT: {(self.com_port_name_combobox.currentText())}\n")
            QtWidgets.QMessageBox.critical(
                None, "Error", "Can't find COM port")
            return
        self.serial_port.setBaudRate(
            int(self.com_boderate_combo_box.currentText()))
        self.serial_port.setPortName(
            self.com_port_name_combobox.currentText())
        self.logger.info("Set COM settings")

        # Check measurement file
        if not self.table_widget.total_time:
            self.cycle_num_value_change()
            if not self.choose_and_load_file():
                self.logger.info("No data from file")
                return
        self.logger.info("Data from file was loaded")

        # Open COM
        if not self.serial_port.open(QtCore.QIODevice.OpenModeFlag.ReadWrite):
            self.logger.warning(
                f"Can't open {self.com_port_name_combobox.currentText()}")
            return

        # # Check filenames
        # for i in range(self.GYRO_NUMBER):  # !
        #     self.make_filename(i)  # !

        self.custom_tab_plot_widget.clear_plots()
        self.custom_tab_plot_widget.append_fft_plot_tab()

        self.cycle_num_value_change()
        self.progress_bar_set_max()
        self.set_avaliable_butttons(flag_running=True)  # disable widgets

        self.logger.info(f"{self.com_port_name_combobox.currentText()} open")
        self.logger.info(f"self.cycle_num = {self.total_cycle_num}")
        self.logger.warning("Start")

        self.serial_port.clear()
        # self.timer_recieve.setInterval(0)
        # self.timer_sent_com.setInterval(0)
        # Start timers
        self.start_time = time()
        self.timer_event_sent_com()
        self.timer_sent_com.start()
        self.timer_recieve.start()
        self.fs = int(self.fs_combo_box.currentText())
        self.points_shown = self.PLOT_TIME_INTERVAL_SEC * self.fs
        # Copy variables to another classes and start thread
        self.custom_tab_plot_widget.fs = self.fs
        self.processing_thr.fs = self.fs
        self.processing_thr.flag_measurement_start = True
        self.processing_thr.total_time = self.table_widget.total_time
        self.processing_thr.num_measurement_rows = self.table_widget.rowCount()
        self.processing_thr.total_cycle_num = self.total_cycle_num
        self.processing_thr.start()

# ------ Timer Recieve --------------------------------------------------------
    @QtCore.pyqtSlot()
    def timer_read_event(self):
        """Read data from COM port.
        Generate warning if avaliable less than 14 bytes"""
        bytes_num = self.serial_port.bytesAvailable()
        if bytes_num <= 14:
            self.logger.warning(
                f"No data from {self.com_port_name_combobox.currentText()}")
            return
        if self.serial_port.receivers(self.serial_port.readyRead):
            self.serial_port.readyRead.disconnect(self.read_serial)
        self.serial_port.readyRead.connect(self.read_serial)
        # self.read_serial()

    def read_serial(self):
        self.serial_port.readyRead.disconnect(self.read_serial)
        bytes_num = self.serial_port.bytesAvailable()
        # if bytes_num <= 14:
        #     self.logger.warning(
        #         f"No data from {self.com_port_name_combobox.currentText()}")
        #     return
        # if self.processing_thr.flag_recieve: 
        if self.processing_thr.data_recieved_event.is_set():
            self.logger.warning("Thread still work with previous data")
            return

        self.logger.info(
            f"ready to read, bytes num = {bytes_num}")  # +
        self.copy_variables_to_thread()
        self.logger.info(f"command thr to start, count = {self.count}")

    def copy_variables_to_thread(self):
        self.processing_thr.rx = self.serial_port.readAll().data()
        # self.processing_thr.flag_recieve = True
        self.processing_thr.data_recieved_event.set()
        self.processing_thr.count_fft_frame = self.count
        self.processing_thr.flag_sent = self.flag_sent

# ------- Timer Sent ----------------------------------------------------------

    @QtCore.pyqtSlot()
    def timer_event_sent_com(self):
        """
        Sent command with frequency and amplitude or stop vibration
        """
        if self.flag_sent:
            self.logger.info(
                f"count = {self.count}")
            if self.count >= self.table_widget.rowCount():
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
        self.serial_port.write(bytes([0, 0, 0, 0, 0, 0, 0, 0]))
        self.timer_sent_com.setInterval(self.PAUSE_INTERVAL_MS)

    def sent_vibro_command(self):
        self.table_widget.selectRow(self.count)
        F = int.to_bytes(self.table_widget.get_current_F(),
                         length=2, byteorder='little', signed=False)
        A = int.to_bytes(self.table_widget.get_current_A(),
                         length=2, byteorder='little', signed=False)
        self.serial_port.write(
            bytes([77, 0, F[0], F[1], A[0], A[1], 0, 0]))

        self.timer_sent_com.setInterval(self.table_widget.get_current_T())
        self.count += 1
        self.logger.info("- Command was sent -")

# ----- End cycle, stop, etc --------------------------------------------------
    def new_cycle_event(self):
        self.logger.warning(
            f"End of cycle {self.current_cylce} of {self.total_cycle_num}")
        self.current_cylce += 1
        self.count = 0
        self.custom_tab_plot_widget.append_fft_plot_tab()
        self.processing_thr.new_cycle()

    @QtCore.pyqtSlot()
    def stop(self):
        self.set_avaliable_butttons(False)
        if self.timer_sent_com.isActive():
            self.timer_sent_com.stop()
        if self.timer_recieve.isActive():
            self.timer_recieve.stop()
        self.logger.info(
            f"time = {self.progress_value}, " +
            f"total time = {self.progress_bar.maximum()}")

        if self.serial_port.isOpen():
            self.serial_port.write(bytes([0, 0, 0, 0, 0, 0, 0, 0]))
            self.logger.info("COM close? " +
                             str(self.serial_port.waitForBytesWritten(250)))
            self.serial_port.close()
            self.logger.warning("End of measurements\n")
            if self.progress_value > 2:
                check = int(self.package_num / self.progress_value)
                if not (0.95 * self.fs < check < 1.05 * self.fs):
                    QtWidgets.QMessageBox.critical(
                        None, "Warning",
                        f"You set fs = {self.fs} Hz," +
                        f"but in fact it's close to {check} Hz")
            # Check filenames
            for i in range(self.GYRO_NUMBER):
                self.make_filename(i)
        self.processing_thr.flag_measurement_start = False
        self.processing_thr.data_recieved_event.set()

###############################################################################
# ----- plotting --------------------------------------------------------------

    @QtCore.pyqtSlot(int)
    def plot_time_graph(self, pack_num_signal):
        # package_num можно брать из массива time_data
        self.package_num = pack_num_signal
        self.package_num_label.setText(str(self.package_num))

        self.progress_value = time() - self.start_time
        self.progress_bar.setValue(int(round(self.progress_value)))
        self.logger.info(f"Progress: {self.progress_value}")

        start_i = (self.package_num - self.points_shown
                   if self.package_num > self.points_shown else 0)
        self.logger.info(f"thr_stop, count = {self.count}\n" +
                         f"package_num = {self.package_num} ")
        self.custom_tab_plot_widget.plot_time_graph(
            self.processing_thr.time_data[start_i:pack_num_signal, 0] / self.fs,
            self.processing_thr.time_data[start_i:pack_num_signal, 2] / 1000,
            [self.processing_thr.time_data[start_i:pack_num_signal, 1 + 4*i] /
             self.processing_thr.k_amp[i] / 1000
            for i in range(self.GYRO_NUMBER)])

    @QtCore.pyqtSlot(bool)
    def plot_fft(self, _):
        """Adds points to frequency graphs"""
        self.custom_tab_plot_widget.set_fft_data(
            self.processing_thr.fft_data_current_cycle,
            self.processing_thr.bourder)
        self.logger.info("end plot_fft")

    # @QtCore.pyqtSlot(str)
    @QtCore.pyqtSlot(list)
    def plot_fft_final(self, name):
        self.logger.info(f"Final median plot {name}")
        self.custom_tab_plot_widget.set_fft_median_data(
            self.processing_thr.all_fft_data[:, -4:],
            self.processing_thr.special_points, name)

    @QtCore.pyqtSlot()
    def save_image(self):
        self.logger.info("Save image")
        for i in range(self.GYRO_NUMBER):
            if (len(self.processing_thr.filename_new[i])
                and self.check_box_list[i].isChecked()):
                if self.processing_thr.flag_measurement_start:  # !
                    self.make_filename(i)  # !
                self.custom_tab_plot_widget.save_plot_image(
                    self.processing_thr.filename_new[i])
        self.logger.info("Saving complite")

# ------ Widgets events -------------------------------------------------------

    def cycle_num_value_change(self):
        # if not self.timer_recieve.isActive():  # is this required?
        self.total_cycle_num = self.cycle_num_widget.value()

    def progress_bar_set_max(self):
        if self.table_widget.total_time and not self.timer_recieve.isActive():  # is this required?
            self.total_cycle_num = self.cycle_num_widget.value()
            self.progress_bar.setMaximum(int(
                self.total_cycle_num * 
                (self.table_widget.total_time +
                 (self.table_widget.rowCount() + 1) * self.PAUSE_INTERVAL_MS / 1000)))
            # self.progress_bar.setValue(0)

    def set_avaliable_butttons(self, flag_running: bool):
        """Enable or disable widgets"""
        self.cycle_num_widget.setDisabled(flag_running)
        self.edit_file_button.setDisabled(flag_running)
        # self.save_image_button.setDisabled(flag_running)
        self.start_button.setDisabled(flag_running)
        self.stop_button.setDisabled(not flag_running)
        self.choose_file.setDisabled(flag_running)
        # for groupbox in self.saving_measurements_groupbox_list:
            # groupbox.setDisabled(flag_running)
        # saving_measurements_groupbox_list можно редактировать,
        # т.к. путь отправляется в поток перед окончанием цикла

    def get_avaliable_com(self):
        """Append avaliable com ports to combo box widget"""
        port_name_list = [ports.portName() 
               for ports in QSerialPortInfo.availablePorts()]
        # port_name_list = ['com2', 'com11', 'com3']
        if len(port_name_list):
            # print(port_name_list.sort(key=self.natural_keys))
            # self.logger.info(len(port_name_list))
            # self.logger.info(list.sort(port_name_list))
            # self.logger.info(sorted(port_name_list, key=self.natural_keys))
            # self.com_port_name_combobox.addItems(port_name_list.sort())
            for _ in range(self.com_port_name_combobox.count()):
                self.com_port_name_combobox.removeItem()
            self.com_port_name_combobox.addItems(
                sorted(port_name_list, key=self.natural_keys))
        self.logger.warning('Update avaliable COM port list')

    @staticmethod
    def natural_keys(text):
        def atoi(text):
            return int(text) if text.isdigit() else text
        return [atoi(c) for c in re.split(r'(\d+)', text)]
# ------ file name and data from file -----------------------------------------

    def make_filename(self, i: int):
        # подправить if
        if not len(self.file_name_line_edit_list[i].text()) or not len(self.folder_name_list[i]): # or not len():
            self.processing_thr.filename_new[i] = ''
            return
        if not os.path.isdir(self.folder_name_list[i]):
            self.processing_thr.filename_new[i] = ''
            self.logger.warning(f"Path {self.folder_name_list[i]} doesn't exist!")
            return
        if self.create_folder_checkbox_list[i].isChecked():
            folder = re.split("_", self.file_name_line_edit_list[i].text())[0]
            # if not os.path.isdir(folder):  # ? будет ли это работать, надо ведь путь добавить
            if not os.path.isdir(self.folder_name_list[i] + folder):
                os.mkdir(self.folder_name_list[i] + folder)
                # os.mkdir(folder)
            folder += '/'
        else:
            folder = ''
        self.processing_thr.filename_new[i] = \
            self.folder_name_list[i] + folder + self.file_name_line_edit_list[i].text()
        self.logger.info(f"name {self.processing_thr.filename_new[i]}")

    # def directory_changed(self, path):
    #     self.logger.info(f'Directory Changed: {path}')
    #     print(f'Directory Changed: {path}')
    def folder_chage_event(self):
        for i in range(len(self.saving_result_folder_label_list)):
            if self.sender() == self.saving_result_folder_label_list[i]:
                break
        else:
            return
        self.folder_name_list[i] = self.saving_result_folder_label_list[i].toPlainText()   
        # print(i)

    @QtCore.pyqtSlot()
    def choose_result_saving_path(self):
        for i in range(len(self.choose_path_button_list)):
            if self.sender() == self.choose_path_button_list[i]:
                break
        else:
            return
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Выбрать папку", ".")
        if not len(folder):
            return
        self.folder_name_list[i] = folder + '/'
        self.saving_result_folder_label_list[i].setText(
            self.folder_name_list[i])

    @QtCore.pyqtSlot()
    def filename_and_path_text_change(self):
        if not os.path.exists(self.filename_and_path_widget.toPlainText()):  # text
            self.logger.warning("The file path does not exist!")
            # доработать, чтобы человек не получал кучу таких уведомлений
            return False
        if len(self.filename_and_path_widget.toPlainText()):
            self.file_watcher.removePath(self.filename_path_watcher)
        self.filename_path_watcher = self.filename_and_path_widget.toPlainText()  # os.path.basename(filename)
        self.file_watcher.addPath(self.filename_path_watcher)
        return self.get_data_from_file(self.filename_path_watcher)

    @QtCore.pyqtSlot(str)
    def check_filename_and_get_data(self, path: str):
        """Вызывается при изменении файла"""
        self.logger.info(
            f'File Changed, {path},' +
            f'thr run? {self.processing_thr.flag_measurement_start}')
        if not self.processing_thr.flag_measurement_start and os.path.exists(path):
            self.get_data_from_file(path)

    @QtCore.pyqtSlot()
    def choose_and_load_file(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Выберите методику измерений",
            ".", "Text Files(*.txt)")
        if not filename:
            return False
        self.logger.info(
            f"filename: {filename}, basebame: {os.path.basename(filename)}")
        if len(self.filename_path_watcher):
            self.file_watcher.removePath(self.filename_path_watcher)
        self.file_watcher.addPath(filename)
        self.filename_and_path_widget.setText(filename)
        self.filename_path_watcher = filename  # os.path.basename(filename)
        return self.get_data_from_file(self.filename_path_watcher)

    def get_data_from_file(self, filename_path_watcher: str):
        """Get data from file and put it in table"""
        with open(filename_path_watcher, 'r') as file:
            self.table_widget.set_table(file)
            self.progress_bar_set_max()
        return self.table_widget.total_time > 0

    # @QtCore.pyqtSlot()
    # def open_file(self):
    #     os.startfile(self.filename_and_path_widget.toPlainText())

    @QtCore.pyqtSlot()
    def closeEvent(self, _):
        """
        Sending stop command to the vibrostand and saving user settings
        """
        self.stop()
        self.settings.setValue("autosave",
                               int(self.settings_autosave_action.isChecked()))
        if self.settings_autosave_action.isChecked():
            self.save_all_settings()
        self.logger.warning("Saving the settings and exit")

# ------ settings --------------------------------------------------------------------

    def save_all_settings(self):
        self.com_boderate_combo_box.save_all()
        self.fs_combo_box.save_all()
        self.com_port_name_combobox.save_current_text()
        self.settings.setValue("cycle_num",
                                self.cycle_num_widget.value())
        self.settings.setValue("filename",
                                self.filename_and_path_widget.toPlainText())
        self.settings.setValue("current_folders", self.folder_name_list)
                            #    self.saving_result_folder_label.toPlainText())  # text
        # self.settings.setValue('dict', self.custom_tab_plot_widget.projects_dict)
        self.settings.setValue(
            'dict', self.custom_tab_plot_widget.projects_combo_box.projects_dict)
        self.settings.setValue('create_folder_flag',
                               [int(checkbox.isChecked()) 
                                for checkbox in self.create_folder_checkbox_list])

    def load_previous_settings(self, settings: QtCore.QSettings):
        if self.settings.contains("autosave"):
            self.settings_autosave_action.setChecked(
                int(self.settings.value("autosave")))
        if settings.contains("cycle_num"):
            self.cycle_num_widget.setValue(
                settings.value("cycle_num"))
        if settings.contains("filename"):
            name = settings.value("filename")
            if os.path.exists(name):
                self.filename_and_path_widget.setText(name)
                if self.get_data_from_file(name):
                    self.logger.warning("The previous file is loaded")
                self.filename_path_watcher = self.filename_and_path_widget.toPlainText()  # os.path.basename(filename)
                self.file_watcher.addPath(self.filename_path_watcher)
        if settings.contains("create_folder_flag"):
            # for i in range(len(settings.value("create_folder_flag"))):
            for i in range(min(len(settings.value("create_folder_flag")),
                               len(self.create_folder_checkbox_list))):
                self.create_folder_checkbox_list[i].setChecked(
                    int(settings.value("create_folder_flag")[i]))
        if settings.contains("current_folders"):
            # for folder in settings.value("current_folders"):
            for i in range(min(len(settings.value("current_folders")),
                               len(self.saving_result_folder_label_list))):
                if os.path.isdir(settings.value("current_folders")[i]) or len(settings.value("current_folders")[i]) == 0:
                    self.saving_result_folder_label_list[i].setText(
                        settings.value("current_folders")[i])
                    self.folder_name_list[i] = settings.value("current_folders")[i]
        if self.settings.contains('dict'):
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


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
#
###############################################################################
#
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class AppWindowTest(AppWindow):
    def __init__(self, parent=None):
        AppWindow.__init__(self, parent)

    def measurement_start(self):
        # for i in range(self.GYRO_NUMBER):
            # self.make_filename(i)
        self.progress_bar.setValue(0)
        self.progress_value = 0
        self.count = 0
        self.current_cylce = 1
        self.package_num = 0  # можно не создавать эту переменную, а брать из виджета значения
        self.flag_sent = False
        if not self.table_widget.total_time:
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
        filename = 'прежнее/6884_139_6.2_4.txt'
        self.time_data_test = np.array(
            read_csv(filename, delimiter='\t', 
                     dtype=np.int32, header=None,  #,
                     keep_default_na=False, na_filter=False,
                     index_col=False, usecols=[1, 2, 3, 4], 
                     skiprows=2000))
        # from PyQt_Functions import get_fft_data  # ! показательно !
        # print(get_fft_data(self.time_data_test[4_400:9_400, 0], self.time_data_test[4_400:9_400, 1], 1000))
        # print(get_fft_data(self.time_data_test[6_400:8_400, 0], self.time_data_test[6_400:8_400, 1], 1000))
        # print(get_fft_data(self.time_data_test[2_400:11_400, 0], self.time_data_test[2_400:11_400, 1], 1000))
        # print(get_fft_data(self.time_data_test[4_400:5_400, 0], self.time_data_test[4_400:5_400, 1], 1000))
        # print(get_fft_data(self.time_data_test[4_900:5_900, 0], self.time_data_test[4_900:5_900, 1], 1000))
        # print(get_fft_data(self.time_data_test[4_400:5_900, 0], self.time_data_test[4_400:5_900, 1], 1000))
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
        self.points_shown = self.PLOT_TIME_INTERVAL_SEC * self.fs
        self.custom_tab_plot_widget.fs = self.fs
        self.processing_thr.fs = self.fs
        self.processing_thr.flag_measurement_start = True
        self.processing_thr.total_time = self.table_widget.total_time * 3 # !!!
        self.processing_thr.num_measurement_rows = self.table_widget.rowCount()
        self.processing_thr.total_cycle_num = self.total_cycle_num
        self.processing_thr.start()

    @QtCore.pyqtSlot()
    def timer_read_event(self):
        self.read_serial()

    def read_serial(self):
        self.progress_value = time() - self.start_time
        self.progress_bar.setValue(int(round(self.progress_value)))
        data: bytearray = b""
        for i in range(200):
            data += int.to_bytes(0x72, length=1, byteorder='big')
            for j in range(4):
                data += int.to_bytes(int(self.time_data_test[self.package_num + i, j]),
                                     length=3, byteorder='big', signed=True)
            data += int.to_bytes(0x27, length=1, byteorder='big')
        self.processing_thr.rx = data
        # self.processing_thr.flag_recieve = True
        self.processing_thr.data_recieved_event.set()  ###########################################################
        self.processing_thr.count_fft_frame = self.count
        self.processing_thr.flag_sent = self.flag_sent
        self.logger.info(f"thr_start, count = {self.count}")

    @QtCore.pyqtSlot()
    def timer_event_sent_com(self):
        if self.flag_sent:
            self.logger.info(
                f"count = {self.count}, num_rows={self.table_widget.rowCount()}")
            if self.count >= self.table_widget.rowCount():
                if self.current_cylce < self.total_cycle_num:
                    self.new_cycle_event()
                else:
                    self.stop()
                return
        if self.flag_sent:
            self.sent_vibro_command()
        else:
            self.timer_sent_com.setInterval(self.PAUSE_INTERVAL_MS)
        self.flag_sent = not self.flag_sent
        self.logger.info("---end_sent_command")

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
        self.logger.info(
            f"time = {self.progress_value}, " +
            f"total time = {self.progress_bar.maximum()}")

        if self.processing_thr.isRunning():
            self.logger.warning("End of measurements\n")
            if self.progress_value > 5:
                check = int(self.package_num / self.progress_value)
                if not (0.95 * self.fs < check < 1.05 * self.fs):
                    QtWidgets.QMessageBox.critical(
                        None, "Warning",
                        f"You set fs = {self.fs} Hz," +
                        f"but in fact it's close to {check} Hz")
                            # Check filenames
            for i in range(self.GYRO_NUMBER):
                self.make_filename(i)
            # print(self.processing_thr.data_recieved_event.is_set())
            # print(self.processing_thr.flag_measurement_start)
        self.processing_thr.flag_measurement_start = False
        self.processing_thr.data_recieved_event.set()


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
###############################################################################
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    test = True
    # test = False
    splash = QtWidgets.QSplashScreen(QtGui.QPixmap(get_res_path('res/G.png')))
    # splash = QtWidgets.QSplashScreen()
    # splash.showMessage('<h1 style="color:white;">\n\n\n.\nЖдите...</h1>', 
                    #    QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter, QtCore.Qt.white)  
                    #    QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter, QtCore.Qt.black)
    splash.show()
    # splash.setWindowOpacity(0.0)
    app.processEvents()
    # QtCore.QThread.msleep(2000)   # 

    # demo = QtWidgets.MainWindow()
    # demo.show()
    if test:
        window = AppWindowTest()
    else:
        window = AppWindow()
    splash.finish(window)
    sys.exit(app.exec())