import logging
import sys
import os
import numpy as np
import win32com.client as win32
import pyqtgraph as pg
import pyqtgraph.exporters
from PyQt5 import QtWidgets, QtCore, QtGui
# from openpyxl import load_workbook  # лучше использовать Pandas, наверняка работает быстрее
# from typing import overload
# from PyQt_Functions import get_icon_by_name, get_res_path
import PyQt_ProjectsComboBox
from PyQt_Functions import check_name_simple, get_icon_by_name


class CustomViewBox(pg.ViewBox):
    def __init__(self, *args, **kwds):
        # kwds['enableMenu'] = True
        # kwds['enableMenu'] = False
        pg.ViewBox.__init__(self, *args, **kwds)
        # self.setMouseMode(self.RectMode)

    def mouseDoubleClickEvent(self, e):
        if (e.buttons() & QtCore.Qt.LeftButton):
            self.autoRange()
            self.enableAutoRange()  # так действительно возвращает в режим автоматического масштабирования

    #  reimplement right-click to zoom out
    # def mouseClickEvent(self, ev):
    #     if ev.button() == QtCore.Qt.MouseButton.RightButton:
    #         # self.autoRange()
    #         self.enableAutoRange()  # так действительно возвращает в режим автоматического масштабирования

    # #  reimplement mouseDragEvent to disable continuous axis zoom
    # def mouseDragEvent(self, ev, axis=None):
    #     if axis is not None and ev.button() == QtCore.Qt.MouseButton.RightButton:
    #         ev.ignore()
    #     else:
    #         pg.ViewBox.mouseDragEvent(self, ev, axis=axis)


class CustomTabWidget(QtWidgets.QTabWidget):
    warning_signal = QtCore.pyqtSignal(str)
    info_signal = QtCore.pyqtSignal(str)
    get_filename_signal = QtCore.pyqtSignal(bool)

    def __init__(self, GYRO_NUMBER, fs=1000, logger_name='', parent=None):
        # QtWidgets.QTabWidget.__init__(self)
        super(CustomTabWidget, self).__init__(parent)
        self.GYRO_NUMBER = GYRO_NUMBER
        self.visibility_flags_list = [True] * (self.GYRO_NUMBER + 1)
        self.LABEL_STYLE = {'color': '#FFF', 'font-size': '16px'}
        self.ICON_COLOR_LIST = ['red', 'green', 'blue']
        self.COLOR_LIST = ['r', 'g', '#006bf7']
        self.COLOR_LIST2 = ['#FF0000', '#00FF00', '#006bf7'] #'' blue
        self.fs = fs
        self.selected_files_to_fft = []
        self.pt = 12
        # self.settings = QtCore.QSettings("settings")
        self.logger = logging.getLogger(logger_name)
        pg.setConfigOption('background', '#151515')
        pg.setConfigOption('foreground', '#BBBBBB') 
        pg.setConfigOption('weaveDebug', True) # вроде может ускорить
        pg.setConfigOption('crashWarning', True)
        pg.setConfigOption('mouseRateLimit', 24)
        pg.setConfigOption('useOpenGL', False)
        # STYLE_SHEETS_FILENAME = 'res\StyleSheets.css'
        # from PyQt_Functions import get_res_path 
        # with open(get_res_path(STYLE_SHEETS_FILENAME),
        #           "r") as style_sheets_css_file:
        #     self.setStyleSheet(style_sheets_css_file.read())

# ------ time plot ------------------------------------------------------------
        self.plot_check_box_list: list[QtWidgets.QCheckBox] = []
        self.plot_check_box_list.append(
            QtWidgets.QCheckBox("encoder",
                                objectName="0", checked=True,
                                icon=get_icon_by_name('white')))
        for i in range(self.GYRO_NUMBER):
            self.plot_check_box_list.append(
                QtWidgets.QCheckBox(
                    f"gyro {i + 1}", objectName=f"{i + 1}", checked=True,
                    icon=get_icon_by_name(self.ICON_COLOR_LIST[i])))
        for i in range(self.GYRO_NUMBER + 1):
            self.plot_check_box_list[i].stateChanged.connect(
                self.change_curve_visibility)
        self.logger.debug("1")
        self.time_plot_item = pg.PlotItem(viewBox=CustomViewBox())
        self.logger.debug("1.25")
        self.time_plot = pg.PlotWidget(plotItem=self.time_plot_item)
        self.logger.debug("1.5")
        self.time_plot.setLimits(xMin=-0.01)
        # self.time_plot_item.setTitle('Угловая скорость', size=f'{self.pt}pt')  # Velosity Graph
        self.time_plot_item.showGrid(x=True, y=True)
        self.time_plot_item.addLegend(offset=(-1, 1), labelTextSize=f'{self.pt}pt',
                                      labelTextColor=pg.mkColor('w'))
        self.time_plot_item.setLabel('left', 'Velosity',
                                     units='\u00b0/second', **self.LABEL_STYLE)
        self.time_plot_item.setLabel('bottom', 'Time',
                                     units='seconds', **self.LABEL_STYLE)

        self.time_curves = [self.time_plot_item.plot(pen='w', name="encoder")]
        for i in range(self.GYRO_NUMBER):
            self.time_curves.append(self.time_plot_item.plot(
                pen=self.COLOR_LIST[i], name=f"gyro {i + 1}", skipFiniteCheck=True))

        self.region = pg.LinearRegionItem([0, 0], movable=False)
        self.time_plot_item.addItem(self.region)
        self.logger.debug("2")

        # self.y1 = [108, 116, 131, 147, 148, 146, 141, 141, 139, 130, 123, 120, 115, 113, 114, 122, 120, 131, 147, 165,
        # 188, 198, 227, 224, 246, 384, 399, 423, 462, 521, 542, 565, 636, 685, 726, 830, 960, 1070, 1060, 1173, 1409, 1584, 2270, 4619, 4876, 5524]
        # self.x1 = [1, 5, 10, 15, 20, 25, 33, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130,
        #            135, 140, 150, 156, 162, 170, 180, 190, 200, 210, 220, 230, 240, 260, 270, 290, 310, 320, 325]
        # self.x1 = np.array([1, 5, 10, 15, 20, 25, 33, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 102, 105,
        #                     107, 110, 115, 118, 120, 122, 125, 130, 135, 140, 150, 156, 162, 170, 180, 190, 200, 205, 210,
        #                     215, 220, 225, 230, 235, 240, 243, 247, 250, 255, 260, 265, 270, 275, 280, 285, 290, 295, 300, 305, 310, 315])
        # self.y1 =np.array(
        #     [94, 99, 105, 114, 112, 113, 122, 127, 137, 160, 169, 205, 221, 243, 292, 306, 339, 392, 419, 554, 861, 913, 1079, 1276, 595, 645, 659, 666, 781, 810, 863, 948, 1024, 1103, 1227, 1329, 1319, 1362, 1468, 1791, 1921, 1959, 2641, 2477, 3384, 3484, 3254, 4482, 3888, 3931, 2795, 3021, 3246, 3046, 3147, 3505, 3424, 3430, 4049, 4157, 4385, 3980, 5340, 4897]
        #     )/100
        # self.x1 = np.arange(1000, 0.1, -0.1)
        # self.y1 = np.arange(0.1, 1000, 0.1)
        # from time import time
        # t = time()
        # for i in range(1000):
        # self.time_curves[0].setData(x=self.x1, y=self.y1)
        # print(time() - t)
