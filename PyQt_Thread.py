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
    package_num_signal = QtCore.pyqtSignal(int)
    fft_data_signal = QtCore.pyqtSignal(bool)
    median_data_ready_signal = QtCore.pyqtSignal(list)
    # median_data_ready_signal = QtCore.pyqtSignal(str)
    warning_signal = QtCore.pyqtSignal(str)

    def __init__(self, gyro_number, READ_INTERVAL_MS, logger_name: str = ''):
        # QtCore.QThread.__init__(self)

        self.data_recieved_event = Event()
        # self.flag_recieve: bool = False

        super(SecondThread, self).__init__()
        self.logger = logging.getLogger(logger_name)
        self.GYRO_NUMBER = gyro_number
        self.READ_INTERVAL_MS = READ_INTERVAL_MS
        self.filename: list[str] = ["", ""]
        self.flag_measurement_start: bool = False
        self.rx: bytes = b''
        self.fft_data_current_cycle: np.ndarray = np.array([], dtype=np.float32)  # ???
        self.all_fft_data: np.ndarray = np.array([], dtype=np.float32)  # ???
        self.time_data: np.ndarray = np.array([], dtype=np.int32)
        # self.time_data = np.ndarray((1, 1 + 4*self.GYRO_NUMBER), dtype=np.int32)
        self.special_points: np.ndarray = np.empty((5, self.GYRO_NUMBER))

        self.bourder: np.ndarray = np.array([0, 0], dtype=np.uint32)
        self.k_amp = (np.ones(self.GYRO_NUMBER)).astype(np.float32)
        self.fs = 0
        # self.WAIT_TIME_SEC = 1
        self.WAIT_TIME_SEC = 0.6
        self.flag_sent: bool = False
        self.num_measurement_rows = 0
        self.total_cycle_num = 0  # !!!
        self.cycle_count = 1

        self.flag_all = False
        self.flag_by_name = False
        self.selected_files_to_fft: list[str] = []
        self.total_time: int = 0
        # self.folder = ''
        self.package_num = 0
        self.package_num_list: list = [0]

        self.filename_new = [''] * self.GYRO_NUMBER
        # self.filename_new = ['' for _ in range(self.GYRO_NUMBER)]
        self.POWERS = np.matrix(
            [(256 ** np.arange(4)[::-1])] * 4)
            # [(256 ** np.arange(4)[::-1]) for _ in range(4)])
        # self.time_data.resize(int(183 * 1000 * 1.5 * 10),
        #                           1 + 4*self.GYRO_NUMBER, refcheck=False)
        # import sys
        # print(sys.getsizeof(self.time_data))
        # print((self.time_data.dtype))
        # print((self.time_data.shape))
