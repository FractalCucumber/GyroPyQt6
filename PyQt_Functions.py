# cSpell:includeRegExp #.*
# cSpell:includeRegExp /(["]{3}|[']{3})[^\1]*?\1/g

import os
import re
import sys
import numpy as np
from PyQt5.QtGui import QIcon
# from numba import jit, prange, njit


def natural_keys(text):
    def atoi(text):
        return int(text) if text.isdigit() else text
    return [atoi(c) for c in re.split(r'(\d+)', text)]

def get_res_path(relative_path: str):
    """
    Get absolute path to resource, works with PyInstaller
    """
    base_path = getattr(
        sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

get_icon_by_name = lambda name: QIcon(get_res_path(f'res/{name}.png'))

# def get_icon_by_name(name):
    # return QIcon(get_res_path(f'res/{name}.png'))

def check_name_simple(name: str):
    basename, extension = os.path.splitext(name)
    # print('dir ' + os.path.dirname(name))
    # print('exist ' + os.path.isdir(os.path.dirname(name)))
    # if not os.path.isdir(os.path.dirname(name)):
        # return ""
    i = 0
    while os.path.exists(name):
        i += 1
        name = basename + f"({i})" + extension
    return name

def custom_g_filter(len: int, k: float):
    if not len % 2:
        len = len + 1
    custom_filter = np.ndarray((len))
    custom_filter[int((len - 1)/2)] = 1
    for i in range(int((len - 1)/2)):  # можно сделать через np
        custom_filter[int((len - 1)/2) - 1 - i] = np.exp(-k * np.power((i + 1), 2))
        custom_filter[int((len - 1)/2) + 1 + i] = custom_filter[int((len - 1)/2) - 1 - i]
    custom_filter = custom_filter/np.sum(custom_filter)
    return custom_filter

# def get_new_border(border, fs: int):
#     # border[0] = border[1] - ((border[1] - border[0]) // self.fs) * self.fs
#     border[1] = border[0] + ((border[1] - border[0]) // fs) * fs
#     return ([0, 0] if (border[1] - border[0]) < fs else border)

def find_value_between_points(point1, point2, value):
    x1, y1 = point1
    x2, y2 = point2
    result = y1 + ((y2 - y1) / (x2 - x1)) * (value - x1)
    return result

def get_fft_data(gyro: np.ndarray, encoder: np.ndarray, fs: int):
    """
    Detailed explanation goes here:
    amp [безразмерная] - соотношение амплитуд воздействия (encoder)
    и реакции гироскопа(gyro) = gyro/encoder
    d_phase [degrees] - разница фаз = gyro - encoder
    freq [Hz] - частота гармоники (воздействия)
    gyro [degrees/sec] - показания гироскопа во время гармонического воздействия
    encoder [degrees/sec] - показания энкодера, задающего гармоническое воздействие
    FS [Hz] - частота дискретизации
    """
    L = gyro.size  # длина записи
    next_power = np.ceil(np.log2(L))  # показатель степени 2 для числа длины записи
    NFFT = np.int32(np.power(2, next_power))
    HALF = np.int32(NFFT / 2)

    # Yg = np.fft.fft(gyro, NFFT) / L  # преобразование Фурье сигнала гироскопа
    Yg = (np.fft.rfft(gyro, NFFT)/L).astype(np.complex64)  #
    # Ye = np.fft.fft(encoder, NFFT) / L  # преобразование Фурье сигнала энкодера
    Ye = (np.fft.rfft(encoder, NFFT)/L).astype(np.complex64)  #
    f = fs / 2 * np.linspace(0, 1, HALF + 1, endpoint=True)  # получение вектора частот
    #  delta_phase = asin(2*np.mean(encoder1.*gyro1)/(np.mean(abs(encoder1))*np.mean(abs(gyro1))*pi^2/4))*180/pi
    ng = np.argmax(np.abs(Yg[0:HALF]))
    Mg = 2 * np.abs(Yg[ng])
    freq = f[ng]  # !  у гироскопов меньше помехи обычно
    # если с гироскопа придет постоянное число, то частота будет нулевой
    # freq = f[ne]  # make sense?
    ne = np.argmax(np.abs(Ye[0:HALF]))
    Me = 2 * np.abs(Ye[ne])
    if freq == 0:  # !!!
        freq = f[ne]

    d_phase = np.angle(Yg[ng], deg=True) - np.angle(Ye[ne], deg=True)
    amp = Mg/Me
    #  amp = std(gyro)/std(encoder)% по шуму (метод —урова)
    return [freq, amp, d_phase]

def get_fft_data_ext(gyro: np.ndarray, encoder: np.ndarray, fs: int, n: int = 5):
    """
    Detailed explanation goes here:
    amp [безразмерная] - соотношение амплитуд воздействия (encoder)
    и реакции гироскопа(gyro) = gyro/encoder
    d_phase [degrees] - разница фаз = gyro - encoder
    freq [Hz] - частота гармоники (воздействия)
    gyro [degrees/sec] - показания гироскопа во время гармонического воздействия
    encoder [degrees/sec] - показания энкодера, задающего гармоническое воздействие
    FS [Hz] - частота дискретизации
    """
    gyro_ = np.empty([n, gyro.shape[0]])
    gyro_[:] = gyro
    gyro_ = gyro_.reshape(gyro_.shape[1] * gyro_.shape[0])
    encoder_ = np.empty([n, encoder.shape[0]])
    encoder_[:] = encoder
    encoder_ = encoder_.reshape(encoder_.shape[1] * encoder_.shape[0])
    L = gyro_.size  # длина записи
    # print(L)
    next_power = np.ceil(np.log2(L))  # показатель степени 2 для числа длины записи
    NFFT = np.int32(np.power(2, next_power))
    HALF = np.int32(NFFT / 2)

    Yg = (np.fft.rfft(gyro_, NFFT)/L).astype(np.complex64)  # преобразование Фурье сигнала гироскопа
    Ye = (np.fft.rfft(encoder_, NFFT)/L).astype(np.complex64)  # преобразование Фурье сигнала энкодера
    f = fs / 2 * np.linspace(0, 1, HALF + 1, endpoint=True)  # получение вектора частот
    #  delta_phase = asin(2*np.mean(encoder1.*gyro1)/(np.mean(abs(encoder1))*np.mean(abs(gyro1))*pi^2/4))*180/pi
    ng = np.argmax(np.abs(Yg[0:HALF]))
    Mg = 2 * np.abs(Yg[ng])
    freq = f[ng]  # !  у гироскопов меньше помехи обычно
    # если с гироскопа придет постоянное число, то частота будет нулевой
    # freq = f[ne]  # make sense?
    # print(f[ng])
    ne = np.argmax(np.abs(Ye[0:HALF]))
    Me = 2 * np.abs(Ye[ne])
    if freq == 0:  # !!!
        freq = f[ne]
    # print(f[ne])

    d_phase = np.angle(Yg[ng], deg=True) - np.angle(Ye[ne], deg=True)
    amp = Mg/Me
    # print("-------------------------------------")
    # print(freq_list)
    # print(amp_list)
    # print(phase_list)
    return [freq, amp, d_phase]

def get_fft_data_median_frame(gyro: np.ndarray, encoder: np.ndarray, fs: int):
    """
    Detailed explanation goes here:
    amp [безразмерная] - соотношение амплитуд воздействия (encoder)
    и реакции гироскопа(gyro) = gyro/encoder
    d_phase [degrees] - разница фаз = gyro - encoder
    freq [Hz] - частота гармоники (воздействия)
    gyro [degrees/sec] - показания гироскопа во время гармонического воздействия
    encoder [degrees/sec] - показания энкодера, задающего гармоническое воздействие
    FS [Hz] - частота дискретизации
    """
    n = 3
    freq_list = np.ones(n, dtype=np.float32)
    amp_list = np.ones(n, dtype=np.float32)
    phase_list = np.ones(n, dtype=np.float32)
    # print(gyro.size)
    for i in range(n):
        # k = int(gyro.size * 0.5 * (2**(-1+i)))
        k = int(0.03 * i * gyro.size)
        # print(k)
        gyro_ = np.copy(gyro[k:-k-1])
        encoder_ = np.copy(encoder[k:-k-1])
        L = gyro_.size  # длина записи
        next_power = np.ceil(np.log2(L))  # показатель степени 2 для числа длины записи
        NFFT = np.int32(np.power(2, next_power))
        HALF = np.int32(NFFT / 2)

        # Yg = np.fft.fft(gyro, NFFT) / L
        Yg = (np.fft.rfft(gyro_, NFFT)/L).astype(np.complex64)  # преобразование Фурье сигнала гироскопа
        # Ye = np.fft.fft(encoder, NFFT) / L
        Ye = (np.fft.rfft(encoder_, NFFT)/L).astype(np.complex64)  # преобразование Фурье сигнала энкодера
        f = fs / 2 * np.linspace(0, 1, HALF + 1, endpoint=True)  # получение вектора частот
        #  delta_phase = asin(2*np.mean(encoder1.*gyro1)/(np.mean(abs(encoder1))*np.mean(abs(gyro1))*pi^2/4))*180/pi
        ng = np.argmax(np.abs(Yg[0:HALF]))
        Mg = 2 * np.abs(Yg[ng])
        freq = f[ng]  # !  у гироскопов меньше помехи обычно
        # если с гироскопа придет постоянное число, то частота будет нулевой
        # freq = f[ne]  # make sense?
        ne = np.argmax(np.abs(Ye[0:HALF]))
        Me = 2 * np.abs(Ye[ne])
        if freq == 0:  # !!!
            freq = f[ne]

        d_phase = np.angle(Yg[ng], deg=True) - np.angle(Ye[ne], deg=True)
        amp = Mg/Me
        freq_list[i] = freq
        amp_list[i] = amp
        phase_list[i] = d_phase
    # print("-------------------------------------")
    # print(freq_list)
    # print(amp_list)
    # print(phase_list)
    return [np.nanmedian(freq_list), np.nanmedian(amp_list), np.nanmedian(phase_list)]
