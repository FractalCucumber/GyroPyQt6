from PyQt6 import QtCore
# import PyQt6.QtCore.QThread.Slot
import numpy
from PyQt6.QtSerialPort import QSerialPort
import time


class MyThread(QtCore.QThread):
    sec_count = QtCore.pyqtSignal(int)
    # end_signal = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.Serial = QSerialPort()

        self.filename = []
        self.package_num = 0
        self.rx: bytes = b''

    def run(self):

        # print("--------------------Число_байтов " +
        #         str(self.Serial.bytesAvailable()))
        # # print(self.filename)
        # # if self.Serial.bytesAvailable() >= 14:
        # if self.Serial.bytesAvailable() >= 14:

        i = self.rx.find(0x72)

        # print("-------------------- i = " + str(i))
        
        nums_united = numpy.array([])

        while (i + 13) < len(self.rx) and self.rx[i] == 0x72 and self.rx[i + 13] == 0x27:
            nums = numpy.array([self.package_num])

            for shift in [1, 4, 7, 10]:
                res = int.from_bytes(
                    self.rx[(i + shift):(i + shift + 3)],
                    byteorder='big', signed=True)
                nums = numpy.append(nums, res)
            i += 14

            nums_united = numpy.append(nums_united, nums)
            self.package_num += 1

            # with open(self.filename, 'a') as file:
            #     numpy.savetxt(file, [nums], delimiter='\t', fmt='%d')

        # print("len = " + str(len(nums_united)))
        nums_united = numpy.reshape(nums_united, [int(len(nums_united)/5), 5])
        # print(self.package_num)
        with open(self.filename, 'a') as file:
            numpy.savetxt(file, nums_united, delimiter='\t', fmt='%d')

        # self.end_signal.emit()
        self.sec_count.emit(self.package_num)
