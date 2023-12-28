from PyQt5 import QtCore
import numpy as np
# from PyQt6.QtSerialPort import QSerialPort
# import pyqtgraph as pg
import logging
import os
from pandas import read_csv, DataFrame
import re


class MyThread(QtCore.QThread):
    package_num_signal = QtCore.pyqtSignal(int)
    fft_data_signal = QtCore.pyqtSignal(bool)
    median_data_ready_signal = QtCore.pyqtSignal(str)
    warning_signal = QtCore.pyqtSignal(str)

    def __init__(self, gyro_number=3, logger_name: str = ''):
        # QtCore.QThread.__init__(self)
        super(MyThread, self).__init__()
        self.GYRO_NUMBER = gyro_number
        self.filename: list[str] = ["", ""]
        self.flag_measurement_start: bool = False
        self.flag_recieve: bool = False
        self.rx: bytes = b''
        self.amp_and_freq_for_plot: np.ndarray = np.array([], dtype=np.float32)  # ???
        self.amp_and_freq: np.ndarray = np.array([], dtype=np.float32)  # ???
        self.k_amp = 1
        self.fs = 0
        self.TIMER_INTERVAL = 0
        # self.WAIT_TIME_SEC = 1
        self.WAIT_TIME_SEC = 0.6
        self.flag_sent: bool = False
        self.logger = logging.getLogger(logger_name)
        self.num_measurement_rows = 0
        self.total_cycle_num = 0  # !!!

        self.flag_all = False
        self.flag_by_name = False
        self.filenames_to_fft = []
        # self.name_list = ["6021_135_4.4_1.txt", "6021_135_4.4_2.txt",  # ], self.fs) 
        #                                "6021_135_4.4_9.txt", "6021_135_4.4_10.txt"]
        self.fft_filename = ''
        self.folder = ''
        self.package_num = 0
        self.package_num_list: list = [0]

        self.filename_new = ['', '', '']
        self.filename_new_for_fft = ['', '', '']

        self.POWERS = np.matrix(
            [(256 ** np.arange(4)[::-1]) for _ in range(4)])
# -------------------------------------------------------------------------------------------------

    def run(self):
        self.cycle_count = 1
        self.k_amp = 1
        temp = self.GYRO_NUMBER
        if self.flag_by_name:
            self.GYRO_NUMBER = 1
            self.logger.info("flag_by_name")
            self.folder = os.path.split(self.filenames_to_fft[0])[0] + '/'  # меняем folder для сохранения в ту же папку!!!!
            file = os.path.basename(self.filenames_to_fft[0])
            last_str = list(filter(None, re.split("_|_|.txt", file)))
            name_part = (f'{last_str[0]}_{last_str[1]}_{last_str[2]}'
                         if len(last_str) >= 3 else file)
            self.fft_filename = self.folder + name_part + \
                    f'%_{len(self.filenames_to_fft)}%_FRQ_AMP_dPh_{self.fs}Hz.txt'              
            self.fft_from_file_median(self.filenames_to_fft, self.fs)  #, self.fft_filename)

        if self.flag_all:
            self.GYRO_NUMBER = 1
            self.logger.info("flag_all")
            self.flag_all = False
            self.get_fft_from_folders()
            return

        if self.flag_measurement_start:
            self.package_num_list: list = [0]
            self.total_num_time_rows = 0  #
            self.package_num = 0
            self.time_data = np.ndarray((1, 5), dtype=np.int32)
            self.count_fft_frame = 1
            self.i = 0
            self.flag_frame_start = False
            self.flag_sent = True
            self.bourder = np.array([0, 0], dtype=np.uint32)
            self.amp_and_freq_for_plot.resize(
                (self.num_measurement_rows, 4))
            self.amp_and_freq_for_plot *= np.nan
            self.amp_and_freq.resize(
                (self.num_measurement_rows, 4 * (self.total_cycle_num + 1)))
            self.amp_and_freq *= np.nan

        while self.flag_measurement_start or self.flag_recieve:
            if not self.flag_recieve:
                self.msleep(5)

            if self.flag_recieve:
                self.logger.info("start matrix prosessing data frame")
                bytes_arr = np.frombuffer(self.rx, dtype=np.uint8)
                start = np.where(
                    (bytes_arr[:-13] == 0x72) & (bytes_arr[13:] == 0x27))[0] + 1
                start = np.insert(start, len(start), start[-1] + 14)
                start = start[np.where(np.diff(start) == 14)[0]]
                expand = len(start)
                array_r = np.zeros((expand, 4, 4), dtype=np.uint8)
                for i in range(4):
                    for j in range(3):
                        array_r[:, i, j] = bytes_arr[np.add(start, 3*i + j)]
                self.time_data.resize(self.package_num + expand, 5)
                self.time_data[self.package_num:, 0] = np.arange(
                    self.package_num, expand + self.package_num)
                self.time_data[self.package_num:, 1:] = (
                    np.einsum("ijk,jk->ij", array_r, self.POWERS) / 256)
                self.package_num += expand
                self.package_num_signal.emit(self.package_num)
                self.flag_recieve = False
                self.make_fft_frame(encoder=self.time_data[:, 2],  # пусть эта функция срабатывает всегда, даже если данных нет, поскольку ее поведение зависит в первую очередь от протокола измерений
                                    gyro=self.time_data[:, 1])
        if self.package_num:
            self.logger.info("save cycles!")
            self.save_time_cycles()
        # if self.cycle_count > 1:
        if (len(self.amp_and_freq_for_plot) or self.flag_by_name) and not self.flag_all:   ### можно убрать другое сохранение, раз это уже есть
            for i in range(self.GYRO_NUMBER):
                self.logger.info("save fft !")
                self.save_fft(  # проверять, есть ли такое имя уже
                    self.fft_filename)  # формировать имя
                    # self.filename[0] + f'%_{self.total_cycle_num}%_FRQ_AMP_dPh_{self.fs}Hz.txt')
            self.flag_by_name = False
        self.logger.info("Tread stop")
        self.GYRO_NUMBER = temp

