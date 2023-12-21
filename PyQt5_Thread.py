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
        # self.all_data = np.array([], dtype=np.int32)
        self.SIZE_EXTENTION_STEP = 20000
        self.k_amp = 1
        self.fs = 0
        self.TIMER_INTERVAL = 0
        # self.WAIT_TIME_SEC = 1
        self.WAIT_TIME_SEC = 0.6
        self.flag_pause: bool = False
        self.logger = logging.getLogger(logger_name)
        self.num_measurement_rows = 0
        self.total_cycle_num = 0  # !!!

        self.flag_all = False
        self.flag_by_name = False
        self.filenames_to_fft = []
        # self.name_list = ["6021_135_4.4_1.txt", "6021_135_4.4_2.txt",  # ], self.fs) 
        #                                "6021_135_4.4_3.txt", "6021_135_4.4_4.txt",
        #                                "6021_135_4.4_5.txt", "6021_135_4.4_6.txt",
        #                                "6021_135_4.4_7.txt", "6021_135_4.4_8.txt",
        #                                "6021_135_4.4_9.txt", "6021_135_4.4_10.txt"]
        self.fft_filename = ''
        self.folder = ''
        self.package_num = 0
        self.package_num_list: list = [0]
    
    def run(self):
        temp = (256 ** np.arange(4)[::-1]) #############
        powers = np.matrix([temp, temp, temp, temp]) #############

        self.cycle_count = 1
        self.k_amp = 1
        if self.flag_by_name:
            self.logger.info("flag_by_name")
            file = os.path.basename(self.filenames_to_fft[0])
            last_str = list(filter(None, re.split("_|_|.txt", file)))
            if len(last_str) >= 3:
                # переделать так, чтобы результат сохранялся в ту папку, из которой берется файл
                self.fft_filename = self.folder + last_str[0] + '_' + last_str[1] + '_' +  last_str[2] + \
                    f'%_{len(self.filenames_to_fft)}%.txt_FRQ_AMP_dPh_{self.fs}Hz.txt'
            else:
                self.fft_filename = self.folder + file + \
                    f'%_{len(self.filenames_to_fft)}%.txt_FRQ_AMP_dPh_{self.fs}Hz.txt'                
            self.fft_from_file_median(self.filenames_to_fft, self.fs)  #, self.fft_filename)

        if self.flag_all:
            self.logger.info(f"flag_all")
            self.flag_all = False
            self.get_fft_from_folders()

        if self.flag_measurement_start:
            self.package_num_list: list = [0]
            self.total_num_time_rows = 0  #
            self.package_num = 1
            self.time_data = np.ndarray((self.SIZE_EXTENTION_STEP, 5),
                                        dtype=np.int32)
            self.time_data2 = np.ndarray((self.SIZE_EXTENTION_STEP, 5),
                                        dtype=np.int32)
            self.count_fft_frame = 1
            self.i = 0
            self.flag_frame_start = False
            self.flag_pause = True
            self.bourder = np.array([0, 0], dtype=np.uint32)
            # self.amp_and_freq_for_plot = np.array([])
            self.amp_and_freq = np.resize(
                self.amp_and_freq,
                (self.num_measurement_rows, 4 * (self.total_cycle_num + 1)))
            self.amp_and_freq *= np.nan
        while self.flag_measurement_start or self.flag_recieve:
            if not self.flag_recieve:
                self.msleep(5)

            if self.flag_recieve:
######################
                self.logger.info("start matrix prosessing data frame")
                # i = self.rx.find(0x72) + 1
                # bytes_arr = np.frombuffer(self.rx[i:], dtype=np.uint8)
                bytes_arr = np.frombuffer(self.rx, dtype=np.uint8)
                start = np.where(
                    (bytes_arr[:-13] == 0x72) & (bytes_arr[13:] == 0x27))[0] + 1
                # start = np.where((bytes_arr[:-1] == 0x27) & (bytes_arr[1:] == 0x72))[0] + 2
                # start = np.insert(start, 0, 0)
                start = start[np.where(np.diff(start) == 14)[0]]
                expand = len(start)
                array_r = np.zeros((expand, 4, 4), dtype=np.uint8)
                for i in range(4):
                    for j in range(3):
                        array_r[:, i, j] = bytes_arr[np.add(start, 3*i + j)]
                # self.time_data2.resize(self.package_num + expand, 5)
                self.time_data2.resize(self.package_num - 1 + expand, 5)
                self.time_data2[self.package_num - 1:, 0] = np.arange(
                    self.package_num, expand + self.package_num)
                # self.time_data2[self.package_num:, 0] = np.arange(self.package_num + 1, expand + self.package_num + 1)
                # self.time_data2[self.package_num:, 1:] = (np.einsum("ijk,jk->ij", array_r, powers) / 256)
                self.time_data2[self.package_num - 1:, 1:] = np.einsum(
                    "ijk,jk->ij", array_r, powers) / 256
                # self.package_num += expand