# ------ Tab widget -----------------------------------------------------------

        page = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(spacing=0)
        layout.setContentsMargins(5, 10, 5, 5)

        layout.addWidget(self.time_plot)
        self.spectrum_button = QtWidgets.QPushButton("От времени")  # Time plot
        layout.addWidget(self.spectrum_button)
        self.spectrum_button.clicked.connect(self.switch_plot_x_axis)
        page.setLayout(layout)
        self.addTab(page, "\u03C9(t)")  # &Time plot От времени
        self.tab_widget_page_list: list[QtWidgets.QWidget] = []
        self.phase_curves: list[pg.PlotCurveItem] = []
        self.amp_curves: list[pg.PlotCurveItem] = []
        self.phase_plot_list: list[pg.PlotWidget] = []
        self.amp_plot_list: list[pg.PlotWidget] = []

        self.bytes_widget = QtWidgets.QTextEdit(visible=False)
        layout.addWidget(self.bytes_widget)  # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

# -----------------------------------------------------------------------------
        self.groupbox = QtWidgets.QGroupBox(
            '', maximumWidth=180, minimumWidth=120)
        median_plot_groupbox_layout = QtWidgets.QGridLayout(spacing=6)
        median_plot_groupbox_layout.setContentsMargins(3, 5, 3, 5)
        # self.median_plot_groupbox_layout.setRowStretch(4, 0)
        # self.median_plot_groupbox_layout.setSpacing(0)
        self.groupbox.setLayout(median_plot_groupbox_layout)

        self.groupbox_list: list[QtWidgets.QGroupBox] = []
        self.max_amp_line_edit_list: list[QtWidgets.QLineEdit] = []
        self.rez_freq_line_edit_list: list[QtWidgets.QLineEdit] = []
        self.sensor_name_line_edit_list: list[QtWidgets.QLineEdit] = []

        for i in range(self.GYRO_NUMBER):
            self.append_gyro_groupbox()
            median_plot_groupbox_layout.addWidget(
                self.groupbox_list[-1], 2 + i, 0, 1, 3)
        self.logger.debug("3")

        self.projects_combo_box = PyQt_ProjectsComboBox.ProjectsComboBox(self)
        median_plot_groupbox_layout.addWidget(
            self.projects_combo_box, 0, 0, 1, 3)

        self.ok_btn = QtWidgets.QPushButton("Запись в Excel")
        median_plot_groupbox_layout.addWidget(self.ok_btn, 1, 0, 1, 3)
        self.ok_btn.clicked.connect(self.write_xlsx)

        self.get_filenames_btn = QtWidgets.QPushButton("АФЧХ для файла")
        # self.get_filenames_btn.setContextMenuPolicy(
            # QtCore.Qt.CustomContextMenu)
        # self.get_filenames_btn.customContextMenuRequested.connect(
            # self.__contextMenu)
        median_plot_groupbox_layout.addWidget(
            self.get_filenames_btn, 7, 0, 1, 3)
        self.get_filenames_btn.clicked.connect(self.get_filenames_to_fft)

        self.plot_fft_median()

        # !!!
        # self.selected_curve = 0
        # self.groupbox_list[self.selected_curve].setChecked(True)
        # for j in range(1, len(self.groupbox_list)):
        #     self.groupbox_list[j].setChecked(False)
        # for i in range(2):
        #     self.infinite_x_line_list[i].setPen(
        #         pg.mkPen(self.COLOR_LIST[self.selected_curve]))
        # !!!
        # self.groupbox_clicked(self.groupbox_list[0])
        # print(self.palette().window().color().name())
        # pg.setConfigOption('background', self.palette().window().color().name())
        self.start_folder = "."  # !
        # self.log_mode()
        self.excel_com_object = None
        self.plot_index = 0
# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------
#
        
    def __contextMenu(self):
        # self._normalMenu = self.combo_box_name.layout().createStandardContextMenu()
        # self._normalMenu = self.com_port_name_combobox.lineEdit().createStandardContextMenu()
        self._normalMenu = QtWidgets.QMenu()
        # self._normalMenu = self.combo_box_name.visibleRegion().createStandardContextMenu()
        # self._normalMenu = self.combo_box_name.layoutDirection().createStandardContextMenu()
        self._addCustomMenuItems(self._normalMenu)
        self._normalMenu.exec_(QtGui.QCursor.pos())

    def _addCustomMenuItems(self, menu: QtWidgets.QMenu):
        # menu.addSeparator()
        # action = QtWidgets.QAction("Обновить", self, shortcut="Ctrl+U")
        # action.setShortcut("Ctrl+U")
        # action.triggered.connect(self.get_avaliable_com)        
        # menu.addAction(action)
        menu.addAction('Посмотреть без сохранения', self.get_filenames_to_fft) # теперь и так без сохранения

    # def action(self):
    #     # отсюда в поток ведь ничего не передать
    #     self.get_filenames_to_fft()
################################################################################################
#
# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------
# ----- plotting -------------------------------------------------------------------------------
            
    # @overload
    def plot_time_graph(self, time: np.ndarray,
                        enc_data: np.ndarray, gyro_data: np.ndarray):
        """Adds points to time curves."""
        self.time_curves[0].setData(time, enc_data)
        for i in range(gyro_data.shape[1]):
            self.time_curves[i + 1].setData(time, gyro_data[:, i])

    def set_fft_data(self, freq_data: np.ndarray, frame: list):
        """Adds points to frequency graphs."""
        ind = self.GYRO_NUMBER * (self.count() - 2)
        for i in range(self.GYRO_NUMBER):
            # self.amp_plot_list[-1].getPlotItem().curves[i].setData(freq_data[:, 0, i],
                                        # freq_data[:, 1, i])
            # self.phase_plot_list[-1].getPlotItem().curves[i].setData(freq_data[:, 0, i],
                                        # freq_data[:, 2, i])
            self.amp_curves[ind + i].setData(freq_data[:, 0, i],
                                            freq_data[:, 1, i])
            self.phase_curves[ind + i].setData(freq_data[:, 0, i],
                                              freq_data[:, 2, i])
            #                                np.copy(freq_data[:, 2, i]))
        self.region.setRegion([frame[0]/self.fs, frame[1]/self.fs])
        self.amp_plot_list[-1].autoRange()
        self.phase_plot_list[-1].autoRange()

# ------ FFT median plot ------------------------------------------------------------------
    def set_fft_median_data(self, freq_data: np.ndarray,
                            special_points: np.ndarray, folder: list):
        """Adds points to median frequency graphs."""
        self.logger.debug(f"Final median plot, sensor: {folder}")
        if np.isnan(freq_data[:, -4, :]).all():
            self.logger.debug("Only NaN in fft")
            return False
        self.setCurrentIndex(1)
        for i in range(2):
            self.infinite_x_line_list[i].setVisible(True)
        temp = np.empty(
            # (freq_data.shape[0] + 1, freq_data.shape[1], len(self.groupbox_list)))
            (freq_data.shape[0] + 1, freq_data.shape[1], freq_data.shape[2]))  # подправить! 
        # temp.fill(np.nan)
        for i in range(len(self.groupbox_list)):
            self.groupbox_list[i].setVisible(False)
        # for i in range(len(folder)):
        for i in range(freq_data.shape[2]):  # !!!
            self.groupbox_list[i].setVisible(True)
            temp[:, :, i] = np.insert(
                freq_data[:, :, i],
                int(special_points[-1, i]), special_points[:-1, i], axis=0)

            self.amp_curves[i].setData(temp[:, -4, i],
                                        temp[:, -3, i])
            self.phase_curves[i].setData(temp[:, -4, i],
                                        temp[:, -2, i])
            self.max_amp_line_edit_list[i].setText(
                f"{np.max(freq_data[:, -3, i]):.3f}")
            self.rez_freq_line_edit_list[i].setText(
                f"{freq_data[np.argmax(freq_data[:, -3, i]), -4, i]:.2f}")
            self.sensor_name_line_edit_list[i].setText(folder[i])
        self.freq_data = temp
        self.logger.debug(self.freq_data[1, :, :])
        self.amp_plot_list[0].autoRange()
        self.phase_plot_list[0].autoRange()
        self.logger.debug("Final median plot end")
        # self.mouse_x = None
        # self.mouse_y = None

