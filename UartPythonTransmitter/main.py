#!/usr/bin/env python3
import sys
import os
import select
import threading

import matplotlib.pyplot as plt
import numpy as np
import serial

device_name = "/dev/ttyUSB0"
source_img_w = 4
source_img_h = 3

target_img = np.zeros((source_img_h, source_img_w, 3), dtype=np.uint8)

fifo_path = "/tmp/screencapture.fifo"

delay_between_frames = 0.5


def parse_img(data):
    try:
        global target_img
        image = np.fromstring(data, dtype='uint8')
        image = image.reshape((source_img_h, source_img_w, 3))
        # print("img parsed")
        target_img = image
        target_img[0][0][0] = 255
        target_img[0][0][1] = 0
        target_img[0][0][2] = 0

        target_img[source_img_h - 1][0][0] = 0
        target_img[source_img_h - 1][0][1] = 255
        target_img[source_img_h - 1][0][2] = 0

        target_img[0][source_img_w - 1][0] = 0
        target_img[0][source_img_w - 1][1] = 0
        target_img[0][source_img_w - 1][2] = 255

        target_img[source_img_h - 1][source_img_w - 1][0] = 255
        target_img[source_img_h - 1][source_img_w - 1][1] = 255
        target_img[source_img_h - 1][source_img_w - 1][2] = 255

    except Exception:
        print("error in parse_img")


def avg_pixel(fromx, fromy, tox, toy):
    avgs = [0.0, 0.0, 0.0]
    pixel = bytearray(3)
    count = 0
    for y in range(fromy, toy):
        for x in range(fromx, tox):
            for z in range(0, 3):
                avgs[z] += target_img[y][x][z]
                target_img[y][x][z] = 128
                count += 1
    for z in range(0, 3):
        avgs[z] = avgs[z] / count
        pixel[z] = int(avgs[z])

    return pixel


def send_pixel(ser, pixel):
    data = bytearray(3)
    data[0] = pixel[0]
    data[1] = pixel[1]
    data[2] = pixel[2]
    ser.write(data)
    ser.flush()


def send_preambula(ser):
    data = bytearray(6)
    data[0] = ord('A')
    data[1] = ord('d')
    data[2] = ord('a')
    data[3] = 12
    data[4] = 34
    data[5] = 123
    ser.write(data)
    ser.flush()


def send_uart():
    ser = serial.Serial(device_name, 115200)  # open serial port
    import time
    time.sleep(5)
    print("serial ready")
    while True:
        send_preambula(ser)

        for h in range(source_img_h - 1, 0, -1):
            send_pixel(ser, target_img[h][0])

        for w in range(0, source_img_w):
            send_pixel(ser, target_img[0][w])

        for h in range(1, source_img_h):
            send_pixel(ser, target_img[h][source_img_w - 1])

        # data = bytearray(3)
        # data[0] = 0
        # data[1] = 0
        # data[2] = 0
        #
        # for i in range(0, 8):
        #     send_pixel(ser, data)
        #     data[1] = (i + 1) * 30
        #     data[2] = (8 - i) * 30

        time.sleep(delay_between_frames)

    ser.close()  # close port


def read_exactly(fd, size):
    data = bytearray(0)
    remaining = size
    while remaining > 0:  # or simply "while remaining", if you'd like
        newdata = fd.read(remaining)
        if len(newdata) != 0:
            data.extend(newdata)
            remaining -= len(newdata)

    return data


def show_img():
    while True:
        # print("drawn")
        fg = plt.figure()
        ax = fg.gca()
        form = ax.imshow(target_img)
        plt.show()
        plt.pause(delay_between_frames)


def upd_source_img():
    print("fifo read started")
    with open(fifo_path, "rb") as fifo:
        while True:
            select.select([fifo], [], [fifo])
            data = read_exactly(fifo, source_img_h * source_img_w * 3)
            if len(data) > 0:
                parse_img(bytes(data))


def dump_with_ffmpeg():
    print("dump started")
    import time
    while True:
        os.system(
            "ffmpeg -y -loglevel error -f x11grab -s 1920x1080 -i :0.0 -s " + str(source_img_w) + "x" + str(
                source_img_h) + " -vframes 1 -f rawvideo -threads 2 -pix_fmt rgb24 - > " + fifo_path)
        time.sleep(delay_between_frames)


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("usage: " + sys.argv[0] + " <serial device name> <led strip pixels width> <led strip pixels height>")
        exit(-1)
    device_name = sys.argv[1]
    source_img_w = int(sys.argv[2])
    source_img_h = int(sys.argv[3])

    print("using port " + device_name + " image size " + str(source_img_w) + "x" + str(source_img_h))

    os.system("rm -rf " + fifo_path)
    os.system("mkfifo " + fifo_path)

    dump_thread = threading.Thread(target=dump_with_ffmpeg)
    dump_thread.daemon = True
    dump_thread.start()

    parse_thread = threading.Thread(target=upd_source_img)
    parse_thread.daemon = True
    parse_thread.start()

    send_thread = threading.Thread(target=send_uart)
    send_thread.daemon = True
    send_thread.start()

    while True:
        import time

        time.sleep(1)
        show_img()
