import logging
import os
import re
import numpy as np
from PyQt5 import QtCore
from pandas import read_csv, DataFrame
from threading import Event
from PyQt_Functions import get_fft_data, check_name_simple, custom_g_filter
# from numba import jit, prange, njit


class SecondThread(QtCore.QThread):
    # package_num_signal = QtCore.pyqtSignal(int)
    package_num_signal = QtCore.pyqtSignal(int, np.ndarray)
    fft_data_signal = QtCore.pyqtSignal(bool)
    median_data_ready_signal = QtCore.pyqtSignal(list)
    # median_data_ready_signal = QtCore.pyqtSignal(str)
    warning_signal = QtCore.pyqtSignal(str)

    def __init__(self, gyro_number, READ_INTERVAL_MS, logger_name: str = ''):
        # QtCore.QThread.__init__(self)

        self.data_recieved_event = Event()
        super(SecondThread, self).__init__()
        self.logger = logging.getLogger(logger_name)
        self.GYRO_NUMBER = gyro_number
        self.READ_INTERVAL_MS = READ_INTERVAL_MS
        self.filename: list[str] = ["", ""]
        self.flag_full_measurement_start: bool = False
        self.rx: bytes = b''
        self.all_fft_data: np.ndarray = np.array([], dtype=np.float32)  # ???
        self.time_data: np.ndarray = np.array([], dtype=np.int32)
        # self.time_data = np.ndarray((1, 1 + 4*self.GYRO_NUMBER), dtype=np.int32)
        self.special_points: np.ndarray = np.empty((5, self.GYRO_NUMBER))

        self.bourder: np.ndarray = np.array([0, 0], dtype=np.uint32)
        self.k_amp = np.ones(self.GYRO_NUMBER, dtype=np.float32)
        self.amp_shift = np.zeros(self.GYRO_NUMBER, dtype=np.float32)
        self.fs = 0
        # self.WAIT_TIME_SEC = 1
        self.WAIT_TIME_SEC = 0.7
        self.flag_sent: bool = False
        self.num_measurement_rows = 0
        self.total_cycle_num = 0  # !!!
        self.cycle_count = 1
        # 1/0
        self.flag_do_not_save = False
        self.flag_by_name = False
        self.selected_files_to_fft: list[str] = []
        self.total_time: int = 0
        # self.folder = ''
        self.package_num = 0
        self.package_num_list: list = [0]

        self.save_file_name = [''] * self.GYRO_NUMBER
        self.POWERS14_4 = np.matrix(
            [(256 ** np.arange(4)[::-1])] * 4)  # !
        self.POWERS14_2 = np.matrix(
            [(256 ** np.arange(4)[::-1])] * 2)  # !!
        self.POWERS20_2 = np.matrix(
            [(256 ** np.arange(4)[::-1])] * 6)  # !!
            # [(256 ** np.arange(4)[::-1])] * 4)
        # self.time_data.resize(int(183 * 1000 * 1.5 * 10),
        #                           1 + 4*self.GYRO_NUMBER, refcheck=False)
        # import sys
        # print(sys.getsizeof(self.time_data))
        # print((self.time_data.dtype))
        # print((self.time_data.shape))
        self.package_len = 18
        self.total_num_rows = 10_000
        self.flag_measurement_start = False
        self.flag_big_processing = False
        self.points_shown = 20_000
        self.package_len = 2
        # self.package_len = 4
        # print(get_fft_data(np.array([1, 1, 1, 1, 1, 1, 1, 1, 1]), np.array([0, 1, 2, 1, 0, -1, -2, -1, 0]), 9))