# -------------------------------------------------------------------------------------------------

    @QtCore.pyqtSlot()
    def run(self):
        self.cycle_count = 1
        temp = self.GYRO_NUMBER

        if self.flag_all:
            self.package_num = 0
            self.GYRO_NUMBER = 1
            self.k_amp.resize(self.GYRO_NUMBER)
            self.k_amp.fill(1)
            self.logger.info("flag_all")
            self.get_fft_from_folders(folder=os.getcwd())

        if self.flag_by_name:
            self.package_num = 0
            self.GYRO_NUMBER = 1
            self.k_amp.resize(self.GYRO_NUMBER)
            self.k_amp.fill(1)
            self.logger.info("flag_by_name")
            file = os.path.basename(self.selected_files_to_fft[0])
            last_str = list(filter(None, re.split("_|_|.txt", file)))
            name_part = (f'{last_str[0]}_{last_str[1]}_{last_str[2]}'
                         if len(last_str) >= 3 else file)
            folder = os.path.split(self.selected_files_to_fft[0])[0] + '/'  # меняем folder для сохранения в ту же папку!!!!
            # self.fft_filename = self.folder + name_part + \
            # self.fft_filename = folder + name_part + \
            self.filename_new[0] = folder + name_part  # а потом в методе save сделать название для fft
            self.fft_from_file_median(self.selected_files_to_fft)  #, self.fft_filename)

        if self.flag_measurement_start:
            self.package_num = 0
            self.logger.info("flag_measurement_start")
            self.k_amp.resize(self.GYRO_NUMBER)
            self.k_amp.fill(1)
            self.total_num_time_rows = 0  #
            self.count_fft_frame = 1
            self.current_delay = 0
            self.delay = self.WAIT_TIME_SEC * self.fs / self.READ_INTERVAL_MS
            self.flag_frame_start = False
            self.flag_sent = True

            self.package_num_list = [0]
            self.bourder.fill(0)
            self.fft_data_current_cycle.resize(
                (self.num_measurement_rows, 4, self.GYRO_NUMBER),
                refcheck=False)
            self.fft_data_current_cycle.fill(np.nan)
            self.all_fft_data.resize(
                (self.num_measurement_rows,
                 4 * (self.total_cycle_num + 1),
                 self.GYRO_NUMBER),
                refcheck=False)
            self.all_fft_data.fill(np.nan)

            # либо заранее с запасом выделять память, либо с отдельными цилками работать
            self.time_data.resize(int(self.total_time * self.fs * 1.5 * self.total_cycle_num),
                                  1 + 4*self.GYRO_NUMBER, refcheck=False)
        # while self.flag_measurement_start or self.flag_recieve:
            while self.flag_measurement_start:
                # QWaitCondition
                self.data_recieved_event.wait()
                # if not self.flag_recieve:  # добавить event
                    # self.msleep(10)
                if self.flag_measurement_start:
                # if self.flag_recieve:
                    self.get_ints_from_bytes()
                    self.package_num_signal.emit(self.package_num)
                    # self.flag_recieve = False
                    # пусть эта функция срабатывает всегда, даже если данных нет, поскольку ее поведение зависит в первую очередь от протокола измерений
                    self.make_3_fft_frame(encoder=self.time_data[:, 2],
                                        gyro_list=self.time_data[:, 1::4])
                                        # gyro=[self.time_data[i][:, 1 + 4*i]
                                            #   for i in range(self.GYRO_NUMBER)])
                    # self.make_fft_frame(encoder=self.time_data[:, 2],
                    #                     gyro=self.time_data[:, 1])
                self.data_recieved_event.clear()
            self.package_num_list.append(self.package_num)
        # self.time_data.resize(self.package_num,
                            #   1 + 4*self.GYRO_NUMBER, refcheck=False)
        self.logger.info("Start saving")
        if self.package_num:
            self.save_time_cycles()
        self.logger.info(self.fft_data_current_cycle.size)
        if (self.fft_data_current_cycle.size
            or self.flag_by_name) and not self.flag_all:   ### можно убрать другое сохранение, раз это уже есть
            self.save_fft()  # формировать имя
        self.flag_by_name = False
        self.flag_all = False
        self.GYRO_NUMBER = temp
        self.logger.info("Tread stop")

# -------------------------------------------------------------------------------------------------
#
# -------------------------------------------------------------------------------------------------

    def get_ints_from_bytes(self):
        self.logger.info("start matrix processing data frame")
        bytes_arr = np.frombuffer(self.rx, dtype=np.uint8)
        start = np.where(
            (bytes_arr[:-13] == 0x72) & (bytes_arr[13:] == 0x27))[0] + 1
        start = np.insert(start, start.size, start[-1] + 14)
        start = start[np.where(np.diff(start) == 14)[0]]
        expand = start.size
        array_r = np.zeros((expand, 4, 4), dtype=np.uint8)
        for i in range(4):
            for j in range(3):
                array_r[:, i, j] = bytes_arr[np.add(start, 3*i + j)]
        # self.time_data.resize(
            # self.package_num + expand, 1 + 4*self.GYRO_NUMBER, refcheck=False)
        self.time_data[self.package_num:self.package_num + expand, 0] = np.arange(
            self.package_num, expand + self.package_num)
        # self.logger.info(self.GYRO_NUMBER)

        for k in range(self.GYRO_NUMBER):  # !
            self.time_data[self.package_num:self.package_num + expand,
                           (1 + 4*k):(5 + 4*k)] = (
                               np.einsum("ijk,jk->ij", array_r, self.POWERS) / 256)
        self.package_num += expand
        self.logger.info("end matrix processing")
