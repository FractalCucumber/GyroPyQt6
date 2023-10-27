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

        self.all_data = np.array([], dtype=np.int32)
        self.ftt_data = np.array([])  #, dtype=np.complex128)

    def run(self):
        self.package_num = 0
        first = True
        while self.flag_start or self.flag_recieve:
            if not self.flag_recieve:
                self.msleep(5)
            if self.flag_recieve:
                i = self.rx.find(0x72)
                logging.info(f"thread_run_start, len {len(self.rx)}")

                if first:
                    first = False
                    self.all_data = np.array(
                        [self.int_from_bytes(self.rx, i, self.package_num)])
                    i += 14
                    self.package_num += 1

                while ((i + 13) < len(self.rx)
                       and (self.rx[i] == 0x72 and self.rx[i + 13] == 0x27)):
                    # check flag
                    nums = np.array(
                        [self.int_from_bytes(self.rx, i, self.package_num)])
                    i += 14
                    self.all_data = np.vstack([self.all_data, nums])
                    self.package_num += 1

                logging.info(f"len = {self.all_data.size}")
                # print("dt_0 = ", time.time() - t1)
                self.package_num_signal.emit(self.package_num)
                self.flag_recieve = False
        with open(self.filename, 'a') as file:
            np.savetxt(file, self.all_data, delimiter='\t', fmt='%d')

        self.fft_data(gyro=self.all_data[:, 2],
                      encoder=self.all_data[:, 2],
                      FS=2000)

    def data_for_fft_graph(self, data: np.ndarray, gyro: np.ndarray, Fs):
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

    def fft_data(self, gyro: np.ndarray, encoder: np.ndarray, FS):
        #   AmpPhF Summary of this function goes here
        #   Detailed explanation goes here
        #   Amp [безразмерна¤]- соотношение амплитуд воздействи¤ (encoder)
        #   и реакции гироскопа(gyro) = gyro/encoder
        #   dPhase [радианы] - разница фаз = gyro - encoder
        #   Freq [√ц] - частота гармоники (воздействия)
        #
        #   gyro [град/с] - показани¤ гироскопа во время гармонического воздействия
        #   encoder [град/с] - показани¤ энкодера, задающего гармоническое воздействие
        #   FS [√ц] - частота дискретизации

        # T = 1/FS
        L = len(gyro)  # L = size(gyro,1);  # длина записи
        # t = (0:L-1)*T  # вектор времени
        # t = np.arrange(0, L - 1, 1) * T
        NFFT = np.array([])
        for i in range(L):
            NFFT = np.append(NFFT, self.next_power_of_2(i))  # 2^nextpow2(L)   # показатель степени 2 дл¤ числа длины записи
        logging.info(f"NFFT {NFFT}")
        Yg = np.fft.fft(gyro, NFFT)/L  # преобразование Фурье сигнала гироскопа
        Ye = np.fft.fft(encoder, NFFT)/L  # преобразование Фурье сигнала энкодера
        f = FS/2 * np.linspace(0, 1, NFFT/2 + 1, endpoint=True)  # получение вектора частот
        logging.info(f"Yg {Yg}")
        #  delta_phase = asin(2*mean(encoder1.*gyro1)/(mean(abs(encoder1))*mean(abs(gyro1))*pi^2/4))*180/pi
        # [Mg, ng] = max(2*abs(Yg[1:(NFFT/2 + 1)]))
        ng = np.argmax(2*abs(Yg[0:(NFFT/2)]))
        Mg = Yg[ng]

        Freq = f[0, ng]
        [Me, ne] = max(2*abs(Ye[0:(NFFT/2)]))
        # Fe = f[1, ne]

        dPhase = (np.angle((Yg(ng, 0)), deg=False) -
                  np.angle((Ye(ne, 0)), deg=False))
        #  dPhase = (atan2(imag(Yg(ng,1)), real(Yg(ng,1)))-atan2(imag(Ye(ne,1)), real(Ye(ne,1))));
        Amp = Mg/Me
        #  Amp = std(gyro)/std(encoder)% пошуму (метод —урова)
        with open("fft.txt", 'a') as file:
            np.savetxt(file, [Amp, dPhase, Freq], delimiter='\t', fmt='%d')
        return [Amp, dPhase, Freq]

    def next_power_of_2(self, x):
        return 1 if x == 0 else 2**(x - 1).bit_length()

    def int_from_bytes(self, rx, i, package_num):
        ints = np.array([package_num], dtype=np.int32)
        for shift in [1, 4, 7, 10]:
            res = int.from_bytes(
                rx[(i + shift):(i + shift + 3)],
                byteorder='big', signed=True)
            ints = np.append(ints, res)
        return ints
