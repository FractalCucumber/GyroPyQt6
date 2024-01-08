import os
import sys
import numpy as np
from PyQt5 import QtGui
# from numba import jit, prange, njit


def get_res_path(relative_path: str):
    """
    Get absolute path to resource, works with PyInstaller
    """
    base_path = getattr(
        sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

get_icon_by_name = lambda name: QtGui.QIcon(get_res_path(f'res/{name}.png'))

# def get_icon_by_name(name):
    # return QtGui.QIcon(get_res_path(f'res/{name}.png'))

def check_name_simple(name: str):
    basename, extension = os.path.splitext(name)
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

def get_new_bourder(bourder, fs: int):
    # bourder[0] = bourder[1] - ((bourder[1] - bourder[0]) // self.fs) * self.fs
    bourder[1] = bourder[0] + ((bourder[1] - bourder[0]) // fs) * fs
    return ([0, 0] if (bourder[1] - bourder[0]) < fs else bourder)

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
    # print(type(L))
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
    # freq = f[ne]  # make sence?

    ne = np.argmax(np.abs(Ye[0:HALF]))
    Me = 2 * np.abs(Ye[ne])
    freq = f[ne]

    d_phase = np.angle(Yg[ng], deg=True) - np.angle(Ye[ne], deg=True)
    amp = Mg/Me
    #  amp = std(gyro)/std(encoder)% пошуму (метод —урова)
    return [freq, amp, d_phase]