# -------------------------------------------------------------------------------------------------

    @QtCore.pyqtSlot()
    def run(self):
        temp = self.GYRO_NUMBER

        if self.flag_big_processing or self.flag_by_name:
            self.cycle_count = 1
            self.package_num = 0
            self.GYRO_NUMBER = 1
            self.k_amp.resize(self.GYRO_NUMBER)
            self.k_amp.fill(1)
            self.amp_shift.resize(self.GYRO_NUMBER)
            self.amp_shift.fill(0)

            if self.flag_do_not_save and self.flag_big_processing:
                self.logger.debug("do_not_save")  # добавить создание папки в текущей директории
                self.get_fft_from_folders(folder=os.getcwd())

            if self.flag_by_name:
                self.logger.debug("flag_by_name")
                file = os.path.basename(self.selected_files_to_fft[0])
                last_str = list(filter(None, re.split("_|_|.txt", file)))
                name_part = (f'{last_str[0]}_{last_str[1]}_{last_str[2]}'
                            if len(last_str) >= 3 else file)
                folder = os.path.dirname(self.selected_files_to_fft[0]) + '/'  # меняем folder для сохранения в ту же папку
                self.save_file_name[0] = folder + name_part
                self.fft_from_file_median(self.selected_files_to_fft)

        if self.flag_measurement_start or self.flag_full_measurement_start:
            self.points_shown = 20 * self.fs
            self.amp_shift.resize(self.GYRO_NUMBER)
            self.amp_shift.fill(0)
            # self.get_ints_from_bytes = self.get_ints_from_bytes14
            if self.GYRO_NUMBER == 1:  # !
                self.time_data.resize(
                    # self.total_num_rows, 1 + 2 * self.GYRO_NUMBER, refcheck=False)
                    self.total_num_rows, 1 + self.package_len, refcheck=False)
                if self.package_len == 4:
                    self.get_ints_from_bytes = self.get_ints_from_bytes14_4
                else:
                    self.get_ints_from_bytes = self.get_ints_from_bytes14_2
            if self.GYRO_NUMBER == 3:  # !
                self.time_data.resize(
                    self.total_num_rows, 1 + 2*self.GYRO_NUMBER, refcheck=False)
                self.get_ints_from_bytes = self.get_ints_from_bytes20_2

            if self.flag_measurement_start:
                self.package_num = 0
                self.count_fft_frame = 0
                self.logger.debug(f"flag_measurement_start {self.flag_measurement_start}")
                while self.flag_measurement_start:
                    self.data_recieved_event.wait(1)  # Timeout 1 sec!
                    if not self.data_recieved_event.is_set():
                        self.logger.debug("Timeout")
                    if self.flag_measurement_start:
                        self.get_ints_from_bytes()
                        self.prepare_to_emit()
                    self.data_recieved_event.clear()
                if self.package_num > 5 * self.fs:
                    self.amp_shift = np.mean(self.time_data[:5 * self.fs, 1::self.package_len], axis=0)
                else:
                    self.amp_shift = np.mean(self.time_data[:self.package_num, 1::self.package_len], axis=0)
                self.logger.debug(f"amp_shift = {self.amp_shift}")
                for i in range(self.GYRO_NUMBER):
                    if np.equal(self.amp_shift[i], -1):
                        self.amp_shift[i] = 0  # нет нужды тогда 0 выводить, -1 показательнее
                        self.warning_signal.emit(f"There is no data from gyro{i+1}!")
                self.package_num = 0
                # добавить проверку на -1
                # можно тут же проверять частоту дискретизации
                # желательно добавить пункт "не сохранять" на случай ошибки

            if self.flag_full_measurement_start:
                self.logger.debug(f"flag_full_measurement_start {self.flag_full_measurement_start}")
                self.cycle_count = 1
                self.package_num = 0
                self.k_amp.resize(self.GYRO_NUMBER)
                self.k_amp.fill(1)
                self.total_num_time_rows = 0  #
                self.count_fft_frame = 1
                self.required_delay = int(self.WAIT_TIME_SEC * self.fs)
                self.flag_frame_start = False
                self.flag_sent = True
                self.package_num_list = [0]
                self.bourder.fill(0)
                self.all_fft_data.resize(
                    (self.num_measurement_rows, 4 * (self.total_cycle_num + 1),
                    self.GYRO_NUMBER), refcheck=False)
                self.all_fft_data.fill(np.nan)
                # self.time_data.resize(
                    # self.total_num_rows, 1 + 4*self.GYRO_NUMBER, refcheck=False)

                while self.flag_full_measurement_start:
                    self.data_recieved_event.wait(1)  # Timeout 1 sec!
                    if not self.data_recieved_event.is_set():
                        self.logger.debug("Timeout")
                    if self.flag_full_measurement_start:
                        self.get_ints_from_bytes()
                        self.prepare_to_emit()
                        self.make_fft_frame(encoder=self.time_data[:, 2],
                                            gyro_list=self.time_data[:, 1::self.package_len])
                        self.logger.debug("end thread cycle\n")
                    self.data_recieved_event.clear()
                self.package_num_list.append(self.package_num)
        self.logger.debug(
            f"Start saving {(not self.flag_by_name and self.package_num) and not self.flag_do_not_save}")
        if self.package_num and not self.flag_do_not_save:
            self.save_time_cycles()
        if not self.flag_do_not_save:
            if (not self.flag_by_name and self.package_num) or self.flag_by_name:
                self.save_fft()  # формировать имя
        self.GYRO_NUMBER = temp
        self.flag_by_name = False
        self.flag_do_not_save = False
        self.logger.debug("Tread stop")