# ----- cursor ---------------------------------------------------------------------------------
    def update_crosshair(self, e):  # упросить для 3 гироскопов, может, выводить сразу 3 числа
        """Move cursor to nearest frequency point and update label."""
        pos = e[0]
        # print(self.amp_plot_list[0].plotItem.sceneBoundingRect())
        # print(self.amp_plot_list[0].plotItem.vb.mapSceneToView(pos))
        # print(self.amp_plot_list[0].plotItem.vb.mapViewToScene())
        # print(self.amp_plot_list[0].plotItem.vb.viewRect())
        # print(self.selected_curve)
        if (self.amp_plot_list[0].plotItem.sceneBoundingRect().contains(pos)
            and self.freq_data.size and any(self.visibility_flags_list[1:])):
            mouse_point = self.amp_plot_list[0].plotItem.vb.mapSceneToView(pos)
            self.selected_curve = self.visibility_flags_list[1:].index(True)
            # print(self.selected_curve)
            # print(self.freq_data.shape)
            prev_ind = self.plot_index
            self.plot_index = np.nanargmin(
                np.abs(self.freq_data[:, -4, self.selected_curve] - mouse_point.x()))
            if self.plot_index == prev_ind: # чтобы лишний раз не пересчитывать
                return
                # np.abs(self.freq_data[:, -4, 0] - mouse_point.x()))
                # np.abs(self.freq_data[:, -4, self.selected_curve] - np.power(10, mouse_point.x())))
            if 0 <= self.plot_index < len(self.freq_data[:, -4, self.selected_curve]):  # index >= 0 and
                message = []
                for i in range(self.freq_data.shape[2]):
                    if self.visibility_flags_list[i+1]:
                        message.append(
                            f'\t\t\t\t\t\t\t<font color={self.COLOR_LIST2[i]}>gyro{i + 1}</font>: \
                                f {self.freq_data[self.plot_index, -4, i]:.2f}, \
                                \tA {self.freq_data[self.plot_index, -3, i]:.2f}, \
                                \t\u03C6 {self.freq_data[self.plot_index, -2, i]:.1f}')
                self.point_label.setText('; \t'.join(message))
                for i in range(2):
                    self.infinite_x_line_list[i].setPos(
                        self.freq_data[self.plot_index, -4, self.selected_curve])  
            # if 0 <= index < len(self.freq_data[:, -4, 0]):  # index >= 0 and 
                # self.point_label.setText(
                #     f"\t\t\t\t\t\t\tf {self.freq_data[index, -4, self.selected_curve]:.2f}" +
                #     f"\tA {self.freq_data[index, -3, self.selected_curve]:.2f}" +
                #     f"\t\u03C6 {self.freq_data[index, -2, self.selected_curve]:.1f}")
                # self.mouse_x = (self.freq_data[index, -4, self.selected_curve]) # freq_data[:, -4]
                # self.mouse_y = (self.freq_data[index, -3, self.selected_curve]) # freq_data[:, -3]
            
    # def mouseDoubleClickEvent(self, e):
    #     if (e.buttons() & QtCore.Qt.LeftButton & (
    #         self.amp_plot_list[0].underMouse() |
    #         self.phase_plot_list[0].underMouse()
    #         )) and self.freq_data.size:
    #         # )) and self.freq_data[0, 0, 0] != -1:
    #         # )) and self.freq_data.size:
    #         pass
            # self.amp_info_line_edit_list[self.selected_curve].setText(
            #     f'{self.mouse_y:.3f}')
            # self.freq_info_line_edit_list[self.selected_curve].setText(
            #     f'{self.mouse_x:.2f}')
            # self.cursor_label.setPos(self.mouse_x + 3, self.mouse_y + 0.3)

            # print(self.amp_plot_list[0].plotItem.vb.viewRect())
            # print(self.amp_plot_list[0].plotItem.vb.viewRect().width())
            # print(self.amp_plot_list[0].plotItem.vb.viewRect().x())
            # print(self.amp_plot_list[0].plotItem.vb.viewRect().y())
            # self.cursor_label.setPos(
            #     self.amp_plot_list[0].plotItem.vb.viewRect().x() + 0.02 * self.amp_plot_list[0].plotItem.vb.viewRect().width(),
            #     self.amp_plot_list[0].plotItem.vb.viewRect().y() + 0.98 * self.amp_plot_list[0].plotItem.vb.viewRect().height())
