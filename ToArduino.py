# coding:utf-8

import serial
import time

# plist = list(serial.tools.list_ports.comports())

# if len(plist) <= 0:
#         print("没有发现端口!")
# else:
#     plist_0 = list(plist[0])
#     serialName = plist_0[0]
serialName = "COM3"
baudRate=9600
serialFd = serial.Serial(serialName, baudRate, timeout=5)
# print("可用端口名>>>", serialFd.name)
while 1:
    serialFd.write("1".encode())
    time.sleep(0.5)
    serialFd.write("0".encode())
    time.sleep(1)