# -------------------------------------------------------------------------------------------------
#
# -------------------------------------------------------------------------------------------------

    def prepare_to_emit(self):
        start_i = (self.package_num - self.points_shown
            if self.package_num > self.points_shown else 0)
        self.logger.debug(f"prepare data to graph, {start_i}, {self.package_num}")
        array = (np.copy(self.time_data[start_i:self.package_num, :])).astype(np.float32)
        # я добавляю только 200 точек, логично именн их обрабатывать
        # (измерить, насколько быстро точки на график вывдятся)
        # мжно использовать roll или %, чтобы обращаться к другим индексам или take с mode="wrap"
        # сдвигать на размер пакета влево с помощью roll, а потом вставлять в конец нужные данные
        # можно сделать несколько режимов вывода, которые можно будет переключать
        array[:, 0] = array[:, 0] / self.fs
        # array[:, [1, 2, 3, 4]] = array[:, [2, 1, 3, 5]]
        # array[:, 1] = array[:, 1] / 1000
        array[:, 2] = array[:, 2] / 1000
        # array[:, 1:4] = array[:, 1::self.package_len] / 1000 / self.k_amp
        array[:, 1::self.package_len] = array[:, 1::self.package_len] / 1000 / self.k_amp
        # array[:, 1::self.pachage_len] = (array[:, 1::self.pachage_len] - self.amp_shift) / 1000 / self.k_amp
        self.time_data[:, 1::self.package_len] = self.time_data[:, 1::self.package_len] # !!!
        # self.time_data[:, 1::self.package_len] = self.time_data[:, 1::self.package_len] # !!!
        self.package_num_signal.emit(self.package_num, array)
        
    def get_ints_from_bytes(self):
        pass

    def get_ints_from_bytes14_4(self):
        self.logger.debug("start matrix processing data frame")
        bytes_arr = np.frombuffer(self.rx, dtype=np.uint8)
        start = np.where(
            (bytes_arr[:-13] == 0x72) & (bytes_arr[13:] == 0x27))[0] + 1
        if not start.size:
            self.warning_signal.emit("Check settings, inncorrect data from COM port!")
            self.logger.debug("Incorrect data in rx!")
            return
        start = np.insert(start, start.size, start[-1] + 14)
        start = start[np.where(np.diff(start) == 14)[0]]
        expand = start.size
        array_r = np.zeros((expand, 4, 4), dtype=np.uint8)
        for i in range(4):
            for j in range(3):
                array_r[:, i, j] = bytes_arr[np.add(start, 3*i + j)]
        # self.logger.debug(expand)
        if self.package_num + expand >= self.total_num_rows:
            self.total_num_rows += 10_000
            self.logger.debug("expand array")
            self.time_data.resize(self.total_num_rows, 1 + 4*self.GYRO_NUMBER, refcheck=False)  # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        self.time_data[self.package_num:self.package_num + expand, 0] = np.arange(
            self.package_num, self.package_num + expand)
        for k in range(self.GYRO_NUMBER):
            self.time_data[self.package_num:self.package_num + expand,
                           (1 + 4*k):(5 + 4*k)] = (
                               np.einsum("ijk,jk->ij", array_r, self.POWERS14_4) / 256)
        self.package_num += expand
        self.logger.debug("end matrix processing")

    def get_ints_from_bytes14_2(self):
        self.logger.debug("\n\nstart matrix processing data frame")
        bytes_arr = np.frombuffer(self.rx, dtype=np.uint8)
        start = np.where(
            (bytes_arr[:-13] == 0x72) & (bytes_arr[13:] == 0x27))[0] + 1
        if not start.size:
            self.logger.debug("Incorrect data in rx!")
            self.warning_signal.emit("Check settings, inncorrect data from COM port!")
            return
        start = np.insert(start, start.size, start[-1] + 14)
        start = start[np.where(np.diff(start) == 14)[0]]
        expand = start.size
        array_r = np.zeros((expand, 2, 4), dtype=np.uint8)
        for i in range(2):
            for j in range(3):
                array_r[:, i, j] = bytes_arr[np.add(start, 3*i + j)]
        self.logger.debug(expand)
        if self.package_num + expand >= self.total_num_rows:
            self.total_num_rows += 10_000
            self.logger.debug("expand array")
            self.time_data.resize(self.total_num_rows, 1 + 2*self.GYRO_NUMBER, refcheck=False)  # !!!!!!!!!!!!!!!!!!!!
        self.time_data[self.package_num:self.package_num + expand, 0] = np.arange(
            self.package_num, self.package_num + expand)
        self.time_data[self.package_num:self.package_num + expand, 1:3] = (
            np.einsum("ijk,jk->ij", array_r, self.POWERS14_2) / 256)
        self.package_num += expand
        self.logger.debug("end matrix processing")

    def get_ints_from_bytes20_2(self):
        self.logger.debug("\n\nstart matrix processing data frame")
        bytes_arr = np.frombuffer(self.rx, dtype=np.uint8)
        start = np.where(
            (bytes_arr[:-19] == 0x72) & (bytes_arr[19:] == 0x27))[0] + 1
        if not start.size:
            self.logger.debug("Incorrect data in rx!")
            self.warning_signal.emit("Check settings, inncorrect data from COM port!")
            return
        start = np.insert(start, start.size, start[-1] + 20)
        start = start[np.where(np.diff(start) == 20)[0]]
        expand = start.size
        array_r = np.zeros((expand, 6, 4), dtype=np.uint8)
        for i in range(6):
            for j in range(3):
                array_r[:, i, j] = bytes_arr[np.add(start, 3*i + j)]
        self.logger.debug(expand)
        if self.package_num + expand >= self.total_num_rows:
            self.total_num_rows += 15_000
            self.logger.debug("expand array")
            self.time_data.resize(self.total_num_rows, 1 + self.package_len*self.GYRO_NUMBER, refcheck=False)
        self.time_data[self.package_num:self.package_num + expand, 0] = np.arange(
            self.package_num, self.package_num + expand)
        for k in range(self.GYRO_NUMBER):  # !!!
            self.time_data[self.package_num:self.package_num + expand,
                           (1 + self.package_len*k):(1 + (self.package_len)*k + 2)] = (
                               np.einsum("ijk,jk->ij", array_r[:,2*k:2*k+2, :], self.POWERS14_2) / 256)
                            #    np.einsum("ijk,jk->ij", array_r, self.POWERS14_4) / 256)
        self.package_num += expand
        self.logger.debug("end matrix processing")