# -------------------------------------------------------------------------------------------------

    def save_time_cycles(self):
        self.logger.info("save time cycles!")
        for j in range(self.GYRO_NUMBER):
            if not len(self.filename_new[j]):
                self.logger.info("skip")
                continue  # ???  # continue
            if not os.path.isdir(os.path.dirname(self.filename_new[j])):
                self.logger.info(f"Folder {os.path.dirname(self.filename_new[i])} doesn't exist!")
                self.warning_signal.emit(f"Folder {os.path.dirname(self.filename_new[i])} doesn't exist!")
                continue
            for i in range(len(self.package_num_list) - 1):
                filename = check_name_simple(
                    f"{self.filename_new[j] }_{i + 1}.txt")
                self.logger.info(f"save cycle {filename}")
                time_data_df = DataFrame(
                    self.time_data[
                        self.package_num_list[i]:self.package_num_list[i + 1], :])
                time_data_df.to_csv(filename, columns=[0, 1 + 4*i, 2 + 4*i,
                                                       3 + 4*i, 4 + 4*i],
                                    header=None, index=None,
                                    sep='\t', mode='w', date_format='%d')
# -------------------------------------------------------------------------------------------------

    def save_fft(self):
        self.logger.info(f"names {self.filename_new}")
        filename_list_cycles = []
        sensor_numbers_list = []
        self.fft_approximation(round_flag=False)
        self.get_special_points()
        self.logger.info(
            f"total_cycle_num {self.total_cycle_num}, cycle_count {self.cycle_count}")
        for i in range(self.all_fft_data.shape[2]):
            if not len(self.filename_new[i]):
                self.logger.info("skip")
                continue
            if not os.path.isdir(os.path.dirname(self.filename_new[i])):
                self.logger.info(f"Folder {os.path.dirname(self.filename_new[i])} doesn't exist!")
                self.warning_signal.emit(f"Folder {os.path.dirname(self.filename_new[i])} doesn't exist!")
                continue
            if self.package_num:
                self.cycle_count = len(self.package_num_list) - 1  # если отдельно сохранять
            filename_new_for_fft = self.filename_new[i] + \
                f'%_{self.cycle_count}%_FRQ_AMP_dPh_{self.fs}Hz.txt'
            name_parts = re.split("\%", filename_new_for_fft)
            filename_cycles = check_name_simple(
                name_parts[0] + name_parts[1] + name_parts[2])

            self.logger.info(f"save fft file {filename_cycles}")
            # np.savetxt(filename_cycles,
                    # self.all_fft_data[:, :-4, i], delimiter='\t', fmt='%.3f')
                    #    self.amp_and_freq[:, :4*self.cycle_count], delimiter='\t', fmt='%.3f')  # возможно, так будет обрезать лишнее
            DataFrame(self.all_fft_data[:, :-4, i]).to_csv(
                filename_cycles, header=None, index=None,
                sep='\t', mode='w', float_format='%.3f', decimal=',')
            filename_median = check_name_simple(name_parts[0] + name_parts[2])
            # np.savetxt(filename_median,
                    # self.all_fft_data[:, -4:, i], delimiter='\t', fmt='%.3f') # 
            DataFrame(self.all_fft_data[:, -4:, i]).to_csv(
                filename_median, header=None, index=None,
                sep='\t', mode='w', float_format='%.3f', decimal=',')
            self.logger.info("end saving fft file")
            filename_list_cycles.append(os.path.basename(filename_median))
            sensor_numbers_list.append(
                re.split("_", filename_list_cycles[-1])[0])
        if len(filename_list_cycles):
            self.median_data_ready_signal.emit(sensor_numbers_list)
            self.warning_signal.emit(
                "Save files:\n" + ',\n'.join(filename_list_cycles) + '\n')
