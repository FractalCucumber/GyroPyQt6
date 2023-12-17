from PyQt5 import QtCore
import numpy as np
# from PyQt6.QtSerialPort import QSerialPort
# import pyqtgraph as pg
import logging
import os
from pandas import read_csv, DataFrame

class MyThread(QtCore.QThread):
    package_num_signal = QtCore.pyqtSignal(int)
    fft_data_emit = QtCore.pyqtSignal(bool)
    approximate_data_emit = QtCore.pyqtSignal(bool)

    def __init__(self, gyro_number=3, logger_name: str = ''):
        # QtCore.QThread.__init__(self)
        super(MyThread, self).__init__()
        self.GYRO_NUMBER = gyro_number
        self.filename: list[str] = ["", ""]
        self.flag_start: bool = False
        self.flag_recieve: bool = False
        self.rx: bytes = b''
        self.amp_and_freq_for_plot: np.ndarray = np.array([], dtype=np.float64)  # ???
        self.amp_and_freq: np.ndarray = np.array([])  # ???
        # self.all_data = np.array([], dtype=np.int32)
        self.SIZE_EXTENTION_STEP = 20000
        self.k_amp = 1
        self.fs = 0
        self.TIMER_INTERVAL = 0
        self.WAIT_TIME_SEC = 1
        self.flag_pause: bool = False
        self.logger = logging.getLogger(logger_name)
        # self.approximate = np.array([])
        self.num_measurement_rows = 0
        self.total_cycle_num = 0  # !!!

        self.flag = False

    def run(self):
        if self.flag:
            self.flag = False
            self.fft_from_file_median(["6021_135_4.4_1.txt", "6021_135_4.4_2.txt",  # ], self.fs) 
                                    #    "6021_135_4.4_3.txt", "6021_135_4.4_4.txt",
                                    #    "6021_135_4.4_5.txt", "6021_135_4.4_6.txt",
                                    #    "6021_135_4.4_7.txt", "6021_135_4.4_8.txt",
                                       "6021_135_4.4_9.txt", "6021_135_4.4_10.txt"], self.fs) 
            return
        # self.sign = 1
        self.k_amp = 1

        self.cycle_count = 1
        self.total_num_rows = 0
        self.package_num = 0
        self.time_data = np.ndarray((self.SIZE_EXTENTION_STEP, 5),
                                   dtype=np.int32)
        # self.fft_data = np.ndarray((, 2))
        self.count_fft_frame = 1
        self.i = 0
        self.flag_frame_start = False
        self.flag_pause = True
        self.bourder = np.array([0, 0])
        self.amp_and_freq_for_plot = np.array([])
        self.amp_and_freq = np.resize(self.amp_and_freq,
                                      (self.num_measurement_rows, 4 * (self.total_cycle_num + 1)))
        self.amp_and_freq *= np.nan
        # self.approximate = np.array([])
        self.add_points = 0
        # k = 0 # flag_start = False # flag_end = True
        while self.flag_start or self.flag_recieve:
            if not self.flag_recieve:
                self.msleep(5)

            if self.flag_recieve:
                i = self.rx.find(0x72)
                self.logger.info(
                    f"thread_start, i = {i}, len rx = {len(self.rx)}")
                # start = np.where((self.rx[:-1] == 0x72) & (self.rx[1:] == 0x27))[0]
                # после нахождения всех нужных индексов блоками по 3 байта преобразовать массив в числа
                # bytes_array = np.array([byte1, byte2, byte3], dtype=np.uint8)
                # int_value = np.dot(bytes_array, 256 ** np.arange(len(bytes_array))[::-1])
                while (i + 13) < len(self.rx):
                    if not (self.rx[i] == 0x72 and self.rx[i + 13] == 0x27):
                        self.logger.info(f"before i={i}, 0x72:{self.rx[i] == 0x72}, 0x27:{self.rx[i + 13] == 0x27}")
                        i += self.rx[i:].find(0x27) + 1
                        self.logger.info(f"now i={i}, 0x72:{self.rx[i] == 0x72}, 0x27:{self.rx[i + 13] == 0x27}")
                        continue
                    self.time_data[self.package_num, :] = np.array(
                        [self.int_from_bytes(self.rx, i, self.package_num)])
                    i += 14
                    self.package_num += 1
                    self.extend_array_size()

                self.logger.info(f"\t\treal package_num = {self.package_num}")
                self.package_num_signal.emit(self.package_num)
                self.flag_recieve = False
                self.make_fft_frame(encoder=self.time_data[:, 2],  # пусть эта функция срабатывает всегда, даже если данных нет, поскольку ее поведение зависит в первую очередь от протокола измерений
                                        gyro=self.time_data[:, 1])
        if self.package_num:
            # self.all_data = np.resize(self.all_data, (self.package_num, 5))
            self.time_data.resize(self.package_num, 5)
            for i in range(self.GYRO_NUMBER):
                # y = (x if x > 0 else 0) 
                name_part = ('' if self.GYRO_NUMBER == 1 else f"_{i + 1}")
                # with open(self.filename[0] + name_part
                        #   + self.filename[1], 'w') as file:
                    # np.savetxt(file, self.time_data, delimiter='\t', fmt='%d')
                time_data_df = DataFrame(self.time_data)  # !!!!!!!!!!!!!!!!!!!!
                time_data_df.to_csv(self.filename[0] + name_part
                          + self.filename[1], header=None, index=None,
                          sep='\t', mode='w', fmt='%d')  # лучше сохранять после каждого цикла

        self.logger.info(f"\tfft = {str(self.amp_and_freq_for_plot)}" +
                         f"\tfft size = {self.amp_and_freq_for_plot.size}" +
                         f"\tfft len = {len(self.amp_and_freq_for_plot)}")
        if len(self.amp_and_freq_for_plot):
            for i in range(self.GYRO_NUMBER):
                # if self.cycle_count > 1:
                self.save_fft(i)
        self.logger.info("Tread stop")
                # else:
                #     # self.check_f_c()  
                #     name_part = ('' if self.GYRO_NUMBER == 1 else f"_{i + 1}")
                #     # if self.GYRO_NUMBER == 1:
                #     #     name_part = ''
                #     # else:
                #     #     name_part = f"_{i + 1}"
                #     self.logger.info("save fft file")
                #     with open(self.filename[0] + '_FFT' + name_part
                #               + self.filename[1], 'w') as file:
                #         np.savetxt(file, self.amp_and_freq,
                #                 delimiter='\t', fmt='%.3f')
                # # self.approximate = np.array(self.fft_approximation(self.amp_and_freq))