# -------------------------------------------------------------------------------------------------

    def save_time_cycles(self):
        self.logger.debug("save time cycles!")
        for j_gyro in range(self.GYRO_NUMBER):
            if not len(self.save_file_name[j_gyro]):
                self.logger.debug(f"skip gyro{j_gyro}")
                continue
            if not os.path.isdir(os.path.dirname(self.save_file_name[j_gyro])):
                self.logger.debug(
                    f"Folder {os.path.dirname(self.save_file_name[j_gyro])} doesn't exist!")
                self.warning_signal.emit(
                    f"Folder {os.path.dirname(self.save_file_name[j_gyro])} doesn't exist!")
                continue
            for i in range(len(self.package_num_list) - 1):
                filename = check_name_simple(
                    f"{self.save_file_name[j_gyro] }_{i + 1}.txt")
                self.logger.debug(f"save cycle {filename}")
                time_data_df = DataFrame(
                    self.time_data[
                        self.package_num_list[i]:self.package_num_list[i + 1], :])
                # k = 2  # !
                k = (self.time_data.shape[1] - 1) / self.GYRO_NUMBER
                self.logger.debug(f"k={k}")
                cols = np.array([0, *(k*j_gyro + np.arange(1, k + 1))])
                time_data_df.to_csv(
                    filename, columns=cols, header=None,
                    index=None, sep='\t', mode='w', date_format='%d')
# -------------------------------------------------------------------------------------------------

    def save_fft(self):
        self.fft_approximation(round_flag=False)
        if np.isnan(self.all_fft_data[:, -4, :]).all():
            self.logger.debug("FFT data contains only NaN")
            return
        self.logger.debug(f"names {self.save_file_name}")
        filename_list_cycles = []
        sensor_numbers_list = []
        self.get_special_points()
        self.logger.debug(
            f"total_cycle_num {self.total_cycle_num}, cycle_count {self.cycle_count}")
        for i in range(self.all_fft_data.shape[2]):
            if not len(self.save_file_name[i]):
                self.logger.debug(f"skip gyro{i}")
                continue
            if not os.path.isdir(os.path.dirname(self.save_file_name[i])):
                self.logger.debug(f"Folder {os.path.dirname(self.save_file_name[i])} doesn't exist!")
                self.warning_signal.emit(f"Folder {os.path.dirname(self.save_file_name[i])} doesn't exist!")
                continue
            if self.package_num:
                self.cycle_count = len(self.package_num_list) - 1  # если отдельно сохранять
            filename_cycles = self.save_file_name[i] + \
                f'_{self.cycle_count}_FRQ_AMP_dPh_{self.fs}Hz.txt'
            filename_cycles = check_name_simple(filename_cycles)

            self.logger.debug(f"save fft file {filename_cycles}")
                    #    self.amp_and_freq[:, :4*self.cycle_count], delimiter='\t', fmt='%.3f')  # возможно, так будет обрезать лишнее
            DataFrame(self.all_fft_data[:, :-4, i]).to_csv(
                filename_cycles, header=None, index=None,
                sep='\t', mode='w', float_format='%.3f', decimal=',')
            filename_median = self.save_file_name[i] + \
                f'_FRQ_AMP_dPh_{self.fs}Hz.txt'
            filename_median = check_name_simple(filename_median)
            DataFrame(self.all_fft_data[:, -4:, i]).to_csv(
                filename_median, header=None, index=None,
                sep='\t', mode='w', float_format='%.3f', decimal=',')
            self.logger.debug("end saving fft file")
            filename_list_cycles.append(os.path.basename(filename_median))
            sensor_numbers_list.append(
                re.split("_", filename_list_cycles[-1])[0])
        if len(filename_list_cycles):
            self.median_data_ready_signal.emit(sensor_numbers_list)
            self.warning_signal.emit(
                "Save files:\n" + ',\n'.join(filename_list_cycles) + '\n')
