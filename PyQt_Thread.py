# cSpell:includeRegExp #.*
# cSpell:includeRegExp /(["]{3}|[']{3})[^\1]*?\1/g

import logging
import os
import re
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
from pandas import read_csv, DataFrame
from threading import Event
from PyQt_Functions import (get_fft_data, get_fft_data_median_frame, get_fft_data_ext,
                            check_name_simple, custom_g_filter)


CRC8_END_VALUE = 0x17
CRC8_INIT_VALUE = 0xfa
CRC8_Table = np.array([
	0x273a1d00,0x534e6974,0xcfd2f5e8,0xbba6819c,0xeaf7d0cd,0x9e83a4b9,0x021f3825,0x766b4c51,
	0xa0bd9a87,0xd4c9eef3,0x4855726f,0x3c21061b,0x6d70574a,0x1904233e,0x8598bfa2,0xf1eccbd6,
	0x34290e13,0x405d7a67,0xdcc1e6fb,0xa8b5928f,0xf9e4c3de,0x8d90b7aa,0x110c2b36,0x65785f42,
	0xb3ae8994,0xc7dafde0,0x5b46617c,0x2f321508,0x7e634459,0x0a17302d,0x968bacb1,0xe2ffd8c5,
	0x011c3b26,0x75684f52,0xe9f4d3ce,0x9d80a7ba,0xccd1f6eb,0xb8a5829f,0x24391e03,0x504d6a77,
	0x869bbca1,0xf2efc8d5,0x6e735449,0x1a07203d,0x4b56716c,0x3f220518,0xa3be9984,0xd7caedf0,
	0x120f2835,0x667b5c41,0xfae7c0dd,0x8e93b4a9,0xdfc2e5f8,0xabb6918c,0x372a0d10,0x435e7964,
	0x9588afb2,0xe1fcdbc6,0x7d60475a,0x0914332e,0x5845627f,0x2c31160b,0xb0ad8a97,0xc4d9fee3])


class SecondThread(QThread):
    package_num_signal = pyqtSignal(int, np.ndarray)
    fft_data_signal = pyqtSignal(bool)
    median_data_ready_signal = pyqtSignal(list)
    warning_signal = pyqtSignal(str)
    info_signal = pyqtSignal(str)

    def __init__(self, gyro_number: int, read_interval_ms: int,
                 logger_name='', wait_time_sec=0.5, OPTIONS_FILE_NAME: str = 'settings/fft_options.json'):
        # QThread.__init__(self)
        super(SecondThread, self).__init__()
        self.data_received_event = Event()
        self.logger = logging.getLogger(logger_name)
        self.GYRO_NUMBER = gyro_number
        self.READ_INTERVAL_MS = read_interval_ms
        self.WAIT_TIME_SEC = wait_time_sec
        # self.WAIT_TIME_SEC = 0.2
        # self.WAIT_TIME_SEC = 0
        self.rx: bytes = b''
        self.all_fft_data: np.ndarray = np.array([], dtype=np.float32)
        self.time_data: np.ndarray = np.array([], dtype=np.int32)
        self.special_points: np.ndarray = np.empty((5, self.GYRO_NUMBER))
        self.k_amp: np.ndarray = np.ones(self.GYRO_NUMBER, dtype=np.float32)
        self.amp_shift: np.ndarray = np.zeros(self.GYRO_NUMBER, dtype=np.float32)
        self.border: np.ndarray = np.zeros(2, dtype=np.uint32)
        self.to_plot: np.ndarray = np.array([], dtype=np.float32)  # !
        self.fs = 0
        self.flag_send: bool = True
        self.total_time: int = 0
        self.total_cycle_num = 0  # !
        self.cycle_count = 1
        self.num_measurement_rows = 0
        self.pack_num = 0
        self.package_num_list: list = [0]
        self.pack_len = 2
        self.received_pack_len = 0
        self.flag_full_measurement_start = False  # лучше все эти флаги загнать в словарь
        self.flag_measurement_start = False
        self.flag_big_processing = False
        self.flag_by_name = False
        self.flag_do_not_save = False
        self.save_again = False
        self.crc_flag = False
        self.flag_by_name_ = False

        self.selected_files_to_fft: list[str] = []
        self.save_file_name = [''] * self.GYRO_NUMBER
        self.POWERS14_4 = np.matrix([(256 ** np.arange(4)[::-1])] * 4)  # !
        self.POWERS14_2 = np.matrix([(256 ** np.arange(4)[::-1])] * 2)  # !
        self.POWERS20_6 = np.matrix([(256 ** np.arange(4)[::-1])] * 6)  # !
        # import sys
        # print(sys.getsizeof(self.time_data))
        # print(get_fft_data(np.array([1, 1, 1, 1, 1, 1, 1, 1, 1]),
        #   np.array([0, 1, 2, 1, 0, -1, -2, -1, 0]), 9))
        # self.fft_opt = {'decimation': 4, # 1-4
        #        'threshold': 5300,  # 5000 - 5500
        #        'min_frame_len_k': 1, # 1.5
        #        'n_get_fft_data_ext': 4,
        #        'n_repeat': 10
        #        }
        # self.OPTIONS_FILE_NAME = 'settings/fft_options.json'
        # with open(self.OPTIONS_FILE_NAME, 'w', encoding='utf-8') as file:
        #     json.dump(self.fft_opt,
        #               file, ensure_ascii=False, indent=4)
            
    # def load_json(self, PROJECT_FILE_NAME):
        # with open(self.OPTIONS_FILE_NAME, 'r', encoding='utf-8') as file:
        from json import load
        with open(OPTIONS_FILE_NAME, 'r', encoding='utf-8') as file:
            # self.fft_opt = json.load(file)
            self.fft_opt = load(file)
            self.logger.debug(self.fft_opt)
        # kwargs['threshold'] = 1.0 * self.fs  # сколько времени минимум длится вибрация + пауза, при 1 работало
        # n_get_fft_data_ext = 4
        # n_repeat = 10
        # min_frame_len =  * self.fs
# -------------------------------------------------------------------------------------------------
#   
# -------------------------------------------------------------------------------------------------

    @pyqtSlot()
    def run(self):
        self.logger.debug("Thread Start")
        temp = self.GYRO_NUMBER
        # --- check file processing flags ---
        if self.flag_big_processing or self.flag_by_name:  # лучше все эти флаги загнать в словарь
            self.flag_do_not_save = True  # !!!
            self.package_num_list = [0]
            self.get_fft_from_existing_data()
            self.save_again = False
            self.flag_by_name_ = True
        # --- check measurements flags ---
        if self.flag_measurement_start or self.flag_full_measurement_start:
            self.package_num_list = [0]
            self.start_measurements()
            self.save_again = False
            self.flag_by_name_ = False
        # --- check save flag and save results ---
        self.logger.debug(
            f"Start saving time {(not self.flag_by_name and self.pack_num) and not self.flag_do_not_save}")
        if self.pack_num and not self.flag_do_not_save and not self.flag_by_name_:
            self.save_time_cycles()
        # self.logger.debug(
        #     f"Start saving fff {((not self.flag_do_not_save or self.save_again) and self.pack_num) and (self.flag_by_name or self.save_again)}")
        # self.logger.debug(
        #     f"Start saving fff {((not self.flag_do_not_save or self.save_again) and self.pack_num)}")
        # if ((not self.flag_do_not_save or self.save_again) and self.pack_num) and (self.flag_by_name or self.save_again):
        if not self.flag_do_not_save and self.pack_num:
            self.save_fft()
        elif self.save_again:
            self.warning_signal.emit("Nothing to save")
        # --- reset flags ---
        self.GYRO_NUMBER = temp
        self.flag_by_name = False
        self.flag_do_not_save = False
        self.save_again = True
        self.logger.debug("Thread stop")