# def bytes_to_int(byte1, byte2, byte3):
#     byte4 = 0x00
#     # byte_array = np.array([byte0, byte1, byte2, byte3], dtype=np.uint8)
#     bytes_array = np.array([byte1, byte2, byte3, byte4], dtype=np.uint8)
#     int_value = (np.dot(bytes_array, 256 ** np.arange(len(bytes_array))[::-1])).astype(np.int32)
#     return (int_value / 256).astype(np.int32)
# rx: bytes = b'\xFF\xFF\x00'
# result = bytes_to_int(rx[0], rx[1], rx[2])
# print(result) #

    def save_fft(self, i):
        self.fft_approximation()
        amp_max_i = np.argmax(self.amp_and_freq[:, -3])
        self.get_special_points(
            f_max = self.amp_and_freq[amp_max_i, -4],
            amp_w_c = 0.707 * self.amp_and_freq[amp_max_i, -3])
        self.approximate_data_emit.emit(True)
        # self.check_f_c()  
        name_part = ('' if self.GYRO_NUMBER == 1 else f"_{i + 1}")
        self.logger.info("save fft file")

        np.savetxt(self.filename[0] + '_FFT_cycles' + name_part +
                self.filename[1], self.amp_and_freq[:, :-4],
                delimiter='\t', fmt='%.3f')
        np.savetxt(self.filename[0] + '_FFT' + name_part +
                self.filename[1], self.amp_and_freq[:, -4:],
                delimiter='\t', fmt='%.3f') # , decimal=','
        # в коде функции уже есть finally close, так что with не нужен,
        # файл также по умолчанию перезаписывается
        self.logger.info("end saving fft file")

    def extend_array_size(self):
        if self.package_num >= self.total_num_rows:
            self.total_num_rows += self.SIZE_EXTENTION_STEP
            # self.time_data = np.resize(
            #     self.time_data, (self.num_rows, 5))
            self.time_data.resize(self.total_num_rows, 5)  # !!!!!
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
        self.add_points = 0
        # self.bourder = np.array([0, 0])
        # self.amp_and_freq.resize(self.num_measurement_rows, 4*self.cycle_count)
        # temp = np.copy(self.amp_and_freq[:, :4*(self.cycle_count - 2)])
        # self.amp_and_freq = np.resize(
        #         self.amp_and_freq,
        #         (self.num_measurement_rows, 4*(self.cycle_count + 1)))
        # self.logger.info(f"self.amp_and_freq all = {self.amp_and_freq}")
        # self.amp_and_freq[:, :4*(self.cycle_count - 2)] = np.copy(temp)
        self.logger.info(f"amp_and_freq_for_plot size = {self.amp_and_freq_for_plot.size}")
        self.amp_and_freq[:, 4*(self.cycle_count - 1):4*self.cycle_count] = np.copy(self.amp_and_freq_for_plot)
        self.logger.info(f"amp_and_freq after resize2 = {self.amp_and_freq.size}")
        self.cycle_count += 1
        # self.amp_and_freq[:, 4*self.cycle_count:] = np.nan
        self.logger.info(f"self.amp_and_freq all = {self.amp_and_freq[0, :]}")
        # self.logger.info(f"self.amp_and_freq all = {self.amp_and_freq}")
        self.amp_and_freq_for_plot = np.array([])
        # self.amp_and_freq[:, 4*self.cycle_count:(4*self.cycle_count + 4)] = self.amp_and_freq[:, 0:4]

    def fft_approximation(self, round_flag=True):
        self.amp_and_freq[:, 4*(self.cycle_count - 1):4*(self.cycle_count)] = np.copy(self.amp_and_freq_for_plot)
        # нужна проверка на то, что все частоты +- совпадают
        self.mediana = np.ndarray((self.amp_and_freq.size))
        self.amp_and_freq[:, -4:] = np.nan
        # self.temp = np.ndarray((self.amp_and_freq.size))
        # self.logger.info(f"\namp_and_freq = {self.amp_and_freq}")

        for i in range(len(self.amp_and_freq[:, 1])):  # цикл по всем частотам
            for j in range(4):
                # так получиаем элементы из всех циклов
                self.amp_and_freq[i, j - 4] = np.nanmedian(self.amp_and_freq[i, j::4])
            # self.check_180_degrees(self.amp_and_freq[i, cols_num + 0],
            #                        self.amp_and_freq[i, cols_num + 1],
            #                        self.amp_and_freq[i, cols_num + 2])
            # self.freq180, self.freq_w_c = self.check_f_c(self.amp_and_freq[:, -4:])
        if round_flag:
            self.amp_and_freq[:, -4] = np.round(self.amp_and_freq[:, -4], 1)
            self.amp_and_freq[:, -3] = np.round(self.amp_and_freq[:, -3], 3)
        self.logger.info(f"\namp_and_freq = {self.amp_and_freq}")    
        # return result

    def make_fft_frame(self, encoder: np.ndarray, gyro: np.ndarray):
        if not self.flag_pause:
            self.flag_frame_start = True
            self.i += 1
            if self.i < self.WAIT_TIME_SEC * self.fs / self.TIMER_INTERVAL:
                self.bourder[0] = self.package_num
        if self.flag_frame_start and self.flag_pause:
            self.flag_frame_start = False
            self.bourder[1] = self.package_num  # frame end
            self.i = 0
            self.bourder = self.get_new_bourder(self.bourder)  # !!!!!!!!!!!!!!!!!!!!!!!!
            if self.bourder:
                # self.logger.info(
                #     f"\n\tbourders={self.bourder},count={self.count}")
                # self.bourder[1] = self.bourder[0] + (
                #     (self.bourder[1] - self.bourder[0]) // self.fs
                #     ) * self.fs
                # self.logger.info(f"\tnew bourders = {self.bourder}")
                # if (self.bourder[1] - self.bourder[0]) < self.fs:
                #     return
                [freq, amp, d_phase, tau] = self.fft_data(
                    gyro=gyro[self.bourder[0]:self.bourder[1]],
                    encoder=encoder[self.bourder[0]:self.bourder[1]], fs=self.fs)
                # self.check_180_degrees(freq, amp, d_phase)
                # self.amp_and_freq_for_plot = np.resize(
                #     self.amp_and_freq_for_plot, (self.count + self.add_points, 4))
                self.amp_and_freq_for_plot.resize(self.count_fft_frame, 4)  # !!!!!!!!!!!!!!!!!!!!!!!!!
                self.amp_and_freq_for_plot[(
                    self.count_fft_frame - 1), :] = [freq, amp, d_phase, tau]
                self.fft_data_emit.emit(True)
            else:
                self.logger.warning("Too small data frame!")
                self.amp_and_freq_for_plot.resize(self.count_fft_frame, 4)
                self.amp_and_freq_for_plot[(
                    self.count_fft_frame - 1), :] = [np.nan, np.nan, np.nan, np.nan]
            # self.amp_and_freq[(self.count - 1),
            #                   4*(self.cycle_count - 1):
            #                   4*self.cycle_count] = [freq, amp, d_phase, tau]
            # self.logger.info(
            #     f"\(self.count - 1) = {(self.count - 1)}, 4*(self.cycle_count - 1) = {4*(self.cycle_count - 1)}," +
            #     f"freq = {[freq, amp, d_phase, tau]}")
            # self.logger.info(f"self.amp_and_freq lin = {self.amp_and_freq[(self.count - 1), :]}")
            # self.logger.info(f"self.amp_and_freq lin = {self.amp_and_freq}")
            # self.logger.info(
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
                self.logger.info(f"freq180 = {self.freq180} " +
                                 f"ph = {0} " +
                                 f"amp180 = {amp180/100}")# +
                                #  f"fr = {0}\n interp={np.interp(self.freq180, [freq_prev, freq], [amp, amp_prev])}\
                                    #   {[freq_prev, freq]} {[amp_prev, amp]}\n {[d_phase_prev, d_phase]}")
            # if  (amp_prev < amp_w_c and amp > amp_w_c):
            #     self.freq_w_c[0], _ = self.point_on_line(
            #         [freq_prev, freq], [amp_prev, amp], amp_w_c)
            #     self.logger.info(f"freq_w_c[0] = {self.freq_w_c[0]}")
            # if (amp_prev > amp_w_c and amp < amp_w_c):
            #     self.freq_w_c[1], _ = self.point_on_line(
            #         [freq_prev, freq], [amp_prev, amp], amp_w_c)
            #     self.logger.info(f"freq_w_c[1] = {self.freq_w_c[1]}")
            # if  (freq_prev < 5 and freq > 5):
            #     self.freq_w_c[0], ddd = self.point_on_line(
            #         [freq_prev, freq], [amp_prev, amp], 5)
            #     # self.logger.info(f"freq_w_c[0] = {self.freq_w_c[0]}")
            #     self.logger.info(f"amp 5 = {self.freq_w_c[0]}")
            # if (freq > 10 and freq_prev < 10):
            #     self.freq_w_c[1], ddd = self.point_on_line(
            #         [freq_prev, freq], [amp_prev, amp], 10)
            #     # self.logger.info(f"freq_w_c[1] = {self.freq_w_c[1]}")
            #     self.logger.info(f"amp 10 = {self.freq_w_c[1]}")
        # self.f_Q = f_max / abs(self.freq_w_c[1] - self.freq_w_c[0])

    # @staticmethod
    def point_on_line(self, x: list, y: list, y_point_to_find=0):
        k = (x[0] - x[1]) / (y[0] - y[1])
        b = y[0] - k * x[0]
        res_x = (y_point_to_find - b) / k
        res_y = k * res_x + b      
        self.logger.info(f"y=k{k}*x+b{b}")  
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
                    self.logger.info(f"prev f = {freq_prev}, now f = {freq}, between = {freq180}")
                    d_phase += 2*np.pi
                    self.logger.info(f"prev ph = {phase_prev}, now ph = {d_phase}, amp = {amp180}")

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
        # gyro = np.divide(gyro, self.k_amp) 
        encoder = np.multiply(encoder, self.k_amp)

        L = len(gyro)  # длина записи
        next_power = np.ceil(np.log2(L))  # показатель степени 2 дл¤ числа длины записи
        NFFT = np.array([], dtype=int)
        NFFT = int(np.power(2, next_power))
        self.logger.info(
            f"\nNFFT {NFFT}, next_power {next_power}, len(gyro) {len(gyro)}")
        Yg = np.fft.fft(gyro, NFFT)/L  # преобразование Фурье сигнала гироскопа
        # Yg = np.fft.rfft(gyro, NFFT)/L  #
        Ye = np.fft.fft(encoder, NFFT)/L  # преобразование Фурье сигнала энкодера
        # Ye = np.fft.rfft(encoder, NFFT)/L  #
        f = fs/2 * np.linspace(0, 1, int(NFFT/2 + 1), endpoint=True)  # получение вектора частот
        #  delta_phase = asin(2*mean(encoder1.*gyro1)/(mean(abs(encoder1))*mean(abs(gyro1))*pi^2/4))*180/pi
        ng = np.argmax(abs(Yg[0:int(NFFT/2)]))
        Mg = 2 * abs(Yg[ng])
        # freq = f[ne]  # make sence?

        ne = np.argmax(abs(Ye[0:int(NFFT/2)]))
        Me = 2 * abs(Ye[ne])
        freq = f[ne]
        # self.logger.info(f"\tne {ne}, Me {Me}\tng {ng}, Mg {Mg}")

        d_phase = np.angle(Yg[ng], deg=False) - np.angle(Ye[ne], deg=False)
        amp = Mg/Me
        self.logger.info(
            f"FFt results\td_phase {d_phase}\tamp {amp}\tfreq {freq}")
        #  amp = std(gyro)/std(encoder)% пошуму (метод —урова)

        while d_phase > 0:
            d_phase -= 2 * np.pi
        while d_phase < -2 * np.pi:
            d_phase += 2 * np.pi
        d_phase = d_phase * 180/np.pi

        if 1.5 > freq > 0.5 and amp > 0:
            # a if condition else b
            if -200 < d_phase < -160:
                sign = -1
                d_phase += 180
            else:
                sign = 1
            self.logger.info(f"sign = {sign}")
            # if amp > 1.10 or amp < 0.9:
            self.k_amp = amp * sign
            amp = 1
            self.logger.info(f"k_amp = {self.k_amp}")
        
        tau = -1000 * d_phase / freq / 360
        self.logger.info(f"FFt\td_phase {d_phase}\ttau {tau}")
        return [freq, amp, d_phase, tau]
    
    def fft_from_file_median(self, file_list, fs):
        self.total_cycle_num = len(file_list)
        self.fs = fs
        self.cycle_count = 1
        # self.amp_and_freq = np.resize(self.amp_and_freq,
                                    #   (44, 4 * (self.total_cycle_num + 1)))
        for file in file_list:
            self.k_amp = 1
            self.logger.info(file)
            self.fft_for_file(file)
            if self.cycle_count == 1:
                # if int(self.amp_and_freq_for_plot.size / 4) > prev_len:
                    # print(self.amp_and_freq_for_plot.size/4)
                self.amp_and_freq = np.resize(
                    self.amp_and_freq,
                    (int(self.amp_and_freq_for_plot.size / 4),
                    4 * (self.total_cycle_num + 1)))
                self.amp_and_freq *= np.nan
            if self.total_cycle_num != self.cycle_count:
                self.new_cycle()
        self.save_fft(0)
        # self.fft_approximation()
        # # amp_max_i = np.argmax(self.amp_and_freq[:, -3])
        # # self.get_special_points(
        # #     f_max = self.amp_and_freq[amp_max_i, -4],
        # #     amp_w_c = 0.707 * self.amp_and_freq[amp_max_i, -3])
        # self.approximate_data_emit.emit(True)
        # # self.check_f_c()  
        # # name_part = ('' if self.GYRO_NUMBER == 1 else f"_{i + 1}")

    def fft_for_file(self, filename: str, threshold: int = 6100):
        min_frame_len = 1.75 * self.fs  # сколько времени минимум длится вибрация + пауза, при 1 работало
        g_filter = self.custom_g_filter(len=55, k=0.0065) * 1.45
        # threshold = 6000  # работает # = 6200   # работает
        # sz = 53 * os.path.getsize(filename)
        self.logger.info(f"start download")
        time_data = np.array(read_csv(filename, delimiter='\t',
                                      dtype=int, header=None)) #,
                                    #   keep_default_na=False,
                                    #   na_filter=False))
        # time_data = np.loadtxt(filename)
        self.logger.info(f"1, end download, file len {len(time_data)}")
        # time_data2 = (read_csv(filename, delimiter='\t',
        #                        dtype=np.int, header=None,
        #                     #    dtype={'a': np.uint32, 'b': np.int32, 'c': np.int32, 'd': np.uint16, 'e': np.uint16}, header=None,
        #                        decimal='.', skipinitialspace=True,
        #                        keep_default_na=False,
        #                        na_filter=False))  # na_values low_memory=False
        arr = np.greater(abs(time_data[:, 2]), threshold)
        self.logger.info("2")
        # arr = np.convolve(arr, self.custom_filter(45, 0.0075)*1.4, 'same')
        arr = np.convolve(arr, g_filter, 'same') # работает
        # arr = np.convolve(arr, self.custom_filter(75, 0.005)*1.55, 'same') # работает
        arr = np.round(arr)
        # arr = arr.astype(bool)
        self.logger.info("3")
        start = np.where((arr[:-1] == 0) & (arr[1:] == 1))[0]
        end = np.where((arr[:-1] == 1) & (arr[1:] == 0))[0]

        self.logger.info(f"4, len start = {len(start)}")
        real_start = np.where(np.diff(start) > min_frame_len)[0]
        start_arr = np.insert(start[real_start + 1], 0, start[0])

        real_end = np.where(np.diff(end) > min_frame_len)[0]
        end_arr = np.insert(end[real_end], len(end[real_end]), end[-1])
        self.logger.info(f"5, len real start = {len(real_start)}")
        for i in range(len(end_arr)):
            if i > 0:
                if start_arr[i] < end_arr[i - 1]:
                    self.logger.info(f"!!! start[{i}]={start_arr[i]}, end[{i}]={end_arr[i]}")
                    start_arr[i] = end_arr[i - 1]
            bourder = self.get_new_bourder([start_arr[i], end_arr[i]])
            if bourder:
                [freq, amp, d_phase, tau] = self.fft_data(
                    gyro=time_data[bourder[0]:bourder[1], 1],
                    encoder=time_data[bourder[0]:bourder[1], 2], fs=self.fs)
                # [freq, amp, d_phase, tau] = self.fft_data(
                #     gyro=time_data[start_arr[i]:end_arr[i], 1],
                #     encoder=time_data[start_arr[i]:end_arr[i], 2], fs=self.fs)
                # self.logger.info(f"start[{i}]={start_arr[i]}, end[{i}]={end_arr[i]}")
                self.logger.info(f"start[{i}]={bourder[0]}, end[{i}]={bourder[1]}")
                # self.check_180_degrees(freq, amp, d_phase)
                self.amp_and_freq_for_plot.resize(i + 1, 4)  #
                self.amp_and_freq_for_plot[i, :] = [freq, amp, d_phase, tau]
            else:
                self.logger.warning("Too small data frame!")
                self.amp_and_freq_for_plot.resize(i + 1, 4)
                self.amp_and_freq_for_plot[i, :] = [np.nan, np.nan, np.nan, np.nan]
        self.logger.info(f"\n fft end for {filename}")

    @staticmethod
    def custom_g_filter(len, k):
        if not len % 2:
            len = len + 1
        custom_filter = np.ndarray((len))
        custom_filter[int((len - 1)/2)] = 1
        for i in range(int((len - 1)/2)):
            custom_filter[int((len - 1)/2) - 1 - i] = np.exp(-k * np.power((i + 1), 2))
            custom_filter[int((len - 1)/2) + 1 + i] = custom_filter[int((len - 1)/2) - 1 - i]
        custom_filter = custom_filter/np.sum(custom_filter)
        return custom_filter

    def get_new_bourder(self, bourder):
        bourder[0] = bourder[1] - ((bourder[1] - bourder[0]) // self.fs) * self.fs
        self.logger.info(f"\tnew bourders = {bourder}")
        if (bourder[1] - bourder[0]) < self.fs:
            return []
        self.logger.info(f"before")
        return bourder

# if (not flag_end) and (np.absolute(self.all_data[self.package_num, 2]) < self.threshold):
#     if k > 750 and flag_start: #  and (self.package_num - k > self.bourder1[0]):
#         flag_end = True
#         self.bourder1[1] = self.package_num - k + 1
#         self.logger.info(
#             f"alt self.bourder stop = {self.bourder1}, k = {
#                 k}, data = {self.all_data[self.package_num - k, 2]}, package_num = {self.package_num}")
        
#         [amp, d_phase, freq] = self.fft_data(
#             self.all_data[self.bourder1[0]:self.bourder1[1], 2],
#             self.all_data[self.bourder1[0]:self.bourder1[1], 2], self.FS)
#         self.logger.info(
#             f"\namp = {amp}, self.d_phase = {d_phase}, freq = {freq}")
#         self.amp_and_freq = np.resize(self.amp_and_freq,
#                                         (self.count, 3))
#         self.amp_and_freq[(self.count - 1), :] = [amp, d_phase, freq]

#         self.amp_and_freq = self.amp_and_freq[self.amp_and_freq[:, 2].argsort()]
#         self.fft_data_emit.emit(True)
#     else:
#         k += 1
# else:
#     k = 0
# if flag_end and np.absolute(self.all_data[self.package_num, 2]) > self.threshold:
#     # self.logger.info(self.all_data[self.package_num, 2])
#     flag_end = False
#     flag_start = True
#     self.bourder1[0] = self.package_num + self.FS - 1
#     self.logger.info(
#         f"alt self.bourder start = {
#             self.bourder1}, data = {self.all_data[self.package_num, 2]}, package_num = {self.package_num}")
#     k = 0

    # def data_for_fft_graph_____(self, data: np.ndarray, gyro: np.ndarray, Fs):
    # #     fft_data = np.array([]) 
    # #     bourder = np.array([0, 0]) 
    # #     i = 0
    # #     flag_wait = False
    # #     if flag_sent:
    # #         flag_wait = True
    # #         i +=1
    # #         if i > 5:
    # #             bourder[0] = i
    # #     if flag_wait:
    # #         if not flag_sent:
    # #             flag_wait = False
    # #             bourder[1] = i
        
    #     # data = dlmread(fullfile(PathName,FileName));
    #     # encoder = data(:,3)./1000;
    #     # %
    #     # Flag = 0;
    #     # okno = 195;
    #     # R = zeros(2,2); % границы интервалов воздействия
    #     # k = 0;
    #     # l = 0;
    #     # porog = 3;
    #     # for i = 12000:okno:size(data,1)-2*okno
    #     #     if Flag == 0 % определение начала интервала воздействия
    #     #         D = std(encoder(i:i+okno,1));
    #     #         if D > porog
    #     #             k = k+1;
    #     #             R(k,1) = i + 3*okno;%2 + step
    #     #             Flag = 1;
    #     #         end
    #     #     end
    #     #     if Flag == 1 % определение конца интервала воздействия
    #     #         D = std(encoder(i:i+2*okno,1));%1
    #     #         if D < porog
    #     #             l = l+1;
    #     #             R(l,2) = i-2*okno;%1
    #     #             Flag = 0;
    #     #         end
    #     #     end
    #     # end
    #     # %
    #     # рассмотрим ситуацию, в которой нам известен промежуотк данных,
    #     # то есть, что ничего не надо выделять
    #     MK = -1
    #     Fs = Fs
    #     T = 1/Fs
    #     # for i in range(size(R,1):
    #     gyro = np.array(-gyro)
    #     encoder = np.divide(data, 1000)
    #     amp, d_phase, freq = self.fft_data(gyro, encoder, Fs)  # менял gyro на encoder  ampPhF( gyro,encoder,Fs );
    #     # end
    #     amp = amp/amp[0]  # нормирующий множитель: считаем, что при 1 Гц АЧХ=1
    #     # %%поиск максимальной амплитуды
    #     # [amp_max, i_max] = max(amp)
    #     i_max = np.argmax(amp)
    #     amp_max = amp[i_max]

    #     # поиск частоты среза (границы полосы пропускания)
    #     for i in range(len(amp)):
    #         if amp[i] < 0.707:
    #             n = i
    #             break
    #     # for i=1:size(amp,1)
    #     #     if amp(i,1)<0.707
    #     #         n = i;
    #     #         break
    #     #     end
    #     # end
    #     # if (exist('n','var')==1)
    #     # if  (n>1)
    #     # p = polyfit([amp(n-1,1) amp(n,1)],[freq(n-1,1) freq(n,1)],1);
    #     # Fpp = polyval(p,0.707); % частота среза
    #     # end
    #     # end

    #     # поиск частоты, при которой происходит сдвиг фазы на 180

    #     # dPh =  unwrap(d_phase(:,1))*180/pi;
    #     # for j=1:size(d_phase,1)
    #     #     if (dPh(j,1) < -180)
    #     #         nn = j;
    #     #         break
    #     #     end
    #     # end
    #     # if (exist('nn','var')==1)
    #     #     if (nn>1)
    #     # p = polyfit([dPh(nn-1,1) dPh(nn,1)],[freq(nn-1,1) freq(nn,1)],1);
    #     # Fh = polyval(p,-180); % частота, при которой происходит сдвиг фазы на 180
    #     #     end
    #     # end

    #     tau = 1000*dPh/freq/360 ## временная задержка

    #     return [freq, amp, dPh, tau]

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
        # # self.logger.info(
        # #     f"bandwidth_freq = {freq_approximation[bandwidth_index]}")
        # # # self.logger.info(bandwidth_index)
        # # # self.logger.info(amp_approximation[bandwidth_index])

        # # k_list = np.polyfit(freq, phase, order)
        # # fun = np.poly1d(k_list)
        # # phase_approximation = np.array(fun(freq_approximation))
        # # # f = np.deg2rad(f)
        # # phase_approximation = np.unwrap(phase_approximation)
        # # phase_approximation = np.rad2deg(phase_approximation)
        # # result = np.array([amp_approximation,
        # #                    phase_approximation, freq_approximation])
        
        # #  этап 1 - проверка на то, что все частоты +- совпадают
        # #  этап 2 - проверка на выбросы по амплитуде и частоте
        # #  формируется массив номеров опытов, которые требуется исключить
        # #  для данного значения частоты
        # self.mediana = np.ndarray((self.amp_and_freq.size))
        # cols_num = 4*(self.cycle_count + 1)
        # self.amp_and_freq = np.resize(self.amp_and_freq,
        #         (self.num_measurement_rows, cols_num))
        # self.amp_and_freq[:, cols_num:(cols_num + 4)] = np.nan
        # # можно результирующие значения не в отдельном массиве, а рядом записать
        # # self.temp = np.ndarray((self.amp_and_freq.size))
        # for i in range(len(self.amp_and_freq[:, 1])):  # цикл по всем частотам
        #     for j in range(4):  # надо вычислить среднее для A, f, fi, tay
        #         # self.temp = self.amp_and_freq[self.amp_and_freq[i, j:-1:4].argsort()]
        #         # [i, j:-1:4] - строка i, столбец j с шагом 4 до конца массива
        #         # так получиаем элементы из всех циклов
        #         self.amp_and_freq[i, cols_num + j] = np.nanmedian(self.amp_and_freq[i, j:-1:4])
        # self.approximate_data_emit.emit(True)         
        # # return result

    # def check_f_c(self):
        # self.freq180 = np.nan
        # self.freq_w_c = [np.nan, np.nan]
        # w_c = 0.707 * np.max(self.amp_and_freq[:, -3])
        # f = -180
        # for i in range(len(self.amp_and_freq[:, 1])):
        #     freq = self.amp_and_freq[i, -4]
        #     freq_prev = self.amp_and_freq[i - 1, -4]
        #     amp = self.amp_and_freq[i, -3]
        #     amp_prev = self.amp_and_freq[i - 1, -3]
        #     # amp_next = self.amp_and_freq[i + 1, -3]
        #     d_phase = self.amp_and_freq[i, -2]
        #     phase_prev = self.amp_and_freq[i - 1, -2]
        #     if (self.count + self.add_points - 1) >= 1:
        #         if (phase_prev > f and d_phase < f) or (phase_prev < f and d_phase > f):
        #             self.freq180, amp180 = self.point_on_line(
        #                 [phase_prev, d_phase], [freq_prev, freq], f)
        #             # k = (phase_prev - d_phase) / (freq_prev - freq)
        #             # b = phase_prev - k * freq_prev
        #             # self.freq180 = (- 180 - b)/k
        #             # amp180 = k * self.freq180 + b
        #             self.logger.info(f"freq180 = {self.freq180}")
        #             self.logger.info(f"amp180 = {amp180}")
        #         if  (amp_prev < w_c and amp > w_c):
        #             k = (amp_prev - amp) / (freq_prev - freq)
        #             b = amp_prev - k * freq_prev
        #             self.freq_w_c[0] = (w_c - b)/k
        #             self.logger.info(f"freq_w_c[0] = {self.freq_w_c[0]}")
        #             temp = self.freq_w_c[0]
        #             # if temp < self.freq_w_c[1]:
        #             #     self.freq_w_c[0] = temp
        #         if (amp_prev > w_c and amp < w_c):
        #             k = (amp_prev - amp) / (freq_prev - freq)
        #             b = amp_prev - k * freq_prev
        #             self.freq_w_c[1] = (w_c - b)/k
        #             self.logger.info(f"freq_w_c[1] = {self.freq_w_c[1]}")
        #             temp = self.freq_w_c[1]
        #             if temp < self.freq_w_c[1]:
        #                 self.freq_w_c[1] = temp
        # self.f_Q = abs(self.freq_w_c[1] - self.freq_w_c[0])
    
    # def fft_for_file(self, filename: str):
    #     # sz = 53 * os.path.getsize(filename)
    #     self.logger.info(f"start download")
    #     time_data = np.array(read_csv(filename, delimiter='\t', dtype=int, header=None))
    #     self.logger.info(f"end download, file len {len(time_data)}")
    #     # for i in range(int(len(matrix)/5 - 1)):
    #     # k = 1
    #     # k2 = 0
    #     # num = 1
    #     # flag = True
    #     # flag_start = False
    #     # # bourder: list[int] = [0, 0]
    #     # bourder: np.ndarray = np.array([0, 0], dtype=int)
    #     # threshold = 6000
    #     threshold = 6200  # можно меньше

    #     # for i in range(2, len(time_data), 3):
    #     #     # if np.greater(threshold, np.abs(time_data[i, 2])):
    #     #     if np.abs(time_data[i, 2]) < threshold:
    #     #         k2 = 0
    #     #         if (k > self.fs / 5) and flag_start:
    #     #             bourder[1] = i
    #     #             flag = True
    #     #         else:
    #     #             k += 3
    #     #     else:
    #     #         # if np.greater(np.abs(time_data[i - 1, 2]), threshold):
    #     #         if np.abs(time_data[i - 1, 2]) > threshold:
    #     #             k = 0
    #     #     # if flag and np.abs(time_data[i, 2]) >= threshold and np.abs(time_data[i - 1, 2]) >= threshold and np.abs(time_data[i - 2, 2]) >= threshold:
    #     #     if flag and np.abs(time_data[i, 2]) >= threshold:
    #     #     # if flag and np.greater(np.abs(time_data[i, 2]), threshold):
    #     #         k2 += 1
    #     #         # if k23 > 3:
    #     #         if k2 > 3:
    #     #             k2 = 0
    #     #             flag = False
    #     #             flag_start = True
    #     #             # if bourder[1]:
    #     #             if all(self.new_bourder(bourder)):
    #     #                 [freq, amp, d_phase, tau] = self.fft_data(
    #     #                     gyro=time_data[bourder[0]:bourder[1], 1],
    #     #                     encoder=time_data[bourder[0]:bourder[1], 2], fs=self.fs)
    #     #                 self.logger.info(f"now, num = {num}")
    #     #                 # self.check_180_degrees(freq, amp, d_phase)
    #     #                 self.amp_and_freq_for_plot.resize(num, 4)  # !!!!!!!!!!!!!!!!!!!!!!!!!
    #     #                 self.amp_and_freq_for_plot[(
    #     #                     num - 1), :] = [freq, amp, d_phase, tau]
    #     #                 num += 1
    #     #                 # print(f"num={num}, {bourder}, {[freq, amp, d_phase, tau]}")
    #     #             bourder[0] = i
    #     #             k = 0
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

    #     # self.logger.info("222")
    #     # with open(self.filename[0] + f'BBBB{self.cycle_count}' +
    #     #         self.filename[1], 'w') as file:
    #     #     np.savetxt(file, arr,
    #     #         delimiter='\t', fmt='%.3f')
    #     self.logger.info("2221")
    #     # arr = (np.convolve(arr, np.array([0.0125, 0.0125, 0.025, 0.025, 0.025, 0.0375, 0.05, 0.0625, 0.0625, 0.075, 0.075,
    #                                     #   0.075,
    #                                     #   0.075, 0.075, 0.0625, 0.0625, 0.05, 0.0375, 0.025, 0.025, 0.025, 0.0125, 0.0125]) * 1.23, 'same'))
    #     # arr = np.convolve(arr, self.custom_filter(45, 0.0075)*1.4, 'same')
    #     arr = np.convolve(arr, self.custom_filter(55, 0.0065)*1.45, 'same')
    #     # можно шире, более размыто и умножать на больший коэффициент
    #     self.logger.info("2223") # 
    #     arr = np.round(arr)
    #     self.logger.info("2225")
    #     start = np.where((arr[:-1] == 0) & (arr[1:] == 1))[0]
    #     end = np.where((arr[:-1] == 1) & (arr[1:] == 0))[0]
        
    #     # print(start)
    #     # print(end)
    #     # with open(self.filename[0] + f'round{self.cycle_count}' +
    #     #         self.filename[1], 'w') as file:
    #     #      np.savetxt(file, arr,
    #     #         delimiter='\t', fmt='%.3f')
    #     self.logger.info("2227")
    #     # k = 1
    #     d = np.diff(start)
    #     # print(f"d = {d}")
    #     real_start = np.where(d > self.fs)[0]
    #     d = np.diff(end)
    #     # print(f"d end = {d}")

    #     real_end = np.where(d > self.fs)[0]
    #     # print(f"real_end = {end[real_end]}")  # + fistr start
    #     # for i in real:
    #         # print(end[i])
    #     # print(start[real])
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
    #         # self.logger.info(f"now, num = {num}")
    #         # self.check_180_degrees(freq, amp, d_phase)
    #         # self.amp_and_freq_for_plot = np.resize(
    #         #     self.amp_and_freq_for_plot, (self.count + self.add_points, 4))
    #         self.amp_and_freq_for_plot.resize(i+1, 4)  # !!!!!!!!!!!!!!!!!!!!!!!!!
    #         self.amp_and_freq_for_plot[(i), :] = [freq, amp, d_phase, tau]
    #     self.logger.info(f"\n !!!!!!!!!!!!!!!!!! {filename}")
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
        #     # self.logger.info(f"now, num = {num}")
        #     # self.check_180_degrees(freq, amp, d_phase)
        #     # self.amp_and_freq_for_plot = np.resize(
        #     #     self.amp_and_freq_for_plot, (self.count + self.add_points, 4))
        #     self.amp_and_freq_for_plot.resize(num, 4)  # !!!!!!!!!!!!!!!!!!!!!!!!!
        #     self.amp_and_freq_for_plot[(
        #         num - 1), :] = [freq, amp, d_phase, tau]
        # print(f"num={num}, {bourder}, {[freq, amp, d_phase, tau]}")
        # print(self.amp_and_freq_for_plot)
        # print(f"{time_data[i, 3]}, {time_data[i + 1, 3]}, {i}, amp = {time_data[i, 4]}")