##############################
                self.logger.info("start prosessing data frame")
                i = self.rx.find(0x72)
                ###self.logger.info(
                    ###f"thread_start, i = {i}, len rx = {len(self.rx)}")
                while (i + 13) < len(self.rx):
                    if not (self.rx[i] == 0x72 and self.rx[i + 13] == 0x27):
                        ###self.logger.info(f"before i={i}, 0x72:{self.rx[i] == 0x72}, 0x27:{self.rx[i + 13] == 0x27}")
                        i += self.rx[i:].find(0x27) + 1
                        ###self.logger.info(f"now i={i}, 0x72:{self.rx[i] == 0x72}, 0x27:{self.rx[i + 13] == 0x27}")
                        continue
                    self.time_data[self.package_num, :] = np.array(
                        [self.int_from_bytes(self.rx, i, self.package_num)])
                    i += 14
                    self.package_num += 1
                    self.extend_array_size()
                self.logger.info("end prosessing data frame")
                ###self.logger.info(f"\t\treal package_num = {self.package_num}")
                self.package_num_signal.emit(self.package_num)
                self.flag_recieve = False
                self.make_fft_frame(encoder=self.time_data[:, 2],  # пусть эта функция срабатывает всегда, даже если данных нет, поскольку ее поведение зависит в первую очередь от протокола измерений
                                    gyro=self.time_data[:, 1])
                
        if self.package_num:
            self.logger.info("save cycle !")
            # self.all_data = np.resize(self.all_data, (self.package_num, 5))
            self.time_data.resize(self.package_num, 5)
            for j in range(self.GYRO_NUMBER):
                self.package_num_list.append(self.package_num)
                for i in range(len(self.package_num_list) - 1):
                    # name_part = ('' if self.GYRO_NUMBER == 1 else f"_{i + 1}")
                    name_part = f"_{i + 1}"
                    self.logger.info(
                        f"save cycle {self.filename[0] + name_part + self.filename[1]}")
                    time_data_df = DataFrame(self.time_data[self.package_num_list[i]:self.package_num_list[i + 1], :])
                    time_data_df.to_csv(self.filename[0] + name_part
                          + self.filename[1], header=None, index=None,
                          sep='\t', mode='w', date_format='%d')  # лучше сохранять после каждого цикла
                    time_data_df2 = DataFrame(self.time_data2[self.package_num_list[i]:self.package_num_list[i + 1], :])
                    time_data_df2.to_csv(self.filename[0] + "___" + name_part + ########################
                          "_matrix_check_" + self.filename[1], header=None, index=None,
                          sep='\t', mode='w', date_format='%d')  ################################
                # name_part = ('' if self.GYRO_NUMBER == 1 else f"_{i + 1}")
                #     # np.savetxt(self.filename[0] + name_part
                #         #   + self.filename[1], self.time_data, delimiter='\t', fmt='%d')
                # time_data_df = DataFrame(self.time_data)  # !!!!!!!!!!!!!!!!!!!!
                # time_data_df.to_csv(self.filename[0] + name_part
                #           + self.filename[1], header=None, index=None,
                #           sep='\t', mode='w', date_format='%d')  # лучше сохранять после каждого цикла
        # if self.cycle_count > 1:
        if (len(self.amp_and_freq_for_plot) or self.flag_by_name) and not self.flag_all:   ### можно убрать другое сохранение, раз это уже есть
            for i in range(self.GYRO_NUMBER):
                # if self.cycle_count > 1:
                # self.save_fft(i, self.name)
                self.logger.info("save fft !")
                self.save_fft(  # проверять, есть ли такое имя уже
                    i,
                    self.fft_filename)  # формировать имя
                    # self.filename[0] + f'%_{self.total_cycle_num}%.txt_FRQ_AMP_dPh_{self.fs}Hz.txt')
            self.flag_by_name = False
        self.logger.info("Tread stop")
                # else:
                #     # self.check_f_c()  
                #     name_part = ('' if self.GYRO_NUMBER == 1 else f"_{i + 1}")
                #     ###self.logger.info("save fft file")
                #         np.savetxt(self.filename[0] + '_FFT' + name_part
                #               + self.filename[1], self.amp_and_freq,
                #                 delimiter='\t', fmt='%.3f')
                # # self.approximate = np.array(self.fft_approximation(self.amp_and_freq))

    def get_fft_from_folders(self):
        # path = 'D:/Gyro2023_Git/sensors_nums2.txt'
        # path = 'sensors_nums2.txt'
        path = 'sensors_nums — копия.txt'
        sensor_list = read_csv(path, dtype=np.str, delimiter='\n', header=None)
        # print(sensor_list)
        # with open(path, 'r') as sensor_list:
        # for sensor_number in sensor_list:
        for sensor_number in sensor_list[0]:
            # print(type(sensor_number))
            check = list(filter(None, re.split("\.|\n", sensor_number)))
            if len(check[-1]) < 3:
                sensor_number_ = check[-2] + "." + check[-1]
            if len(check[-1]) == 4:
                sensor_number_ = check[-1]
            mypath = '//fs/Projects/АФЧХ/' + sensor_number_
            ###self.logger.info(f"\npath: {mypath}")
            onlyfiles = [f for f in os.listdir(mypath) if os.path.isfile(os.path.join(mypath, f))]
            self.filenames_to_fft = []
            for file in onlyfiles:
                string = list(filter(None, re.split("_|_|.txt", file)))
                if len(string) == 4 and string[1] != 'fresh':
                    # name_list.append(mypath + '/' + file)
                    self.filenames_to_fft.append(mypath + '/' + file)
                    last_str = string
            ## mypath + '/' добавлять это, чтобы сохранять в той же папке
            self.fft_filename = self.folder + last_str[0] + '_' + last_str[1] + '_' +  last_str[2] + \
                f'%_{len(self.filenames_to_fft)}%.txt_FRQ_AMP_dPh_{self.fs}Hz.txt'
            # self.name = self.folder + last_str[0] + '_' + last_str[1] + '_' +  last_str[2] + f'%_{len(name_list)}%.txt_FRQ_AMP_dPh_{self.fs}Hz.txt'
            # name = folder + name
            # self.name = name
            self.logger.info(f"list: {self.filenames_to_fft}")
            self.fft_from_file_median(self.filenames_to_fft, self.fs) #, self.fft_filename)
            self.logger.info("save")
            self.save_fft(0, self.fft_filename)
    
    def save_fft(self, i, name):
        name_parts = re.split("\%", name)
        self.logger.info(name_parts[0] + name_parts[1] + name_parts[2])
        self.fft_approximation(round_flag=False)
        amp_max_i = np.argmax(self.amp_and_freq[:, -3])
        self.get_special_points(
            f_max=self.amp_and_freq[amp_max_i, -4],
            amp_w_c=0.707 * self.amp_and_freq[amp_max_i, -3])
        self.median_data_ready_signal.emit(
            re.split("_", os.path.basename(
                name_parts[0] + name_parts[1] + name_parts[2]))[0])
            # list(filter(None, re.split("_", os.path.basename("D:\Gyro2023_Git\ddddd_3242_444"))))[0])
        # self.check_f_c()
        # name_part = ('' if self.GYRO_NUMBER == 1 else f"_{i + 1}")
        ###self.logger.info("save fft file")

        np.savetxt(name_parts[0] + name_parts[1] + name_parts[2],
                   self.amp_and_freq[:, :-4], delimiter='\t', fmt='%.3f')
        np.savetxt(name_parts[0] + name_parts[2], 
                   self.amp_and_freq[:, -4:], delimiter='\t', fmt='%.3f') # , decimal=','
        self.warning_signal.emit(f"Save file {name_parts[0] + name_parts[2]}\n")
        # np.savetxt(self.filename[0] + '_FFT_cycles' + name_part +
        #         self.filename[1], self.amp_and_freq[:, :-4],
        #         delimiter='\t', fmt='%.3f')
        # np.savetxt(self.filename[0] + '_FFT' + name_part +
        #         self.filename[1], self.amp_and_freq[:, -4:],
        #         delimiter='\t', fmt='%.3f') # , decimal=','
        # в коде функции уже есть finally close, так что with не нужен,
        # файл также по умолчанию перезаписывается
        self.logger.info("end saving fft file")

    def extend_array_size(self):
        if self.package_num >= self.total_num_time_rows:
            self.total_num_time_rows += self.SIZE_EXTENTION_STEP
            # self.time_data = np.resize(
            #     self.time_data, (self.num_rows, 5))
            self.time_data.resize(self.total_num_time_rows, 5)  # !!!!!
        # self.num_rows = self.package_num + int(len(self.rx)/14) + 1
        # self.all_data = np.resize(
        #     self.all_data, (self.num_rows, 5))  # !!!!!

    @staticmethod
    def int_from_bytes(rx: bytes, i: int, package_num: int):
        ints = np.array([package_num], dtype=np.int32)
        for shift in [1, 4, 7, 10]:
            res = int.from_bytes(
                rx[(i + shift):(i + shift + 3)],
                byteorder='big', signed=True)
            ints = np.append(ints, res)
        return ints

    def new_cycle(self):  # добавить сброс числа пакетов, изменение имени файла и т.д.
        # self.count = 0
        # self.add_points = 0
        # self.bourder = np.array([0, 0])
        # self.amp_and_freq.resize(self.num_measurement_rows, 4*self.cycle_count)
        # temp = np.copy(self.amp_and_freq[:, :4*(self.cycle_count - 2)])
        # self.amp_and_freq = np.resize(
        #         self.amp_and_freq,
        #         (self.num_measurement_rows, 4*(self.cycle_count + 1)))
        # ###self.logger.info(f"self.amp_and_freq all = {self.amp_and_freq}")
        # self.amp_and_freq[:, :4*(self.cycle_count - 2)] = np.copy(temp)
        ###self.logger.info(f"amp_and_freq_for_plot size = {self.amp_and_freq_for_plot.size}")
        if self.flag_measurement_start:
            self.package_num_list.append(self.package_num)
        # self.logger.info(self.total_cycle_num)
        # self.logger.info(f"cycle_count {self.cycle_count}")
        # self.logger.info(self.amp_and_freq.shape)
        # self.logger.info(self.amp_and_freq_for_plot.shape)
        if self.amp_and_freq.shape[0] == self.amp_and_freq_for_plot.shape[0]:
            # print(self.amp_and_freq.size)
            # print(self.amp_and_freq_for_plot.size)
            self.amp_and_freq[:, 4*(self.cycle_count - 1):4*self.cycle_count] = np.copy(self.amp_and_freq_for_plot)
            ###self.logger.info(f"amp_and_freq after resize2 = {self.amp_and_freq.size}")
            self.cycle_count += 1
            # self.amp_and_freq[:, 4*self.cycle_count:] = np.nan
            ###self.logger.info(f"self.amp_and_freq all = {self.amp_and_freq[0, :]}")
        else:
            pass
            ###self.logger.info(f"Wrong shape")
            # np.savetxt('file' + self.name, arr, delimiter='\t', fmt='%.2f')
        # ###self.logger.info(f"self.amp_and_freq all = {self.amp_and_freq}")
        self.amp_and_freq_for_plot = np.array([])
        # self.amp_and_freq[:, 4*self.cycle_count:(4*self.cycle_count + 4)] = self.amp_and_freq[:, 0:4]

    def fft_approximation(self, round_flag=True):
        if self.amp_and_freq.shape[0] == self.amp_and_freq_for_plot.shape[0]:
            self.amp_and_freq[:, 4*(self.cycle_count - 1):4*(self.cycle_count)] = np.copy(self.amp_and_freq_for_plot)
        # нужна проверка на то, что все частоты +- совпадают
        # self.amp_and_freq[:, -4:] = np.nan
        # ###self.logger.info(f"\namp_and_freq = {self.amp_and_freq}")

        for i in range(len(self.amp_and_freq[:, 1])):  # цикл по всем частотам
            for j in range(4):
                # так получиаем элементы из всех циклов
                self.amp_and_freq[i, j - 4] = np.nanmedian(self.amp_and_freq[i, j::4])
        if round_flag:
            self.amp_and_freq[:, -4] = np.round(self.amp_and_freq[:, -4], 1)
            self.amp_and_freq[:, -3] = np.round(self.amp_and_freq[:, -3], 3)
        ###self.logger.info(f"\namp_and_freq = {self.amp_and_freq}")    

    def make_fft_frame(self, encoder: np.ndarray, gyro: np.ndarray):
        if not self.flag_pause:
            self.flag_frame_start = True
            if self.i < self.WAIT_TIME_SEC * self.fs / self.TIMER_INTERVAL:
                self.bourder[0] = self.package_num
            self.i += 1
        if self.flag_frame_start and self.flag_pause:
            self.flag_frame_start = False
            # self.bourder[1] = self.package_num - int(self.fs / 20)  # frame end
            self.bourder[1] = self.package_num  # frame end
            self.i = 0
            self.amp_and_freq_for_plot.resize(self.count_fft_frame, 4, refcheck=False)  # !!!!!!!!!!!!!!!!!!!!!!!!!
            self.logger.info(f"old bourders = {self.bourder}")
            self.bourder = self.get_new_bourder(self.bourder, self.fs)  # !!!!!!!!!!!!!!!!!!!!!!!!
            self.logger.info(f"\tnew bourders = {self.bourder}")
            if all(self.bourder):
                [freq, amp, d_phase, tau] = self.fft_data(
                    gyro=gyro[self.bourder[0]:self.bourder[1]],
                    encoder=encoder[self.bourder[0]:self.bourder[1]], fs=self.fs)
                # self.check_180_degrees(freq, amp, d_phase)
                self.amp_and_freq_for_plot[(
                    self.count_fft_frame - 1), :] = [freq, amp, d_phase, tau]
                self.fft_data_signal.emit(True)
            else:
                self.warning_signal.emit("Too small data frame!")
                self.amp_and_freq_for_plot[(
                    self.count_fft_frame - 1), :] = [np.nan, np.nan, np.nan, np.nan]
            # self.amp_and_freq[(self.count - 1),
            #                   4*(self.cycle_count - 1):
            #                   4*self.cycle_count] = [freq, amp, d_phase, tau]
            # ###self.logger.info(
            #     f"\(self.count - 1) = {(self.count - 1)}, 4*(self.cycle_count - 1) = {4*(self.cycle_count - 1)}," +
            #     f"freq = {[freq, amp, d_phase, tau]}")
            # ###self.logger.info(f"self.amp_and_freq lin = {self.amp_and_freq[(self.count - 1), :]}")
            # ###self.logger.info(f"self.amp_and_freq lin = {self.amp_and_freq}")
            # ###self.logger.info(
            #     f"\nself.amp_and_freq line = {self.amp_and_freq[(self.count - 1), 4*(self.cycle_count - 1):4*self.cycle_count]}")
            # self.amp_and_freq_for_plot = self.amp_and_freq_for_plot[self.amp_and_freq_for_plot[:, 2].argsort()]

    def get_special_points(self, f_max, amp_w_c):
        self.freq180 = np.nan
        # self.freq_w_c = [np.nan, np.nan]
        # amp_max_i = np.argmax(self.amp_and_freq[:, -3])
        # f_max = self.amp_and_freq[amp_max_i, -4]
        # amp_w_c = 0.707 * self.amp_and_freq[amp_max_i, -3]
        f_180degrees = -180
        for i in range(1, len(self.amp_and_freq[:, 1])):
            freq = self.amp_and_freq[i, -4]
            freq_prev = self.amp_and_freq[i - 1, -4]
            d_phase = self.amp_and_freq[i, -2]
            d_phase_prev = self.amp_and_freq[i - 1, -2]
            amp = self.amp_and_freq[i, -3]
            amp_prev = self.amp_and_freq[i - 1, -3]
            if (d_phase_prev > f_180degrees and
                d_phase < f_180degrees) or (d_phase_prev < f_180degrees and
                                            d_phase > f_180degrees):
                # self.freq180, ph = self.point_on_line(
                    # x=[freq_prev, freq], y=[d_phase_prev, d_phase], y_point_to_find=-180)
                self.freq180 = np.interp(f_180degrees, np.sort([d_phase_prev, d_phase]),
                                         np.sort([freq_prev, freq]))
                amp180 = np.interp(self.freq180, np.sort([freq_prev, freq]),
                                   np.sort([amp_prev, amp])) # не будет работать, потому что упорядочиваю массив
                # amp180, fr = self.point_on_line(
                    # x=[amp, amp_prev], y=[freq_prev, freq], y_point_to_find=self.freq180)
                    # x=[amp_prev, amp], y=[freq_prev, freq], y_point_to_find=self.freq180)
                ###self.logger.info(f"freq180 = {self.freq180} " +
                                 ###f"ph = {0} " +
                                 ###f"amp180 = {amp180/100}")# +
                                #  f"fr = {0}\n interp={np.interp(self.freq180, [freq_prev, freq], [amp, amp_prev])}\
                                    #   {[freq_prev, freq]} {[amp_prev, amp]}\n {[d_phase_prev, d_phase]}")
            # if  (amp_prev < amp_w_c and amp > amp_w_c):
            #     self.freq_w_c[0], _ = self.point_on_line(
            #         [freq_prev, freq], [amp_prev, amp], amp_w_c)
            #     ###self.logger.info(f"freq_w_c[0] = {self.freq_w_c[0]}")
            # if (amp_prev > amp_w_c and amp < amp_w_c):
            #     self.freq_w_c[1], _ = self.point_on_line(
            #         [freq_prev, freq], [amp_prev, amp], amp_w_c)
            #     ###self.logger.info(f"freq_w_c[1] = {self.freq_w_c[1]}")
            # if  (freq_prev < 5 and freq > 5):
            #     self.freq_w_c[0], ddd = self.point_on_line(
            #         [freq_prev, freq], [amp_prev, amp], 5)
            #     # ###self.logger.info(f"freq_w_c[0] = {self.freq_w_c[0]}")
            #     ###self.logger.info(f"amp 5 = {self.freq_w_c[0]}")
            # if (freq > 10 and freq_prev < 10):
            #     self.freq_w_c[1], ddd = self.point_on_line(
            #         [freq_prev, freq], [amp_prev, amp], 10)
            #     # ###self.logger.info(f"freq_w_c[1] = {self.freq_w_c[1]}")
            #     ###self.logger.info(f"amp 10 = {self.freq_w_c[1]}")
        # self.f_Q = f_max / abs(self.freq_w_c[1] - self.freq_w_c[0])

    @staticmethod
    def point_on_line(self, x: list, y: list, y_point_to_find=0):
        k = (x[0] - x[1]) / (y[0] - y[1])
        b = y[0] - k * x[0]
        res_x = (y_point_to_find - b) / k
        res_y = k * res_x + b
        ###self.logger.info(f"y=k{k}*x+b{b}")  
        return [res_x, res_y]

    def check_180_degrees(self, freq, amp, d_phase):
        if (self.count_fft_frame + self.add_points - 1) >= 1:
            # ind = self.count + self.add_points
            amp_prev = self.amp_and_freq_for_plot[(self.count_fft_frame + self.add_points - 2), 0]
            phase_prev = self.amp_and_freq_for_plot[(self.count_fft_frame + self.add_points - 2), 1]
            freq_prev = self.amp_and_freq_for_plot[(self.count_fft_frame + self.add_points - 2), 2]
            if abs(phase_prev - d_phase) > 5/4*np.pi:
                self.add_points += 2
                self.amp_and_freq_for_plot = np.resize(
                    self.amp_and_freq_for_plot, (self.count_fft_frame + self.add_points, 4))
                if not (freq_prev - freq == 0):
                    d_phase += -2*np.pi
                    k = (phase_prev - d_phase) / (freq_prev - freq)
                    b = phase_prev - k * freq_prev
                    freq180 = (- np.pi - b)/k
                    k = (amp_prev - amp) / (freq_prev - freq)
                    b = amp_prev - k * freq_prev
                    amp180 = k * freq180 + b
                    self.amp_and_freq_for_plot[(self.count_fft_frame + self.add_points - 3), :] = [amp180, -np.pi, freq180, np.nan]
                    self.amp_and_freq_for_plot[(self.count_fft_frame + self.add_points - 2), :] = [amp180, np.pi, freq180, np.nan]
                    ###self.logger.info(f"prev f = {freq_prev}, now f = {freq}, between = {freq180}")
                    d_phase += 2 * np.pi
                    ###self.logger.info(f"prev ph = {phase_prev}, now ph = {d_phase}, amp = {amp180}")

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
            ###self.logger.info(file)
            self.logger.info(f"total_cycle_num={self.total_cycle_num} " +
                             f"cycle_count={self.cycle_count}")
            self.fft_for_file(file_for_fft)
            if self.cycle_count == 1:
                self.amp_and_freq = np.resize(
                    self.amp_and_freq,
                    (int(self.amp_and_freq_for_plot.size / 4),
                    4 * (self.total_cycle_num + 1)))
                self.amp_and_freq *= np.nan
            if self.cycle_count != self.total_cycle_num:
                self.new_cycle()
        # self.save_fft(0, name)  ## в конце run сохранение есть
        # self.fft_approximation()
        # # amp_max_i = np.argmax(self.amp_and_freq[:, -3])
        # # self.get_special_points(
        # #     f_max = self.amp_and_freq[amp_max_i, -4],
        # #     amp_w_c = 0.707 * self.amp_and_freq[amp_max_i, -3])
        # self.approximate_data_emit.emit(True)
        # # self.check_f_c() 
        # # name_part = ('' if self.GYRO_NUMBER == 1 else f"_{i + 1}")

    def fft_for_file(self, filename: str, threshold: int = 5500):
        min_frame_len = 1.0 * self.fs  # сколько времени минимум длится вибрация + пауза, при 1 работало
        # min_frame_len = 1.5 * self.fs  # сколько времени минимум длится вибрация + пауза, при 1 работало
        # очень важный параметр
        # при 1 Гц раз в 0.5 Fs появляются лишние начало и конец; сгладить сложно да и незачем
        # g_filter = self.custom_g_filter(len=59, k=0.0065) * 1.49
        # g_filter = self.custom_g_filter(len=59, k=0.0065) * 1.4
        # g_filter = self.custom_g_filter(len=47, k=0.0075) * 1.45
        # g_filter = self.custom_g_filter(len=255, k=0.00001) * 1.45
        filter_len = int(self.fs * 0.15) * 2 + 1
        # const_filter = (np.ones(301) / 301 * 1.5).astype(np.float32)
        const_filter = (np.ones(filter_len) / filter_len * 1.5).astype(np.float32)
        g_filter = (self.custom_g_filter(len=25, k=0.0075) * 1).astype(np.float32)
        # print(self.custom_g_filter(len=25, k=0.0075))
        self.logger.info(f"start download")
        self.logger.info(filename)
        # пример чтения части столбцов (возможно, лучше делать так)
        time_data = np.array(read_csv(filename, delimiter='\t',
                                      dtype=np.int32, header=None,  #,
                                      keep_default_na=False,
                                      na_filter=False,
                                      index_col=False,
                                      usecols=[1, 2, 3, 4]))
        # time_data = np.array(read_csv(filename, delimiter='\t',
        #                               dtype=np.int32, header=None,  #,
        #                               keep_default_na=False,
        #                               na_filter=False))
        # self.logger.info(f"1, end download, file len {len(time_data)}")
        self.bool_arr = np.greater(
            abs(time_data[:, 2-1]), threshold).astype(np.float32)  # self сделал, чтобы сохранять в конце
        ###self.logger.info("2")
        # arr = np.convolve(arr, self.custom_filter(45, 0.0075)*1.4, 'same')
        self.bool_arr = np.convolve(self.bool_arr, const_filter, 'same') # работает
        self.bool_arr = np.convolve(
            self.bool_arr, g_filter, 'same') # 
        # arr = np.convolve(arr, self.custom_filter(75, 0.005)*1.55, 'same') # работает
        self.logger.info("3")
        start = np.where(
            (self.bool_arr[:-1] <= 0.5) & (self.bool_arr[1:] > 0.5))[0]
        # start = np.where((arr[:-1] == 0) & (arr[1:] == 1))[0]
        # real_start = np.where(np.diff(start) > min_frame_len)[0]
        start_arr = np.where(np.diff(start) > min_frame_len)[0]
        # start_arr = np.insert(start[start_arr + 1], 0, start[0])
        # self.logger.info(f"\nstart qeweqwarr= {start_arr}")
        # st = start[start_arr[-1] + 1]
        start_arr = np.insert(
            start[start_arr + 1], 0, start[0]) + int(0.015 * self.fs)
        # start_arr = np.insert(start_arr, len(start_arr), st)

        end = np.where(
            (self.bool_arr[:-1] >= 0.5) & (self.bool_arr[1:] < 0.5))[0]
        self.logger.info(f"\nstart= {start}\n end = {end}")

        # end = np.where((arr[:-1] == 1) & (arr[1:] == 0))[0]
        # real_end = np.where(np.diff(end) > min_frame_len)[0]
        end_arr = np.where(np.diff(end) > min_frame_len)[0]
        # self.logger.info(f"\nd start= {np.diff(start)}\nd  end = {np.diff(end)}")
        end_arr = np.insert(
            end[end_arr], len(end[end_arr]), end[-1]) - int(0.015 * self.fs)
        if len(start_arr) != len(end_arr):
            self.warning_signal.emit(
                f"Problems with frame selection! ({os.path.basename(filename)})")  # !!!!!!!!!!!!!!!!!!!!!!!!!
            np.savetxt('error_' + os.path.basename(filename),
                       self.bool_arr, delimiter='\t', fmt='%.3f')
        self.logger.info(f"\n\nstart arr= {start_arr}\n end  arr = {end_arr}")
        self.logger.info(
            f"4, len start = {len(start)}, len start after = {len(start_arr)}")
        self.logger.info(
            f"4, len end = {len(end)}, len end after = {len(end_arr)}")
        flag_first = True
        for i in range(min(len(end_arr), len(start_arr))):
            if i > 0:
                if start_arr[i] < end_arr[i - 1]:
                    ###self.logger.info(f"!!! start[{i}]={start_arr[i]}, end[{i}]={end_arr[i]}")
                    start_arr[i] = end_arr[i - 1]
            # self.logger.info(f"old bourders = {start_arr[i], end_arr[i]}")
            bourder = self.get_new_bourder([start_arr[i], end_arr[i]], self.fs)
            # self.logger.info(f"\tnew bourders = {bourder}")
            self.amp_and_freq_for_plot.resize(i + 1, 4, refcheck=False)
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
                self.amp_and_freq_for_plot[i, :] = [np.nan, np.nan, np.nan, np.nan]
        ###self.logger.info(f"\n fft end for {filename}")
        # print(os.path.basename(filename), np.nanmedian(np.diff(self.amp_and_freq_for_plot[:, 1])))
        self.logger.info(f"median noise {os.path.basename(filename)}, " +
                         f"{np.nanmedian(abs(np.diff(self.amp_and_freq_for_plot[:, 1])))}")
        self.logger.info(
            np.nanmean(abs(np.diff(self.amp_and_freq_for_plot[:, 1]))))

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
        if (bourder[1] - bourder[0]) < fs:
            return [0, 0]
        # ###self.logger.info(f"before")
        return bourder

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
    import PyQt5_ApplicationClass
    from PyQt5 import QtWidgets
    import sys
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')  # 'Fusion' ... QtWidgets.QStyle
    window = PyQt5_ApplicationClass.AppWindow()
    window.setWindowTitle("GyroVibroTest")
    # window.resize(850, 500)
    window.show()
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