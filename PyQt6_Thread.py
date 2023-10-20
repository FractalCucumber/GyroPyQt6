from PyQt6 import QtCore
# import PyQt6.QtCore.QThread.pyqtSignalSlot
import numpy as np
from PyQt6.QtSerialPort import QSerialPort
import pyqtgraph as pg


class MyThread(QtCore.QThread):
    sec_count = QtCore.pyqtSignal(int)

    def __init__(self, block):
        # QtCore.QThread.__init__(self)
        super(MyThread, self).__init__()
        self.Serial = QSerialPort()
        self.filename = []
        self.package_num = 0
        self.rx: bytes = b''

        self.subblock1rightright = block

        self.time_plot = pg.plot()
        self.time_plot.showGrid(x=True, y=True)

        self.time_plot.addLegend()
        self.time_plot.setLabel('left', 'Velosity Amplitude', units='smth')
        self.time_plot.setLabel('bottom', 'Horizontal Values', units='smth')

        # self.scatter = pg.ScatterPlotItem(
        #     size=10, brush=pg.mkBrush(30, 255, 35, 255))
        
        # x_data = np.array([1, 4, 4, 4, 5, 6, 7, 8, 9, 10])
        # y_data = np.array([5, 4, 6, 4, 3, 5, 6, 6, 7, 8])

        # self.time_plot.plot(
        #     x_data, y_data, symbol='o', pen={'color': 0.8, 'width': 1}, name='first')
        
        # self.time_plot.ctrl.fftCheck.setChecked(True)
        self.time_plot.getPlotItem().ctrl.fftCheck.setChecked(False)
        
        self.subblock1rightright.addWidget(self.time_plot)

    def run(self):

        i = self.rx.find(0x72)
        nums_united = np.array([])

        while (i + 13) < len(self.rx) and self.rx[i] == 0x72 and self.rx[i + 13] == 0x27:
            nums = np.array([self.package_num])

            for shift in [1, 4, 7, 10]:
                res = int.from_bytes(
                    self.rx[(i + shift):(i + shift + 3)],
                    byteorder='big', signed=True)
                nums = np.append(nums, res)
            i += 14

            nums_united = np.append(nums_united, nums)
            self.package_num += 1

        print(f"len = {len(nums_united)}")
        nums_united = np.reshape(nums_united, [int(len(nums_united)/5), 5])
        # print(self.package_num)
        with open(self.filename, 'a') as file:
            np.savetxt(file, nums_united, delimiter='\t', fmt='%d')

        # graph
        self.time_plot.plot(
            nums_united[:, 0], nums_united[:, 2])
            # t, velosity_amp, symbol='o', pen={'color': 0.8, 'width': 1})

        self.sec_count.emit(self.package_num)

    def plot_change(self, text):
        if text == "FFT":
            self.time_plot.getPlotItem().ctrl.fftCheck.setChecked(False)
            self.time_plot.setLabel('bottom', 'Horizontal Values', units='smth')
            return "Time"
        else:
            self.time_plot.getPlotItem().ctrl.fftCheck.setChecked(True)
            self.time_plot.setLabel('bottom', 'Frequency', units='Hz')
            return "FFT"