# -------------------------------------------------------------------------------------------------

    def new_measurement_cycle(self):
        # добавить сброс числа пакетов, изменение имени файла и т.д.
        self.package_num_list.append(self.package_num)
        self.cycle_count += 1
# -------------------------------------------------------------------------------------------------

    def fft_approximation(self, round_flag=True):
        for i in range(self.all_fft_data.shape[2]):
            # нужна проверка на то, что все частоты +- совпадают, проще при создании массива проверять
            for k in range(self.all_fft_data.shape[0]):
                for j in range(4):
                    self.all_fft_data[k, j - 4, i] = np.nanmedian(self.all_fft_data[k, j::4, i])
            if round_flag:
                self.all_fft_data[:, -4, i] = np.round(self.all_fft_data[:, -4, i], 2)
                self.all_fft_data[:, -3, i] = np.round(self.all_fft_data[:, -3, i], 4)
# -------------------------------------------------------------------------------------------------

    def make_fft_frame(self, encoder: np.ndarray, gyro_list: np.ndarray):
        if not self.flag_sent and not self.flag_frame_start: # пусть срабатывает только 1 раз
            self.flag_frame_start = True
            self.bourder[0] = self.package_num + self.required_delay
        elif self.flag_frame_start and self.flag_sent:
            self.flag_frame_start = False
            # self.bourder[1] = self.package_num - int(self.fs / 20)  # frame end
            # self.bourder[1] = self.package_num  # frame end
            self.bourder[1] = self.package_num - int(self.required_delay / 5)  # frame end  
            self.logger.debug(f"old bourders = {self.bourder}")
            self.bourder = self.get_new_bourder(self.bourder, self.fs)  # !!!!!!!!!!!!!!!!!!!!!!!!
            self.logger.debug(f"\tnew bourders = {self.bourder}")
            if all(self.bourder):
                for i in range(self.GYRO_NUMBER):
                    [freq, amp, d_phase] = get_fft_data(
                        # gyro=gyro_list[self.bourder[0]:self.bourder[1], i],
                        gyro=(gyro_list[self.bourder[0]:self.bourder[1], i] - self.amp_shift[i]),  # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                        # добавил сюда учет смещения
                        encoder=encoder[self.bourder[0]:self.bourder[1]] * self.k_amp[i],
                        fs=self.fs)
                    [freq, amp, d_phase, tau] = self.fft_normalisation(
                        freq, amp, d_phase, i=i)
                        # freq, amp, d_phase, d_phase_prev=self.all_fft_data[i-1, (self.cycle_count-1)*4, 0], i=i)
                    self.all_fft_data[(
                        self.count_fft_frame - 1), (self.cycle_count-1)*4:self.cycle_count*4, i
                        ] = [freq, amp, d_phase, tau]
                self.fft_data_signal.emit(True)
            else:
                self.warning_signal.emit("Too small data frame!")