# ----- Excel and file selecting ----------------------------------------------

    @QtCore.pyqtSlot()
    def get_filenames_to_fft(self):
        """Open folder for file selection."""
        self.selected_files_to_fft, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Выберите файлы для построения АФЧХ",
            self.start_folder,
            "Text Files (*.txt)")
            # "All Files (*);;Python Files (*.py);;Text Files (*.txt)")
        if len(self.selected_files_to_fft):
            self.get_filename_signal.emit(True)
            self.start_folder = os.path.dirname(self.selected_files_to_fft[0])
 
    def create_excel_com_object(self):
        self.logger.debug("Создаем COM объект")
        # self.excel_com_object = win32.gencache.EnsureDispatch('Excel.Application')
        # self.excel_com_object = win32.Dispatch('Excel.Application')
        # self.excel_com_object = win32.DispatchEx("Excel.Application")  # !
        # self.excel_com_object.Interactive = False
        # self.excel_com_object.DisplayAlerts = False
        # self.logger.debug(f"excel.Visible: {self.excel_com_object.Visible}")
        self.logger.debug("Продолжаем")

    def close_excel_com_object(self):
        if not self.excel_com_object is None:
            self.excel_com_object.Quit  # !
            del self.excel_com_object

    @QtCore.pyqtSlot()
    def write_xlsx(self):
        """Write data in Excel cells."""
        # self.ok_btn.setEnabled(False)  # не хочется отключать, потому что может ошибка случиться
        # for i in range(self.freq_data.shape[2]):
        for i in range(len(self.groupbox_list)):
            # print(self.groupbox_list[i].isVisible())
            if not (self.sensor_name_line_edit_list[i].text() and self.groupbox_list[i].isVisible()):
                self.logger.debug(f"skip {i}")
                continue
            currnt_xlsx_path = \
                self.projects_combo_box.projects_dict[
                    self.projects_combo_box.currentText()] + '/' +\
                        self.sensor_name_line_edit_list[i].text() + '.xlsm'
            self.logger.debug(f"path {currnt_xlsx_path}")
            if not os.path.exists(currnt_xlsx_path):
                self.warning_signal.emit(
                    f"File {self.sensor_name_line_edit_list[i].text() + '.xlsm'} not found!")
                continue
            try: # удобная проверка на открытие файла
                os.rename(currnt_xlsx_path, currnt_xlsx_path)
                self.logger.debug("File is closed")
                self.info_signal.emit("Start saving")
                excel_com_object = self.excel_com_object  # !
                # excel_com_object.Visible = False
                close_flag = True
                excel_com_object.DisplayAlerts = False   # !
            except OSError:
                self.logger.debug("Saving to an open file")
                self.info_signal.emit("Start saving to an open file")
                # Excel = win32.GetActiveObject('Excel.Application')  # ! GetActiveObject ?
                # excel_com_object = win32.GetActiveObject(currnt_xlsx_path)
                excel_com_object = win32.GetObject(currnt_xlsx_path).Application
                self.logger.debug(type(excel_com_object))
                self.logger.debug(f"{excel_com_object}, {excel_com_object.ActiveWorkbook}")
                if excel_com_object.ActiveWorkbook is None:  # проверить!
                    self.warning_signal.emit("Erorr! (the file may be open on another device)")
                    excel_com_object.Quit()
                    del excel_com_object
                    continue
                self.logger.debug(f"{excel_com_object.ActiveWorkbook.FullName}")
                close_flag = False
            self.ok_btn.setDisabled(True)  # !
            wb = excel_com_object.Workbooks.Open(currnt_xlsx_path)
            if not close_flag:
                wb.Save()  # если файл открыт, в нем сохраняются прежние изменения
            wb.Worksheets(u'Настройка КП').Cells(11, "I").Value = \
                float(self.rez_freq_line_edit_list[i].text())
            wb.Worksheets(u'Настройка КП').Cells(11, "K").Value = \
                float(self.max_amp_line_edit_list[i].text())
            wb.Save()
            self.ok_btn.setDisabled(False)  # !
            if close_flag:
                wb.Close()
                del wb  # excel_com_object.Quit()  # !
            else:
                excel_com_object.Goto(wb.Worksheets(u'Настройка КП').Range("I10:K10"), True)
            self.logger.debug(f"Successfully save in {currnt_xlsx_path}")
            self.info_signal.emit(f"Successfully save in {currnt_xlsx_path}")
        # self.ok_btn.setEnabled(True)
        return True

    # @QtCore.pyqtSlot()
    # def write_xlsx(self):
    #     self.warning_signal.emit("Start saving")
    #     self.logger.debug(f"Get Excel")
    #     if not len(self.sensor_name_line_edit_list[self.selected_curve].text()):
    #         return
    #     currnt_xlsx_path = \
    #         self.projects_combo_box.projects_dict[
    #             self.projects_combo_box.currentText()] + \
    #                 '/' + self.sensor_name_line_edit_list[self.selected_curve].text() + '.xlsm'
    #     self.logger.debug(currnt_xlsx_path)
    #     try:
    #         wb = load_workbook(currnt_xlsx_path,
    #                            read_only=False, keep_vba=True)
    #     except FileNotFoundError:
    #         self.warning_signal.emit("File not found!")
    #         return
    #     ws = wb['Настройка КП']  #
    #     self.logger.debug(f"Save in Excel 2")
    #     ws['I11'] = float(self.freq_info_line_edit_list[self.selected_curve].text())
    #     ws['K11'] = float(self.amp_info_line_edit_list[self.selected_curve].text())
    #     try:
    #         wb.save(currnt_xlsx_path)
    #     except IOError:
    #         self.warning_signal.emit("File was open! Close and try again")
    #         return
    #     self.logger.debug(f"Successfully save in {currnt_xlsx_path}")
    #     self.warning_signal.emit(f"Successfully save in {currnt_xlsx_path}")

