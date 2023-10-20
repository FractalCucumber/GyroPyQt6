from PyQt6 import QtCore
# import PyQt6.QtCore.QThread.Slot
import numpy
from PyQt6.QtSerialPort import QSerialPort
import time


class MyThread(QtCore.QThread):
    sec_count = QtCore.pyqtSignal(bytes)

    def __init__(self, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.Serial = QSerialPort()

        self.filename = []
        self.package_num = 0
        self.rx = bytearray()

    def run(self):  # бесконечный цикл здесь должен быть
        # try:
        # print("RUN")
        # self.Serial.readyRead.connect(self.test_read_serial1)
        # self.Serial.readyRead.connect(self.test_read_serial1, QtCore.Qt.ConnectionType.SingleShotConnection)
        # self.sleep(1)

        # print("--------------------Число_байтов " +
        #         str(self.Serial.bytesAvailable()))
        # # print(self.filename)
        # # if self.Serial.bytesAvailable() >= 14:
        # if self.Serial.bytesAvailable() >= 14:

        i = self.rx.data().find(0x72)

        # print("-------------------- i = " + str(i))
        
        nums1 = numpy.array([])

        while (i + 13) < len(self.rx.data()) and self.rx.data()[i] == 0x72 and self.rx.data()[i + 13] == 0x27:
            nums = numpy.array([self.package_num])

            for shift in [1, 4, 7, 10]:
                res = int.from_bytes(
                    self.rx.data()[(i + shift):(i + shift + 3)],
                    byteorder='big', signed=True)
                nums = numpy.append(nums, res)
            i += 14

            # nums1 = numpy.append(nums1, nums)
            nums1 = numpy.append(nums1, nums)
            self.package_num += 1

            # numpy.savetxt(self.filename, nums, delimiter='  ', fmt="%d")
            with open(self.filename, 'a') as file:
                file.write(str(nums[0]) + '\t' + str(nums[1]) + '\t' +
                            str(nums[2]) + '\t' + str(nums[3]) + '\t' +
                            str(nums[4]) + '\n')
            # with open("numpy.txt", 'a') as file:
                # file.writelines(
                #       numpy.array2string(nums1, separator='\t', fmt="%d"))
            # numpy.savetxt("text.txt", nums1, delimiter='\t', fmt="%d")
            # numpy.savetxt("np222", nums1, delimiter='   ', fmt="%d")
        
            # self.Serial.flush()
            # self.Serial.clear()
            # print("--------------")
            # print(numpy.array2string(nums1, separator='\t', fmt="%d"))
            # print(numpy.array2string(nums, separator='\t'))
        # print((rx.data()))
        # print("(rx")
        # self.sec_count.emit(self.package_num)
        # self.sec_count.emit(rx.data())
            # self.sleep(0.02)
            # self.sleep(1)
            # except:
                # print(())
                # print("(rx.dd())")
            # else:
            #     QtWidgets.QMessageBox.critical(
            #               None, "", "Нет данных c COM порта")

            # self.Serial.close

# ----------------------------------------------------------------------------
    def test_read_serial1(self):
        print("before")
        # self.sleep(1)
        print("after")
    # def stop(self):
    #     self.Serial.write([0, 0, 0, 0, 0, 0, 0, 0])
