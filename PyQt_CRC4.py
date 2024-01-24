

import numpy as np
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

def CRC8_CountBYTE(uiData, iSize):
	iRez=np.full((iSize), CRC8_INIT_VALUE)
	# unsigned int i
	# unsigned int iIndex
	# for(i=0;i <iSize; i++):
	for i in range(iSize):
		iIndex = np.bitwise_and(np.bitwise_xor(iRez, uiData[:, i]), 0xff)
		iRez = np.right_shift(CRC8_Table[np.right_shift(iIndex, 2)], (8 * (iIndex % 4)))
	return np.bitwise_and(np.bitwise_xor(iRez, CRC8_END_VALUE), 0xff)

# rx: bytes = b'\x72\xFF\xFF\xFF\x00\x00\x02\xFF\xFF\xFF\x00\x02\x09\x27\x72\x07\x02\x0F\x02\x29\x72\x25\x00\x00\x02\x00\x00\x27\x72\xFF\xFF\xFF\x00\x00\x02\xFF\xFF\xFF\x00\x02\x09\x27\x72\x07\x02\x0F\x02\x29\x72\x25\x00\x00\x02\x00\x00\x27\x72\xFF\xFF\xFF\x00\x00\x02\xFF\xFF\xFF\x00\x02\x09\x27\x72\x07\x02\x0F\x02\x29\x72\x25\x00\x00\x02\x00\x00\x27\x72\xFF\xFF\xFF\x00\x00\x02\xFF\xFF\xFF\x00\x02\x09\x27\x72\x07\x02\x0F\x02\x29\x72\x25\x00\x00\x02\x00\x00\x27\x72\xFF\xFF\xFF\x00\x00\x02\xFF\xFF\xFF\x00\x02\x09\x27\x72\x07\x02\x0F\x02\x29\x72\x25\x00\x00\x02\x00\x00\x27\x72\xFF\xFF\xFF\x00\x00\x02\xFF\xFF\xFF\x00\x02\x09\x27\x72\x07\x02\x0F\x02\x29\x72\x25\x00\x00\x02\x00\x00\x27\x72\xFF\xFF\xFF\x00\x00\x02\xFF\xFF\xFF\x00\x02\x09\x27\x72\x07\x02\x0F\x02\x29\x72\x25\x00\x00\x02\x00\x00\x27\x72\xFF\xFF\xFF\x00\x00\x02\xFF\xFF\xFF\x00\x02\x09\x27\x72\x07\x02\x0F\x02\x29\x72\x25\x00\x00\x02\x00\x00\x27\x72\xFF'
rx: bytes = b'\x72\xFF\xFF\xFF\x00\x00\x02\xFF\xFF\xFF\x00\x02\x09\x27\x72\xFF\xFF\xFF\x00\x00\x02\xFF\xFF\xFF\x00\x02\x09\x27'
bytes_arr = np.frombuffer(rx, dtype=np.uint8)
# print(np.unpackbits(b'\x72\xFF\xFF'))
start = np.where((bytes_arr[:-13] == 0x72) & (bytes_arr[13:] == 0x27))[0] + 1
start = start[np.where(np.diff(start) == 14)[0]]
start = np.insert(start, start.size, start[-1] + 14)
print(start)
expand = len(start)
array_r = np.zeros((expand, 4, 4), dtype=np.uint8)
iRez=np.full((expand), CRC8_INIT_VALUE)
for i in range(4):
	for j in range(3):
		array_r[:, i, j] = bytes_arr[np.add(start, 3*i + j)]
		# CRC8
		uiData = bytes_arr[np.add(start, 3*i + j)]
		iIndex = np.bitwise_and(np.bitwise_xor(iRez, uiData), 0xff)
		iRez = np.right_shift(CRC8_Table[np.right_shift(iIndex, 2)], (8 * (iIndex % 4)))
		# uint8 ???
		print("----")
		print(np.add(start, 3*i + j))
		print(uiData)
		print(iIndex)
		print(iRez)
	# print(CRC8_CountBYTE(array_r[:, i, j], len(bytes_arr[np.add(start, 3*i + j)])))
print(np.bitwise_and(np.bitwise_xor(iRez, CRC8_END_VALUE), 0xff))

exit(0)
def ff():
	# for i in range(12):
	i = 0
	# print(i)
	i += 1
	yield i	
	i += 1
	yield i
	i += 1
	if True:
		print("true")
	yield i



def infinite_sequence():
	num = 0
	while True:
		if (num > 3):
			num = 0
		yield num
		num += 1

def infinite_print():
	num = 0
	while True:
		if (num > 3):
			num = 0
		print(f"print: {num}")
		yield
		num += 1
# print(ff)
# print(ff())
def infinite_sequence2():
	print("start")
	value = yield
	while True:
		print(value)
		value = yield
f = infinite_sequence2()
# f = infinite_sequence2(1).sent(2)
print(type(f))
next(f)
print(f.send(2))
print(f.send(5))
# print(iter(f))
exit(0)
		
f = ff()
print(next(f))
print(next(f))
print(next(f))
# next(ff)
# inf = infinite_sequence()
# print(next(inf))
# print(next(inf))
# print(next(inf))
# print(next(inf))
# print(next(inf))
# print(next(inf))
# print(next(inf))
inf = infinite_print()
next(inf)
next(inf)
next(inf)
next(inf)
next(inf)
next(inf)
next(inf)
exit(0)
for num in infinite_sequence():
	print(num)