# -------------------------------------------------------------------------------------------------

    def new_cycle(self):  # добавить сброс числа пакетов, изменение имени файла и т.д.
        if self.flag_measurement_start:
            self.package_num_list.append(self.package_num)
        # self.k_amp.fill(1)
        # self.logger.info(self.total_cycle_num)
        if self.all_fft_data.shape[0] == self.fft_data_current_cycle.shape[0]:
            self.all_fft_data[:, 4*(self.cycle_count - 1):
                              4*self.cycle_count, :] = np.copy(
                                  self.fft_data_current_cycle)
            self.cycle_count += 1
        else:
            self.logger.info('wrong shape!')
        self.fft_data_current_cycle.fill(np.nan)
        # self.amp_and_freq[:, 4*self.cycle_count:(4*self.cycle_count + 4)] = self.amp_and_freq[:, 0:4]
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
            self.logger.info(f"\npath: {sensor_folder}")
            only_files = [f for f in os.listdir(sensor_folder)
                         if os.path.isfile(os.path.join(sensor_folder, f))]
            self.selected_files_to_fft = []
            for file in only_files:
                split_filename = list(filter(None, re.split("_|_|.txt", file)))
                if len(split_filename) == 4 and split_filename[1] != 'fresh':
                    self.selected_files_to_fft.append(sensor_folder + '/' + file)
                    last_filename = split_filename
            # sensor_folder + '/' добавлять это, чтобы сохранять в той же папке
            self.filename_new[0] = folder + \
                last_filename[0] + '_' + last_filename[1] + '_' +  last_filename[2]
            self.logger.info(f"files in folder: {self.selected_files_to_fft}")
            self.fft_from_file_median(self.selected_files_to_fft) #, self.fft_filename)
            self.logger.info("save fft")
            self.save_fft()
# -------------------------------------------------------------------------------------------------

    def fft_approximation(self, round_flag=True):
        for i in range(self.all_fft_data.shape[2]):
            if self.all_fft_data.shape[0] == self.fft_data_current_cycle.shape[0]:
                self.all_fft_data[:, 4*(self.cycle_count - 1):4*(self.cycle_count), i] = np.copy(
                    self.fft_data_current_cycle[:, :, i])
            else:
                self.logger.info('Different shape!')
            # нужна проверка на то, что все частоты +- совпадают, проще при создании массива проверять
            for k in range(self.all_fft_data.shape[0]):
                for j in range(4):
                    self.all_fft_data[k, j - 4, i] = np.nanmedian(self.all_fft_data[k, j::4, i])
            if round_flag:
                self.all_fft_data[:, -4, i] = np.round(self.all_fft_data[:, -4, i], 2)
                self.all_fft_data[:, -3, i] = np.round(self.all_fft_data[:, -3, i], 4)
            ###self.logger.info(f"\nall_fft_data = {self.all_fft_data}")    
# -------------------------------------------------------------------------------------------------

    def make_3_fft_frame(self, encoder: np.ndarray, gyro_list: np.ndarray):
        if not self.flag_sent:
            self.flag_frame_start = True
            if self.current_delay < self.delay:
                self.bourder[0] = self.package_num
            self.current_delay += 1
        if self.flag_frame_start and self.flag_sent:
            self.flag_frame_start = False
            # self.bourder[1] = self.package_num - int(self.fs / 20)  # frame end
            self.bourder[1] = self.package_num  # frame end
            self.current_delay = 0
            self.logger.info(f"old bourders = {self.bourder}")
            self.bourder = self.get_new_bourder(self.bourder, self.fs)  # !!!!!!!!!!!!!!!!!!!!!!!!
            self.logger.info(f"\tnew bourders = {self.bourder}")
            if all(self.bourder):
                for i in range(self.GYRO_NUMBER):
                    [freq, amp, d_phase] = get_fft_data(
                        gyro=gyro_list[self.bourder[0]:self.bourder[1], i],
                        encoder=encoder[self.bourder[0]:self.bourder[1]] * self.k_amp[i],
                        fs=self.fs)
                    [freq, amp, d_phase, tau] = self.fft_normalisation(freq, amp, d_phase, i)
                    self.fft_data_current_cycle[(
                        self.count_fft_frame - 1), :, i] = [freq, amp, d_phase, tau]
                self.fft_data_signal.emit(True)
            else:
                self.warning_signal.emit("Too small data frame!")