# -------------------------------------------------------------------------------------------------
#
# -------------------------------------------------------------------------------------------------

    def start_measurements(self):
        # --- main init ---
        self.time_data: np.ndarray = np.array([], dtype=np.int32)
        self.time_data.resize(
            10 * self.fs,
            1 + self.pack_len * self.GYRO_NUMBER, refcheck=True)
        self.time_data.fill(0)
        self.to_plot.resize(16 * self.fs, self.time_data.shape[1])  # !
        self.amp_shift.resize(self.GYRO_NUMBER)
        self.amp_shift.fill(0)
        self.change_protocol()
        # --- only measurements ---
        if self.flag_measurement_start:
            # --- init ---
            self.logger.debug("flag_measurement_start True")
            self.to_plot.fill(np.nan)
            self.pack_num = 0
            # --- measurement cycle ---
            while self.flag_measurement_start:
                self.data_received_event.wait(1)  # Timeout 1 sec!
                if not self.data_received_event.is_set():
                    self.logger.debug("Timeout")
                    continue
                self.data_received_event.clear()
                if self.flag_measurement_start:
                    self.get_ints_from_bytes()
                    self.prepare_to_emit()
            # --- ---
            self.check_shift_and_gyro()
            self.package_num_list.append(self.pack_num)
            self.pack_num = 0

        # --- measurements and fft processing ---
        if self.flag_full_measurement_start:
            # --- init ---
            self.logger.debug("flag_full_measurement_start True")
            self.package_num_list = [0]
            self.to_plot.fill(np.nan)
            self.cycle_count = 1
            self.pack_num = 0
            self.k_amp.resize(self.GYRO_NUMBER)
            self.k_amp.fill(1)
            self.flag_send = True
            make_fft_frame_gen = self.make_fft_frame_generator() #####################################################################
            # --- measurement and fft processing cycle ---
            while self.flag_full_measurement_start:
                self.data_received_event.wait(0.5)  # Timeout 500 msec!
                if not self.data_received_event.is_set():
                    self.logger.debug("Timeout")
                    continue
                self.data_received_event.clear()
                if self.flag_full_measurement_start:
                    self.get_ints_from_bytes()
                    # next(make_fft_frame_gen)
                    self.prepare_to_emit()
                    next(make_fft_frame_gen)  # выполняется и в случае таймаута, позволяет бороться с неправильными выделениями рамок
                    self.logger.debug("end thread cycle\n")
            self.package_num_list.append(self.pack_num)

    def change_protocol(self):
        if self.GYRO_NUMBER == 1:
            if self.pack_len == 4:
                if self.crc_flag:
                    self.get_ints_from_bytes = self.get_ints_from_bytes14_4_crc8
                    self.logger.debug("get_ints_from_bytes14_4_crc8")
                else:
                    self.get_ints_from_bytes = self.get_ints_from_bytes14_4
                    self.logger.debug("get_ints_from_bytes14_4")
            else:
                self.get_ints_from_bytes = self.get_ints_from_bytes14_2
                self.logger.debug("get_ints_from_bytes14_2")
        if self.GYRO_NUMBER == 3:
            if self.crc_flag:
                self.get_ints_from_bytes = self.get_ints_from_bytes20_2_crc8
                self.logger.debug("get_ints_from_bytes20_2_crc8")
            else:
                self.get_ints_from_bytes = self.get_ints_from_bytes20_2
                self.logger.debug("get_ints_from_bytes20_2")
# -------------------------------------------------------------------------------------------------
#
# -------------------------------------------------------------------------------------------------
    def check_shift_and_gyro(self):
        if self.pack_num > 5 * self.fs:
            self.amp_shift = np.mean(self.time_data[:5 * self.fs, 1::self.pack_len], axis=0)
        else:
            self.amp_shift = np.mean(self.time_data[:self.pack_num, 1::self.pack_len], axis=0)
        self.logger.debug(f"amp_shift = {self.amp_shift}")
        for i in range(self.GYRO_NUMBER):
            if np.equal(self.amp_shift[i], -1):
                self.amp_shift[i] = 0
                self.warning_signal.emit(f"There is no data from gyro{i+1}!")
        # можно тут же проверять частоту дискретизации
        # желательно добавить пункт "не сохранять" на случай ошибки
# -------------------------------------------------------------------------------------------------

    def prepare_to_emit(self):
        """Normalize data and send it in main thread"""
        # и тут можно итератор сделать, тогда не надо знать self.received_pack_len
        self.logger.debug(
            f"prepare data to graph, {self.pack_num}, {self.received_pack_len}")
        # (измерить, насколько быстро точки на график выводятся)
        # можно сделать несколько режимов вывода, которые можно будет переключать
        if not self.received_pack_len:
            self.logger.debug("No data")
            return False
        self.to_plot = np.roll(self.to_plot, -self.received_pack_len, axis=0)
        if self.flag_full_measurement_start:
            start = self.pack_num - self.received_pack_len
            end = self.pack_num
        else:
            start = 0
            end = self.received_pack_len
        self.to_plot[-self.received_pack_len:, 0] = (
            np.copy(self.time_data[start:end, 0])
            ).astype(np.float32) / self.fs
        self.to_plot[-self.received_pack_len:, 2] = (
            np.copy(self.time_data[start:end, 2])
            ).astype(np.float32) / 1000
        self.to_plot[-self.received_pack_len:, 1::self.pack_len] = (
            np.copy(self.time_data[start:end, 1::self.pack_len])
            ).astype(np.float32) / 1000 / self.k_amp
        self.package_num_signal.emit(self.pack_num, self.to_plot)
        return True