# ----- plot change -----------------------------------------------------------

    @QtCore.pyqtSlot()
    def log_mode(self):  # !
        self.amp_plot_list[0].setLogMode(True, True)
        self.phase_plot_list[0].setLogMode(True, False)
        # self.amp_plot_list[0].getAxis('left').setWidth(100)
        self.amp_plot_list[0].setLimits(
            xMin=-1.05, xMax=np.log10(int(self.fs * 0.53)), yMin=-2.05, yMax=1.5)
        # self.phase_plot_list[0].getAxis('left').setWidth(100)
        self.phase_plot_list[0].setLimits(
            xMin=-1.05, xMax=np.log10(int(self.fs * 0.53)), yMin=-375, yMax=20)
        self.amp_plot_list[0].autoRange()
        self.phase_plot_list[0].autoRange()
        # self.amp_plot_list[-1].setLimits(
        #     xMin=-4, xMax=int(self.fs * 0.53), yMin=-0.08, yMax=100)
        # self.phase_plot_list[-1].setLimits(
        #     xMin=-4, xMax=int(self.fs * 0.53), yMin=-375, yMax=20)
        # self.amp_plot_list[0].ctrl.fftCheck.setChecked(False)
        # менять ограничения для осей
        # менять отображение точек

    @QtCore.pyqtSlot()
    def change_curve_visibility(self):
        ind = int(self.sender().objectName())
        # self.flag_visibility[num] = self.check_box_list[num].checkState()
        # self.visibility_flags_list[ind] = not self.visibility_flags_list[ind]
        self.time_curves[ind].setVisible(self.plot_check_box_list[ind].isChecked())
        if ind == 0:
            return
        for i in range(self.count() - 1):
            self.phase_curves[i*self.GYRO_NUMBER - 1 + ind].setVisible(
                self.plot_check_box_list[ind].isChecked())
            self.amp_curves[i*self.GYRO_NUMBER - 1 + ind].setVisible(
                self.plot_check_box_list[ind].isChecked())
        print([check_box.isChecked() for check_box in self.plot_check_box_list])
        if any(self.visibility_flags_list[1:]):
            for j in range(2):
                self.infinite_x_line_list[j].setPen(
                    pg.mkPen(self.COLOR_LIST[self.visibility_flags_list[1:].index(True)]))

    def clear_plots(self):
        self.freq_data = np.array([])  # лучше пустой массив создавать
        self.point_label.setText('')
        self.region.setRegion([0, 0])
        for i in range(2):
            self.infinite_x_line_list[i].setVisible(False)
        for i in range(self.count() - 2):
            for _ in range(self.GYRO_NUMBER):
                # self.amp_curves[-1].clear()  # self.phase_curves[-1].clear()
                self.amp_curves.pop()
                self.phase_curves.pop()
            self.amp_plot_list.pop()
            self.phase_plot_list.pop()
            self.tab_widget_page_list.pop()
            i = self.count() - 1
            self.widget(i).deleteLater()  # без этого удаление не работает и случается утечка памяти
            self.removeTab(i)
        # так можно убирать вкладку без удаления:
        # self.custom_tab_plot_widget.setTabVisible(0, False)  
        self.time_curves[0].setData([])
        for i in range(self.GYRO_NUMBER):
            self.time_curves[i + 1].setData([])
            self.amp_curves[i].setData([])
            self.phase_curves[i].setData([])
        # self.phase_curves: list[pg.PlotCurveItem] = []
        # self.amp_curves: list[pg.PlotCurveItem] = []
        # self.phase_plot_list: list[pg.PlotWidget] = []
        # self.amp_plot_list: list[pg.PlotWidget] = []
        # self.tab_widget_page_list: list[QtWidgets.QWidget] = []

    @QtCore.pyqtSlot()
    def switch_plot_x_axis(self):
        # меню добавить
        """Switching between time plot and spectrum."""
        if self.spectrum_button.text() == "Спектр":  # Frequency plot
            self.spectrum_button.setText("От времени")  # Time plot
            self.time_plot_item.ctrl.fftCheck.setChecked(False)
            self.time_plot_item.setLabel(
                'bottom', 'Time', units='seconds')
            self.region.show()
        else:
            self.spectrum_button.setText("Спектр")  # Frequency plot
            self.time_plot_item.ctrl.fftCheck.setChecked(True)
            self.time_plot_item.setLabel(
                'bottom', 'Frequency', units='Hz')
            self.region.hide()

    @QtCore.pyqtSlot(str)
    def save_plot_image(self, path: str):
        if not os.path.isdir(os.path.dirname(path)):
            self.warning_signal.emit(f"Folder {os.path.dirname(path)} doesn't exist!")
            return False
        pyqtgraph.exporters.ImageExporter(
            self.time_plot_item).export(
                check_name_simple(path + '_time_plot.png'))
        for i in range(self.count() - 1):
            pyqtgraph.exporters.ImageExporter(
                self.amp_plot_list[i].getPlotItem()).export(
                    check_name_simple(path + f'_amp_plot_{i + 1}.png'))
            pyqtgraph.exporters.ImageExporter(
                self.phase_plot_list[i].getPlotItem()).export(
                    check_name_simple(path + f'_phase_plot_{i + 1}.png'))
        self.info_signal.emit("Save plots")

    def plot_fft_median(self):
        self.freq_data = np.array([])
        last_tab_layout = QtWidgets.QGridLayout(spacing=0)
        last_tab_layout.setContentsMargins(5, 10, 5, 5)
        last_tab_layout.addWidget(self.groupbox, 0, 1, 3, 1) 

        self.tab_widget_page_list.append(QtWidgets.QWidget(self))
        self.append_amp_plot()
        last_tab_layout.addWidget(self.amp_plot_list[0], 0, 0, 1, 1)
        self.point_label = QtWidgets.QLabel()
        last_tab_layout.addWidget(self.point_label, 1, 0, 1, 1)
        self.append_phase_plot()
        last_tab_layout.addWidget(self.phase_plot_list[0], 2, 0, 1, 1)
        self.tab_widget_page_list[0].setLayout(last_tab_layout)
        self.addTab(
            self.tab_widget_page_list[0], "&АФЧХ (средний)")  # FC average
  
        # # amp =np.array([96, 97, 108, 112, 113, 114, 121, 127, 136, 163, 166, 191, 219, 240, 258, 284, 400, 371, 450, 699, 791, 1154, 631, 697, 722, 743, 834, 823, 918, 995, 1022, 1125, 1220, 1244, 1373, 1468, 1618, 1851, 1865, 2166, 2548, 2539, 3409, 3521, 3514, 4220, 3473, 2573, 3081, 3028, 3028, 3230, 3056, 3132, 3102, 3621, 3669, 4561])/100
        # self.cursor = QtCore.Qt.BlankCursor
        amp_plot_cursor = QtCore.Qt.CrossCursor
        self.amp_plot_list[0].setCursor(amp_plot_cursor)
        phase_plot_cursor = QtCore.Qt.CrossCursor # was
        self.phase_plot_list[0].setCursor(phase_plot_cursor)  # self.cursor ##########################

        self.infinite_x_line_list = [pg.InfiniteLine(angle=90, pen=pg.mkPen(self.COLOR_LIST[0]))
                                     for _ in range(2)]
        for i in range(2):
            self.infinite_x_line_list[i].setVisible(False)
        self.amp_plot_list[0].addItem(self.infinite_x_line_list[0], ignoreBounds=True)
        self.phase_plot_list[0].addItem(self.infinite_x_line_list[1], ignoreBounds=True)
        self.amp_plot_list[0].addItem(
            pg.InfiniteLine(
                pos=np.sqrt(0.5), angle=0, movable=False,
                pen=pg.mkPen((205, 205, 205), dash=[15, 3], width=0.75)),
                ignoreBounds=True)  # полоса пропускания
        self.phase_plot_list[0].addItem(
            pg.InfiniteLine(
                pos=-180, angle=0, movable=False,
                pen=pg.mkPen((205, 205, 205), dash=[10, 2], width=0.75)),
                ignoreBounds=True)  # -180 degrees
        # self.cursor_label = pg.TextItem()
        # self.cursor_label.setPos(3, 0.8)
        # self.cursor_label.setPos(10, 0)

        # self.amp_plot_list[0].addItem(self.cursor_label) #################################
        self.proxy_amp = pg.SignalProxy(
            self.amp_plot_list[0].scene().sigMouseMoved, delay=0,
            rateLimit=12, slot=self.update_crosshair)
        self.proxy_phase = pg.SignalProxy(
            self.phase_plot_list[0].scene().sigMouseMoved, delay=0,
            rateLimit=12, slot=self.update_crosshair)
        self.amp_plot_list[0].autoRange()

    def append_fft_plot_tab(self):
        """
        Create new tab and append amplitude and grequency graphs.
        """
        # index = 
        self.tab_widget_page_list.append(QtWidgets.QWidget())
        layout = QtWidgets.QVBoxLayout(spacing=0)
        layout.setContentsMargins(5, 10, 5, 5)
        self.append_amp_plot()
        # layout.addWidget(self.amp_plot_list[index])
        layout.addWidget(self.amp_plot_list[-1])
        self.append_phase_plot()
        # layout.addWidget(self.phase_plot_list[index])
        layout.addWidget(self.phase_plot_list[-1])
        self.tab_widget_page_list[-1].setLayout(layout)
        self.addTab(
            self.tab_widget_page_list[-1], f"ЧХ &{self.count() - 1}")  # FC

    def append_amp_plot(self):
        amp_plot_item = pg.PlotItem(viewBox=CustomViewBox(),
                                    name=f'amp_plot{self.count()}')
        amp_plot_item.setXLink(f'phase_plot{self.count()}')
        # amp_plot_item.setTitle('АЧХ', size=f'{self.pt - 1}pt')  # Amp Graph
        amp_plot_item.showGrid(x=True, y=True)
        amp_plot_item.addLegend(offset=(-1, 1), labelTextSize=f'{self.pt - 1}pt',
                                     labelTextColor=pg.mkColor('w'))
        amp_plot_item.setLabel('left', 'Amplitude',
                               units="", **self.LABEL_STYLE)
        # amp_plot_item.setLabel('bottom', 'Frequency',
        #                             units='Hz', **self.LABEL_STYLE)
        # self.SYMBOL_SIZE = 6
        for i in range(self.GYRO_NUMBER):
            self.amp_curves.append(amp_plot_item.plot(
                pen=self.COLOR_LIST[i], name=f"gyro {i + 1}", symbol="o",
                symbolSize=6, symbolBrush=self.COLOR_LIST[i]))
            self.amp_curves[-1].setVisible(self.plot_check_box_list[i+1].isChecked())  
        self.amp_plot_list.append(pg.PlotWidget(plotItem=amp_plot_item))
        self.amp_plot_list[-1].getAxis('left').setWidth(60)
        self.amp_plot_list[-1].setLimits(
            xMin=-4, xMax=int(self.fs * 0.53), yMin=-0.08, yMax=5000)
            # xMin=-4, xMax=int(self.fs * 0.53), yMin=-0.08, yMax=100)
    
    def append_phase_plot(self):
        phase_plot_item = pg.PlotItem(viewBox=CustomViewBox(),
                                           name=f'phase_plot{self.count()}')
        phase_plot_item.setXLink(f'amp_plot{self.count()}')
        # phase_plot_item.setTitle('ФЧХ', size='12pt')  # Phase Graph
        phase_plot_item.showGrid(x=True, y=True)
        phase_plot_item.addLegend(offset=(-1, 1), labelTextSize=f'{self.pt - 1}pt',
                                  labelTextColor=pg.mkColor('w'))
        phase_plot_item.setLabel('left', 'Phase',
                                 units='degrees', **self.LABEL_STYLE)  # rad
        phase_plot_item.setLabel('bottom', 'Frequency',
                                 units='Hz', **self.LABEL_STYLE) # \u00b0
        for i in range(self.GYRO_NUMBER):
            self.phase_curves.append(phase_plot_item.plot(
                pen=self.COLOR_LIST[i], name=f"gyro {i + 1}", symbol="o",
                symbolSize=6, symbolBrush=self.COLOR_LIST[i]))
            self.phase_curves[-1].setVisible(self.plot_check_box_list[i+1].isChecked())  
        self.phase_plot_list.append(
            pg.PlotWidget(plotItem=phase_plot_item))
        self.phase_plot_list[-1].getAxis('left').setWidth(60)
        self.phase_plot_list[-1].setLimits(
            xMin=-4, xMax=int(self.fs * 0.53), yMin=-720, yMax=20)
            # xMin=-4, xMax=int(self.fs * 0.53), yMin=-375, yMax=20)

    def append_gyro_groupbox(self):
        ind = len(self.groupbox_list)
        self.groupbox_list.append(QtWidgets.QGroupBox(
            f'gyro {ind + 1}', maximumWidth=190, maximumHeight=250,
            objectName='small'))
            # checkable=True, objectName='small'))
        groupbox_layout = QtWidgets.QGridLayout(spacing=2)
        groupbox_layout.setContentsMargins(5, 5, 5, 2)
        # self.groupbox_list[-1].clicked.connect(self.groupbox_clicked)
        # self.median_plot_groupbox_layout.setRowStretch(4, 0)
        self.groupbox_list[-1].setLayout(groupbox_layout)
        # QToolButton # есть wordWrap
        msx_amp_label = QtWidgets.QLabel("amp")
        groupbox_layout.addWidget(
            msx_amp_label, 0, 0, 1, 1)
        self.max_amp_line_edit_list.append(QtWidgets.QLineEdit())
        double_validator = QtGui.QDoubleValidator(bottom=0)
        double_validator.setLocale(QtCore.QLocale("en_US"))
        self.max_amp_line_edit_list[-1].setValidator(double_validator)
        groupbox_layout.addWidget(
            self.max_amp_line_edit_list[-1], 0, 1, 1, 2)

        rez_freq_label = QtWidgets.QLabel("f, Hz")
        groupbox_layout.addWidget(
            rez_freq_label, 1, 0, 1, 1)
        self.rez_freq_line_edit_list.append(QtWidgets.QLineEdit())
        double_validator = QtGui.QDoubleValidator(bottom=0)
        double_validator.setLocale(QtCore.QLocale("en_US"))
        self.rez_freq_line_edit_list[-1].setValidator(double_validator)
        groupbox_layout.addWidget(
            self.rez_freq_line_edit_list[-1], 1, 1, 1, 2)

        sensor_name_label = QtWidgets.QLabel(
            "номер", maximumHeight=40)
        groupbox_layout.addWidget(
            sensor_name_label, 2, 0, 1, 1)
        self.sensor_name_line_edit_list.append(QtWidgets.QLineEdit())
        groupbox_layout.addWidget(
            self.sensor_name_line_edit_list[-1], 2, 1, 1, 2)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