# -------------------------------------------------------------------------------------------------

    def get_special_points(self):
        self.special_points.resize((5, self.all_fft_data.shape[2]))
        self.special_points.fill(np.nan)
        self.special_points[-1, :] = 0
        f_180deg = -180
        for j in range(self.all_fft_data.shape[2]):
            i = np.where(
                (self.all_fft_data[:-1, -2, j] > f_180deg) &
                (self.all_fft_data[1:, -2, j] <= f_180deg))[0] + 1 #&
                # (np.roll(self.amp_and_freq[1:, -2], -1) <= f_180degrees)
            self.logger.info(i)
            if any(i):
                i = i[0]  # можно сделать цикл по всем i, если их несколько 
                self.logger.info(f'new {i}')
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
                self.logger.info(f"special_points = {self.special_points[:, j]}")
# -------------------------------------------------------------------------------------------------

    def fft_from_file_median(self, file_list: list):
        self.total_cycle_num = len(file_list)
        self.logger.info(f"total_cycle_num={self.total_cycle_num}")
        self.cycle_count = 1
        for file_for_fft in file_list:
            with open(file_for_fft) as f:
                if len(f.readline().split("\t")) == 4:
                    # сразу вывести график афчх средний
                    # можно сделать так, чтобы до трех разных датчиков можно было выбирать
                    self.all_fft_data = np.array(read_csv(f, delimiter='\t',
                                        dtype=np.float32, header=None,  #,
                                        index_col=False))
                    self.all_fft_data.resize(
                        self.all_fft_data.shape[0], self.all_fft_data.shape[1], 1)
                    self.get_special_points()
                    filename_list_median = [re.split("_", os.path.basename(file_for_fft))[0]]
                    self.median_data_ready_signal.emit(filename_list_median)
                    self.flag_all = True
                    break
                if len(f.readline().split("\t")) != 5:
                    self.logger.info(f"{f.readline()}")
                    self.warning_signal.emit(f"You choose wrong file!")
                    continue
            # self.k_amp[0] = 1
            self.fft_for_file(file_for_fft)
            if self.cycle_count == 1:
                self.all_fft_data.resize(
                    (self.fft_data_current_cycle.shape[0],
                    4 * (self.total_cycle_num + 1), self.GYRO_NUMBER),
                    refcheck=False)
                self.all_fft_data.fill(np.nan)
            if self.cycle_count != self.total_cycle_num:
                self.new_cycle()
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
        self.logger.info(f"start download {filename}")
        time_data = np.array(read_csv(
            filename, delimiter='\t', dtype=np.int32, 
            header=None, keep_default_na=False, na_filter=False,
            index_col=False, usecols=[1, 2]))  # чтение части столбцов
        #   usecols=[1, 2, 3, 4]))
        self.logger.info(f"1, end download, file len {time_data.size}")
        self.bool_arr = np.greater(
            np.abs(time_data[:, 2-1]), threshold).astype(np.float32)  # self, чтобы сохранять в случае чего
        self.bool_arr = np.convolve(
            self.bool_arr, const_filter, 'same') # работает
        self.bool_arr = np.convolve(
            self.bool_arr, g_filter, 'same') # 
        self.logger.info("2, convolve end")
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

        # self.logger.info(f"\nd start= {np.diff(start)}\nd  end = {np.diff(end)}")
        if start_arr.size != end_arr.size:
            self.warning_signal.emit(
                f"Problems with frame selection! ({os.path.basename(filename)})")  # !!!!!!!!!!!!!!!!!!!!!!!!!
            # np.savetxt('error_' + os.path.basename(filename),
                    #    self.bool_arr, delimiter='\t', fmt='%.3f')
        self.logger.info(f"\nstart= {start}\n end = {end}" +
                         f"\nstart arr= {start_arr}\n end  arr = {end_arr}")
        self.logger.info(
            f"3, len start = {start.size}, len start after = {start_arr.size}" +
            f"4, len end = {end.size}, len end after = {end_arr.size}")
        
        flag_first = True
        rows_count = min(end_arr.size, start_arr.size)
        self.fft_data_current_cycle.resize(
            (rows_count, 4, self.GYRO_NUMBER), refcheck=False)
        self.fft_data_current_cycle.fill(np.nan)
        # ind = np.where(start_arr[1:rows_count] < end_arr[:rows_count-1])
        # print(rows_count) # print(ind) # print(start)
        # if ind[0]:
        #     print(1111111)
        #     start[ind + 1] = end_arr[ind]
        # print(start)
        for i in range(rows_count):
            if i and start_arr[i] < end_arr[i - 1]:  # можно векторно проверять
                self.logger.info(f"!!! start[{i}]={start_arr[i]}, end[{i}]={end_arr[i]}")
                start_arr[i] = end_arr[i - 1]
            # self.logger.info(f"old bourders = {start_arr[i], end_arr[i]}")
            bourder = self.get_new_bourder([start_arr[i], end_arr[i]], self.fs)  # можно векторно округлить
            # self.logger.info(f"\tnew bourders = {bourder}")
            if all(bourder):
                [freq, amp, d_phase] = get_fft_data(
                    gyro=time_data[bourder[0]:bourder[1], 1-1],
                    encoder=time_data[bourder[0]:bourder[1], 2-1] * self.k_amp[0],
                    fs=self.fs)
                [freq, amp, d_phase, tau] = self.fft_normalisation(freq, amp, d_phase)
                self.fft_data_current_cycle[i, :, 0] = [freq, amp, d_phase, tau]
            else:
                if flag_first:
                    flag_first = False
                    self.warning_signal.emit(
                        f"Too small data frame! ({os.path.basename(filename)})")
                    # np.savetxt('error_' + os.path.basename(filename),
                    #    self.bool_arr, delimiter='\t', fmt='%.3f')
                else:
                    self.warning_signal.emit("Again...")
                self.logger.info(f"{[start_arr[i], end_arr[i]]}")
        self.logger.info(f"median noise {os.path.basename(filename)}, " +
                         f"{np.nanmedian(np.abs(np.diff(self.fft_data_current_cycle[:, 1, 0])))}")
        self.logger.info(
            np.nanmean(np.abs(np.diff(self.fft_data_current_cycle[:, 1, 0]))))