# -------------------------------------------------------------------------------------------------

    def get_ints_from_bytes14_4_crc8(self):
        if len(self.rx) <= 28:
            self.received_pack_len = 0
            return False
        bytes_arr = np.frombuffer(self.rx, dtype=np.uint8)
        start = np.where(
            (bytes_arr[:-14] == 0x72) & (bytes_arr[14:] == 0x72))[0] + 1
        self.logger.debug(f"len was: {start.size}")
        if not start.size:
            self.warning_signal.emit("Check settings, incorrect data from COM port!")
            self.received_pack_len = 0
            self.rx = b''
            return False
        # --- start CRC8 ---
        i_rez = np.full((start.size), CRC8_INIT_VALUE)
        ui_data = bytes_arr[np.add(start, -1)]
        i_index = np.bitwise_and(
            np.bitwise_xor(i_rez, ui_data), 0xff)
            # np.bitwise_xor(i_rez, np.bitwise_and(ui_data, 0xff)), 0xff)
        i_rez = np.right_shift(
            CRC8_Table[np.right_shift(i_index, 2)],
            (8 * (np.bitwise_and(i_index, 0x03))))
        for i in range(4):
            for j in range(3):
                # array_r[:, i, j] = bytes_arr[np.add(start, 3*i + j)]
                ui_data = bytes_arr[np.add(start, 3*i + j)]
                i_index = np.bitwise_and(
                    # np.bitwise_xor(i_rez, np.bitwise_and(ui_data, 0xff)), 0xff)
                    np.bitwise_xor(i_rez, ui_data), 0xff)
                i_rez = np.right_shift(
                    CRC8_Table[np.right_shift(i_index, 2)],
                    (8 * (np.bitwise_and(i_index, 0x03))))
        # ---
        last = np.bitwise_and(np.bitwise_xor(i_rez, CRC8_END_VALUE), 0xff)
        start = start[np.where(np.equal(bytes_arr[start + 12], last) == 1)]
        self.logger.debug(f"len real: {self.received_pack_len}")
        if not start.size:
            self.warning_signal.emit("Incorrect CRC8 data!")
            self.rx = b''
            return False
        # --- Form numpy 3D-array from bytes ---
        start = np.insert(start, start.size, start[-1] + 14)
        start = start[np.where(np.diff(start) == 14)[0]]
        self.logger.debug(f"len was 2: {start.size}")
        self.received_pack_len = start.size
        array_r = np.zeros((self.received_pack_len, 4, 4), dtype=np.uint8)
        for i in range(4):
            for j in range(3):
                array_r[:, i, j] = bytes_arr[np.add(start, 3*i + j)]
        # ---
        pack_num_ = self.pack_num * self.flag_full_measurement_start
        if pack_num_ + self.received_pack_len >= self.time_data.shape[0]:
            self.time_data.resize(
                self.time_data.shape[0] + 15 * self.fs,
                self.time_data.shape[1], refcheck=False)
        self.time_data[pack_num_:pack_num_ + self.received_pack_len, 0] = np.arange(
            self.pack_num, self.pack_num + self.received_pack_len)
        for k in range(self.GYRO_NUMBER):
            self.time_data[pack_num_:pack_num_ + self.received_pack_len,
                            (1 + 4*k):(5 + 4*k)] = (
                                np.einsum("ijk,jk->ij", array_r, self.POWERS14_4) / 256)
        self.pack_num += self.received_pack_len
        # print(np.nanmean(np.abs(
        #     (self.time_data[pack_num_:pack_num_ + self.received_pack_len, 1]))))
        # print(np.nanmean(np.abs(
        #     (self.time_data[pack_num_:pack_num_ + self.received_pack_len, 2]))))
        # print('--------------------------')
        # --- save part of package
        if len(self.rx[start[-1] + 13:]) < 28:
            self.rx = self.rx[start[-1] + 13:]
        else:
            self.rx = b''
        return True

    def get_ints_from_bytes20_2_crc8(self):
        if len(self.rx) <= 60:
            self.received_pack_len = 0
            return False
        bytes_arr = np.frombuffer(self.rx, dtype=np.uint8)
        start = np.where(
            (bytes_arr[:-20] == 0x72) & ((bytes_arr[20:] == 0x72)))[0] + 1
            # (bytes_arr[:-40] == 0x72) & (bytes_arr[40:] == 0x72) & (bytes_arr[20:-20] == 0x72))[0] + 1
        self.logger.debug(f"len was: {start.size}")
        if not start.size:
            self.warning_signal.emit("Check settings, incorrect data from COM port!")
            self.received_pack_len = 0
            self.rx = b''
            return False
        # --- start CRC8 ---
        i_rez = np.full((start.size), CRC8_INIT_VALUE)
        ui_data = bytes_arr[np.add(start, -1)]
        i_index = np.bitwise_and(np.bitwise_xor(i_rez, ui_data), 0xff)
        # i_index = np.bitwise_xor(i_rez, np.bitwise_and(ui_data, 0xff)), 0xff)
        i_rez = np.right_shift(CRC8_Table[np.right_shift(i_index, 2)],
                               (8 * (np.bitwise_and(i_index, 0x03))))
        for i in range(6):
            for j in range(3):
                ui_data = bytes_arr[np.add(start, 3*i + j)]
                i_index = np.bitwise_and(np.bitwise_xor(i_rez, ui_data), 0xff)
                # i_index = np.bitwise_xor(i_rez, np.bitwise_and(ui_data, 0xff)), 0xff)
                i_rez = np.right_shift(CRC8_Table[np.right_shift(i_index, 2)],
                                       (8 * (np.bitwise_and(i_index, 0x03))))
        last = np.bitwise_and(np.bitwise_xor(i_rez, CRC8_END_VALUE), 0xff)
        start = start[np.where(np.equal(bytes_arr[start + 18], last) == 1)]
        self.logger.debug(f"len real: {start.size}")
        if not start.size:
            self.warning_signal.emit("Incorrect CRC8 data!")
            self.received_pack_len = 0
            self.rx = b''
            return False
        # --- Form numpy 3D-array from bytes ---
        start = np.insert(start, start.size, start[-1] + 20)
        start = start[np.where(np.diff(start) == 20)[0]]
        self.logger.debug(f"len was 2: {start.size}")
        self.received_pack_len = start.size
        array_r = np.zeros((self.received_pack_len, 6, 4), dtype=np.uint8)
        for i in range(6):
            for j in range(3):
                array_r[:, i, j] = bytes_arr[np.add(start, 3*i + j)]
        # --- Check size ---
        pack_num_ = self.pack_num * self.flag_full_measurement_start
        if pack_num_ + self.received_pack_len >= self.time_data.shape[0]:
            self.time_data.resize(
                self.time_data.shape[0] + 18 * self.fs,
                self.time_data.shape[1], refcheck=False)  # !!!!!!!!!!!!!!!!!!!!
        self.time_data[pack_num_:pack_num_ + self.received_pack_len, 0] = np.arange(
            self.pack_num, self.pack_num + self.received_pack_len)
        # for k in range(self.GYRO_NUMBER):  # !!!
            # self.time_data[pack_num_:pack_num_ + self.recieved_pack_len,
            #                (1 + self.pack_len*k):(1 + (self.pack_len)*k + 2)] = (
            #                    np.einsum("ijk,jk->ij", array_r[:,2*k:2*k+2, :], self.POWERS14_2) / 256)
        self.time_data[pack_num_:pack_num_ + self.received_pack_len, 1:] = (
                            np.einsum("ijk,jk->ij", array_r, self.POWERS20_6) / 256)
        self.pack_num += self.received_pack_len
        if len(self.rx[start[-1] + 19:]) < 60:
            self.rx = self.rx[start[-1] + 19:]
        else:
            self.rx = b''
        return True

    def get_ints_from_bytes14_4(self):
        if len(self.rx) <= 28:
            self.received_pack_len = 0
            return False
        self.logger.debug("start matrix processing data frame")
        bytes_arr = np.frombuffer(self.rx, dtype=np.uint8)
        start = np.where(
            (bytes_arr[:-13] == 0x72) & (bytes_arr[13:] == 0x27))[0] + 1
            # (bytes_arr[:-14] == 0x72) & (bytes_arr[13:-1] == 0x27) & (bytes_arr[14:] == 0x72))[0] + 1
        if not start.size:
            self.warning_signal.emit("Check settings, incorrect data from COM port!")
            self.logger.debug("Incorrect data in rx!")
            self.received_pack_len = 0
            self.rx = b''
            return False
        start = np.insert(start, start.size, start[-1] + 14)
        start = start[np.where(np.diff(start) == 14)[0]]
        self.received_pack_len = start.size
        array_r = np.zeros((self.received_pack_len, 4, 4), dtype=np.uint8)
        for i in range(4):
            for j in range(3):
                array_r[:, i, j] = bytes_arr[np.add(start, 3*i + j)]
        pack_num_ = self.pack_num * self.flag_full_measurement_start
        if pack_num_ + self.received_pack_len >= self.time_data.shape[0]:
            self.logger.debug("expand array")
            self.time_data.resize(
                self.time_data.shape[0] + 15 * self.fs,
                self.time_data.shape[1], refcheck=False)  # !!!!!!!!!!!!!!!!!!!!
        self.time_data[pack_num_:pack_num_ + self.received_pack_len, 0] = np.arange(
            self.pack_num, self.pack_num + self.received_pack_len)
        for k in range(self.GYRO_NUMBER):
            self.time_data[pack_num_:pack_num_ + self.received_pack_len,
                           (1 + 4*k):(5 + 4*k)] = (
                               np.einsum("ijk,jk->ij", array_r, self.POWERS14_4) / 256)
        self.pack_num += self.received_pack_len
        self.logger.debug("end matrix processing")
        if len(self.rx[start[-1] + 13:]) < 28:
            self.rx = self.rx[start[-1] + 13:]
        else:
            self.rx = b''
        return True

    def get_ints_from_bytes14_2(self):
        self.logger.debug("start matrix processing data frame")
        if len(self.rx) <= 28:
            self.received_pack_len = 0  # self.rx = b''
            return False
        bytes_arr = np.frombuffer(self.rx, dtype=np.uint8)
        start = np.where(
            (bytes_arr[:-13] == 0x72) & (bytes_arr[13:] == 0x27))[0] + 1
        if not start.size:
            self.logger.debug("Incorrect data in rx!")
            self.warning_signal.emit("Check settings, incorrect data from COM port!")
            self.received_pack_len = 0
            self.rx = b''
            return False
        start = np.insert(start, start.size, start[-1] + 14)
        start = start[np.where(np.diff(start) == 14)[0]]
        self.received_pack_len = start.size
        array_r = np.zeros((self.received_pack_len, 2, 4), dtype=np.uint8)
        for i in range(2):
            for j in range(3):
                array_r[:, i, j] = bytes_arr[np.add(start, 3*i + j)]
        self.logger.debug(self.received_pack_len)
        pack_num_ = self.pack_num * self.flag_full_measurement_start
        if pack_num_ + self.received_pack_len >= self.time_data.shape[0]:
            self.logger.debug("expand array")
            self.time_data.resize(
                self.time_data.shape[0] + 15 * self.fs,
                self.time_data.shape[1], refcheck=False)  # !!!!!!!!!!!!!!!!!!!!
        self.time_data[pack_num_:pack_num_ + self.received_pack_len, 0] = np.arange(
            self.pack_num, self.pack_num + self.received_pack_len)
        self.time_data[pack_num_:pack_num_ + self.received_pack_len, 1:3] = (
            np.einsum("ijk,jk->ij", array_r, self.POWERS14_2) / 256)
        self.pack_num += self.received_pack_len
        self.logger.debug("end matrix processing")
        if len(self.rx[start[-1] + 13:]) < 28:
            self.rx = self.rx[start[-1] + 13:]
        else:
            self.rx = b''
        return True

    def get_ints_from_bytes20_2(self):
        self.logger.debug("start matrix processing data frame")
        if len(self.rx) <= 60:
            self.received_pack_len = 0  # self.rx = b''
            return False
        bytes_arr = np.frombuffer(self.rx, dtype=np.uint8)
        start = np.where(
            (bytes_arr[:-19] == 0x72) & (bytes_arr[19:] == 0x27))[0] + 1
            # (bytes_arr[:-20] == 0x72) & (bytes_arr[19:-1] == 0x27) & (bytes_arr[20:] == 0x72))[0] + 1
        if not start.size:
            self.logger.debug("Incorrect data in rx!")
            self.warning_signal.emit("Check settings, incorrect data from COM port!")
            self.received_pack_len = 0
            self.rx = b''
            return False
        start = np.insert(start, start.size, start[-1] + 20)
        start = start[np.where(np.diff(start) == 20)[0]]
        self.received_pack_len = start.size
        array_r = np.zeros((self.received_pack_len, 6, 4), dtype=np.uint8)
        for i in range(6):
            for j in range(3):
                array_r[:, i, j] = bytes_arr[np.add(start, 3*i + j)]
        self.logger.debug(self.received_pack_len)
        pack_num_ = self.pack_num * self.flag_full_measurement_start
        if pack_num_ + self.received_pack_len >= self.time_data.shape[0]:
            self.logger.debug("expand array")
            self.time_data.resize(
                self.time_data.shape[0] + 18 * self.fs,
                self.time_data.shape[1], refcheck=False)
        self.time_data[pack_num_:pack_num_ + self.received_pack_len, 0] = np.arange(
            self.pack_num, self.pack_num + self.received_pack_len)
        for k in range(self.GYRO_NUMBER):  # !!!
            self.time_data[pack_num_:pack_num_ + self.received_pack_len,
                           (1 + self.pack_len*k):(1 + (self.pack_len)*k + 2)] = (
                               np.einsum("ijk,jk->ij", array_r[:,2*k:2*k+2, :], self.POWERS14_2) / 256)
                            #    np.einsum("ijk,jk->ij", array_r, self.POWERS14_4) / 256)
        self.pack_num += self.received_pack_len
        self.logger.debug("end matrix processing")
        if len(self.rx[(start[-1] + 13):]) < 40:
            self.rx = self.rx[start[-1] + 13:]
        else:
            self.rx = b''
        return True
