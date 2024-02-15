# import logging
import sys
# import os
# import re
# import json
import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui
# from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo
from time import time, sleep
# import PyQt_Logger
# import PyQt_Thread
# import PyQt_CustomWidgets
from PyQt_Functions import get_icon_by_name, get_res_path, natural_keys
from PyQt_ApplicationClass import AppWindow


class AppWindowTest(AppWindow):
    def __init__(self, parent=None):
        AppWindow.__init__(self, parent, GYRO_NUMBER=3)
        # print(bytes([114, 0, 0, 0]))
        # print(bytes([0x72, 0, 0, 0]))
        # print(bytes([255, 0, 9, 0]))
        # print(bytes([0xFF, 0, 0x09, 0]))
        # print(sys.getsizeof(self))

                # del (self.custom_tab_plot_widget.widget(self.custom_tab_plot_widget.count()-1)
                # self.custom_tab_plot_widget.time_curves[0].setData([])
                # for i in range(self.GYRO_NUMBER):
                #     self.custom_tab_plot_widget.time_curves[i + 1].setData([])
                #     self.custom_tab_plot_widget.amp_curves[i].setData([])
                #     self.custom_tab_plot_widget.phase_curves[i].setData([])
        # # print(sys.getsizeof(self))
        # sleep(3)
        # self.new_cycle_event()
        # self.new_cycle_event()
        # self.new_cycle_event()
        # self.new_cycle_event()
        # self.new_cycle_event()
        # # # self.custom_tab_plot_widget.append_fft_plot_tab()
        # # # self.custom_tab_plot_widget.append_fft_plot_tab()
        # # # self.custom_tab_plot_widget.append_fft_plot_tab()
        # # # self.custom_tab_plot_widget.append_fft_plot_tab()
        # # # self.custom_tab_plot_widget.append_fft_plot_tab()
        # sleep(3)
        # self.custom_tab_plot_widget.clear_plots()
        # print(sys.getsizeof(self))

    @QtCore.pyqtSlot()
    def measurement_start(self):
        # self.custom_tab_plot_widget.append_fft_plot_tab()
        # for i in range(self.GYRO_NUMBER):
        #     # self.amp_plot_list[-1].getPlotItem().curves[i].setData(freq_data[:, 0, i],
        #                                 # freq_data[:, 1, i])
        #     # self.phase_plot_list[-1].getPlotItem().curves[i].setData(freq_data[:, 0, i],
        #                                 # freq_data[:, 2, i])
        #     # ind = self.GYRO_NUMBER * (self.count() - 2) + i
        #     self.custom_tab_plot_widget.amp_curves[-1 - i].setData([3, 6])
        #     self.custom_tab_plot_widget.phase_curves[-1 - i].setData([7, 9])
        # print(self.custom_tab_plot_widget.count())
        # self.custom_tab_plot_widget.setTabVisible(0, False)
        # self.custom_tab_plot_widget.setTabEnabled(0, False)
        # self.custom_tab_plot_widget.widget(0).setDisabled(False)
        # print(self.custom_tab_plot_widget.vis())
        # return
        # for i in range(5):
        #     sleep(1)
        #     print("")
        #     print("create")
        #     print("")
        #     # self.new_cycle_event()
        #     # self.new_cycle_event()
        #     # self.new_cycle_event()
        #     # self.new_cycle_event()
        #     # self.new_cycle_event()
        #     self.custom_tab_plot_widget.append_fft_plot_tab()
        # for i in range(self.GYRO_NUMBER):
        #     # self.amp_plot_list[-1].getPlotItem().curves[i].setData(freq_data[:, 0, i],
        #                                 # freq_data[:, 1, i])
        #     # self.phase_plot_list[-1].getPlotItem().curves[i].setData(freq_data[:, 0, i],
        #                                 # freq_data[:, 2, i])
        #     # ind = self.GYRO_NUMBER * (self.count() - 2) + i
        #     self.custom_tab_plot_widget.amp_curves[-1 - i].setData([7, 9,7,5,7,5,5,4,77,7,5,7, 9,7,5,7,5,5,4,77,7,5,7, 9,7,5,7,5,5,4,77,7,5,7])
        #     self.custom_tab_plot_widget.phase_curves[-1 - i].setData([7, 9,7,5,7,5,5,4,77,7,5,7, 9,7,5,7,5,5,4,77,7,5,7, 9,7,5,7,5,5,4,77,7,5,7])
        #     self.custom_tab_plot_widget.append_fft_plot_tab()
        # for i in range(self.GYRO_NUMBER):
        #     # self.amp_plot_list[-1].getPlotItem().curves[i].setData(freq_data[:, 0, i],
        #                                 # freq_data[:, 1, i])
        #     # self.phase_plot_list[-1].getPlotItem().curves[i].setData(freq_data[:, 0, i],
        #                                 # freq_data[:, 2, i])
        #     # ind = self.GYRO_NUMBER * (self.count() - 2) + i
        #     self.custom_tab_plot_widget.amp_curves[-1 - i].setData([7, 9,7,5,7,5,5,4,77,7,5,7, 9,7,5,7,5,5,4,77,7,5,7, 9,7,5,7,5,5,4,77,7,5,7])
        #     self.custom_tab_plot_widget.phase_curves[-1 - i].setData([7, 9,7,5,7,5,5,4,77,7,5,7, 9,7,5,7,5,5,4,77,7,5,7, 9,7,5,7,5,5,4,77,7,5,7])
        #     # self.custom_tab_plot_widget.append_fft_plot_tab()
        #     # self.custom_tab_plot_widget.append_fft_plot_tab()
        #     # self.custom_tab_plot_widget.append_fft_plot_tab()
        #     # print(sys.getsizeof(self))
        #     # print(2)
        #     sleep(1)
        #     print("")
        #     print("clear")
        #     print("")
        #     # self.custom_tab_plot_widget.clear_plots()
        #     for _ in range(self.custom_tab_plot_widget.count() - 2):
        #         for _ in range(self.GYRO_NUMBER):
        #             # self.amp_curves[-1].clear()
        #             # self.phase_curves[-1].clear()
        #             self.custom_tab_plot_widget.amp_curves.pop()
        #             self.custom_tab_plot_widget.phase_curves.pop()
        #         print(self.custom_tab_plot_widget.count())
        #         # print(self.custom_tab_plot_widget.amp_plot_list[-1])
        #         # print(self.custom_tab_plot_widget.amp_plot_list[-1].parent())
        #         # print(self.custom_tab_plot_widget.amp_plot_list[-1].parent().parent())
        #         print(self.custom_tab_plot_widget.widget(self.custom_tab_plot_widget.count()-1))
        #         # self.custom_tab_plot_widget.amp_plot_list[-1].deleteLater()
        #         self.custom_tab_plot_widget.amp_plot_list.pop()
        #         # self.custom_tab_plot_widget.phase_plot_list[-1].deleteLater()
        #         self.custom_tab_plot_widget.phase_plot_list.pop()
        #         # self.custom_tab_plot_widget.tab_widget_page_list[-1].deleteLater()
        #         self.custom_tab_plot_widget.tab_widget_page_list.pop()
        #         i =self.custom_tab_plot_widget.count()-1
        #         self.custom_tab_plot_widget.widget(i).deleteLater()
        #         self.custom_tab_plot_widget.removeTab(i)
        #         # print(self.custom_tab_plot_widget.tab_widget_page_list)
        # return
        self.progress_value = 0  # не создавать эту переменную
        self.progress_bar.setValue(0)
        self.package_num_label.setText('0')
        self.count = 0
        self.current_cycle = 1
        if self.processing_thr.isRunning():
            self.logger.warning("Thread still work")
            return
        # Check COM port
        self.logger.debug(F"\nPORT: {self.com_port_name_combobox.currentText()}\n")
        from pandas import read_csv, DataFrame
        # filename = 'прежнее/6884_139_6.2_4.txt'
        filename = '6884_139_6.2_5.txt'
        self.time_data_test = np.array(
            read_csv(filename, delimiter='\t', 
                     dtype=np.int32, header=None,  #,
                     keep_default_na=False, na_filter=False,
                     index_col=False, usecols=[1, 2, 3, 4], 
                     skiprows=2000))
        # self.get_gyro_count()  # !!!!!!!!!!! #################################################
        self.progress_bar.setMaximum(-1)
        self.tab_plot_widget.clear_plots()
        self.set_available_buttons(flag_running=True)  # disable widgets

        self.logger.debug(f"{self.com_port_name_combobox.currentText()} open")
        self.logger.warning("Start")
        # Start timers
        self.start_time = time()
        self.timer_receive.start()
        self.fs = int(self.fs_combo_box.currentText())
        # Copy variables to another classes and start thread
        self.tab_plot_widget.fs = self.fs
        self.processing_thr.pack_len = 2
        self.processing_thr.fs = self.fs
        self.processing_thr.flag_measurement_start = True
        self.processing_thr.flag_do_not_save = True
        self.processing_thr.total_time = self.table_widget.total_time
        self.processing_thr.start()

    def full_measurement_start(self):
        self.progress_bar.setValue(0)
        self.progress_value = 0
        self.count = 0
        self.current_cycle = 1
        self.package_num_label.setText('0')
        self.flag_send = False
        if not self.table_widget.total_time:
            self.cycle_num_value_change()
            if not self.choose_and_load_file():
                self.logger.debug("No data from file")
                return
        self.logger.debug("Data from file was loaded")
        self.cycle_num_value_change()
        self.progress_bar_set_max()
        self.set_available_buttons(True)  # disable widgets
        self.logger.debug(f"self.cycle_num = {self.total_cycle_num}")
        self.logger.warning("Start")
        self.tab_plot_widget.clear_plots()
        self.tab_plot_widget.append_fft_cycle_plot_tab() 
        from pandas import read_csv, DataFrame
        # filename = 'прежнее/6884_139_6.2_4.txt'
        # filename = 'прежнее/6884_139_6.2_4.txt'
        filename = '6884_139_6.2_5.txt'
        self.time_data_test = np.array(
            read_csv(filename, delimiter='\t', 
                     dtype=np.int32, header=None,  #,
                     keep_default_na=False, na_filter=False,
                     index_col=False, usecols=[1, 2, 3, 4], 
                     skiprows=2000))
        # self.logger.debug("1")
        # DataFrame(self.time_data_test).to_csv(
        #     "ddddddd.txt", header=None, index=None,
        #     sep='\t', mode='w', date_format='%d', decimal=',')
        # self.logger.debug("2")
        # from PyQt_Functions import get_fft_data  # ! показательно !
        # print(get_fft_data(self.time_data_test[2_400:11_400, 0], self.time_data_test[2_400:11_400, 1], 1000))
        # # print(get_fft_data(self.time_data_test[4_400:9_400, 0], self.time_data_test[4_400:9_400, 1], 1000))
        # print(get_fft_data(self.time_data_test[6_400:8_400, 0], self.time_data_test[6_400:8_400, 1], 1000))
        # print(get_fft_data(self.time_data_test[4_400:5_400, 0], self.time_data_test[4_400:5_400, 1], 1000))
        # print(get_fft_data(self.time_data_test[4_900:5_900, 0], self.time_data_test[4_900:5_900, 1], 1000))
        # print(get_fft_data(self.time_data_test[4_700:5_900, 0], self.time_data_test[4_700:5_900, 1], 1000))
        # print(get_fft_data(self.time_data_test[4_200:5_900, 0], self.time_data_test[4_200:5_900, 1], 1000))
        # print(get_fft_data(self.time_data_test[6_200:7_200, 0], self.time_data_test[6_200:7_200, 1], 1000))
        # print(get_fft_data(self.time_data_test[3_200:4_900, 0], self.time_data_test[3_200:4_900, 1], 1000))
        # print(get_fft_data(self.time_data_test[10_400:11_400, 0], self.time_data_test[10_400:11_400, 1], 1000))
        # return
        self.PLOT_TIME_INTERVAL_SEC = 20
        self.PAUSE_INTERVAL_MS = 4000
        self.start_time = time()
        self.timer_event_send_com()
        self.timer_send_com.start()
        self.timer_receive.start()
        self.fs = int(self.fs_combo_box.currentText())
        self.tab_plot_widget.fs = self.fs
        self.processing_thr.fs = self.fs
        self.processing_thr.flag_full_measurement_start = True
        self.processing_thr.total_time = self.table_widget.total_time * 5 # !!!
        self.processing_thr.num_measurement_rows = self.table_widget.rowCount()
        self.processing_thr.total_cycle_num = self.total_cycle_num
        self.processing_thr.start()
        # print(np.mean(self.time_data_test[:, 0]))
        print(np.mean(self.time_data_test[:100, 0]))
        print(np.mean(self.time_data_test[:500, 0]))
        print(np.mean(self.time_data_test[:750, 0]))
        print(np.mean(self.time_data_test[:2500, 0]))
        print(np.mean(self.time_data_test[:4000, 0]))
        print("enc " + str(np.mean(self.time_data_test[:4000, 1])))

        self.check_time = time()

    @QtCore.pyqtSlot()
    def timer_read_event(self):
        self.read_serial()

    def read_serial(self):
        self.progress_value = time() - self.start_time
        self.progress_bar.setValue(int(round(self.progress_value)))
        # data = b'\x72\xFF\xFF\xFF\x00\x00\x03\xF0\xF0\xF0\x00\x00\x04\x0F\x0F\x0F\x00\x00\x05\x27\x72\xFF\xFF\xFF\x00\x00\x06\xFF\xFF\xFF\x00\x00\x07\xFF\xFF\xFF\x00\x00\x08\x27'
        data: bytearray = b""
        package_num = int(self.package_num_label.text())
        if self.GYRO_NUMBER == 1:
            for i in range(self.READ_INTERVAL_MS):
            # for i in range(200):
                data += int.to_bytes(0x72, length=1, byteorder='big')
                for j in range(4):
                    data += int.to_bytes(int(self.time_data_test[package_num + i, j]),
                                        length=3, byteorder='big', signed=True)
                data += int.to_bytes(0x27, length=1, byteorder='big')
        if self.GYRO_NUMBER == 3:
            for i in range(self.READ_INTERVAL_MS):
                data += int.to_bytes(0x72, length=1, byteorder='big')
                for j in range(3):
                    # data += int.to_bytes((j+1)*int(self.time_data_test[package_num + i + 8000*j, 0]),
                    data += int.to_bytes((j+1)*int(self.time_data_test[package_num + i + 80*j, 0]),
                                        length=3, byteorder='big', signed=True)
                    # data += int.to_bytes((j+1)*int(self.time_data_test[package_num + i + 8000*j, 1]),
                    data += int.to_bytes((j+1)*int(self.time_data_test[package_num + i + 80*j, 1]),
                                        length=3, byteorder='big', signed=True)
                data += int.to_bytes(0x27, length=1, byteorder='big')
        self.processing_thr.rx = data
        self.processing_thr.data_received_event.set()
        self.processing_thr.count_fft_frame = self.count
        self.processing_thr.flag_send = self.flag_send
        self.logger.debug(f"thr_start, count = {self.count}")

    @QtCore.pyqtSlot()
    def timer_event_send_com(self):
        # print(self.current_cycle)
        if self.flag_send:
            self.logger.debug(
                f"count = {self.count}, num_rows={self.table_widget.rowCount()}")
            if self.count >= self.table_widget.rowCount():
                if self.current_cycle < self.total_cycle_num:
                    self.new_cycle_event()
                else:
                    self.stop()
                return
            self.send_vibro_command()
        else:
            self.timer_send_com.setInterval(self.PAUSE_INTERVAL_MS)
        self.flag_send = not self.flag_send
        self.logger.debug("---end_send_command")

    def send_vibro_command(self):
        self.table_widget.selectRow(self.count)
        self.timer_send_com.setInterval(self.table_widget.get_current_T())
        self.count += 1

    @QtCore.pyqtSlot()
    def stop(self):
        self.set_available_buttons(False)
        if self.timer_send_com.isActive():
            self.timer_send_com.stop()
        if self.timer_receive.isActive():
            self.timer_receive.stop()
        self.logger.debug(
            f"time = {self.progress_value}, " +
            f"total time = {self.progress_bar.maximum()}")

        if self.processing_thr.isRunning():
            self.logger.warning("End of measurements\n")
            if self.progress_value > 5:
                check = int(int(self.package_num_label.text()) / self.progress_value)
                if not (0.95 * self.fs < check < 1.05 * self.fs):
                    QtWidgets.QMessageBox.critical(
                        None, "Warning",
                        f"You set fs = {self.fs} Hz," +
                        f"but in fact it's close to {check} Hz")
            # Check filenames
            for i in range(self.GYRO_NUMBER):
                self.make_filename(i)
        self.processing_thr.flag_full_measurement_start = False
        self.processing_thr.flag_measurement_start = False
        self.processing_thr.data_received_event.set()

    # def show_certain_data(self):
    #     pass

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
###############################################################################
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    splash = QtWidgets.QSplashScreen(QtGui.QPixmap(get_res_path('res/G.png')))
    splash.show()
    app.processEvents()

    test = True
    # test = False
    if test:
        window = AppWindowTest()
    else:
        window = AppWindow()
    splash.finish(window)
    sys.exit(app.exec())
    # можно перезапуск приложения добавить для случая, если пользователь меняет число гироскопов