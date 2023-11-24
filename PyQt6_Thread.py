from PyQt6 import QtCore
import numpy as np
# from PyQt6.QtSerialPort import QSerialPort
# import pyqtgraph as pg
import logging


class MyThread(QtCore.QThread):
    package_num_signal = QtCore.pyqtSignal(int)
    fft_data_emit = QtCore.pyqtSignal(bool)
    approximate_data_emit = QtCore.pyqtSignal(bool)

    def __init__(self, gyro_number=3):
        # QtCore.QThread.__init__(self)
        super(MyThread, self).__init__()
        self.GYRO_NUMBER = gyro_number
        self.filename: list(str) = ["", ""]
        self.flag_start = False
        self.flag_recieve = False
        self.rx: bytes = b''
        self.amp_and_freq_for_plot = np.array([])  # ???
        # self.all_data = np.array([], dtype=np.int32)
        self.SIZE_EXTENTION_STEP = 20000

        self.fs = []
        self.TIMER_INTERVAL = []
        self.flag_pause: bool = []

        self.logger = logging.getLogger('main')
        # self.approximate = np.array([])

    def run(self):
        self.cycle_count = 1
        self.num_rows = 0
        self.package_num = 0
        self.all_data = np.ndarray((self.SIZE_EXTENTION_STEP, 5), dtype=np.int32)
        # self.fft_data = np.ndarray((, 2))

        self.count = 1
        self.i = 0
        self.flag_sequence_start = False
        self.flag_pause = False
        self.bourder = np.array([0, 0])
        self.amp_and_freq_for_plot = np.array([])
        self.amp_and_freq = np.array([])
        self.approximate = np.array([])

        self.add_points = 0
        # self.threshold = 6000
        # k = 0
        # flag_start = False
        # flag_end = True
        # self.bourder1 = np.array([0, 0])
        self.WAIT_TIME_SEC = 1
        while self.flag_start or self.flag_recieve:
            if not self.flag_recieve:
                self.msleep(5)

            if self.flag_recieve:
                i = self.rx.find(0x72)
                self.logger.info(
                    f"thread_run_start, len rx = {len(self.rx)}, i = {i}")

                while (i + 13) < len(self.rx):
                    if not (self.rx[i] == 0x72 and self.rx[i + 13] == 0x27):
                        self.logger.info(f"before i = {i}, 0x72:{self.rx[i] == 0x72}, 0x27:{self.rx[i + 13] == 0x27}")
                        i += self.rx[i:].find(0x27) + 1
                        self.logger.info(f"now i = {i}, 0x72:{self.rx[i] == 0x72}, 0x27:{self.rx[i + 13] == 0x27}")
                        continue

                    self.all_data[self.package_num, :] = np.array(
                        [self.int_from_bytes(self.rx, i, self.package_num)])

                    i += 14
                    self.package_num += 1
                    self.extend_array_size()

                self.logger.info(f"\t\treal package_num = {self.package_num}")
                self.package_num_signal.emit(self.package_num)
                self.flag_recieve = False

                self.data_for_fft_graph(encoder=self.all_data[:, 2],
                                        gyro=self.all_data[:, 1],
                                        FS=self.fs)

        self.all_data = np.resize(self.all_data, (self.package_num, 5))
        for i in range(self.GYRO_NUMBER):
            with open(self.filename[0] + f"_{i + 1}" + self.filename[1], 'w') as file:
                np.savetxt(file, self.all_data, delimiter='\t', fmt='%d')

        self.logger.info(f"\tFFT = {str(self.amp_and_freq_for_plot)}")
        self.logger.info(f"\tfft size = {self.amp_and_freq_for_plot.size}")
        if self.amp_and_freq_for_plot.size:
            with open(self.filename[0] + '_FFT' + self.filename[1], 'w') as file:
                np.savetxt(file, self.amp_and_freq_for_plot,
                           delimiter='\t', fmt='%.3f')
            # self.fft_data(gyro=self.all_data[:, 2],
            #               encoder=self.all_data[:, 2],
            #               FS=2000)
            # self.approximate = np.array(self.fft_approximation(self.amp_and_freq[:, 0],
            #                             self.amp_and_freq[:, 2],
            #                             self.amp_and_freq[:, 1]))
            # self.approximate_data_emit.emit(True)

        self.logger.info("Tread stop")

    def extend_array_size(self):
        if self.package_num >= self.num_rows:
            self.num_rows += self.SIZE_EXTENTION_STEP
            self.all_data = np.resize(
                self.all_data, (self.num_rows, 5))

    def new_cycle(self):
        self.count = 0
        self.add_points = 0
        self.bourder = np.array([0, 0])
        self.amp_and_freq_for_plot = np.array([])
        self.approximate = np.array([])
        self.cycle_count += 1
        self.amp_and_freq = np.resize(
                self.amp_and_freq,
                (self.count + self.add_points, 3*self.cycle_count))
        self.amp_and_freq[:, 3*self.cycle_count:(3*self.cycle_count + 3)] = self.amp_and_freq[:, 0:3]

    @staticmethod
    def int_from_bytes(rx, i, package_num):
        ints = np.array([package_num], dtype=np.int32)
        # ints = np.resize(ints, (1, 5))
        for shift in [1, 4, 7, 10]:
            res = int.from_bytes(
                rx[(i + shift):(i + shift + 3)],
                byteorder='big', signed=True)
            ints = np.append(ints, res)
        return ints

    def fft_approximation(self, freq, amp, phase):
        freq_approximation = np.linspace(freq[0], freq[-1], num=100)
        order = 4
        k_list = np.polyfit(freq, amp, order)
        fun = np.poly1d(k_list)
        # np.roots(k_list)
        # amp_approximation = fun(freq_values)
        # f = [1, 5, 20, 50]
        # amp = [1, 0.9, 0.7, 0.2]
        # k_list = np.polyfit(f, amp, 5)
        # fun = np.poly1d(k_list)
        # R = np.roots(k_list)
        # freq_values = np.linspace(f[0], f[-1], 20)
        amp_approximation = np.array(fun(freq_approximation))
        abs_amp = np.abs(amp_approximation - 0.707)
        bandwidth_index = np.argmin(abs_amp)
        self.logger.info(
            f"bandwidth_freq = {freq_approximation[bandwidth_index]}")
        # self.logger.info(amp_approximation)
        # self.logger.info(R)
        # self.logger.info(bandwidth_index)
        # self.logger.info(amp_approximation[bandwidth_index])

        k_list = np.polyfit(freq, phase, order)
        fun = np.poly1d(k_list)
        phase_approximation = np.array(fun(freq_approximation))
        # f = np.deg2rad(f)
        phase_approximation = np.unwrap(phase_approximation)
        # phase_approximation = np.rad2deg(phase_approximation)
        result = np.array([amp_approximation,
                           phase_approximation, freq_approximation])
        return result

    def data_for_fft_graph_____(self, data: np.ndarray, gyro: np.ndarray, Fs):
    #     fft_data = np.array([]) 
    #     bourder = np.array([0, 0]) 
    #     i = 0
    #     flag_wait = False
    #     if flag_sent:
    #         flag_wait = True
    #         i +=1
    #         if i > 5:
    #             bourder[0] = i
    #     if flag_wait:
    #         if not flag_sent:
    #             flag_wait = False
    #             bourder[1] = i
        
        # data = dlmread(fullfile(PathName,FileName));
        # encoder = data(:,3)./1000;
        # %
        # Flag = 0;
        # okno = 195;
        # R = zeros(2,2); % границы интервалов воздействия
        # k = 0;
        # l = 0;
        # porog = 3;
        # for i = 12000:okno:size(data,1)-2*okno
        #     if Flag == 0 % определение начала интервала воздействия
        #         D = std(encoder(i:i+okno,1));
        #         if D > porog
        #             k = k+1;
        #             R(k,1) = i + 3*okno;%2 + step
        #             Flag = 1;
        #         end
        #     end
        #     if Flag == 1 % определение конца интервала воздействия
        #         D = std(encoder(i:i+2*okno,1));%1
        #         if D < porog
        #             l = l+1;
        #             R(l,2) = i-2*okno;%1
        #             Flag = 0;
        #         end
        #     end
        # end
        # %
        # рассмотрим ситуацию, в которой нам известен промежуотк данных,
        # то есть, что ничего не надо выделять
        MK = -1
        Fs = Fs
        T = 1/Fs
        # for i in range(size(R,1):
        gyro = np.array(-gyro)
        encoder = np.divide(data, 1000)
        amp, d_phase, freq = self.fft_data(gyro, encoder, Fs)  # менял gyro на encoder  ampPhF( gyro,encoder,Fs );
        # end
        amp = amp/amp[0]  # нормирующий множитель: считаем, что при 1 Гц АЧХ=1
        # %%поиск максимальной амплитуды
        # [amp_max, i_max] = max(amp)
        i_max = np.argmax(amp)
        amp_max = amp[i_max]

        # поиск частоты среза (границы полосы пропускания)
        for i in range(len(amp)):
            if amp[i] < 0.707:
                n = i
                break
        # for i=1:size(amp,1)
        #     if amp(i,1)<0.707
        #         n = i;
        #         break
        #     end
        # end
        # if (exist('n','var')==1)
        # if  (n>1)
        # p = polyfit([amp(n-1,1) amp(n,1)],[freq(n-1,1) freq(n,1)],1);
        # Fpp = polyval(p,0.707); % частота среза
        # end
        # end

        # поиск частоты, при которой происходит сдвиг фазы на 180

        # dPh =  unwrap(d_phase(:,1))*180/pi;
        # for j=1:size(d_phase,1)
        #     if (dPh(j,1) < -180)
        #         nn = j;
        #         break
        #     end
        # end
        # if (exist('nn','var')==1)
        #     if (nn>1)
        # p = polyfit([dPh(nn-1,1) dPh(nn,1)],[freq(nn-1,1) freq(nn,1)],1);
        # Fh = polyval(p,-180); % частота, при которой происходит сдвиг фазы на 180
        #     end
        # end

        tau = 1000*dPh/freq/360 ## временная задержка

        return [freq, amp, dPh, tau]

    def data_for_fft_graph(self, encoder: np.ndarray, gyro: np.ndarray, FS):
        # fft_data = np.array([])
        if not self.flag_pause:
            self.flag_sequence_start = True
            self.i += 1
            if self.i < self.WAIT_TIME_SEC*self.fs/self.TIMER_INTERVAL:
                self.bourder[0] = self.package_num
        if self.flag_sequence_start and self.flag_pause:
            self.flag_sequence_start = False
            self.bourder[1] = self.package_num
            self.i = 0
            self.logger.info(
                f"\n\tbourders = {self.bourder}, self.count = {self.count}")

            self.bourder[1] = self.bourder[0] + ((self.bourder[1] - self.bourder[0]) // self.fs) * self.fs
            self.logger.info(
                f"\n\tnew bourders = {self.bourder}")
            if (self.bourder[1] - self.bourder[0]) < 500:
                return
            [amp, d_phase, freq] = self.fft_data(
                gyro[self.bourder[0]:self.bourder[1]],
                encoder[self.bourder[0]:self.bourder[1]], FS)
            self.logger.info(
                f"\namp = {amp}, self.d_phase = {d_phase}, freq = {freq}")

            if (self.count + self.add_points - 1) >= 1:
                amp_prev = self.amp_and_freq_for_plot[(self.count + self.add_points - 2), 0]
                phase_prev = self.amp_and_freq_for_plot[(self.count + self.add_points - 2), 1]
                freq_prev = self.amp_and_freq_for_plot[(self.count + self.add_points - 2), 2]
                if abs(phase_prev - d_phase) > 5/4*np.pi:
                    self.add_points += 2
                    self.amp_and_freq_for_plot = np.resize(
                        self.amp_and_freq_for_plot, (self.count + self.add_points, 3))

                    if not (freq_prev - freq == 0):
                        d_phase += -2*np.pi
                        k = (phase_prev - d_phase) / (freq_prev - freq)
                        b = phase_prev - k * freq_prev
                        freq180 = (- np.pi - b)/k
                        k = (amp_prev - amp) / (freq_prev - freq)
                        b = amp_prev - k * freq_prev
                        amp180 = k * freq180 + b
                        self.amp_and_freq_for_plot[(self.count + self.add_points - 3), :] = [amp180, -np.pi, freq180]
                        self.amp_and_freq_for_plot[(self.count + self.add_points - 2), :] = [amp180, np.pi, freq180]
                        self.logger.info(f"prev f = {freq_prev}, now f = {freq}, between = {freq180}")
                        d_phase += 2*np.pi
                        self.logger.info(f"prev ph = {phase_prev}, now ph = {d_phase}, amp = {amp180}")

            self.amp_and_freq_for_plot = np.resize(self.amp_and_freq_for_plot,
                                    (self.count + self.add_points, 3))
            self.amp_and_freq_for_plot[(self.count + self.add_points - 1), :] = [amp, d_phase, freq]

            self.amp_and_freq_for_plot = self.amp_and_freq_for_plot[self.amp_and_freq_for_plot[:, 2].argsort()]
            self.fft_data_emit.emit(True)
        # return [amp, d_phase, freq]

    def fft_data(self, gyro: np.ndarray, encoder: np.ndarray, FS):
        """
        Detailed explanation goes here:
        amp [безразмерная]- соотношение амплитуд воздействия (encoder)
        и реакции гироскопа(gyro) = gyro/encoder
        d_phase [радианы] - разница фаз = gyro - encoder
        freq [√ц] - частота гармоники (воздействия)
        gyro [град/с] - показания гироскопа во время гармонического воздействия
        encoder [град/с] - показания энкодера, задающего гармоническое воздействие
        FS [√ц] - частота дискретизации
        """
        gyro = np.array(-gyro)
        encoder = np.divide(encoder, 10)

        L = len(gyro)  # длина записи
        next_power = np.ceil(np.log2(L))  # показатель степени 2 дл¤ числа длины записи
        NFFT = np.array([], dtype=int)
        NFFT = int(np.power(2, next_power))
        self.logger.info(
            f"\nNFFT {NFFT}, next_power {next_power}, len(gyro) {len(gyro)}")
        Yg = np.fft.fft(gyro, NFFT)/L  # преобразование Фурье сигнала гироскопа
        Ye = np.fft.fft(encoder, NFFT)/L  # преобразование Фурье сигнала энкодера
        f = FS/2 * np.linspace(0, 1, int(NFFT/2 + 1), endpoint=True)  # получение вектора частот
        #  delta_phase = asin(2*mean(encoder1.*gyro1)/(mean(abs(encoder1))*mean(abs(gyro1))*pi^2/4))*180/pi
        ng = np.argmax(abs(Yg[0:int(NFFT/2)]))
        Mg = 2*abs(Yg[ng])
        # freq = f[ne]  # make sence?

        ne = np.argmax(abs(Ye[0:int(NFFT/2)]))
        Me = 2*abs(Ye[ne])
        freq = f[ne]
        self.logger.info(f"\tne {ne}, Me {Me}\tng {ng}, Mg {Mg}")

        # with open("FFT_res_e.txt", 'a') as file:
        #     np.savetxt(file, np.array([Ye]), delimiter='\t', fmt='%.3f')
        # with open("FFT_res_g.txt", 'a') as file:
        #     np.savetxt(file, np.array([Yg]), delimiter='\t', fmt='%.3f')

        d_phase = np.angle(Yg[ng], deg=False) - np.angle(Ye[ne], deg=False)
        amp = Mg/Me
        self.logger.info(
            f"FFt results\tPhase {d_phase}\tamp {amp}\tfreq {freq}")
        #  amp = std(gyro)/std(encoder)% пошуму (метод —урова)

        while d_phase > np.pi:
            d_phase -= 2*np.pi
        while d_phase < -np.pi:
            d_phase += 2*np.pi
        return [amp, d_phase, freq]

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