# -------------------------------------------------------------------------------------------------
#
# -------------------------------------------------------------------------------------------------

    def save_condition(self, gyro):
        if not len(self.save_file_name[gyro]): # эта проверка одинаковая и для fft лучше ее вынести отдельно
            self.logger.debug(f"skip gyro{gyro + 1}")
            return False
        if not os.path.isdir(os.path.dirname(self.save_file_name[gyro])):
            self.logger.debug(
                f"Folder {os.path.dirname(self.save_file_name[gyro])} doesn't exist!")
            self.warning_signal.emit(
                f"Folder {os.path.dirname(self.save_file_name[gyro])} doesn't exist!")
            return False
        return True

    def save_time_cycles(self):
        """Check save conditions and save time data from cycles."""
        self.logger.debug("save time cycles!")
        k = (self.time_data.shape[1] - 1) / self.GYRO_NUMBER
        self.logger.debug(f"k={k}, len.package_num_list={len(self.package_num_list)}")
        filename_list_cycles = []
        for j_gyro in range(self.GYRO_NUMBER):
            if not self.save_condition(j_gyro):
                continue
            filename_list_cycles.append(
                os.path.basename(self.save_file_name[j_gyro]))
            cols = np.array([0, *(k*j_gyro + np.arange(1, k + 1))], dtype=np.uint16)  # все столбцы преобразовывать нерационально
            for i in range(len(self.package_num_list) - 1):
                filename = check_name_simple(
                    f"{self.save_file_name[j_gyro]}_{i + 1}.txt")
                self.logger.debug(f"save cycle {filename}")
                time_data_df = DataFrame(
                    self.time_data[
                        # self.package_num_list[i]:self.package_num_list[i + 1], :])
                        self.package_num_list[i]:self.package_num_list[i + 1], cols])
                time_data_df.to_csv(
                    filename, header=None,
                    # filename, columns=cols, header=None,
                    index=None, sep='\t', mode='w', date_format='%d')
        if len(filename_list_cycles):  # вот тут info должно быть, а не warning
            self.info_signal.emit(
                "Successfully save time data for\n" + ',\n'.join(filename_list_cycles) + '\n')
            return True