# -------------------------------------------------------------------------------------------------
#
# -------------------------------------------------------------------------------------------------
    
    def save_time_cycles(self):
        self.package_num_list.append(self.package_num)
        for j in range(self.GYRO_NUMBER):
            for i in range(len(self.package_num_list) - 1):
                if not len(self.filename_new[j]):
                    continue
                self.logger.info(
                    f"save cycle {self.filename_new[j]}_{i + 1}.txt")
                time_data_df = DataFrame(
                    self.time_data[
                        self.package_num_list[i]:self.package_num_list[i + 1], :])
                filename = self.check_name_simple(
                    f"{self.filename_new[j] }_{i + 1}.txt")
                self.logger.info(filename)
                time_data_df.to_csv(filename,
                                    header=None, index=None,
                                    sep='\t', mode='w', date_format='%d')
# -------------------------------------------------------------------------------------------------

    def new_cycle(self):  # добавить сброс числа пакетов, изменение имени файла и т.д.
        # self.amp_and_freq[:, :4*(self.cycle_count - 2)] = np.copy(temp)
        if self.flag_measurement_start:
            self.package_num_list.append(self.package_num)
        # self.logger.info(self.total_cycle_num)
        if self.amp_and_freq.shape[0] == self.amp_and_freq_for_plot.shape[0]:
            self.amp_and_freq[:, 4*(self.cycle_count - 1):
                              4*self.cycle_count] = np.copy(
                                  self.amp_and_freq_for_plot)
            self.cycle_count += 1
            # self.amp_and_freq[:, 4*self.cycle_count:] = np.nan
        else:
            self.logger.info('bad shape')
        # ###self.logger.info(f"self.amp_and_freq all = {self.amp_and_freq}")
        self.amp_and_freq_for_plot = np.array([])
        # self.amp_and_freq[:, 4*self.cycle_count:(4*self.cycle_count + 4)] = self.amp_and_freq[:, 0:4]
# -------------------------------------------------------------------------------------------------

    def get_fft_from_folders(self):
        # path = 'sensors_nums2.txt'
        path = 'sensors_nums — копия.txt'
        sensor_list = read_csv(
            path, dtype=np.str, delimiter='\n', header=None)
        for sensor_number in sensor_list[0]:
            check = list(filter(None, re.split("\.|\n", sensor_number)))
            if len(check[-1]) < 3:
                sensor_num = check[-2] + "." + check[-1]
            if len(check[-1]) == 4:
                sensor_num = check[-1]
            mypath = '//fs/Projects/АФЧХ/' + sensor_num
            ###self.logger.info(f"\npath: {mypath}")
            onlyfiles = [f for f in os.listdir(mypath)
                         if os.path.isfile(os.path.join(mypath, f))]
            self.filenames_to_fft = []
            for file in onlyfiles:
                string = list(filter(None, re.split("_|_|.txt", file)))
                if len(string) == 4 and string[1] != 'fresh':
                    self.filenames_to_fft.append(mypath + '/' + file)
                    last_str = string
            ## mypath + '/' добавлять это, чтобы сохранять в той же папке
            self.fft_filename = self.folder + \
                last_str[0] + '_' + last_str[1] + '_' +  last_str[2] + \
                f'%_{len(self.filenames_to_fft)}%_FRQ_AMP_dPh_{self.fs}Hz.txt'
            self.logger.info(f"list: {self.filenames_to_fft}")
            self.fft_from_file_median(self.filenames_to_fft, self.fs) #, self.fft_filename)
            self.logger.info("save")
            self.save_fft(self.fft_filename)
