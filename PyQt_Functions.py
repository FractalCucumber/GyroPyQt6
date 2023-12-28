import os
import sys
import numpy as np

def get_res_path(relative_path):
    """
    Get absolute path to resource, works with PyInstaller
    """
    base_path = getattr(
        sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def check_name_simple(name):
    basename = os.path.splitext(name)[0]
    extension = os.path.splitext(name)[1]
    i = 0
    while os.path.exists(name):
        i += 1
        name = basename + f"({i})" + extension
    return name

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

def get_new_bourder(bourder, fs):
    # bourder[0] = bourder[1] - ((bourder[1] - bourder[0]) // self.fs) * self.fs
    bourder[1] = bourder[0] + ((bourder[1] - bourder[0]) // fs) * fs
    # if (bourder[1] - bourder[0]) < fs:
    #     return [0, 0]
    # else: 
    #     return bourder
    return ([0, 0] if (bourder[1] - bourder[0]) < fs else bourder)

def find_value_between_points(point1, point2, value):
    x1, y1 = point1
    x2, y2 = point2
    result = y1 + ((y2 - y1) / (x2 - x1)) * (value - x1)
    return result