# -------------------------------------------------------------------------------------------------

    def save_fft(self):
        """Check save conditions and save fft data from cycles and median fft data,
        send signal to plot fft graph."""
        self.fft_median_filter(round_flag=False)  # --- calculate median data ---
        if np.isnan(self.all_fft_data[:, -4, :]).all():
            self.logger.debug("FFT data contains only NaN")
            return False
        self.logger.debug(f"names {self.save_file_name}")
        filename_list_cycles = []
        sensor_numbers_list = []
        self.get_special_points()
        self.logger.debug(
            f"total_cycle_num {self.total_cycle_num}, cycle_count {self.cycle_count}")
        for i in range(self.all_fft_data.shape[2]):
            sensor_numbers_list.append(
                re.split("_", os.path.basename(self.save_file_name[i]))[0])
            if not self.save_condition(i):
                continue
            # if self.pack_num:
                # self.cycle_count = len(self.package_num_list) - 1  # если отдельно сохранять
            # --- fft cycles ---
            filename_cycles = self.save_file_name[i] + \
                f'_{self.cycle_count}_FRQ_AMP_dPh_{self.fs}Hz.txt'
            filename_cycles = check_name_simple(filename_cycles)
            self.logger.debug(f"save fft file {filename_cycles}")
                    #    self.amp_and_freq[:, :4*self.cycle_count], delimiter='\t', fmt='%.3f')  # возможно, так будет обрезать лишнее
            DataFrame(self.all_fft_data[:, :-4, i]).to_csv(
                filename_cycles, header=None, index=None,
                sep='\t', mode='w', float_format='%.3f', decimal=',')
            # --- median ---
            filename_median = self.save_file_name[i] + \
                f'_FRQ_AMP_dPh_{self.fs}Hz.txt'
            filename_median = check_name_simple(filename_median)
            DataFrame(self.all_fft_data[:, -4:, i]).to_csv(
                filename_median, header=None, index=None,
                sep='\t', mode='w', float_format='%.3f', decimal=',')
            self.logger.debug("end saving fft file")

            filename_list_cycles.append(os.path.basename(filename_median))
        self.median_data_ready_signal.emit(sensor_numbers_list)
        if len(filename_list_cycles):
            self.info_signal.emit(
                "Successfully save fft data:\n" + ',\n'.join(filename_list_cycles) + '\n')
            return True
# -------------------------------------------------------------------------------------------------

    def new_measurement_cycle(self):
        self.package_num_list.append(self.pack_num)
        self.cycle_count += 1
# -------------------------------------------------------------------------------------------------

    def make_fft_frame_generator(self):  # generator
        # --- init ---
        self.count_fft_frame = 1
        self.all_fft_data.resize(
            (self.num_measurement_rows, 4 * (self.total_cycle_num + 1),
            self.GYRO_NUMBER), refcheck=False)
        self.all_fft_data.fill(np.nan)
        delays = np.array([int(self.WAIT_TIME_SEC * self.fs),
                           int(-0.4 * self.WAIT_TIME_SEC * self.fs)])
        flag_frame_start = False
        self.border.fill(0)  # можно оставить self, просто обнулять здесь
        fft_norm_gen = self.fft_normalization_generator() # генератор  # d_phase += 360 / 1000 * freq * 0.225  # ?????
        next(fft_norm_gen)
        fft_norm_gen.send((0, 0, 0, 0))
        while True:
            # --- processing cycle ---
            if not self.flag_send and not flag_frame_start:
                flag_frame_start = True
                self.border[0] = self.pack_num  # frame start
            elif flag_frame_start and self.flag_send:
                flag_frame_start = False
                self.border[1] = self.pack_num  # frame end
                self.border = self.border + delays
                self.logger.debug(f"old borders = {self.border}")
                self.border = self.get_new_border(self.border, self.fs)
                self.logger.debug(f"\tnew borders = {self.border}")
                if self.border[1]:
                    for i in range(self.GYRO_NUMBER):
                        if self.count_fft_frame < 10:
                            [freq, amp, d_phase] = get_fft_data_ext(
                            # [freq, amp, d_phase] = get_fft_data_median_frame(  # ! fft делается несколько раз с разными границами
                                gyro=(self.time_data[self.border[0]:self.border[1],
                                                    1 + i * self.pack_len] - self.amp_shift[i]),  # добавил сюда учет смещения
                                encoder=self.time_data[self.border[0]:self.border[1],
                                                       2 + i * self.pack_len] * self.k_amp[i],
                                fs=self.fs)
                        else:
                            [freq, amp, d_phase] = get_fft_data(
                            # gyro=gyro_list[border[0]:border[1], i],
                                gyro=(self.time_data[self.border[0]:self.border[1],
                                                    1 + i * self.pack_len] - self.amp_shift[i]),  # добавил сюда учет смещения
                                encoder=self.time_data[self.border[0]:self.border[1],
                                                       2 + i * self.pack_len] * self.k_amp[i],
                                fs=self.fs)
                        freq, amp, d_phase, tau = fft_norm_gen.send((freq, amp, d_phase, i))
                        # [freq, amp, d_phase, tau] = self.fft_normalization(
                            # freq, amp, d_phase, i=i)
                            # freq, amp, d_phase, d_phase_prev=self.all_fft_data[i-1, (self.cycle_count-1)*4, 0], i=i)
                        self.all_fft_data[(
                            self.count_fft_frame - 1), (self.cycle_count-1)*4:self.cycle_count*4, i
                            ] = [freq, amp, d_phase, tau]
                        self.logger.debug(f"fft: {[freq, amp, d_phase, tau]}")
                    self.fft_data_signal.emit(True)  # надо посылать border, потому что теперь это не свойство класса!
                    # self.fft_data_signal.emit(border)
                else:
                    self.warning_signal.emit("Too small data frame!")
            yield