# -------------------------------------------------------------------------------------------------
    
    def save_fft(self, name):
        # for i in range(self.GYRO_NUMBER):
            # self.filename_new_for_fft[i]
        name_parts = re.split("\%", name)
        self.logger.info(name_parts[0] + name_parts[1] + name_parts[2])
        self.fft_approximation(round_flag=False)
        self.get_special_points()
        self.median_data_ready_signal.emit(
            re.split("_", os.path.basename(
                name_parts[0] + name_parts[1] + name_parts[2]))[0])
            # list(filter(None, re.split("_", os.path.basename("D:\Gyro2023_Git\ddddd_3242_444"))))[0])
        self.logger.info("save fft file")
        filename = self.check_name_simple(name_parts[0] + name_parts[1] + name_parts[2])
        np.savetxt(filename,
                   self.amp_and_freq[:, :-4], delimiter='\t', fmt='%.3f')
                #    self.amp_and_freq[:, :4*self.cycle_count], delimiter='\t', fmt='%.3f')
        filename = self.check_name_simple(name_parts[0] + name_parts[2])
        np.savetxt(filename, 
                   self.amp_and_freq[:, -4:], delimiter='\t', fmt='%.3f') # , decimal=','
        self.logger.info("end saving fft file")
        self.warning_signal.emit(f"Save file {filename}\n")
# -------------------------------------------------------------------------------------------------

    def fft_approximation(self, round_flag=True):
        if self.amp_and_freq.shape[0] == self.amp_and_freq_for_plot.shape[0]:
            self.amp_and_freq[:,4*(self.cycle_count - 1):4*(self.cycle_count)] = np.copy(self.amp_and_freq_for_plot)
        else:
            self.logger.info('Different shape!')
        # нужна проверка на то, что все частоты +- совпадают, проще при создании массива проверять
        # ###self.logger.info(f"\namp_and_freq = {self.amp_and_freq}")
        for i in range(len(self.amp_and_freq[:, 1])):  # цикл по всем частотам
            for j in range(4):
                self.amp_and_freq[i, j - 4] = np.nanmedian(self.amp_and_freq[i, j::4])
        if round_flag:
            self.amp_and_freq[:, -4] = np.round(self.amp_and_freq[:, -4], 2)
            self.amp_and_freq[:, -3] = np.round(self.amp_and_freq[:, -3], 4)
        ###self.logger.info(f"\namp_and_freq = {self.amp_and_freq}")    
# -------------------------------------------------------------------------------------------------

    def make_fft_frame(self, encoder: np.ndarray, gyro: np.ndarray):
        if not self.flag_sent:
            self.flag_frame_start = True
            if self.i < self.WAIT_TIME_SEC * self.fs / self.TIMER_INTERVAL:
                self.bourder[0] = self.package_num
            self.i += 1
        if self.flag_frame_start and self.flag_sent:
            self.flag_frame_start = False
            # self.bourder[1] = self.package_num - int(self.fs / 20)  # frame end
            self.bourder[1] = self.package_num  # frame end
            self.i = 0
            # self.amp_and_freq_for_plot.resize(self.count_fft_frame, 4, refcheck=False)  # !!!!!!!!!!!!!!!!!!!!!!!!!
            self.logger.info(f"old bourders = {self.bourder}")
            self.bourder = self.get_new_bourder(self.bourder, self.fs)  # !!!!!!!!!!!!!!!!!!!!!!!!
            self.logger.info(f"\tnew bourders = {self.bourder}")
            if all(self.bourder):
                [freq, amp, d_phase, tau] = self.fft_data(
                    gyro=gyro[self.bourder[0]:self.bourder[1]],
                    encoder=encoder[self.bourder[0]:self.bourder[1]], fs=self.fs)
                self.amp_and_freq_for_plot[(
                    self.count_fft_frame - 1), :] = [freq, amp, d_phase, tau]
                self.fft_data_signal.emit(True)
            else:
                self.warning_signal.emit("Too small data frame!")
            # self.amp_and_freq[(self.count - 1),
            #                   4*(self.cycle_count - 1):
            #                   4*self.cycle_count] = [freq, amp, d_phase, tau]
            # self.amp_and_freq_for_plot = self.amp_and_freq_for_plot[self.amp_and_freq_for_plot[:, 2].argsort()]
