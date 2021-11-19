#!/usr/bin/env python3
import sys
import threading
import time

import numpy as np
import serial
import cv2
from mss import mss
from flask import Flask, redirect, send_from_directory
from flask import render_template

app = Flask(__name__, template_folder="./template/")

device_name = "/dev/whatever"

source_img_w = 0
source_img_h = 0
target_img = np.zeros((source_img_h, source_img_w, 3), dtype=np.uint8)
total_pixels = 0

current_mode = 1

MODE_OFF = 0
MODE_AMBILIGHT = 1
MODE_CHRISTMAS = 2
MODE_SOLID_COLOUR = 3


mode_christmas_last_update = 0
mode_christmas_counter = 1

mode_solid_colour_r = 0
mode_solid_colour_g = 255
mode_solid_colour_b = 255


def time_millis():
    return int(round(time.time() * 1000))


def time_micros():
    return time.time()


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
    data[0] = pixel[2]
    data[1] = pixel[1]
    data[2] = pixel[0]
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
    ser = serial.Serial(device_name, 691200)
    time.sleep(5)
    print("serial ready")
    tmp_pixel = bytearray(3)
    global mode_christmas_last_update, mode_christmas_counter
    global mode_solid_colour_r, mode_solid_colour_g, mode_solid_colour_b
    while True:
        send_preambula(ser)

        if current_mode == MODE_OFF:
            tmp_pixel[0] = 0
            tmp_pixel[1] = 0
            tmp_pixel[2] = 0
            for x in range(0, total_pixels):
                send_pixel(ser, tmp_pixel)

        if current_mode == MODE_SOLID_COLOUR:
            tmp_pixel[0] = mode_solid_colour_r
            tmp_pixel[1] = mode_solid_colour_g
            tmp_pixel[2] = mode_solid_colour_b
            for x in range(0, total_pixels):
                send_pixel(ser, tmp_pixel)

        if current_mode == MODE_AMBILIGHT:
            for h in range(source_img_h - 1, 0, -1):
                send_pixel(ser, target_img[h][0])

            for w in range(0, source_img_w):
                send_pixel(ser, target_img[0][w])

            for h in range(1, source_img_h):
                send_pixel(ser, target_img[h][source_img_w - 1])

        if current_mode == MODE_CHRISTMAS:
            for x in range(0, total_pixels):
                if (x % 2) == (mode_christmas_counter % 2):
                    tmp_pixel[0] = 255
                    tmp_pixel[1] = 0
                    tmp_pixel[2] = 0
                else:
                    tmp_pixel[0] = 0
                    tmp_pixel[1] = 255
                    tmp_pixel[2] = 0
                send_pixel(ser, tmp_pixel)
            if (time_millis() - mode_christmas_last_update) > 1000:
                mode_christmas_last_update = time_millis()
                mode_christmas_counter += 1

        time.sleep(0.033)

    ser.close()  # close port


def dump_by_webcam():
    global target_img
    print("webcam dump started")
    # fps = 0
    # fps_last_dump = time_millis()
    webcam = cv2.VideoCapture(0)
    while True:
        if current_mode != MODE_AMBILIGHT:
            time.sleep(1)
            continue
        # start_time = time_micros()
        check, frame = webcam.read()
        # print(check)  # prints true as long as the webcam is running
        # print(frame)  # prints matrix values of each framecd
        sct_img = cv2.resize(np.array(frame), dsize=(source_img_w, source_img_h), interpolation=cv2.INTER_CUBIC)
        target_img = np.array(sct_img)
        # dump_time = time_micros() - start_time
        # print(dump_time)
        # ts = 0.029 - dump_time
        # if ts > 0:
        #     time.sleep(ts)
        # fps += 1
        # if (time_millis() - fps_last_dump) > 1000:
        #     fps_last_dump = time_millis()
        #     print("webcam dump fps: " + str(fps))
        #     fps = 0


@app.route('/')
def http_main_entry():
    return render_template('index.html', mode=current_mode)


@app.route('/mode/<mode>')
def change_mode(mode):
    global current_mode
    current_mode = int(mode)
    print("changed mode to " + str(mode))
    return redirect("/", code=302)


@app.route('/colour/<r>/<g>/<b>')
def change_colour(r, g, b):
    global mode_solid_colour_r, mode_solid_colour_g, mode_solid_colour_b
    mode_solid_colour_r = int(r)
    mode_solid_colour_g = int(g)
    mode_solid_colour_b = int(b)
    print("changed colour to " + r + "," + g + "," + b)
    return redirect("/", code=302)


@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('template', path)


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("usage: " + sys.argv[0] + " <serial device name> <led strip pixels width> <led strip pixels height>")
        exit(-1)
    device_name = sys.argv[1]
    source_img_w = int(sys.argv[2])
    source_img_h = int(sys.argv[3])
    np.zeros((source_img_h, source_img_w, 3), dtype=np.uint8)
    total_pixels = source_img_h * 2 + source_img_w

    print("using port " + device_name + " image size " + str(source_img_w) + "x" + str(source_img_h))

    dump_thread = threading.Thread(target=dump_by_webcam)
    dump_thread.daemon = True
    dump_thread.start()

    # send_thread = threading.Thread(target=send_uart)
    # send_thread.daemon = True
    # send_thread.start()

    app.run(host='0.0.0.0', port=8138, threaded=True)