# -------------------------------------------------------------------------------------------------

    def fft_median_filter(self, round_flag=True):
        # нужна проверка на то, что все частоты +- совпадают, проще при создании массива проверять
        for j in range(4):
            self.all_fft_data[:, j - 4, :] = np.nanmedian(self.all_fft_data[:, j::4, :], axis=1)
        if round_flag:
            self.all_fft_data[:, -4, :] = np.round(self.all_fft_data[:, -4, :], 2)
            self.all_fft_data[:, -3, :] = np.round(self.all_fft_data[:, -3, :], 4)
        if not self.all_fft_data.shape[0] < 4:  # !!!
            return
        for i in range(self.all_fft_data.shape[2]):
            # print(np.diff(self.all_fft_data[:-2, -2, i]))
            # print(np.diff(self.all_fft_data[1:-1, -2, i]))
            # print(np.diff(self.all_fft_data[2:, -2, i]))
            # print(self.all_fft_data[:-2, -2, i] - (self.all_fft_data[2:, -2, i]))
            # print(self.all_fft_data[1:-3, -2, i] - (self.all_fft_data[3:-1, -2, i]))
            errors = np.where(
                (self.all_fft_data[1:-3, -2, i] - (self.all_fft_data[2:-2, -2, i]) < 120) &
                (np.diff(self.all_fft_data[3:, -2, i]) < 0) &
                (np.diff(self.all_fft_data[1:-2, -2, i]) < 0) &
                (np.diff(self.all_fft_data[2:-1, -2, i]) > 120))[0]
                # (self.all_fft_data[:-2, -2, i] - (self.all_fft_data[1:-1, -2, i]) > 100) \
                    # | ((self.all_fft_data[:-2, -4, i] - self.all_fft_data[2:, -2, i]) > 100))[0]
            if errors.size:
                # print(errors)
                # print(errors[-1] + 2)
                # print(self.all_fft_data[errors[-1] + 2:, -2, i])
                self.all_fft_data[errors[-1] + 3:, -2, i] -= 360
                self.all_fft_data[errors[-1] + 3:, -1, i] += \
                    -1000 * self.all_fft_data[errors[-1] + 3:, -2, i] / self.all_fft_data[errors[-1] + 3:, -4, i] / 360
            # tau = -1000 * d_phase / freq / 360
        # for i in range(self.all_fft_data.shape[2]):
        #     for j in range(4):
        #         self.all_fft_data[:, j - 4, i] = np.nanmedian(self.all_fft_data[:, j::4, i], axis=1)
        #     if round_flag:
        #         self.all_fft_data[:, -4, i] = np.round(self.all_fft_data[:, -4, i], 2)
        #         self.all_fft_data[:, -3, i] = np.round(self.all_fft_data[:, -3, i], 4)
# -------------------------------------------------------------------------------------------------

    def get_special_points(self):
        # добавить сюда же поиск пересечения с -360
        # (надо не сбрасывать, потому что тогда задержка будет неправильной)
        self.special_points.resize((5, self.all_fft_data.shape[2]))
        self.special_points.fill(np.nan)
        self.special_points[-1, :] = 0
        f_180deg = -180
        for j in range(self.all_fft_data.shape[2]):
            i = np.where(
                (self.all_fft_data[:-1, -2, j] > f_180deg) &
                (self.all_fft_data[1:, -2, j] <= f_180deg))[0] + 1 #&
                # (np.roll(self.amp_and_freq[1:, -2], -1) <= f_180degrees)
            self.logger.debug(i)
            if any(i):
                i = i[0]  # можно сделать цикл по всем i, если их несколько 
                self.logger.debug(f'new {i}')
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
                self.logger.debug(f"special_points = {self.special_points[:, j]}")
# -------------------------------------------------------------------------------------------------
#
# -------------------------------------------------------------------------------------------------

    def get_fft_from_existing_data(self):
        self.delays = np.array(
            [int(0.8 * self.WAIT_TIME_SEC * self.fs),
                int(-0.32 * self.WAIT_TIME_SEC * self.fs)])  # не забыть их учесть в обработке
        # self.cycle_count = 1
        self.pack_num = 0
        self.GYRO_NUMBER = 1
        self.amp_shift.resize(self.GYRO_NUMBER)
        self.amp_shift.fill(0)

        if self.flag_do_not_save and self.flag_big_processing:  # лучше все эти флаги загнать в словарь
            self.logger.debug("do_not_save")  # добавить создание папки в текущей директории
            self.get_fft_from_folders(folder_to_save=os.getcwd(), file_name="sensor_list")  # !!!

        if self.flag_by_name:
            self.logger.debug("flag_by_name")
            file = os.path.basename(self.selected_files_to_fft[0])
            last_str = list(filter(None, re.split("_|_|.txt", file)))
            name_part = (f'{last_str[0]}_{last_str[1]}_{last_str[2]}'
                        if len(last_str) >= 3 else file)
            folder = os.path.dirname(self.selected_files_to_fft[0]) + '/'
            self.save_file_name[0] = folder + name_part
            self.fft_from_file_median(self.selected_files_to_fft)
# -------------------------------------------------------------------------------------------------

    def fft_from_file_median(self, file_list: list):
        """Calculate fft median data from several files."""
        self.k_amp.resize(self.GYRO_NUMBER)
        self.k_amp.fill(1)
        self.amp_shift.resize(self.GYRO_NUMBER)
        self.amp_shift.fill(0)
        self.total_cycle_num = len(file_list)
        self.logger.debug(f"total_cycle_num={self.total_cycle_num}")
        # n = 4
        filter_len = int(self.fs * 0.26 / self.fft_opt['decimation']) * 2 + 1  # filter_len = int(self.fs * 0.1) * 2 + 1, 0.21 for n = 2
        filter_list = [(np.ones(filter_len) / filter_len * 1.5).astype(np.float32), #] # const_filter
                       (custom_g_filter(len=int(35 / self.fft_opt['decimation']), k=0.008) * 1).astype(np.float32)]  # g_filter
        self.cycle_count = 1
        for file_for_fft in file_list:
            with open(file_for_fft) as file:
                line_len = len(file.readline().split("\t"))
                if line_len == 4:
                    self.get_existing_fft_file(file_for_fft)
                    if len(file_list) > 1:
                        self.warning_signal.emit("Only one file processed!")
                    break
                if line_len != 5 and line_len != 3:
                    self.logger.debug(f"{file.readline()}")
                    self.warning_signal.emit("You choose wrong file!")
                    continue
            self.fft_for_file(
                file_for_fft, filter_list, **self.fft_opt)
                # file_for_fft, filter_list, threshold=5300, decimation=n)
        self.cycle_count -= 1

        if self.cycle_count:
            self.fft_median_filter(round_flag=False)
            self.get_special_points()
            filename_list_median = [re.split("_", os.path.basename(file_for_fft))[0]]
            self.to_plot.resize(16 * self.fs, self.time_data.shape[1])  # !
            self.pack_num = self.time_data[-1, 0]
            self.package_num_list.append(self.pack_num)
            self.median_data_ready_signal.emit(filename_list_median)