# -------------------------------------------------------------------------------------------------

    def get_special_points(self):
        # добавить сюда же поиск пересечения с -360
        # (надо не сбрасывать, потому что тогда задержка будет неправильной)
        self.special_points.resize((5, self.all_fft_data.shape[2]))
        self.special_points.fill(np.nan)
        self.special_points[-1, :] = 0
        f_180deg = -180
        for j in range(self.all_fft_data.shape[2]):
            i = np.where(
                (self.all_fft_data[:-1, -2, j] > f_180deg) &
                (self.all_fft_data[1:, -2, j] <= f_180deg))[0] + 1 #&
                # (np.roll(self.amp_and_freq[1:, -2], -1) <= f_180degrees)
            self.logger.debug(i)
            if any(i):
                i = i[0]  # можно сделать цикл по всем i, если их несколько 
                self.logger.debug(f'new {i}')
                self.special_points[0, j] = self.find_value_between_points(
                    (self.all_fft_data[i - 1, -2, j], self.all_fft_data[i - 1, -4, j]),
                    (self.all_fft_data[i, -2, j], self.all_fft_data[i, -4, j]),
                    f_180deg)
                self.special_points[1, j] = self.find_value_between_points(
                    (self.all_fft_data[i - 1, -4, j], self.all_fft_data[i - 1, -3, j]),
                    (self.all_fft_data[i, -4, j], self.all_fft_data[i, -3, j]),
                    self.special_points[0, j])
                self.special_points[2:, j] = [
                    f_180deg, -1000 * f_180deg / self.special_points[0, j] / 360, i]
                self.logger.debug(f"special_points = {self.special_points[:, j]}")
# -------------------------------------------------------------------------------------------------

    def fft_from_file_median(self, file_list: list):
        self.total_cycle_num = len(file_list)
        self.logger.debug(f"total_cycle_num={self.total_cycle_num}")
        self.cycle_count = 1
        for file_for_fft in file_list:
            with open(file_for_fft) as f:
                line_len = len(f.readline().split("\t"))
                if line_len == 4:
                    self.get_exising_fft_file(file_for_fft)
                    break
                if line_len != 5 and line_len != 3:
                    self.logger.debug(f"{f.readline()}")
                    self.warning_signal.emit(f"You choose wrong file!")
                    continue
            self.fft_for_file(file_for_fft)
        self.cycle_count -= 1