#
###############################################################################
#
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


if __name__ == "__main__":
    import PyQt_ApplicationClass
    app = QtWidgets.QApplication(sys.argv)
    window = PyQt_ApplicationClass.AppWindow()
    sys.exit(app.exec())


#    def plot_fft_median(self, freq_data: np.ndarray, special_points: np.ndarray, folder: str):
#         self.logger.debug("Final median plot")
#         # self.append_fft_plot_tab()
#         self.last_tab_layout = QtWidgets.QGridLayout(spacing=0)
#         self.last_tab_layout.addWidget(self.groupbox, 0, 1, 2, 1) 

#         index = self.count() - 1
#         self.tab_widget_page_list.append(QtWidgets.QWidget(self))
#         self.append_amp_plot()
#         self.last_tab_layout.addWidget(self.amp_plot_list[index], 0, 0, 1, 1)
#         self.append_phase_plot()
#         self.last_tab_layout.addWidget(self.phase_plot_list[index], 1, 0, 1, 1)
#         self.tab_widget_page_list[-1].setLayout(self.last_tab_layout)
#         self.addTab(
#             self.tab_widget_page_list[-1], f"ЧХ &{index + 1}")  # FC 
#         self.setTabText(self.count() - 1, "&АФЧХ (средний)")  # FC average
#         self.setCurrentIndex(self.count() - 1)
  