# -------------------------------------------------------------------------------------------------

    # def fft_for_file(self, filename: str, filter_list: list, threshold: int = 5300, decimation: int = 2): # здесь не учитывается смещение по каналу гироскопа!
    def fft_for_file(self, filename: str, filter_list: list, **options): # здесь не учитывается смещение по каналу гироскопа!
        """Open file, find borders and calculate fft data."""
        self.logger.debug(f"start download {filename}")
        self.time_data = np.array(read_csv(
            filename, delimiter='\t', dtype=np.int32, 
            header=None, keep_default_na=False, na_filter=False,
            index_col=False, usecols=[0, 1, 2]))  # чтение части столбцов
        self.logger.debug(f"1, end download, file len {self.time_data.size}")
        bool_arr = np.greater(
            np.abs(self.time_data[::options['decimation'], 2]), options['threshold']).astype(np.float32)
        for current_filter in filter_list:
            bool_arr = np.convolve(bool_arr, current_filter, 'same')
        self.logger.debug("2, convolve end")
        start = options['decimation'] * np.where(
            (bool_arr[:-1] <= 0.5) & (bool_arr[1:] > 0.5))[0]
        start_arr = np.where(np.diff(start) > options['min_frame_len_k'] * self.fs)[0]
        if not start_arr.size:
            self.warning_signal.emit(
                f"No fft frames detected in {os.path.basename(filename)}!")
            return False
        start_arr = (np.insert(
            start[start_arr + 1], 0, start[0]) + self.delays[0]).astype(np.int32)
        end = options['decimation'] * np.where(
            (bool_arr[:-1] >= 0.5) & (bool_arr[1:] < 0.5))[0]
        if not end.size:
            self.warning_signal.emit(
                f"No fft frames detected in {os.path.basename(filename)}!")
            return False
        end_arr = np.where(np.diff(end) > options['min_frame_len_k'] * self.fs)[0]
        end_arr = (np.insert(
            end[end_arr], end[end_arr].size, end[-1]) + self.delays[1]).astype(np.int32)

        # self.logger.debug(f"\nd start= {np.diff(start)}\nd  end = {np.diff(end)}")
        if start_arr.size != end_arr.size:
            self.warning_signal.emit(
                f"Problems with frame selection! ({os.path.basename(filename)})")  # !!!!!!!!!!!!!!!!!!!!!!!!!
            # np.savetxt('error_' + os.path.basename(filename),
                    #    bool_arr, delimiter='\t', fmt='%.3f')
        self.logger.debug(f"\nstart= {start}\n end = {end}" +
                         f"\nstart arr= {start_arr}\n end  arr = {end_arr}")
        self.logger.debug(
            f"3, len start = {start.size}, len start after = {start_arr.size}" +
            f"4, len end = {end.size}, len end after = {end_arr.size}")
        
        rows_count = min(end_arr.size, start_arr.size)
        if self.cycle_count == 1:
            self.all_fft_data.resize(
                (rows_count, 4 * (self.total_cycle_num + 1), self.GYRO_NUMBER),
                refcheck=False)
            self.all_fft_data.fill(np.nan)
        elif rows_count != self.all_fft_data.shape[0]:
            self.logger.debug('wrong shape!')
            self.warning_signal.emit(f"Error in {os.path.basename(filename)} processing!")
            return False
        # ind = np.where(start_arr[1:rows_count] < end_arr[:rows_count-1])
        # print(rows_count) # print(ind) # print(start)
        # if ind[0]:
        #     print(1111111)
        #     start[ind + 1] = end_arr[ind]
        # print(start)
        # --- учет смещения по первым точкам гироскопа ---
        self.amp_shift = np.mean(
            self.time_data[:int(0.8 * start_arr[0] - self.delays[0]), 1], axis=0)
        self.logger.debug(f"amp_shift={self.amp_shift}")
        # --- round borders ---
        [start_arr, end_arr] = self.get_new_borderS(
            np.array([start_arr[:rows_count], end_arr[:rows_count]]), self.fs)  # лучше векторно округлить
        self.logger.debug(
            f"\n5, start arr rounded= {start_arr}\n end arr rounded= {end_arr}")
        # ---  ---
        flag_first = True
        fft_norm_gen = self.fft_normalization_generator()
        next(fft_norm_gen)
        fft_norm_gen.send((0, 0, 0, 0))
        # self.logger.debug("6")
        for i in range(rows_count):
            if i and start_arr[i] < end_arr[i - 1]:  # можно векторно проверять, не особо нужная часть
                self.logger.debug(
                    f"!!! start[{i}]={start_arr[i]}, end[{i}]={end_arr[i]}")
                start_arr[i] = end_arr[i - 1]
            if end_arr[i]:
                # if i < 99:
                if i < rows_count / options['n_get_fft_data_ext']:
                    # self.logger.debug(i)
                    [freq, amp, d_phase] = get_fft_data_ext(
                    # [freq, amp, d_phase] = get_fft_data_median_frame(  # ! fft делается несколько раз с разными границами
                        self.time_data[start_arr[i]:end_arr[i], 1],
                        self.time_data[start_arr[i]:end_arr[i], 2] * self.k_amp[0],
                        fs=self.fs, n=options['n_repeat'])
                        # fs=self.fs, n=30)
                    # self.logger.debug(i)
                else:
                    [freq, amp, d_phase] = get_fft_data(
                    # [freq, amp, d_phase] = get_fft_data_median_frame(  # ! fft делается несколько раз с разными границами
                        (self.time_data[start_arr[i]:end_arr[i], 1] - self.amp_shift),
                        self.time_data[start_arr[i]:end_arr[i], 2] * self.k_amp[0],
                        fs=self.fs)
                self.count_fft_frame = i + 1
                freq, amp, d_phase, tau = fft_norm_gen.send((freq, amp, d_phase, 0))
                # [freq, amp, d_phase, tau] = self.fft_normalization(
                    # freq, amp, d_phase)
                    # freq, amp, d_phase, d_phase_prev=self.all_fft_data[i-1, (self.cycle_count-1)*4, 0])
                self.all_fft_data[
                    i, (self.cycle_count-1)*4:self.cycle_count*4, 0
                    ] = [freq, amp, d_phase, tau]
            else:
                if flag_first:
                    flag_first = False
                    self.warning_signal.emit(
                        f"Too small data frame! ({os.path.basename(filename)})")
                    # np.savetxt('error_' + os.path.basename(filename),
                    #    bool_arr, delimiter='\t', fmt='%.3f')
                else:
                    self.warning_signal.emit("Again...")
                self.logger.debug(f"{[start_arr[i], end_arr[i]]}")
        self.logger.debug(
            f"median noise for {os.path.basename(filename)}: " +
            f"{np.nanmedian(np.abs(np.diff(self.all_fft_data[:, 1 + (self.cycle_count - 1) * 4, 0])))}")
        self.logger.debug(np.nanmean(np.abs(
            np.diff(self.all_fft_data[:, 1 + (self.cycle_count - 1) * 4, 0]))))
        self.cycle_count += 1
