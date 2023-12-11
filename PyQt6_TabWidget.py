import logging
# from PyQt6.QtWidgets import QFileDialog
# from PyQt6.QtCore import pyqtSignal, QThread, QIODevice
# from pyqtgraph.Qt import QtCore, QtGui
# from datetime import datetime
# from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph.exporters
import pyqtgraph as pg
import numpy as np


class CustomViewBox(pg.ViewBox):
    def __init__(self, *args, **kwds):
        kwds['enableMenu'] = True
        # kwds['enableMenu'] = False
        pg.ViewBox.__init__(self, *args, **kwds)
        # self.setMouseMode(self.RectMode)

    #  reimplement right-click to zoom out
    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.MouseButton.RightButton:
            self.autoRange()

    # #  reimplement mouseDragEvent to disable continuous axis zoom
    # def mouseDragEvent(self, ev, axis=None):
    #     if axis is not None and ev.button() == QtCore.Qt.MouseButton.RightButton:
    #         ev.ignore()
    #     else:
    #         pg.ViewBox.mouseDragEvent(self, ev, axis=axis)


class CustomTabWidget(QtWidgets.QTabWidget):
    def __init__(self, fs=1000, GYRO_NUMBER=1, parent=None):
        # QtWidgets.QTabWidget.__init__(self)
        super(CustomTabWidget, self).__init__(parent)
        # QtWidgets.QWidget.__init__(self, parent)
        self.GYRO_NUMBER = GYRO_NUMBER
        self.visibility_flags = [True for i in range(self.GYRO_NUMBER + 1)]
        # print(self.visibility_flags)
        self.LABEL_STYLE = {'color': '#FFF', 'font-size': '16px'}
        self.COLOR_LIST = ['r', 'g', 'b']
        self.fs = fs
# ------ time plot ------------------------------------------------------------

        self.time_plot_item = pg.PlotItem(viewBox=CustomViewBox())
        self.time_plot = pg.PlotWidget(plotItem=self.time_plot_item)
        self.time_plot_item.setTitle('Угловая скорость', size='13pt')  # Velosity Graph
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

        self.region = pg.LinearRegionItem([0, 1], movable=False)
        self.time_plot_item.addItem(self.region)

        # x = [1, 5, 10, 15, 20, 25, 33, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 118, 120, 122, 125, 130, 135, 140, 150, 156, 162, 170, 180, 190, 200, 205, 210, 215, 220, 225, 230, 235, 240, 245, 250, 255, 260, 265, 270, 275, 280, 285, 290, 300, 310]
        self.x = [1, 5, 10, 15, 20, 25, 33, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 102, 105, 107, 110, 115, 118, 120, 122, 125, 130, 135, 140, 150, 156, 162, 170, 180, 190, 200, 205, 210, 215, 220, 225, 230, 235, 240, 243, 247, 250, 255, 260, 265, 270, 275, 280, 285, 290, 295, 300, 305, 310, 315]
        # # amp =np.array([96, 97, 108, 112, 113, 114, 121, 127, 136, 163, 166, 191, 219, 240, 258, 284, 400, 371, 450, 699, 791, 1154, 631, 697, 722, 743, 834, 823, 918, 995, 1022, 1125, 1220, 1244, 1373, 1468, 1618, 1851, 1865, 2166, 2548, 2539, 3409, 3521, 3514, 4220, 3473, 2573, 3081, 3028, 3028, 3230, 3056, 3132, 3102, 3621, 3669, 4561])/100
        self.y =np.array(
            [94, 99, 105, 114, 112, 113, 122, 127, 137, 160, 169, 205, 221, 243, 292, 306, 339, 392, 419, 554, 861, 913, 1079, 1276, 595, 645, 659, 666, 781, 810, 863, 948, 1024, 1103, 1227, 1329, 1319, 1362, 1468, 1791, 1921, 1959, 2641, 2477, 3384, 3484, 3254, 4482, 3888, 3931, 2795, 3021, 3246, 3046, 3147, 3505, 3424, 3430, 4049, 4157, 4385, 3980, 5340, 4897]
            )/100
        # self.time_curves[0].setData(self.x, self.y)
# ------ Tab widget -----------------------------------------------------------
        self.page = QtWidgets.QWidget(self)
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.time_plot)
        self.spectrum_button = QtWidgets.QPushButton("От времени")  # Time plot
        self.layout.addWidget(self.spectrum_button)
        self.page.setLayout(self.layout)
        self.addTab(self.page, "\u03C9(t)")  # &Time plot От времени
        self.phase_curves: list[pg.PlotCurveItem] = []
        self.amp_curves: list[pg.PlotCurveItem] = []
        self.phase_plot_list: list[pg.PlotWidget] = []
        self.amp_plot_list: list[pg.PlotWidget] = []
        self.tab_widget_page_list: list[QtWidgets.QWidget] = []

        self.logger = logging.getLogger('main')
        self.spectrum_button.clicked.connect(self.switch_plot_x_axis)

# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------
#
###############################################################################
#
# ----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------
# ----- plotting --------------------------------------------------------------

    def plot_time_graph(self,time_data: np.ndarray,
                        enc_data: np.ndarray, gyro_data: np.ndarray):
        self.time_curves[0].setData(
            time_data, enc_data)
        for i in range(self.GYRO_NUMBER):
            self.time_curves[i + 1].setData(
                time_data, gyro_data)

    def set_fft_data(self, freq_data: np.ndarray, frame: list, fs: int):
        """Adds points to frequency graphs"""
        self.amp_plot_list[-1].autoRange()
        self.logger.info("plot_fft")
        for i in range(self.GYRO_NUMBER):
            self.amp_curves[-1 - i].setData(freq_data[:, 0],
                                        freq_data[:, 1])
            self.phase_curves[-1 - i].setData(freq_data[:, 0],
                                        freq_data[:, 2])
        self.region.setRegion([frame[0]/fs, frame[1]/fs])

# ------ FFT median plot ------------------------------------------------------------------
    def text_(self, value):
        # self.test_combo_box.currentIndexChanged.disconnect(self.ind)
        print(self.test_combo_box.currentText())
        print(value)
        print("len = " + str(len(value)))
        if not len(self.test_combo_box.currentText()) and self.test_combo_box.count() > 2:
            if self.test_combo_box.currentIndex():
                self.test_combo_box.setCurrentIndex(self.test_combo_box.currentIndex()-1)
                self.test_combo_box.removeItem(self.test_combo_box.currentIndex()+1)
            else:
                self.test_combo_box.removeItem(self.test_combo_box.currentIndex())
            # if self.test_combo_box.currentIndex() == self.test_combo_box.count() - 1:
                # self.test_combo_box.lineEdit().setReadOnly(True)
        else:
            self.test_combo_box.setItemText(self.test_combo_box.currentIndex(), value)
        # self.test_combo_box.currentIndexChanged.connect(self.ind)

    def ind(self):
        print(self.test_combo_box.currentIndex())
        print(self.test_combo_box.currentIndex() == self.test_combo_box.count() - 1)
        if self.test_combo_box.currentIndex() == self.test_combo_box.count() - 1:
            print("last")
            self.test_combo_box.lineEdit().setReadOnly(True)
            self.test_combo_box.setCurrentIndex(0)
            self.test_combo_box.insertItem(0, "введите название проекта")
            self.test_combo_box.setCurrentIndex(0)
        else:
            # self.test_combo_box.setEditable(True)
            self.test_combo_box.lineEdit().setReadOnly(False)
            pass
        # self.test_combo_box.currentIndexChanged.disconnect(self.ind)

    def plot_fft_median(self, freq_data: np.ndarray, special_points: np.ndarray):
        self.logger.info("Final median plot")
        self.append_fft_plot_tab()
        self.Q_label = QtWidgets.QLineEdit('Q=')
        self.f_r_label = QtWidgets.QLineEdit('f_r=')
        self.f_r_label = QtWidgets.QLineEdit()
        # self.layout.addWidget(self.Q_label)
        self.test_combo_box = QtWidgets.QComboBox(editable=True)
        self.test_combo_box.addItem('22')

        self.test_combo_box.addItem(QtGui.QIcon("icon_48.png"), 'Создать новый пункт')
        self.test_combo_box.insertItem(0, "0www")

        self.layout.addWidget(self.test_combo_box)
        self.test_combo_box.currentTextChanged.connect(self.text_)
        self.test_combo_box.currentIndexChanged.connect(self.ind)

        #
        self.x = [1, 5, 13, 20, 55, 62, 80]
        # # amp =np.array([96, 97, 108, 112, 113, 114, 121, 127, 136, 163, 166, 191, 219, 240, 258, 284, 400, 371, 450, 699, 791, 1154, 631, 697, 722, 743, 834, 823, 918, 995, 1022, 1125, 1220, 1244, 1373, 1468, 1618, 1851, 1865, 2166, 2548, 2539, 3409, 3521, 3514, 4220, 3473, 2573, 3081, 3028, 3028, 3230, 3056, 3132, 3102, 3621, 3669, 4561])/100
        self.y =np.array(
            [1, 1.2, 1.3, 1.5, 5, .5, .35]
            )
        self.amp_curves[-1].setData(self.x, self.y)
        self.amp_plot_list[-1].autoRange()
        # self.plot_2d_scatter(self.time_plot, self.x, self.y)
        self.cursor = QtCore.Qt.CrossCursor # was
        # self.cursor = Qt.BlankCursor
        self.amp_plot_list[-1].setCursor(self.cursor)  # self.cursor
    
        # Add crosshair lines.
        self.crosshair_v = pg.InfiniteLine(angle=90, movable=False)
        self.crosshair_h = pg.InfiniteLine(angle=0, movable=False)
        self.amp_plot_list[-1].addItem(self.crosshair_v, ignoreBounds=True)
        self.amp_plot_list[-1].addItem(self.crosshair_h, ignoreBounds=True)
        self.cursorlabel = pg.TextItem()
        self.cursorlabel.setPos(1, 0.9)
    
        self.amp_plot_list[-1].addItem(self.cursorlabel)
        self.proxy = pg.SignalProxy(
            self.amp_plot_list[-1].scene().sigMouseMoved,
            rateLimit=30, slot=self.update_crosshair)
        self.mouse_x = None
        self.mouse_y = None

        self.setTabText(self.count() - 1, "&АФЧХ (средний)")  # FC average
        self.setCurrentIndex(self.count() - 1)
        # # self.plot_fft(True)
        # for i in range(self.GYRO_NUMBER):
        #     self.amp_curves[-1 - i].setData(freq_data[:, -4],
        #                                 freq_data[:, -3])
        #     self.phase_curves[-1 - i].setData(freq_data[:, -4],
        #                                 freq_data[:, -2])

        # app_icon = QtGui.QIcon()
        # app_icon.addFile(self.res_path('icon_24.png'), QtCore.QSize(24, 24))
        # self.setTabIcon(self.current_cylce + 1, app_icon)

    # def plot_2d_scatter(self, plot, x, y, color=(66, 245, 72)):
    #     brush = pg.mkBrush(color)
    #     scatter = pg.ScatterPlotItem(size=5, brush=brush)
    #     scatter.addPoints(x, y)
    #     plot.addItem(scatter)

    def update_crosshair(self, e):
        pos = e[0]
        # print(pos)
        if self.amp_plot_list[-1].plotItem.sceneBoundingRect().contains(pos):
            mousePoint = self.amp_plot_list[-1].plotItem.vb.mapSceneToView(pos)
            mx = np.array(
                [abs(float(i) - float(mousePoint.x())) for i in self.x])
            index = mx.argmin()
            if index >= 0 and index < len(self.x):
                self.cursorlabel.setText(
                        str((self.x[index], self.y[index])))
                self.crosshair_v.setPos(self.x[index])
                self.crosshair_h.setPos(self.y[index]) 
                self.mouse_x = self.crosshair_v.setPos(self.x[index])
                self.mouse_y = self.crosshair_h.setPos(self.y[index])
                self.mouse_x = (self.x[index])
                self.mouse_y = (self.y[index])
            
    def mousePressEvent(self, e):
        if e.buttons() & QtCore.Qt.LeftButton & self.amp_plot_list[-1].underMouse():
            print(f'pressed {self.mouse_x, self.mouse_y}')
            # self.cursorlabel.setPos(self.mouse_x + 1, self.mouse_y + 1)
            # if self.mouse_x in self.x and self.mouse_y in self.y:
# ----- plot change -----------------------------------------------------------

    def clear_plots(self):
        for i in range(self.count() - 1):
            self.removeTab(1)
        #     self.tab_widget_page_list.pop()
        #     for i in range(self.GYRO_NUMBER):
        #         self.time_curves.pop()
        #         self.amp_curves.pop()
        #         phase_plot_list
        self.time_curves[0].setData([])
        for i in range(self.GYRO_NUMBER):
            self.time_curves[i + 1].setData([])
        #     self.amp_curves[i].setData([])
        #     self.phase_curves[i].setData([])
        self.phase_curves: list[pg.PlotCurveItem] = []
        self.amp_curves: list[pg.PlotCurveItem] = []
        self.phase_plot_list: list[pg.PlotWidget] = []
        self.amp_plot_list: list[pg.PlotWidget] = []
        self.tab_widget_page_list: list[QtWidgets.QWidget] = []
        self.append_fft_plot_tab()

    @QtCore.pyqtSlot()
    def switch_plot_x_axis(self):
        """
        Switching between time plot and spectrum
        """
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

    def change_curve_visibility(self):
        num = int(self.sender().objectName())
        # self.flag_visibility[num] = self.check_box_list[num].checkState()
        self.visibility_flags[num] = not self.visibility_flags[num]
        self.time_curves[num].setVisible(self.visibility_flags[num])
        if num == 0:
            return
        for i in range(self.count() - 1):
            self.phase_curves[num - 1 + i].setVisible(self.visibility_flags[num])
            self.amp_curves[num - 1 + i].setVisible(self.visibility_flags[num])

    def append_fft_plot_tab(self):
        """
        Create new tab and append amplitude and grequency graphs
        """
        index = self.count() - 1
        self.tab_widget_page_list.append(QtWidgets.QWidget(self))
        self.layout = QtWidgets.QVBoxLayout(spacing=0)
        self.append_amp_plot()
        self.layout.addWidget(self.amp_plot_list[index])
        self.append_phase_plot()
        self.layout.addWidget(self.phase_plot_list[index])
        self.tab_widget_page_list[-1].setLayout(self.layout)
        self.addTab(
            self.tab_widget_page_list[-1], f"ЧХ &{index + 1}")  # FC        

    def append_amp_plot(self):
        self.amp_plot_item = pg.PlotItem(viewBox=CustomViewBox(),
                                         name=f'amp_plot{self.count()}')
        self.amp_plot_item.setXLink(f'phase_plot{self.count()}')
        self.amp_plot_item.setTitle('АФЧХ', size='12pt')  # Amp Graph
        self.amp_plot_item.showGrid(x=True, y=True)
        self.amp_plot_item.addLegend(offset=(-1, 1), labelTextSize='12pt',
                                     labelTextColor=pg.mkColor('w'))
        self.amp_plot_item.setLabel('left', 'Amplitude',
                                    units="", **self.LABEL_STYLE)
        # self.amp_plot_item.setLabel('bottom', 'Frequency',
        #                             units='Hz', **self.LABEL_STYLE)
        # self.SYMBOL_SIZE = 6
        for i in range(self.GYRO_NUMBER):
            self.amp_curves.append(self.amp_plot_item.plot(
                pen=self.COLOR_LIST[i], name=f"gyro {i + 1}", symbol="o",
                symbolSize=6, symbolBrush=self.COLOR_LIST[i]))
        self.amp_plot_list.append(pg.PlotWidget(plotItem=self.amp_plot_item))
        self.amp_plot_list[-1].getAxis('left').setWidth(60)
        self.amp_plot_list[-1].setLimits(xMin=-5, xMax=int(self.fs*0.58), yMin=-0.1)

    def append_phase_plot(self):
        self.phase_plot_item = pg.PlotItem(viewBox=CustomViewBox(),
                                           name=f'phase_plot{self.count()}')
        self.phase_plot_item.setXLink(f'amp_plot{self.count()}')
        # self.phase_plot_item.setTitle('ФЧХ', size='12pt')  # Phase Graph
        self.phase_plot_item.showGrid(x=True, y=True)
        self.phase_plot_item.addLegend(offset=(-1, 1), labelTextSize='12pt',
                                       labelTextColor=pg.mkColor('w'))
        self.phase_plot_item.setLabel('left', 'Phase',
                                      units='degrees', **self.LABEL_STYLE)  # rad
        self.phase_plot_item.setLabel('bottom', 'Frequency',
                                      units='Hz', **self.LABEL_STYLE) # \u00b0
        for i in range(self.GYRO_NUMBER):
            self.phase_curves.append(self.phase_plot_item.plot(
                pen=self.COLOR_LIST[i], name=f"gyro {i + 1}", symbol="o",
                symbolSize=6, symbolBrush=self.COLOR_LIST[i]))
        self.phase_plot_list.append(
            pg.PlotWidget(plotItem=self.phase_plot_item))
        self.phase_plot_list[-1].getAxis('left').setWidth(60)
        self.phase_plot_list[-1].setLimits(
            xMin=-5, xMax=int(self.fs*0.58), yMin=-380, yMax=20)

    @QtCore.pyqtSlot(str)
    def save_plot_image(self, path):
        # self.logger.info("Save image")
        pyqtgraph.exporters.ImageExporter(
            self.time_plot_item).export(path + '_time_plot.png')
        for i in range(self.count() - 1):
            pyqtgraph.exporters.ImageExporter(
                self.amp_plot_list[i].getPlotItem()).export(
                    path + f'_amp_plot_{i + 1}.png')
            pyqtgraph.exporters.ImageExporter(
                self.phase_plot_list[i].getPlotItem()).export(
                    path + f'_phase_plot_{i + 1}.png')
        # self.logger.info("Saving complite")

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
#
###############################################################################
#
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


# if __name__ == "__main__":

#     app = QtWidgets.QApplication(sys.argv)
#     app.setStyle('Fusion')  # 'Fusion' ... QtWidgets.QStyle
#     window = MyWindow()
#     window.setWindowTitle("Gyro")
#     # window.resize(850, 500)
#     window.show()
#     sys.exit(app.exec())