import pyqtgraph.examples
# pyqtgraph.examples.run()

# print(6456 // 2000)
import numpy as np
import re
# rx: bytes = b'\x05\xA1\x05\x05'
# arr = np.array(rx, dtype=type(rx))
# print(arr)
# # print(arr[0])
# i = np.arange(8 * 8).reshape(8, 8)
# # print(i)
# print(i.dtype)
# k = i.tobytes()
# # print(k)

# # y = np.frombuffer(k, dtype=i.dtype)
# y = np.frombuffer(rx, dtype=np.int32)
# print(y)
# import numpy as np
# arr = np.frombuffer(b'\xa3\x8eq\xb5', dtype=np.int32)
# arr = np.frombuffer(b'q\x10\x00\x00', dtype=np.int32)
# print(arr)
# import numpy as np

def bytes_to_int(byte1, byte2, byte3):
    byte4 = 0x00
    # byte_array = np.array([byte0, byte1, byte2, byte3], dtype=np.uint8)
    bytes_array = np.array([byte1, byte2, byte3, byte4], dtype=np.uint8)
    int_value = (np.dot(bytes_array, 256 ** np.arange(len(bytes_array))[::-1])).astype(np.int32)
    return (int_value / 256).astype(np.int32)
rx: bytes = b'\xFF\xFF\x00'
result = bytes_to_int(rx[0], rx[1], rx[2])
print(result) # 
# def parse_bytes_to_int(byte1, byte2, byte3):
#     # print(byte1)
#     # print(byte2)
#     # print(byte3)
#     # byte0 =
#     # byte_array = np.array([byte0, byte1, byte2, byte3], dtype=np.uint8)
#     byte_array = np.array([byte1, byte2, byte3], dtype=np.uint8)
#     int_value = np.frombuffer(byte_array.tobytes(), dtype=np.int32)
#     return int_value
    # return int(int_value[0])
# byte1 = 0b00000000 # 10 в двоичной системе
# byte2 = 0b00000000 # 150 в двоичной системе
# byte3 = 0b11111100 # 108 в двоичной системе
# byte1 = 0x00
# byte2 = 0x34
# byte3 = 0x56
# result = bytes_to_int(byte1, byte2, byte3)
# print(result) # Вывод: 292284
# result = bytes_to_int(rx[0], rx[1], rx[2])
# result = parse_bytes_to_int(rx[0], rx[1], rx[2])
# print(format(result, 'b')) # Вывод: 292284 
# print(bin(result)) # Вывод: 292284 format(decimal_num, 'b')
# a = np.array([[1, 4, 3], [5, 6, 7], [2, 8, 9]])
# print(a)
# # a = np.sort(a, axis=0)
# a = a[a[:, 0].argsort()]
# print(a)
# f = [1, 5, 20, 50]
# amp = [1, 0.9, 0.7, 0.2]
# k_list = np.polyfit(f, amp, 5)
# fun = np.poly1d(k_list)
# # R = np.roots(k_list)
# freq_values = np.linspace(f[0], f[-1], 20)
# amp_approximation = fun(freq_values)
# amp123 = np.abs(amp_approximation - 0.707)
# index = amp123.argmin()
# print(amp_approximation)
# # print(R)
# print(index)
# print(amp_approximation[index])

# print(f := np.deg2rad(f))
# f = np.unwrap(f)
# print(f)


# req("0|[1-9]\\d{0,4}")

# validator = QRegExpValidator(QRegExp("1[0-2]|[1-9]"), self)
# self.comboBox.setValidator(validator)
# p = np.array([[1, 4, 3], [5, 0, 7]])
# p = np.array([])
# print(p.size)

# print(np.greater(2, 5))
# print(np.greater(7, 5))

# p1 = np.array([1, 2])

# p2 = np.array([2, 4])
# p3 = np.array([2, 3])

# p4 = np.array([p1, p2, p3])
# # p3 = np.array([[p1], [p2]])
# print(p4)
# print(p4[0, :])
# print(p4[:, 1])
###############################################################################
def find_value_between_points(point1, point2, value):
    # Извлечение координат из точек
    x1, y1 = point1
    x2, y2 = point2

    # Формула нахождения значения между точками
    result = y1 + ((y2 - y1) / (x2 - x1)) * (value - x1)

    return result

point1 = (7, 3)
point2 = (8, 5)
value = 6

result = find_value_between_points(point1, point2, value)
# print(result)  # Результат: 5.0
###################################################################################

import sys
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QTextEdit, QVBoxLayout, QPushButton, QWidget

class SaveThread(QThread):
    finished = pyqtSignal()

    def __init__(self, data):
        super().__init__()
        self.data = data

    def run(self):
        with open('data.txt', 'w') as file:
            file.write('\n'.join(self.data))
        self.finished.emit()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.textedit = QTextEdit()
        self.savebtn = QPushButton('Save')
        self.savebtn.clicked.connect(self.saveData)

        layout = QVBoxLayout()
        layout.addWidget(self.textedit)
        layout.addWidget(self.savebtn)
        self.setLayout(layout)

    def saveData(self):
        data = self.textedit.toPlainText().split('\n')
        
        self.save_thread = SaveThread(data)
        self.save_thread.finished.connect(self.saveFinished)
        self.save_thread.start()

    def saveFinished(self):
        print('Data saved successfully.')
        self.savebtn.setEnabled(True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())