# -------------------------------------------------------------------------------------------------

    def get_special_points(self):
        f_180deg = -180
        self.special_points = np.array(
            [np.nan, np.nan, np.nan, np.nan, np.nan])
        i = np.where(
            (self.amp_and_freq[:-1, -2] > f_180deg) &
            (self.amp_and_freq[1:, -2] <= f_180deg) #&
            # (np.roll(self.amp_and_freq[1:, -2], -1) <= f_180degrees)
            )[0] + 1
        self.logger.info(i)
        if any(i):
            i = i[0]
            self.logger.info(f'new {i}')
            self.special_points[0] = self.find_value_between_points(
                (self.amp_and_freq[i - 1, -2], self.amp_and_freq[i - 1, -4]),
                (self.amp_and_freq[i, -2], self.amp_and_freq[i, -4]),
                f_180deg)
            self.special_points[1] = self.find_value_between_points(
                (self.amp_and_freq[i - 1, -4], self.amp_and_freq[i - 1, -3]),
                (self.amp_and_freq[i, -4], self.amp_and_freq[i, -3]),
                self.special_points[0])
            self.special_points[2:] = [
                f_180deg, -1000 * f_180deg / self.special_points[0] / 360, i]
            self.logger.info(f"special_points = {self.special_points}")
# -------------------------------------------------------------------------------------------------

    def fft_from_file_median(self, file_list, fs):
        self.total_cycle_num = len(file_list)
        self.logger.info(f"total_cycle_num={self.total_cycle_num}")
        self.cycle_count = 1
        self.fs = fs
        for file_for_fft in file_list:
            with open(file_for_fft) as f:
                if len(f.readline().split("\t")) != 5:
                    self.logger.info(f"{f.readline()}")
                    self.warning_signal.emit(f"You choose wrong file!")
                    continue
            self.k_amp = 1
            self.logger.info(f"total_cycle_num={self.total_cycle_num} " +
                             f"cycle_count={self.cycle_count}")
            self.fft_for_file(file_for_fft)
            if self.cycle_count == 1:
                self.amp_and_freq.resize(
                    (int(self.amp_and_freq_for_plot.size / 4),
                    4 * (self.total_cycle_num + 1)))
                self.amp_and_freq *= np.nan
            if self.cycle_count != self.total_cycle_num:
                self.new_cycle()
        # self.save_fft(0, name)  ## в конце run сохранение есть
        # self.fft_approximation()
        # # self.get_special_points()
        # self.approximate_data_emit.emit(True)
