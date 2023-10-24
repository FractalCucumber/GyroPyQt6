from PyQt6 import QtCore
# import PyQt6.QtCore.QThread.pyqtSignalSlot
import numpy as np
from PyQt6.QtSerialPort import QSerialPort
import pyqtgraph as pg
import logging
import time


class MyThread(QtCore.QThread):
    package_num_signal = QtCore.pyqtSignal(int)

    def __init__(self):
        # QtCore.QThread.__init__(self)
        super(MyThread, self).__init__()
        self.filename = []
        self.flag_start = False
        self.flag_recieve = False
        self.package_num = 0
        self.rx: bytes = b''

        self.all_data = np.array([], dtype=np.int32)
        self.ftt_data = np.array([]) #, dtype=np.complex128)

    def run(self):
        first = True
        while self.flag_start:
            if self.flag_recieve:

                i = self.rx.find(0x72)
                logging.info(f"thread_run_start, len {len(self.rx)}")

                if first:
                    first = False
                    self.all_data = np.array(
                        [self.int_from_bytes(self.rx, i, self.package_num)])
                    i += 14
                    
                    self.package_num += 1
                
                while ((i + 13) < len(self.rx)
                       and (self.rx[i] == 0x72 and self.rx[i + 13] == 0x27)):
                    # check flag
                    nums = np.array(
                        [self.int_from_bytes(self.rx, i, self.package_num)])
                    i += 14

                    self.all_data = np.vstack([self.all_data, nums])
                    self.package_num += 1

                self.flag_recieve = False
                logging.info(f"len = {self.all_data.size}")
                # print("dt_0 = ", time.time() - t1)

                self.package_num_signal.emit(self.package_num)
                
            self.msleep(10)
        with open(self.filename, 'a') as file:
            np.savetxt(file, self.all_data, delimiter='\t', fmt='%d')

    def fft_data(self):
        pass

    def int_from_bytes(self, rx, i, package_num):
        ints = np.array([package_num], dtype=np.int32)
        for shift in [1, 4, 7, 10]:
            res = int.from_bytes(
                rx[(i + shift):(i + shift + 3)],
                byteorder='big', signed=True)
            ints = np.append(ints, res)
        return ints