# -------------------------------------------------------------------------------------------------

    def fft_for_file(self, filename: str, threshold: int = 5500):
        min_frame_len = 1.0 * self.fs  # сколько времени минимум длится вибрация + пауза, при 1 работало
        # min_frame_len = 1.5 * self.fs  # сколько времени минимум длится вибрация + пауза, при 1 работало
        filter_len = int(self.fs * 0.15) * 2 + 1
        # filter_len = int(self.fs * 0.1) * 2 + 1
        const_filter = (
            np.ones(filter_len) / filter_len * 1.5).astype(np.float32)
        g_filter = (
            custom_g_filter(len=25, k=0.0075) * 1).astype(np.float32)
        self.logger.debug(f"start download {filename}")
        time_data = np.array(read_csv(
            filename, delimiter='\t', dtype=np.int32, 
            header=None, keep_default_na=False, na_filter=False,
            index_col=False, usecols=[1, 2]))  # чтение части столбцов
        self.logger.debug(f"1, end download, file len {time_data.size}")
        self.bool_arr = np.greater(
            np.abs(time_data[:, 2-1]), threshold).astype(np.float32)  # self, чтобы сохранять в случае чего
        self.bool_arr = np.convolve(
            self.bool_arr, const_filter, 'same') # работает
        self.bool_arr = np.convolve(
            self.bool_arr, g_filter, 'same') # 
        self.logger.debug("2, convolve end")
        start = np.where(
            (self.bool_arr[:-1] <= 0.5) & (self.bool_arr[1:] > 0.5))[0]
        start_arr = np.where(np.diff(start) > min_frame_len)[0]
        start_arr = (np.insert(
            start[start_arr + 1], 0, start[0]) + int(0.015 * self.fs)).astype(np.int32)

        end = np.where(
            (self.bool_arr[:-1] >= 0.5) & (self.bool_arr[1:] < 0.5))[0]
        end_arr = np.where(np.diff(end) > min_frame_len)[0]
        end_arr = (np.insert(
            end[end_arr], end[end_arr].size, end[-1]) - int(0.015 * self.fs)).astype(np.int32)

        # self.logger.debug(f"\nd start= {np.diff(start)}\nd  end = {np.diff(end)}")
        if start_arr.size != end_arr.size:
            self.warning_signal.emit(
                f"Problems with frame selection! ({os.path.basename(filename)})")  # !!!!!!!!!!!!!!!!!!!!!!!!!
            # np.savetxt('error_' + os.path.basename(filename),
                    #    self.bool_arr, delimiter='\t', fmt='%.3f')
        self.logger.debug(f"\nstart= {start}\n end = {end}" +
                         f"\nstart arr= {start_arr}\n end  arr = {end_arr}")
        self.logger.debug(
            f"3, len start = {start.size}, len start after = {start_arr.size}" +
            f"4, len end = {end.size}, len end after = {end_arr.size}")
        
        rows_count = min(end_arr.size, start_arr.size)
        if self.cycle_count == 1:
            self.all_fft_data.resize(
                (rows_count, 4 * (self.total_cycle_num + 1), self.GYRO_NUMBER),
                refcheck=False)
            self.all_fft_data.fill(np.nan)
        elif rows_count != self.all_fft_data.shape[0]:
            self.logger.debug('wrong shape!')
            self.warning_signal.emit("Error in processing!")
            return
        # ind = np.where(start_arr[1:rows_count] < end_arr[:rows_count-1])
        # print(rows_count) # print(ind) # print(start)
        # if ind[0]:
        #     print(1111111)
        #     start[ind + 1] = end_arr[ind]
        # print(start)
        # можно добавить учет смещения по первым точкам гироскопа, будет точнее, чем совсем без него
        flag_first = True
        for i in range(rows_count):
            if i and start_arr[i] < end_arr[i - 1]:  # можно векторно проверять
                self.logger.debug(f"!!! start[{i}]={start_arr[i]}, end[{i}]={end_arr[i]}")
                start_arr[i] = end_arr[i - 1]
            # self.logger.debug(f"old bourders = {start_arr[i], end_arr[i]}")
            bourder = self.get_new_bourder([start_arr[i], end_arr[i]], self.fs)  # можно векторно округлить
            # self.logger.debug(f"\tnew bourders = {bourder}")
            if all(bourder):
                [freq, amp, d_phase] = get_fft_data(
                    gyro=time_data[bourder[0]:bourder[1], 1-1],
                    encoder=time_data[bourder[0]:bourder[1], 2-1] * self.k_amp[0],
                    fs=self.fs)
                [freq, amp, d_phase, tau] = self.fft_normalisation(
                    freq, amp, d_phase)
                    # freq, amp, d_phase, d_phase_prev=self.all_fft_data[i-1, (self.cycle_count-1)*4, 0])
                self.all_fft_data[
                    i, (self.cycle_count-1)*4:self.cycle_count*4, 0
                    ] = [freq, amp, d_phase, tau]
            else:
                if flag_first:
                    flag_first = False
                    self.warning_signal.emit(
                        f"Too small data frame! ({os.path.basename(filename)})")
                    # np.savetxt('error_' + os.path.basename(filename),
                    #    self.bool_arr, delimiter='\t', fmt='%.3f')
                else:
                    self.warning_signal.emit("Again...")
                self.logger.debug(f"{[start_arr[i], end_arr[i]]}")
        self.logger.debug(
            f"median noise {os.path.basename(filename)}, " +
            f"{np.nanmedian(np.abs(np.diff(self.all_fft_data[:, 1 + (self.cycle_count - 1) * 4, 0])))}")
        self.logger.debug(np.nanmean(np.abs(
            np.diff(self.all_fft_data[:, 1 + (self.cycle_count - 1) * 4, 0]))))
        self.cycle_count += 1
# -------------------------------------------------------------------------------------------------

    # def fft_normalisation(self, freq, amp, d_phase, d_phase_prev, i=0):
    def fft_normalisation(self, freq, amp, d_phase, i=0):
        while not (-360 < d_phase <= 0 ):
            d_phase += (360 if d_phase < -360 else -360)
        # if d_phase - d_phase_prev > 180:  # !
            # d_phase -= 360  # на перескок фазы плевать (задержка будет считать неверно)
        if self.cycle_count == 1 and 1.5 > freq > 0.5 and amp > 0:
            if -200 < d_phase < -160:
                sign = -1
                d_phase += 180
            else:
                sign = 1
            self.k_amp[i] = amp * sign  #
            amp = 1
            self.logger.debug(f"k_amp[{i}] = {self.k_amp[i]}")
        tau = -1000 * d_phase / freq / 360
        return [freq, amp, d_phase, tau]
