from PyQt6 import QtCore
# import PyQt6.QtCore.QThread.pyqtSignalSlot
import numpy as np
from PyQt6.QtSerialPort import QSerialPort
import pyqtgraph as pg
import logging
import time


class MyThread(QtCore.QThread):
    package_num_signal = QtCore.pyqtSignal(int)

    def __init__(self):
        # QtCore.QThread.__init__(self)
        super(MyThread, self).__init__()
        self.filename = []
        self.flag_start = False
        self.flag_recieve = False
        self.rx: bytes = b''
        self.amp_and_freq = np.ndarray([]) # ???
        # self.all_data = np.array([], dtype=np.int32)
        self.size_change_step = 20000

        # for fft
        self.FS = []
        self.TIMER_INTERVAL = []
        self.flag_sent = []

        self.logger = logging.getLogger('main')

    def run(self):
        self.num_rows = 0
        self.package_num = 0
        self.all_data = np.ndarray((self.size_change_step, 5), dtype=int)
        self.ftt_data = np.array([])  #, dtype=np.complex128)

        self.count = 1
        self.i = 0
        self.flag_wait = False
        self.flag_sent = False
        self.bourder = np.array([0, 0])
        # self.amp_and_freq = np.ndarray([]) # ???
        # first = True
        while self.flag_start or self.flag_recieve:
            if not self.flag_recieve:
                self.msleep(5)
            if self.flag_recieve:
                i = self.rx.find(0x72)
                self.logger.info(f"thread_run_start, len rx = {len(self.rx)}, i = {i}")

                # while ((i + 13) < len(self.rx)
                #        and (self.rx[i] == 0x72 and self.rx[i + 13] == 0x27)):
                while (i + 13) < len(self.rx):
                    if not (self.rx[i] == 0x72 and self.rx[i + 13] == 0x27):
                        self.logger.info(f"before i = {i}, 0x72:{self.rx[i] == 0x72}, 0x27:{self.rx[i + 13] == 0x27}")
                        i += self.rx[i:].find(0x27) + 1
                        self.logger.info(f"now i = {i}, 0x72:{self.rx[i] == 0x72}, 0x27:{self.rx[i + 13] == 0x27}")
                        continue  # ???
                        
                    # check flag
                    nums = np.array(
                        [self.int_from_bytes(self.rx, i, self.package_num)])
                    i += 14
                    self.all_data[self.package_num, :] = nums
                    # self.all_data = np.vstack([self.all_data, nums])
                    self.package_num += 1
                    if self.package_num >= self.num_rows:
                        self.num_rows += self.size_change_step
                        self.all_data = np.resize(self.all_data,
                                                  (self.num_rows, 5))

                self.logger.info(f"\t\treal package_num = {self.package_num}")
                # print("dt_0 = ", time.time() - t1)
                self.package_num_signal.emit(self.package_num)
                self.flag_recieve = False

                self.data_for_fft_graph(
                    self.all_data[:, 2],
                    self.all_data[:, 2],
                    self.FS)
                
        self.all_data = np.resize(self.all_data, (self.package_num, 5))
        with open(self.filename, 'w') as file:
            np.savetxt(file, self.all_data, delimiter='\t', fmt='%d')

        self.logger.info(f"\t\tFFT = {self.amp_and_freq}")
        with open("FFT2.txt", 'w') as file:
            np.savetxt(file, self.amp_and_freq, delimiter='\t', fmt='%d')

        # self.fft_data(gyro=self.all_data[:, 2],
        #               encoder=self.all_data[:, 2],
        #               FS=2000)

    def data_for_fft_graph_____(self, data: np.ndarray, gyro: np.ndarray, Fs):
    #     ftt_data = np.array([]) 
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
        Amp, dPhase, Freq = self.fft_data(gyro, encoder, Fs)  # менял gyro на encoder  AmpPhF( gyro,encoder,Fs );
        # end
        Amp = Amp/Amp[0]  # нормирующий множитель: считаем, что при 1 Гц АЧХ=1
        # %%поиск максимальной амплитуды
        # [Amp_max, i_max] = max(Amp)
        i_max = np.argmax(Amp)
        Amp_max = Amp[i_max]

        # поиск частоты среза (границы полосы пропускания)
        for i in range(len(Amp)):
            if Amp[i] < 0.707:
                n = i
                break
        # for i=1:size(Amp,1)
        #     if Amp(i,1)<0.707
        #         n = i;
        #         break
        #     end
        # end
        # if (exist('n','var')==1)
        # if  (n>1)
        # p = polyfit([Amp(n-1,1) Amp(n,1)],[Freq(n-1,1) Freq(n,1)],1);
        # Fpp = polyval(p,0.707); % частота среза
        # end
        # end

        # поиск частоты, при которой происходит сдвиг фазы на 180

        # dPh =  unwrap(dPhase(:,1))*180/pi;
        # for j=1:size(dPhase,1)
        #     if (dPh(j,1) < -180)
        #         nn = j;
        #         break
        #     end
        # end
        # if (exist('nn','var')==1)
        #     if (nn>1)
        # p = polyfit([dPh(nn-1,1) dPh(nn,1)],[Freq(nn-1,1) Freq(nn,1)],1);
        # Fh = polyval(p,-180); % частота, при которой происходит сдвиг фазы на 180
        #     end
        # end

        tau = 1000*dPh/Freq/360 ## временная задержка

        return [Freq, Amp, dPh, tau]

    def data_for_fft_graph(self, encoder: np.ndarray, gyro: np.ndarray, FS):
        # fft_data = np.array([]) 
        if not self.flag_sent:
            self.flag_wait = True
            self.i += 1
            if self.i < 1*1000/self.TIMER_INTERVAL:
                self.bourder[0] = self.package_num
        if self.flag_wait:
            if self.flag_sent:
                self.flag_wait = False
                self.bourder[1] = self.package_num
                self.i = 0
                self.logger.info(
                    f"\n\tbourders = {self.bourder}, self.count = {self.count}")

                [Amp, dPhase, Freq] = self.fft_data(
                    gyro[self.bourder[0]:self.bourder[1]],
                    encoder[self.bourder[0]:self.bourder[1]],
                    FS)
                self.logger.info(
                    f"\nAmp = {Amp}, self.dPhase = {dPhase}")
                self.amp_and_freq = np.resize(self.amp_and_freq,
                                              (self.count, 3))
                self.amp_and_freq[(self.count - 1), :] = [Amp, dPhase, Freq]
        # return [Amp, dPhase, Freq]
        return [1, 2, 3]

    def fft_data(self, gyro: np.ndarray, encoder: np.ndarray, FS):
        #   AmpPhF Summary of this function goes here
        #   Detailed explanation goes here
        #   Amp [безразмерна¤]- соотношение амплитуд воздействи¤ (encoder)
        #   и реакции гироскопа(gyro) = gyro/encoder
        #   dPhase [радианы] - разница фаз = gyro - encoder
        #   Freq [√ц] - частота гармоники (воздействия)
        #   gyro [град/с] - показани¤ гироскопа во время гармонического воздействия
        #   encoder [град/с] - показани¤ энкодера, задающего гармоническое воздействие
        #   FS [√ц] - частота дискретизации

        # T = 1/FS
        L = len(gyro)  # L = size(gyro,1);  # длина записи
        # t = (0:L-1)*T  # вектор времени
        # t = np.arrange(0, L - 1, 1) * T
        NFFT = np.array([], dtype=int)
        next_power = np.ceil(np.log2(L))  # показатель степени 2 дл¤ числа длины записи
        NFFT = int(np.power(2, next_power))
        self.logger.warning(f"\nNFFT {NFFT}, next_power {next_power}, len(gyro) {len(gyro)}")
        Yg = np.fft.fft(gyro, NFFT)/L  # преобразование Фурье сигнала гироскопа
        Ye = np.fft.fft(encoder, NFFT)/L  # преобразование Фурье сигнала энкодера
        f = FS/2 * np.linspace(0, 1, int(NFFT/2 + 1), endpoint=True)  # получение вектора частот
        self.logger.info(f"\nYe {Ye}\tYg {Yg}")
        #  delta_phase = asin(2*mean(encoder1.*gyro1)/(mean(abs(encoder1))*mean(abs(gyro1))*pi^2/4))*180/pi
        ng = np.argmax(Yg[0:int(NFFT/2)])
        Mg = 2*abs(Yg[ng])
        Freq = f[ng]
        
        ne = np.argmax(Ye[0:int(NFFT/2)])
        Me = 2*abs(Ye[ne])
        self.logger.info(f"\tMe {Me} \tMg {Mg}")

        dPhase = np.angle(Yg[ng], deg=False) - np.angle(Ye[ne], deg=False)
        Amp = Mg/Me
        self.logger.info(f"FFt results\tPhase {dPhase}\tAmp {Amp}\tFreq {Freq}")
        #  Amp = std(gyro)/std(encoder)% пошуму (метод —урова)

        # with open("fft.txt", 'a') as file:
        #     np.savetxt(file, [Amp, dPhase, Freq], delimiter='\t', fmt='%d')

        return [Amp, dPhase, Freq]

    @staticmethod
    def int_from_bytes(rx, i, package_num):
        ints = np.array([package_num], dtype=np.int32)
        for shift in [1, 4, 7, 10]:
            res = int.from_bytes(
                rx[(i + shift):(i + shift + 3)],
                byteorder='big', signed=True)
            ints = np.append(ints, res)
        return ints