# -------------------------------------------------------------------------------------------------

    def fft_normalization_generator(self): # d_phase += 360 / 1000 * freq * 0.225  # ?
        # d_phase_prev_prev_prev = [0, 0, 0]
        # d_phase_prev_prev = [0, 0, 0]
        # d_phase_prev = [0, 0, 0]
        # flag = [False, False, False]
        yield
        cort = yield
        freq, amp, d_phase, i = cort
        while True:
            # --- processing cycle ---
            # d_phase += 360 / 1000 * freq * 0.225  # 0.225 - запаздывание при усреднении по 20 значениям вместо 10
            while not (-360 < d_phase <= 0 or np.isnan(d_phase)):
                d_phase += (360 if d_phase < -360 else -360)
            # while not (-360 < d_phase_prev[i] <= 0 or np.isnan(d_phase_prev[i])):
            #     d_phase_prev[i] += (360 if d_phase_prev[i] < -360 else -360)
                # self.logger.debug("Wrap")
            if self.cycle_count == 1 and 1.5 > freq > 0.5 and amp > 0:
                if -200 < d_phase < -160:
                    sign = -1
                    d_phase += 180
                else:
                    sign = 1
                self.k_amp[i] = amp * sign  #
                amp = 1
                self.logger.debug(f"k_amp[{i}] = {self.k_amp[i]}")
                if self.flag_full_measurement_start:
                    # --- normalization of the data already received ---
                    self.logger.debug("normalization")
                    self.to_plot[:, 1 + self.pack_len * i] = self.to_plot[:, 1 + self.pack_len * i] / self.k_amp[i]
            # if 1.5 > freq > 0.5 and amp > 0:
            #     d_phase_prev_prev = [0, 0, 0]
            #     d_phase_prev = [0, 0, 0]
            #     flag[i] = False
            # self.logger.debug(
                # f"wrap d_phase = {d_phase}, d_phase_prev = {d_phase_prev[i]}, freq={freq}")
            # if d_phase - d_phase_prev[i] > 135 and d_phase - d_phase_prev_prev[i] > 85:
            # if (d_phase - d_phase_prev[i]) > 125 and (d_phase_prev[i] - d_phase_prev_prev[i]) > 125 and d_phase > d_phase_prev_prev[i]:  # может сработать из-за выброса
            # if d_phase - d_phase_prev[i] > 999 and d_phase - d_phase_prev_prev[i] > 195:  # может сработать из-за выброса
                # flag[i] = True
                # self.logger.debug(f"really wrap! d_phase={d_phase}, freq={freq}")
                # self.logger.debug((d_phase - d_phase_prev_prev[i]) > 125)
                # self.logger.debug((d_phase_prev[i] - d_phase_prev_prev[i]) > 125)
                # self.logger.debug(f"d_phase={d_phase}, d_phase_prev[i]={d_phase_prev[i]}, d_phase_prev_prev[i]={d_phase_prev_prev[i]}")
                # d_phase_prev[i] -= 360
                # self.all_fft_data[self.count_fft_frame - 2, (self.cycle_count-1)*4+2:self.cycle_count*4, i] = \
                #         np.array([d_phase_prev[i], -1000 * d_phase_prev[i] / self.all_fft_data[self.count_fft_frame - 2, (self.cycle_count-1)*4, i] / 360])
            # d_phase_prev_prev_prev[i] = d_phase_prev_prev[i]
            # d_phase_prev_prev[i] = d_phase_prev[i]
            # d_phase_prev[i] = d_phase
            # if flag[i]:
            #     d_phase -= 360  # фаза меньше -360

            tau = -1000 * d_phase / freq / 360
            cort = yield (freq, amp, d_phase, tau)  # print(cort)
            freq, amp, d_phase, i = cort   
            # d_phase -= .5 * freq

    # def fft_normalization(self, freq, amp, d_phase, i=0):
    #     while not (-360 < d_phase <= 0):  # если d_phase = np.nan, то все сломается
    #         d_phase += (360 if d_phase < -360 else -360)
    #     if self.cycle_count == 1 and 1.5 > freq > 0.5 and amp > 0:
    #         if -200 < d_phase < -160:
    #             sign = -1
    #             d_phase += 180
    #         else:
    #             sign = 1
    #         self.k_amp[i] = amp * sign  #
    #         amp = 1
    #         self.logger.debug(f"k_amp[{i}] = {self.k_amp[i]}")
    #         if self.flag_full_measurement_start:  # нормировка уже полученных данных
    #             self.logger.debug("normalization")
    #             self.to_plot[:, 1 + self.pack_len * i] = self.to_plot[:, 1 + self.pack_len * i] / self.k_amp[i]
    #     tau = -1000 * d_phase / freq / 360
    #     return [freq, amp, d_phase, tau]
# -------------------------------------------------------------------------------------------------

    @staticmethod
    def get_new_borderS(borders: np.ndarray, fs: int):
        """Round array of borders.""" # тогда нужен лишний аргумент - неудобно
        # логично возвращать только одну измененную границу,
        # если border[0, :] не изменился, то зачем возвращать?
        # border[0] = border[1] - ((border[1] - border[0]) // self.fs) * self.fs
        borders[0, :] = borders[1, :] - ((borders[1, :] - borders[0, :]) // fs) * fs
        return np.greater_equal((borders[1, :] - borders[0, :]), fs) * borders

    @staticmethod
    def get_new_border(border: np.ndarray, fs: int):
        """Round borders."""
        # return (np.array([0, 0]) if (border[1] - border[0] < 0.4 * fs) else border)
        # border[0] = border[1] - ((border[1] - border[0]) // (fs / 2)) * (fs / 2)
        border[0] = border[1] - ((border[1] - border[0]) // fs) * fs
        # border[1] = border[0] + ((border[1] - border[0]) // (fs / 2)) * (fs / 2)
        return (np.array([0, 0]) if (border[1] - border[0]) < fs else border)
        # return (np.array([0, 0]) if (border[1] - border[0]) < fs / 2 else border)
        # border[1] = border[0] + ((border[1] - border[0]) // fs) * fs
        # return (np.array([0, 0]) if (border[1] - border[0]) < fs else border)

    @staticmethod
    def find_value_between_points(point1, point2, value):
        x1, y1 = point1
        x2, y2 = point2
        result = y1 + ((y2 - y1) / (x2 - x1)) * (value - x1)
        return result  # x
# -------------------------------------------------------------------------------------------------

    def get_fft_from_folders(self, folder_to_save, file_name):
        # file_name = 'sensors_nums — копия.txt'
        sensor_list = read_csv(
            file_name, dtype=np.str, delimiter='\n', header=None)
        for sensor_number in sensor_list[0]:
            check = list(filter(None, re.split("\.|\n", sensor_number)))
            if len(check[-1]) < 3:
                sensor_num = check[-2] + "." + check[-1]
            elif len(check[-1]) == 4:
                sensor_num = check[-1]
            sensor_folder = '//fs/Projects/АФЧХ/' + sensor_num
            self.logger.debug(f"\npath: {sensor_folder}")
            # быстрый способ, примерно в 20 раз быстрее
            only_files = [path.name for path in os.scandir(sensor_folder) if path.is_file()]
            # гораздо более медленный способ
            # only_files = [file for file in os.listdir(sensor_folder)
                        #  if os.path.isfile(os.path.join(sensor_folder, file))]
            self.selected_files_to_fft = []
            for file in only_files:
                split_filename = list(filter(None, re.split("_|_|.txt", file)))
                if len(split_filename) == 4 and split_filename[1] != 'fresh':
                    self.selected_files_to_fft.append(sensor_folder + '/' + file)
                    last_filename = split_filename
            # sensor_folder + '/' добавлять это, чтобы сохранять в той же папке
            self.save_file_name[0] = folder_to_save + \
                last_filename[0] + '_' + last_filename[1] + '_' +  last_filename[2]
            self.logger.debug(f"txt files in folder: {self.selected_files_to_fft}")
            self.fft_from_file_median(self.selected_files_to_fft) #, self.fft_filename)
            self.logger.debug("save fft")
            self.save_fft()
# -------------------------------------------------------------------------------------------------

    def get_existing_fft_file(self, file_for_fft):
        """Show data from FRQ_AMP_dPh file."""
        self.logger.debug("plot existing fft")
        # можно сделать так, чтобы до трех разных датчиков можно было выбирать
        try:
            self.all_fft_data = np.array(
                read_csv(file_for_fft, delimiter='\t',
                         dtype=np.float32, header=None,  #,
                         index_col=False, decimal=","))
        except ValueError:  # на случай, если в файле в качестве разделителей точки
            self.all_fft_data = np.array(
                read_csv(file_for_fft, delimiter='\t',
                         dtype=np.float32, header=None,  #,
                         index_col=False, decimal="."))
        self.all_fft_data.resize(
            self.all_fft_data.shape[0], self.all_fft_data.shape[1], 1)
        self.get_special_points()
        filename_list_median = [re.split("_", os.path.basename(file_for_fft))[0]]
        self.median_data_ready_signal.emit(filename_list_median)
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
