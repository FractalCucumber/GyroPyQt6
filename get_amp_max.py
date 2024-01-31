import re
import os
import numpy as np
from time import time
# def uniquify(path):
# path = "test.txt"
# filename, extension = os.path.splitext(path)
# counter = 1

# while os.path.exists(path) and counter < 10:
#     path = filename + "(" + str(counter) + ")" + extension
#     counter += 1
# print(path)

# arr1 = np.array([[1, 2, 3]])
# arr2 = np.array([1, 2, 3, 4, 5])

# # arr3 = np.array([])
# arr3 = np.empty(5, dtype=int)
# arr3 = np.vstack((arr2))
# arr3 = np.vstack((arr3, arr2))
# print(arr3)

# arr1[0, :] = [1, 2, 4]
# arr1[1, :] = [1, 2, 4]
# arr1[1, :] = arr2

# count = 1
# add_points = 0
# amp_and_freq = np.ndarray((2, 3), dtype=float)
# amp_and_freq[(count + add_points - 1), :] = [1, -1, 5]
# count += 1
# amp_and_freq[(count + add_points - 1), :] = [2, -2, 10]
# count += 1
# Freq  = 15
# dPhase = 3
# Amp = 3
# # amp_and_freq[(count + add_points - 1), :] = [Amp, dPhase, Freq]
# # count += 1

# print(amp_and_freq)

# if (count + add_points - 1) >= 1:
#     amp_prev = amp_and_freq[(count + add_points - 2), 0]
#     phase_prev = amp_and_freq[(count + add_points - 2), 1]
#     freq_prev = amp_and_freq[(count + add_points - 2), 2]
#     if abs(phase_prev - dPhase) > 4/3*np.pi:
#         add_points += 2
#         amp_and_freq = np.resize(
#             amp_and_freq, (count + add_points, 3))

#         dPhase += -2*np.pi
#         k = (phase_prev - dPhase) / (freq_prev - Freq)
#         b = phase_prev - k * freq_prev
#         freq_ = (- np.pi - b)/k
#         Freq_ = (-Freq + freq_prev) / (-phase_prev + dPhase)* phase_prev * (-np.pi) + freq_prev # + np.pi
#         k = (amp_prev - Amp) / (freq_prev - Freq)
#         b = amp_prev - k * freq_prev
#         Amp_ = k * freq_ + b
#         amp_and_freq[(count + add_points - 3), :] = [Amp_, -np.pi, freq_]
#         amp_and_freq[(count + add_points - 2), :] = [Amp_, np.pi, freq_]
#         print(f"prev f = {freq_prev}, now f = {Freq}, between = {Freq_}")
#         dPhase += 2*np.pi
#         print(f"prev ph = {phase_prev}, now ph = {dPhase}, amp = {Amp_}")

# amp_and_freq = np.resize(amp_and_freq,
#                         (count + add_points, 3))
# amp_and_freq[(count + add_points - 1), :] = [Amp, dPhase, Freq]
# print(amp_and_freq)

# f = [2, 4, 5]
# f.pop()
# print(f)

# for j in range (4):
#     print(j)
# for j in range (4):
#     print(j)
# for k in range (4):
#     print(k)
# k = 0
# if k is None:
#     print(1)

# with open("test_1(5).txt", "r") as f:
#    data = (f.read())
# i_start = 0
# for line in data:
# # for i in range(10):
#     # i_start += 18
#     # i_end = i_start + 18
#     print(line)
# matrix = np.loadtxt("test_1(8)_important.txt", usecols=range(5), dtype=int)

# matrix = np.loadtxt("D://GyroVibroTest/0test3/0test3_1.txt", usecols=[2], dtype=int)
matrix = np.loadtxt("0000test3_1.txt", usecols=[1], dtype=int)
matrix2 = np.loadtxt("0000test3_1.txt", usecols=[2], dtype=int)
f = []
f2 = []
print(len(matrix))
# for i in range(int(len(matrix)/5 - 1)):
for i in range(len(matrix) - 3):
    # print(matrix[i, :])
    # if not (matrix[i] == matrix[i + 1]):
    if (matrix[i] !=100 and matrix[i + 1] == 100 and matrix[i + 2] == 100 and matrix[i + 3] == 100):
        print(f"{matrix[i]}, {matrix[i + 1]}, {i}, amp = {matrix[i]}")
        f.append(int(matrix[i] / 1))
        f2.append(int(matrix2[i] / 10))
f.append(matrix[i])
f2.append(matrix[i])
arr = np.array([f, f2], dtype=np.int)
for i in range(len(f2)-1):
    print(arr[:, i])
print(f"{matrix[i]}, {matrix[i + 1]}, {i}")
# print(arr)
print(f"Done")
print(f)
print(f2)
print(f"------------")

print(matrix[:])
# matrix[:, 0:2] = matrix[:, 1:3]
# print(len(matrix[1]))
for i in range(1):
    print(i)
print(not (matrix[i] == matrix[i + 1]))
print(not (matrix[29513] == matrix[29513 + 1])) 
print(4 )
# f = []
# f2 = []
# print(len(matrix))
# # for i in range(int(len(matrix)/5 - 1)):
# for i in range(len(matrix) - 1):
#     # print(matrix[i, :])
#     if not (matrix[i, 3] == matrix[i + 1, 3]):
#         print(f"{matrix[i, 3]}, {matrix[i + 1, 3]}, {i}, amp = {matrix[i, 4]}")
#         f.append(matrix[i - 1, 3])
#         f2.append(matrix[i - 1, 4])
# f.append(matrix[i, 3])
# f2.append(matrix[i, 4])
# print(f"{matrix[i, 3]}, {matrix[i + 1, 3]}, {i}")
# print(f)
# print(f2)

# print(matrix[1, :])
# matrix[:, 0:2] = matrix[:, 1:3]
# print(len(matrix[1, :]))
# for i in range(1):
#     print(i)
# print(not (matrix[i, 3] == matrix[i + 1, 3]))
# print(not (matrix[29513, 3] == matrix[29513 + 1, 3])) 
# print(4 )