# -------------------------------------------------------------------------------------------------

    def fft_for_file(self, filename: str, threshold: int = 5500):
        min_frame_len = 1.0 * self.fs  # сколько времени минимум длится вибрация + пауза, при 1 работало
        # min_frame_len = 1.5 * self.fs  # сколько времени минимум длится вибрация + пауза, при 1 работало
        # g_filter = self.custom_g_filter(len=47, k=0.0075) * 1.45
        filter_len = int(self.fs * 0.15) * 2 + 1
        const_filter = (
            np.ones(filter_len) / filter_len * 1.5).astype(np.float32)
        g_filter = (
            self.custom_g_filter(len=25, k=0.0075) * 1).astype(np.float32)
        self.logger.info(f"start download {filename}")
        # чтение части столбцов (возможно, лучше делать так)
        time_data = np.array(read_csv(filename, delimiter='\t',
                                      dtype=np.int32, header=None,  #,
                                      keep_default_na=False,
                                      na_filter=False,
                                      index_col=False,
                                      usecols=[1, 2, 3, 4]))
        self.logger.info(f"1, end download, file len {time_data.size}")
        self.bool_arr = np.greater(
            np.abs(time_data[:, 2-1]), threshold).astype(np.float32)  # self сделал, чтобы сохранять в конце
        ###self.logger.info("2")
        # arr = np.convolve(arr, self.custom_filter(45, 0.0075)*1.4, 'same')
        self.bool_arr = np.convolve(
            self.bool_arr, const_filter, 'same') # работает
        self.bool_arr = np.convolve(
            self.bool_arr, g_filter, 'same') # 
        # arr = np.convolve(arr, self.custom_filter(75, 0.005)*1.55, 'same') # работает
        self.logger.info("3, convolve end")
        start = np.where(
            (self.bool_arr[:-1] <= 0.5) & (self.bool_arr[1:] > 0.5))[0]
        start_arr = np.where(np.diff(start) > min_frame_len)[0]
        start_arr = np.insert(
            start[start_arr + 1], 0, start[0]) + int(0.015 * self.fs)

        end = np.where(
            (self.bool_arr[:-1] >= 0.5) & (self.bool_arr[1:] < 0.5))[0]
        end_arr = np.where(np.diff(end) > min_frame_len)[0]
        end_arr = np.insert(
            end[end_arr], len(end[end_arr]), end[-1]) - int(0.015 * self.fs)
        # self.logger.info(f"\nd start= {np.diff(start)}\nd  end = {np.diff(end)}")
        if len(start_arr) != len(end_arr):
            self.warning_signal.emit(
                f"Problems with frame selection! ({os.path.basename(filename)})")  # !!!!!!!!!!!!!!!!!!!!!!!!!
            np.savetxt('error_' + os.path.basename(filename),
                       self.bool_arr, delimiter='\t', fmt='%.3f')
        self.logger.info(f"\nstart= {start}\n end = {end}" +
                         f"\n\nstart arr= {start_arr}\n end  arr = {end_arr}")
        self.logger.info(
            f"4, len start = {len(start)}, len start after = {len(start_arr)}" +
            f"5, len end = {len(end)}, len end after = {len(end_arr)}")
        
        flag_first = True
        rows_count = min(len(end_arr), len(start_arr))
        self.amp_and_freq_for_plot.resize(rows_count, 4, refcheck=False)
        self.amp_and_freq_for_plot *= np.nan
        for i in range(rows_count):
            if i > 0:
                if start_arr[i] < end_arr[i - 1]:  # можно векторно проверять
                    ###self.logger.info(f"!!! start[{i}]={start_arr[i]}, end[{i}]={end_arr[i]}")
                    start_arr[i] = end_arr[i - 1]
            # self.logger.info(f"old bourders = {start_arr[i], end_arr[i]}")
            bourder = self.get_new_bourder([start_arr[i], end_arr[i]], self.fs)  # можно векторно округлить
            # self.logger.info(f"\tnew bourders = {bourder}")
            if all(bourder):
                [freq, amp, d_phase, tau] = self.fft_data(
                    gyro=time_data[bourder[0]:bourder[1], 1-1],
                    encoder=time_data[bourder[0]:bourder[1], 2-1], fs=self.fs)
                ###self.logger.info(f"start[{i}]={bourder[0]}, end[{i}]={bourder[1]}")
                self.amp_and_freq_for_plot[i, :] = [freq, amp, d_phase, tau]
            else:
                if flag_first:
                    self.warning_signal.emit(
                        f"Too small data frame! ({os.path.basename(filename)})")
                    flag_first = False
                    np.savetxt('error_' + os.path.basename(filename),
                       self.bool_arr, delimiter='\t', fmt='%.3f')
                else:
                    self.warning_signal.emit("Again...")
                    self.logger.info(f"{[start_arr[i], end_arr[i]]}")
        ###self.logger.info(f"\n fft end for {filename}")
        # print(os.path.basename(filename), np.nanmedian(np.diff(self.amp_and_freq_for_plot[:, 1])))
        self.logger.info(f"median noise {os.path.basename(filename)}, " +
                         f"{np.nanmedian(np.abs(np.diff(self.amp_and_freq_for_plot[:, 1])))}")
        self.logger.info(
            np.nanmean(np.abs(np.diff(self.amp_and_freq_for_plot[:, 1]))))