# -------------------------------------------------------------------------------------------------

    @staticmethod
    def get_new_bourder(bourder: np.ndarray, fs: int):
        # bourder[0] = bourder[1] - ((bourder[1] - bourder[0]) // self.fs) * self.fs
        bourder[1] = bourder[0] + ((bourder[1] - bourder[0]) // fs) * fs
        return (np.array([0, 0]) if (bourder[1] - bourder[0]) < fs else bourder)

    @staticmethod
    def find_value_between_points(point1, point2, value):
        x1, y1 = point1
        x2, y2 = point2
        result = y1 + ((y2 - y1) / (x2 - x1)) * (value - x1)
        return result  # x
# -------------------------------------------------------------------------------------------------

    def get_fft_from_folders(self, folder):
        path = 'sensors_nums — копия.txt'
        sensor_list = read_csv(
            path, dtype=np.str, delimiter='\n', header=None)
        for sensor_number in sensor_list[0]:
            check = list(filter(None, re.split("\.|\n", sensor_number)))
            if len(check[-1]) < 3:
                sensor_num = check[-2] + "." + check[-1]
            elif len(check[-1]) == 4:
                sensor_num = check[-1]
            sensor_folder = '//fs/Projects/АФЧХ/' + sensor_num
            self.logger.debug(f"\npath: {sensor_folder}")
            only_files = [f for f in os.listdir(sensor_folder)
                         if os.path.isfile(os.path.join(sensor_folder, f))]
            self.selected_files_to_fft = []
            for file in only_files:
                split_filename = list(filter(None, re.split("_|_|.txt", file)))
                if len(split_filename) == 4 and split_filename[1] != 'fresh':
                    self.selected_files_to_fft.append(sensor_folder + '/' + file)
                    last_filename = split_filename
            # sensor_folder + '/' добавлять это, чтобы сохранять в той же папке
            self.save_file_name[0] = folder + \
                last_filename[0] + '_' + last_filename[1] + '_' +  last_filename[2]
            self.logger.debug(f"files in folder: {self.selected_files_to_fft}")
            self.fft_from_file_median(self.selected_files_to_fft) #, self.fft_filename)
            self.logger.debug("save fft")
            self.save_fft()
# -------------------------------------------------------------------------------------------------

    def get_exising_fft_file(self, file_for_fft):
        self.logger.debug("plot existing fft")
        # сразу вывести график афчх средний
        # можно сделать так, чтобы до трех разных датчиков можно было выбирать
        try:
            self.all_fft_data = np.array(
                read_csv(file_for_fft, delimiter='\t',
                         dtype=np.float32, header=None,  #,
                         index_col=False, decimal=","))
        except ValueError:  # на случай, если в файле в качестве разделителей точки
            self.all_fft_data = np.array(
                read_csv(file_for_fft, delimiter='\t',
                         dtype=np.float32, header=None,  #,
                         index_col=False, decimal="."))
        self.all_fft_data.resize(
            self.all_fft_data.shape[0], self.all_fft_data.shape[1], 1)
        self.get_special_points()
        filename_list_median = [re.split("_", os.path.basename(file_for_fft))[0]]
        self.median_data_ready_signal.emit(filename_list_median)
        self.flag_do_not_save = True
# ----------------------------------------------------------------------------
#
# ----------------------------------------------------------------------------
#
# ----------------------------------------------------------------------------


if __name__ == "__main__":
    import PyQt_ApplicationClass
    from PyQt5 import QtWidgets
    import sys
    app = QtWidgets.QApplication(sys.argv)
    window = PyQt_ApplicationClass.AppWindow()
    sys.exit(app.exec())



        # bytes_arr = np.frombuffer(self.rx, dtype=np.uint8)
        # self.logger.debug(self.rx)
        # # self.logger.debug(bytes_arr[:21])
        # self.logger.debug(f"len {len(self.rx)}")
        # start = np.where(
        #     (bytes_arr[:-(self.package_len+1)] == 0x72) & (bytes_arr[(self.package_len+1):] == 0x27))[0] + 1
        # self.logger.debug(f"srart {start}")
        # if not start.size:
        #     return
        # start = np.insert(start, start.size, start[-1] + self.package_len + 2)
        # start = start[np.where(np.diff(start) == self.package_len + 2)[0]]
        # # self.logger.debug(start)
        # expand = start.size
        # array_r = np.zeros((expand, int(self.package_len/3), 4), dtype=np.uint8)
        # for i in range(int(self.package_len/3)):  # число чисел в посылке
        #     for j in range(3):
        #         array_r[:, i, j] = bytes_arr[np.add(start, 3*i + j)]
        # self.time_data[
        #     self.package_num:self.package_num + expand, 0
        #     ] = np.arange(self.package_num, expand + self.package_num)
        # arr = np.einsum("ijk,jk->ij", array_r, self.POWERS) / 256
        # for k in range(self.GYRO_NUMBER):  # !!!
        #     self.time_data[
        #         # self.package_num:self.package_num + expand, (1 + 2*k)+2*k:(3 + 2*k)+2*k
        #         self.package_num:self.package_num + expand, 4*k + 1:4*k + 3
        #         ] = (arr[:, 2*k:2*k + 2])
        # self.package_num += expand