# -------------------------------------------------------------------------------------------------

    def fft_normalisation(self, freq, amp, d_phase, i=0):
        while not (-360 < d_phase <= 0 ):
            d_phase += (360 if d_phase < -360 else -360)
        if self.cycle_count == 1 and 1.5 > freq > 0.5 and amp > 0:
            if -200 < d_phase < -160:
                sign = -1
                d_phase += 180
            else:
                sign = 1
            self.k_amp[i] = amp * sign  #
            amp = 1
            self.logger.info(f"k_amp[{i}] = {self.k_amp[i]}")
        tau = -1000 * d_phase / freq / 360
        return [freq, amp, d_phase, tau]
# -------------------------------------------------------------------------------------------------

    @staticmethod
    def get_new_bourder(bourder, fs):
        # bourder[0] = bourder[1] - ((bourder[1] - bourder[0]) // self.fs) * self.fs
        bourder[1] = bourder[0] + ((bourder[1] - bourder[0]) // fs) * fs
        return ([0, 0] if (bourder[1] - bourder[0]) < fs else bourder)

    @staticmethod
    def find_value_between_points(point1, point2, value):
        x1, y1 = point1
        x2, y2 = point2
        result = y1 + ((y2 - y1) / (x2 - x1)) * (value - x1)
        return result # x

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


    # def fft_data(self, gyro: np.ndarray, encoder: np.ndarray, fs: int):
    #     """
    #     Detailed explanation goes here:
    #     amp [безразмерная]- соотношение амплитуд воздействия (encoder)
    #     и реакции гироскопа(gyro) = gyro/encoder
    #     d_phase [degrees] - разница фаз = gyro - encoder
    #     freq [Hz] - частота гармоники (воздействия)
    #     gyro [degrees/sec] - показания гироскопа во время гармонического воздействия
    #     encoder [degrees/sec] - показания энкодера, задающего гармоническое воздействие
    #     FS [Hz] - частота дискретизации
    #     """
    #     encoder = np.multiply(encoder, self.k_amp)

    #     L = len(gyro)  # длина записи
    #     next_power = np.ceil(np.log2(L))  # показатель степени 2 дл¤ числа длины записи
    #     NFFT = int(np.power(2, next_power))
    #     half = int(NFFT / 2)

    #     Yg = np.fft.fft(gyro, NFFT) / L  # преобразование Фурье сигнала гироскопа
    #     # Yg = np.fft.rfft(gyro, NFFT)/L  #
    #     Ye = np.fft.fft(encoder, NFFT) / L  # преобразование Фурье сигнала энкодера
    #     # Ye = np.fft.rfft(encoder, NFFT)/L  #
    #     f = fs / 2 * np.linspace(0, 1, half + 1, endpoint=True)  # получение вектора частот
    #     #  delta_phase = asin(2*np.mean(encoder1.*gyro1)/(np.mean(abs(encoder1))*np.mean(abs(gyro1))*pi^2/4))*180/pi
    #     ng = np.argmax(abs(Yg[0:half]))
    #     Mg = 2 * abs(Yg[ng])
    #     # freq = f[ne]  # make sence?

    #     ne = np.argmax(abs(Ye[0:half]))
    #     Me = 2 * abs(Ye[ne])
    #     freq = f[ne]
    #     # ###self.logger.info(f"\tne {ne}, Me {Me}\tng {ng}, Mg {Mg}")

    #     d_phase = np.angle(Yg[ng], deg=True) - np.angle(Ye[ne], deg=True)
    #     amp = Mg/Me
    #     ###self.logger.info(
    #         ####f"FFt results\t\tamp {amp}\tfreq {freq}")
    #         # f"FFt results\td_phase {d_phase}\tamp {amp}\tfreq {freq}")
    #     #  amp = std(gyro)/std(encoder)% пошуму (метод —урова)
    #     while not (-360 < d_phase <= 0 ):
    #         d_phase += (360 if d_phase < -360 else -360)

    #     if 1.5 > freq > 0.5 and amp > 0:
    #         if -200 < d_phase < -160:
    #             sign = -1
    #             d_phase += 180
    #         else:
    #             sign = 1
    #         ###self.logger.info(f"sign = {sign}")
    #         self.k_amp = amp * sign
    #         amp = 1
    #         self.logger.info(f"k_amp = {self.k_amp}")
        
    #     tau = -1000 * d_phase / freq / 360
    #     ###self.logger.info(f"FFt\td_phase {d_phase}\ttau {tau}")
    #     return [freq, amp, d_phase, tau]

        # def fft_approximation(self, freq, amp, phase,):
        # # freq_approximation = np.linspace(freq[0], freq[-1], num=100)
        # # order = 4
        # # k_list = np.polyfit(freq, amp, order)
        # # fun = np.poly1d(k_list)
        # # # np.roots(k_list)
        # # # amp_approximation = fun(freq_values)
        # # # f = [1, 5, 20, 50]
        # # # amp = [1, 0.9, 0.7, 0.2]
        # # # k_list = np.polyfit(f, amp, 5)
        # # # fun = np.poly1d(k_list)
        # # # R = np.roots(k_list)
        # # # freq_values = np.linspace(f[0], f[-1], 20)
        # # amp_approximation = np.array(fun(freq_approximation))
        # # abs_amp = np.abs(amp_approximation - 0.707)
        # # bandwidth_index = np.argmin(abs_amp)
        # # ###self.logger.info(
        # #     f"bandwidth_freq = {freq_approximation[bandwidth_index]}")
        # # # ###self.logger.info(bandwidth_index)
        # # # ###self.logger.info(amp_approximation[bandwidth_index])

        # # k_list = np.polyfit(freq, phase, order)
        # # fun = np.poly1d(k_list)
        # # phase_approximation = np.array(fun(freq_approximation))
        # # # f = np.deg2rad(f)
        # # phase_approximation = np.unwrap(phase_approximation)
        # # phase_approximation = np.rad2deg(phase_approximation)
        # # result = np.array([amp_approximation,
        # #                    phase_approximation, freq_approximation])