# -------------------------------------------------------------------------------------------------

    @staticmethod
    def custom_g_filter(len, k):
        if not len % 2:
            len = len + 1
        custom_filter = np.ndarray((len))
        custom_filter[int((len - 1)/2)] = 1
        for i in range(int((len - 1)/2)):  # можно сделать через np
            custom_filter[int((len - 1)/2) - 1 - i] = np.exp(-k * np.power((i + 1), 2))
            custom_filter[int((len - 1)/2) + 1 + i] = custom_filter[int((len - 1)/2) - 1 - i]
        custom_filter = custom_filter/np.sum(custom_filter)
        return custom_filter

    @staticmethod
    def get_new_bourder(bourder, fs):
        # bourder[0] = bourder[1] - ((bourder[1] - bourder[0]) // self.fs) * self.fs
        bourder[1] = bourder[0] + ((bourder[1] - bourder[0]) // fs) * fs
        # if (bourder[1] - bourder[0]) < fs:
        #     return [0, 0]
        # # ###self.logger.info(f"before")
        # return bourder
        return ([0, 0] if (bourder[1] - bourder[0]) < fs else bourder)

    @staticmethod
    def find_value_between_points(point1, point2, value):
        x1, y1 = point1
        x2, y2 = point2
        result = y1 + ((y2 - y1) / (x2 - x1)) * (value - x1)
        return result

    @staticmethod
    def check_name_simple(name):
        basename = os.path.splitext(name)[0]
        extension = os.path.splitext(name)[1]
        i = 0
        while os.path.exists(name):
            i += 1
            name = basename + f"({i})" + extension
        return name
# -------------------------------------------------------------------------------------------------

    # не могу сделать статическим из-за k_amp, можно просто вынести коэффициент
    def fft_data(self, gyro: np.ndarray, encoder: np.ndarray, fs: int):
        """
        Detailed explanation goes here:
        amp [безразмерная]- соотношение амплитуд воздействия (encoder)
        и реакции гироскопа(gyro) = gyro/encoder
        d_phase [degrees] - разница фаз = gyro - encoder
        freq [Hz] - частота гармоники (воздействия)
        gyro [degrees/sec] - показания гироскопа во время гармонического воздействия
        encoder [degrees/sec] - показания энкодера, задающего гармоническое воздействие
        FS [Hz] - частота дискретизации
        """
        encoder = np.multiply(encoder, self.k_amp)

        L = len(gyro)  # длина записи
        next_power = np.ceil(np.log2(L))  # показатель степени 2 дл¤ числа длины записи
        NFFT = int(np.power(2, next_power))
        half = int(NFFT / 2)

        Yg = np.fft.fft(gyro, NFFT) / L  # преобразование Фурье сигнала гироскопа
        # Yg = np.fft.rfft(gyro, NFFT)/L  #
        Ye = np.fft.fft(encoder, NFFT) / L  # преобразование Фурье сигнала энкодера
        # Ye = np.fft.rfft(encoder, NFFT)/L  #
        f = fs / 2 * np.linspace(0, 1, half + 1, endpoint=True)  # получение вектора частот
        #  delta_phase = asin(2*np.mean(encoder1.*gyro1)/(np.mean(abs(encoder1))*np.mean(abs(gyro1))*pi^2/4))*180/pi
        ng = np.argmax(abs(Yg[0:half]))
        Mg = 2 * abs(Yg[ng])
        # freq = f[ne]  # make sence?

        ne = np.argmax(abs(Ye[0:half]))
        Me = 2 * abs(Ye[ne])
        freq = f[ne]
        # ###self.logger.info(f"\tne {ne}, Me {Me}\tng {ng}, Mg {Mg}")

        d_phase = np.angle(Yg[ng], deg=True) - np.angle(Ye[ne], deg=True)
        amp = Mg/Me
        ###self.logger.info(
            ####f"FFt results\t\tamp {amp}\tfreq {freq}")
            # f"FFt results\td_phase {d_phase}\tamp {amp}\tfreq {freq}")
        #  amp = std(gyro)/std(encoder)% пошуму (метод —урова)
        while not (-360 < d_phase <= 0 ):
            d_phase += (360 if d_phase < -360 else -360)

        if 1.5 > freq > 0.5 and amp > 0:
            if -200 < d_phase < -160:
                sign = -1
                d_phase += 180
            else:
                sign = 1
            ###self.logger.info(f"sign = {sign}")
            self.k_amp = amp * sign
            amp = 1
            self.logger.info(f"k_amp = {self.k_amp}")
        
        tau = -1000 * d_phase / freq / 360
        ###self.logger.info(f"FFt\td_phase {d_phase}\ttau {tau}")
        return [freq, amp, d_phase, tau]
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
    # window.resize(850, 500)
    sys.exit(app.exec())

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
    
    # def fft_for_file(self, filename: str):
    #     # sz = 53 * os.path.getsize(filename)
    #     ###self.logger.info(f"start download")
    #     time_data = np.array(read_csv(filename, delimiter='\t', dtype=int, header=None))
    #     ###self.logger.info(f"end download, file len {len(time_data)}")
    #     # for i in range(int(len(matrix)/5 - 1)):
    #     # k = 1
    #     # k2 = 0
    #     # num = 1
    #     # flag = True
    #     # flag_start = False
    #     # # bourder: list[int] = [0, 0]
    #     # bourder: np.ndarray = np.array([0, 0], dtype=int)
    #     # threshold = 6000
    #     arr = np.greater(abs(time_data[:, 2]), threshold)
    #     # arr = np.array([time_data[:, 0], np.greater(time_data[:, 2], threshold)])

    #     # print(np.where(arr == 1)[0][0])
    #     # print(np.where(arr == 1)[0][1])
    #     # print(np.where(arr == 1)[0][2])

    #     # print(np.where(arr == 1)[0])
    #     # ones = np.where(arr == 1)
    #     # k = 0 
    #     # while ones[0][k] != ones[0][k + 1]:
    #     #     k + 1
    #     # i = ones[0][k - 1]
    #     # if ones[0][0]:
    #         # pass
    #     # while i < len(arr):
    #     #     pass
    #     #     if sum(arr[i:i+self.fs]) > 0.95:
    #     #         start = i
    #     #     i += self.fs

    #     # ###self.logger.info("222")
    #     # with open(self.filename[0] + f'BBBB{self.cycle_count}' +
    #     #         self.filename[1], 'w') as file:
    #     #     np.savetxt(file, arr,
    #     #         delimiter='\t', fmt='%.3f')
    #     ###self.logger.info("2221")
    #     # arr = (np.convolve(arr, np.array([0.0125, 0.0125, 0.025, 0.025, 0.025, 0.0375, 0.05, 0.0625, 0.0625, 0.075, 0.075,
    #                                     #   0.075,
    #                                     #   0.075, 0.075, 0.0625, 0.0625, 0.05, 0.0375, 0.025, 0.025, 0.025, 0.0125, 0.0125]) * 1.23, 'same'))
    #     # arr = np.convolve(arr, self.custom_filter(45, 0.0075)*1.4, 'same')
    #     arr = np.convolve(arr, self.custom_filter(55, 0.0065)*1.45, 'same')
    #     # можно шире, более размыто и умножать на больший коэффициент
    #     ###self.logger.info("2223") # 
    #     arr = np.round(arr)
    #     ###self.logger.info("2225")
    #     start = np.where((arr[:-1] == 0) & (arr[1:] == 1))[0]
    #     end = np.where((arr[:-1] == 1) & (arr[1:] == 0))[0]
        
    #     # print(start)
    #     # print(end)
    #     # with open(self.filename[0] + f'round{self.cycle_count}' +
    #     #         self.filename[1], 'w') as file:
    #     #      np.savetxt(file, arr,
    #     #         delimiter='\t', fmt='%.3f')
    #     ###self.logger.info("2227")
    #     # k = 1
    #     d = np.diff(start)
    #     # print(f"d = {d}")
    #     real_start = np.where(d > self.fs)[0]
    #     d = np.diff(end)
    #     # print(f"d end = {d}")

    #     real_end = np.where(d > self.fs)[0]
    #     # print(f"real_end = {end[real_end]}")  # + fistr start
    #     # for i in real:
    #     # print(start[real-1])
    #     # print(end[real-1])
    #     # print(start[real+1])  # + fistr start
    #     start_arr = np.insert(start[real_start+1], 0, start[0])
    #     # print(start_arr)  # + fistr start
    #     # print(len(start_arr))

    #     # end_arr = end[real]
    #     # print(len(end_arr))
    #     end_arr = np.insert(end[real_end], len(end[real_end]), end[-1])
    #     # print(end_arr) # + last end
    #     # print(len(end_arr))
    #     # print(end[real+1])
    #     for i in range(len(end_arr)):
    #         [freq, amp, d_phase, tau] = self.fft_data(
    #             gyro=time_data[start_arr[i]:end_arr[i], 1],
    #             encoder=time_data[start_arr[i]:end_arr[i], 2], fs=self.fs)
    #         # ###self.logger.info(f"now, num = {num}")
    #         # self.check_180_degrees(freq, amp, d_phase)
    #         # self.amp_and_freq_for_plot = np.resize(
    #         #     self.amp_and_freq_for_plot, (self.count + self.add_points, 4))
    #         self.amp_and_freq_for_plot.resize(i+1, 4)  # !!!!!!!!!!!!!!!!!!!!!!!!!
    #         self.amp_and_freq_for_plot[(i), :] = [freq, amp, d_phase, tau]
    #     ###self.logger.info(f"\n !!!!!!!!!!!!!!!!!! {filename}")
    #     # print(start)
    #     # print(len(start))
    #     # print(end)
    #     # print(len(end))
            # print(np.unique(time_data[1:2000, 2], return_counts=True))
            # print(np.unique(time_data[6000:8000, 2], return_counts=True))
        # print("end" + str(bourder))

        # if all(self.new_bourder(bourder)):
        #     [freq, amp, d_phase, tau] = self.fft_data(
        #         gyro=time_data[bourder[0]:bourder[1], 1],
        #         encoder=time_data[bourder[0]:bourder[1], 2], fs=self.fs)
        #     # ###self.logger.info(f"now, num = {num}")
        #     # self.check_180_degrees(freq, amp, d_phase)
        #     # self.amp_and_freq_for_plot = np.resize(
        #     #     self.amp_and_freq_for_plot, (self.count + self.add_points, 4))
        #     self.amp_and_freq_for_plot.resize(num, 4)  # !!!!!!!!!!!!!!!!!!!!!!!!!
        #     self.amp_and_freq_for_plot[(
        #         num - 1), :] = [freq, amp, d_phase, tau]
        # print(f"num={num}, {bourder}, {[freq, amp, d_phase, tau]}")
        # print(self.amp_and_freq_for_plot)
        # print(f"{time_data[i, 3]}, {time_data[i + 1, 3]}, {i}, amp = {time_data[i, 4]}")
    

        # g_filter = np.ones(255) * 57
        # ffff = np.array(self.custom_g_filter(len=25, k=0.0075)) * 10000
        # # print(ffff.size)
        # # f2 = (int(ffff )).astype(np.uint32)
        # f2 = ((ffff)).astype(np.uint32)
        # # f1 = (int(g_filter)).astype(np.uint32)
        # f1 = ((g_filter)).astype(np.uint32)
        # print(f1)
        # # print(self.custom_g_filter(len=25, k=0.0075))
        # # threshold = 6000  # работает # = 6200   # работает
        # self.logger.info(f"start download")
        # # print(filename)
        # # with open(filename) as f:
        # #     #determining number of columns from the first line of text
        # #     n_cols = len(f.readline().split("\t"))
        # # data = np.loadtxt("./weight_height_5.txt", delimiter=",",usecols=np.arange(1, n_cols))
        # # self.logger.info("First five rows:\n",data[:5])
        # # пример чтения части столбцов (возможно, лучше делать так)
        # time_data = np.array(read_csv(filename, delimiter='\t',
        #                               dtype=np.int32, header=None,  #,
        #                               keep_default_na=False,
        #                               na_filter=False))
        # self.logger.info(f"1, end download, file len {len(time_data)}")
        # # self.bool_arr = np.greater(abs(time_data[:, 2]), threshold)  # self сделал, чтобы сохранять в конце
        # self.bool_arr = np.greater(abs(time_data[:, 2]), threshold).astype(np.uint32)  # self сделал, чтобы сохранять в конце
        # ###self.logger.info("2")
        # # arr = np.convolve(arr, self.custom_filter(45, 0.0075)*1.4, 'same')
        # # можно фильтр в int32 сделать
        # self.bool_arr = np.convolve(self.bool_arr, f1, 'same') # работает
        # self.bool_arr = np.convolve(
        #     self.bool_arr,
        #     f2, 'same') # ТОЛЬКО ЧТО ДОБАВИЛ, НЕ ПРОВЕРЯЛ
        # # self.bool_arr = np.convolve(self.bool_arr, g_filter, 'same') # работает
        # # self.bool_arr = np.convolve( ########################################################################
        # #     self.bool_arr, self.custom_g_filter(len=25, k=0.0075) * 1, 'same') # ТОЛЬКО ЧТО ДОБАВИЛ, НЕ ПРОВЕРЯЛ

        # # arr = np.convolve(arr, self.custom_filter(75, 0.005)*1.55, 'same') # работает
        # self.logger.info("3")
        # # arr = np.round(arr)
        # start = np.where((self.bool_arr[:-1] <= 50000000) & (self.bool_arr[1:] > 50000000))[0]
        # # start = np.where((self.bool_arr[:-1] <= 0.5) & (self.bool_arr[1:] > 0.5))[0] ##########################
        # # start = np.where((arr[:-1] == 0) & (arr[1:] == 1))[0]
        # # real_start = np.where(np.diff(start) > min_frame_len)[0]
        # start_arr = np.where(np.diff(start) > min_frame_len)[0]
        # # self.logger.info(f"\nstartwwwww arr= {start[start_arr]}")
        # # self.logger.info(f"\nstartwwwww +1 arr= {start[start_arr + 1]}")
        # # start_arr = np.insert(start[start_arr + 1], 0, start[0])
        # # self.logger.info(f"\nstart qeweqwarr= {start_arr}")
        # # st = start[start_arr[-1] + 1]
        # start_arr = np.insert(start[start_arr + 1], 0, start[0])
        # # start_arr = np.insert(start_arr, len(start_arr), st)

        # end = np.where((self.bool_arr[:-1] >= 50000000) & (self.bool_arr[1:] < 50000000))[0]