#         # self.del_btn.clicked.connect(
#         #     self.text_())
#         self.name_info.setText(folder)

#         self.x = freq_data[:, -4]  # [1, 5, 13, 20, 55, 62, 80]
#         # # amp =np.array([96, 97, 108, 112, 113, 114, 121, 127, 136, 163, 166, 191, 219, 240, 258, 284, 400, 371, 450, 699, 791, 1154, 631, 697, 722, 743, 834, 823, 918, 995, 1022, 1125, 1220, 1244, 1373, 1468, 1618, 1851, 1865, 2166, 2548, 2539, 3409, 3521, 3514, 4220, 3473, 2573, 3081, 3028, 3028, 3230, 3056, 3132, 3102, 3621, 3669, 4561])/100
#         self.y = freq_data[:, -3]  # np.array([1, 1.2, 1.3, 1.5, 5, .5, .35])
#         # self.amp_curves[-1].setData(self.x, self.y)
#         # self.plot_2d_scatter(self.time_plot, self.x, self.y)
#         # self.cursor = Qt.BlankCursor
#         # self.amp_plot_list[-1].setCursor(self.cursor)  # self.cursor ##########################

#         # Add lines
#         # self.amp_plot_list[-1].addItem(self.infinite_line_x, ignoreBounds=True)
#         # self.amp_plot_list[-1].addItem(self.infinite_line_y, ignoreBounds=True)
    
#         # self.amp_plot_list[-1].addItem(self.cursorlabel)#################################
#         # self.proxy = pg.SignalProxy(
#         #     self.amp_plot_list[-1].scene().sigMouseMoved, delay=0.15,##############################
#         #     rateLimit=15, slot=self.update_crosshair)

#         # self.proxy = pg.SignalProxy(
#             # self.phase_plot_list[-1].scene().sigMouseMoved, delay=0.15,
#             # rateLimit=15, slot=self.update_crosshair) ####################
#         self.mouse_x = None
#         self.mouse_y = None
#         # # self.plot_fft(True)
#         for i in range(self.GYRO_NUMBER):
#             self.amp_curves[-1 - i].setData(freq_data[:, -4],
#                                         freq_data[:, -3])
#             self.phase_curves[-1 - i].setData(freq_data[:, -4],
#                                         freq_data[:, -2])
#         self.amp_plot_list[-1].autoRange()
#     # def plot_2d_scatter(self, plot, x, y, color=(66, 245, 72)):
#     #     brush = pg.mkBrush(color)
#     #     scatter = pg.ScatterPlotItem(size=5, brush=brush)
#     #     scatter.addPoints(x, y)
#     #     plot.addItem(scatter)