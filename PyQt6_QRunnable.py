from PyQt6 import QtCore
# import PyQt6.QtCore.QThread.Slot
import numpy
from PyQt6.QtCore import QRunnable, Qt, QThreadPool
from PyQt6.QtSerialPort import QSerialPort
import logging
import time


class Runnable(QRunnable):
    # def __init__(self, n):
    def __init__(self):
        super().__init__()
        self.Serial = QSerialPort()
        # self.n = n
        self.filename = []
        self.package_num = 0
        self.flag_read = False

    def run(self):

        # Your long-running task goes here ...
        while True:
            if self.flag_read:
                # logging.info(f"Working in thread")
                
                # self.Serial.open(QtCore.QIODevice.OpenModeFlag.ReadOnly)
                # self.Serial.waitForReadyRead(2000)
                print("--------------------Число байтов     " +
                    str(self.Serial.bytesAvailable()))
                logging.info(f"Bytes: {str(self.Serial.bytesAvailable())}")
                rx = self.Serial.readAll()
                # self.Serial.close()
    
                i = rx.data().find(0x72)           
                nums1 = numpy.array([])

                while (i + 13) < len(rx.data()) and rx.data()[i] == 0x72 and rx.data()[i + 13] == 0x27:
                    nums = numpy.array([self.package_num])

                    for shift in [1, 4, 7, 10]:
                        res = int.from_bytes(
                            rx.data()[(i + shift):(i + shift + 3)],
                            byteorder='big', signed=True)
                        nums = numpy.append(nums, res)
                    i += 14

                    # nums1 = numpy.append(nums1, nums)
                    nums1 = numpy.append(nums1, nums)
                    self.package_num += 1

                    with open(self.filename, 'a') as file:
                        file.write(str(nums[0]) + '\t' + str(nums[1]) + '\t' +
                                str(nums[2]) + '\t' + str(nums[3]) + '\t' +
                                str(nums[4]) + '\n')
                self.flag_read = False
                time.sleep(0.1)
                # self.sleep(0.1)
                # print("(rx")
                # self.sec_count.emit(self.package_num)
                # self.sec_count.emit(rx.data())

# class MyThread(QtCore.QThread):
#     sec_count = QtCore.pyqtSignal(bytearray)

#     def __init__(self, parent=None):
#         QtCore.QThread.__init__(self, parent)
#         self.Serial = QSerialPort()

#         self.filename = []
#         self.package_num = 0

#     def run(self):  # бесконечный цикл здесь должен быть
#         # try:
#         while True:
#             # self.sleep(1)
#             # if self.Serial.iread_until(10):
#             #     if self.Serial.read_until(10):
#             #         if self.Serial.waitForReadyWrite(10):

#             print("--------------------Число байтов" +
#                   str(self.Serial.bytesAvailable()))
#             # print(self.filename)
#             # ffff = self.Serial.bytesAvailable()
#             # Length = len(rx.data())
#             # print(Length)
#             # print("(rx.data())")
#             # if self.Serial.bytesAvailable() >= 14:
#             # if self.Serial.bytesAvailable() >= 14:

#             rx = self.Serial.readAll()
            
#             i = rx.data().find(0x72)

#             # print("-------------------- i = " + str(i))
            
#             nums1 = numpy.array([])
#             flag = rx.data()[i] == 0x72 and rx.data()[i + 13] == 0x27
#             while (i + 13) < len(rx.data()) and flag:
#                 nums = numpy.array([self.package_num])

#                 for shift in [1, 4, 7, 10]:
#                     res = int.from_bytes(
#                         rx.data()[(i + shift):(i + shift + 3)],
#                         byteorder='big', signed=True)
#                     nums = numpy.append(nums, res)
#                 i += 14

#                 # nums1 = numpy.append(nums1, nums)
#                 nums1 = numpy.append(nums1, nums)
#                 self.package_num += 1

#                 # numpy.savetxt(self.filename, nums, delimiter='  ', fmt="%d")
#                     # with open(self.filename, 'a') as file:
#                     #     file.write(str(nums[0]) + '\t' + str(nums[1]) + '\t' +
#                     #                str(nums[2]) + '\t' + str(nums[3]) + '\t' +
#                     #                str(nums[4]) + '\n')
#                 # with open("numpy.txt", 'a') as file:
#                     # file.writelines(
#                     #       numpy.array2string(nums1, separator='\t', fmt="%d"))
#                 # numpy.savetxt("text.txt", nums1, delimiter='\t', fmt="%d")
#                 # numpy.savetxt("np222", nums1, delimiter='   ', fmt="%d")
            
#                 # self.Serial.flush()
#                 # self.Serial.clear()
#                 # print("--------------")
#                 # print(numpy.array2string(nums1, separator='\t', fmt="%d"))
#                 # print(numpy.array2string(nums, separator='\t'))
#             # print((rx.data()))
#             # print("(rx")
#             # self.sec_count.emit(self.package_num)
#             self.sec_count.emit(rx.data())
#             self.Serial.clear()
#         # except:
#             # print(())
#             # print("(rx.dd())")
#         # else:
#         #     QtWidgets.QMessageBox.critical(
#         #               None, "", "Нет данных c COM порта")

        # self.Serial.close

# ----------------------------------------------------------------------------

    # def stop(self):
    #     self.Serial.write([0, 0, 0, 0, 0, 0, 0, 0])
