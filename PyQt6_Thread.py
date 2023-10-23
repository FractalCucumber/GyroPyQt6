from PyQt6 import QtCore
# import PyQt6.QtCore.QThread.pyqtSignalSlot
import numpy as np
from PyQt6.QtSerialPort import QSerialPort
import pyqtgraph as pg
import logging
import time


class MyThread(QtCore.QThread):
    sec_count = QtCore.pyqtSignal(int)
    # data = QtCore.pyqtSignal(int)

    def __init__(self):
        # QtCore.QThread.__init__(self)
        super(MyThread, self).__init__()
        self.filename = []
        self.flag_start = False
        self.flag_recieve = False
        self.package_num = 0
        self.rx: bytes = b''

        self.nums_united = np.array([], dtype=np.int32)

    def run(self):
        while self.flag_start:
            if self.flag_recieve:
                
                logging.info(f"thread_run_start, len {len(self.rx)}")
                package_num_prev = self.package_num
                # rx = self.rx
                i = self.rx.find(0x72)
                self.nums_united = np.array([], dtype=np.int32)
                
                # while (i + 13) < len(self.rx): # and (self.rx[i] == 0x72 and self.rx[i + 13] == 0x27):
                while (i + 13) < len(self.rx) and (self.rx[i] == 0x72 and self.rx[i + 13] == 0x27):
                    # if not (self.rx[i] == 0x72 and self.rx[i + 13] == 0x27):
                    #     i = self.rx.find(0x72)
                    #     if not self.rx[i + 13] == 0x27:
                    #         i += 14
                    #         logging.info("Error is squence")
                    #         continue

                    # check flag
                    nums = np.array([self.package_num], dtype=np.int32)

                    for shift in [1, 4, 7, 10]:
                        res = int.from_bytes(
                            self.rx[(i + shift):(i + shift + 3)],
                            byteorder='big', signed=True)
                        nums = np.append(nums, res)
                    i += 14

                    self.nums_united = np.append(self.nums_united, nums)
                    self.package_num += 1

                self.flag_recieve = False
                logging.info(f"len = {self.nums_united.size}")
                self.nums_united = np.reshape(
                    self.nums_united, [self.package_num - package_num_prev, 5])
                # print("dt_0 = ", time.time() - t1)
                with open(self.filename, 'a') as file:
                    np.savetxt(file, self.nums_united, delimiter='\t', fmt='%d')

                # self.time_plot.plot(
                #     nums_united[:, 0], nums_united[:, 2])
                    # t, velosity_amp, symbol='o', pen={'color': 0.8, 'width': 1})

                self.sec_count.emit(self.package_num)

                # print("dt = ", time.time() - t1)
                
            self.msleep(20)
        # self.rx = b''
