#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# BakeBit example for the basic functions of BakeBit 128x64 OLED
# http://wiki.friendlyarm.com/wiki/index.php/BakeBit_-_OLED_128x64
#
# The BakeBit connects the NanoPi NEO and BakeBit sensors.
# You can learn more about BakeBit here:  http://wiki.friendlyarm.com/BakeBit
#
# Have a question about this example?  Ask on the forums here:  http://www.friendlyarm.com/Forum/
#

"""
## License

The MIT License (MIT)

BakeBit: an open source platform for connecting BakeBit Sensors to the NanoPi NEO.
Copyright (C) 2016 FriendlyARM

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""
import functools
import os
import signal
import socket
import subprocess
import threading
import time

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

import bakebit_128_64_oled as oled

width = 128
height = 64
showPageIndicator = False

""""""
image = Image.new('1', (width, height))
draw = ImageDraw.Draw(image)

"""文字"""
font_regular_11 = ImageFont.truetype('DejaVuSansMono.ttf', 11)
font_regular_14 = ImageFont.truetype('DejaVuSansMono.ttf', 14)
font_bold_10 = ImageFont.truetype('DejaVuSansMono-Bold.ttf', 10)
font_bold_14 = ImageFont.truetype('DejaVuSansMono-Bold.ttf', 14)
font_bold_24 = ImageFont.truetype('DejaVuSansMono-Bold.ttf', 24)

"""内部变量"""
pageIndex = 0
drawing = False
display_is_on = True
lock = threading.Lock()


def page_indicator(func):
    def wrapper(*args, **kw):
        if showPageIndicator:
            page_count = len(render.pages)
            dot_width = 4
            dot_padding = 2
            dot_x = width - dot_width - 1
            dot_y = (height - page_count * dot_width - (page_count - 1) * dot_padding) / 2
            for i in range(page_count):
                render.draw_pen.rectangle((dot_x, dot_y, dot_x + dot_width, dot_y + dot_width), outline=255,
                                          fill=255 if i == page_index else 0)
                dot_y = dot_y + dot_width + dot_padding
        return func(*args, **kw)

    return wrapper


class RenderPage:
    def __init__(self, draw_pen, is_drawing):
        self.draw_pen = draw_pen
        self.is_drawing = is_drawing

        self.page_sleep_or_shutdown_sleep = functools.partial(self.__page_sleep_or_shutdown, True)
        self.page_sleep_or_shutdown_shutdown = functools.partial(self.__page_sleep_or_shutdown, False)
        self.page_shutdown_no = functools.partial(self.__page_shutdown, True)
        self.page_shutdown_yes = functools.partial(self.__page_shutdown, False)

        self.pages = (
            self.page_ip, self.page_info, self.page_sleep_or_shutdown_sleep, self.page_sleep_or_shutdown_shutdown,
            self.page_shutdown_no, self.page_shutdown_yes, self.page_closing)

    def __page_sleep_or_shutdown(self, is_first):
        self.draw_pen.text((2, 2), 'You wanna?', font=font_bold_14, fill=255)

        self.draw_pen.rectangle((2, 20, width - 4, 20 + 16), outline=0, fill=255 if is_first else 0)
        self.draw_pen.text((4, 22), 'Sleep', font=font_regular_11, fill=0 if is_first else 255)

        self.draw_pen.rectangle((2, 38, width - 4, 38 + 16), outline=0, fill=0 if is_first else 255)
        self.draw_pen.text((4, 40), 'Shutdown', font=font_regular_11, fill=255 if is_first else 0)

    def __page_shutdown(self, is_first):
        self.draw_pen.text((2, 2), 'Shutdown?', font=font_bold_14, fill=255)

        self.draw_pen.rectangle((2, 20, width - 4, 20 + 16), outline=0, fill=255 if is_first else 0)
        self.draw_pen.text((4, 22), 'Yes', font=font_regular_11, fill=0 if is_first else 255)

        self.draw_pen.rectangle((2, 38, width - 4, 38 + 16), outline=0, fill=0 if is_first else 255)
        self.draw_pen.text((4, 40), 'No', font=font_regular_11, fill=255 if is_first else 0)

    @page_indicator
    def page_ip(self):
        # week
        text = time.strftime("%A")
        self.draw_pen.text((2, 2), text, font=font_regular_14, fill=255)

        # date
        text = time.strftime("%e %b %Y")
        self.draw_pen.text((2, 18), text, font=font_regular_14, fill=255)

        # time
        text = time.strftime("%X")
        self.draw_pen.text((2, 40), text, font=font_bold_24, fill=255)

    @page_indicator
    def page_info(self):
        # Draw some shapes.
        # First define some constants to allow easy resizing of shapes.
        padding = 1
        top = padding
        # bottom = height - padding
        # Move left to right keeping track of the current x position for drawing shapes.
        x = 0
        info_ip = "IP: " + get_ip()

        cmd = "top -bn1 | grep load | awk '{printf \"CPU Load: %.2f\", $(NF-2)}'"
        info_cpu = str(subprocess.check_output(cmd, shell=True))

        cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%sMB %.2f%%\", $3,$2,$3*100/$2 }'"
        info_mem = str(subprocess.check_output(cmd, shell=True))

        cmd = "df -h | awk '$NF==\"/\"{printf \"Disk: %d/%dGB %s\", $3,$2,$5}'"
        info_disk = str(subprocess.check_output(cmd, shell=True))

        temp = int(open('/sys/class/thermal/thermal_zone0/temp').read())
        if temp > 1000:
            temp = temp / 1000
        info_temp = "CPU TEMP: %sC" % str(temp)

        self.draw_pen.text((x, top + 5), info_ip, font=font_bold_10, fill=255)
        self.draw_pen.text((x, top + 5 + 12), info_cpu, font=font_bold_10, fill=255)
        self.draw_pen.text((x, top + 5 + 24), info_mem, font=font_bold_10, fill=255)
        self.draw_pen.text((x, top + 5 + 36), info_disk, font=font_bold_10, fill=255)
        self.draw_pen.text((x, top + 5 + 48), info_temp, font=font_bold_10, fill=255)

    def page_closing(self):
        self.draw_pen.text((2, 2), 'Shutting down', font=font_bold_14, fill=255)
        self.draw_pen.text((2, 20), 'Please wait', font=font_regular_11, fill=255)

    def closing(self):
        time.sleep(2)
        while True:
            lock.acquire()
            is_drawing_close_page = self.is_drawing
            lock.release()

            if not is_drawing_close_page:
                lock.acquire()
                self.is_drawing = True
                lock.release()

                oled.clearDisplay()

                break
            else:
                time.sleep(.1)
                continue
        time.sleep(1)
        os.system('systemctl poweroff')


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        ip = str(s.getsockname()[0])
    except socket.error:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def is_page(try_index):
    global pageIndex

    lock.acquire()
    index = pageIndex
    lock.release()

    return index == try_index


def draw_page(index=-1):
    global drawing
    global image
    global draw
    global font_regular_14
    global font_bold_10
    global width
    global height
    global pageIndex
    global showPageIndicator
    global width
    global height
    global lock

    if index > -1:
        lock.acquire()
        pageIndex = index
        lock.release()

    lock.acquire()
    is_drawing = drawing
    index = pageIndex
    lock.release()

    if is_drawing:
        return

    lock.acquire()
    drawing = True
    lock.release()

    # Draw a black filled box to clear the image.
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    render.pages[index]()

    oled.drawImage(image)

    lock.acquire()
    drawing = False
    lock.release()


def receive_signal(signum, stack):
    global pageIndex
    global display_is_on

    lock.acquire()
    index = pageIndex
    lock.release()

    if index == 6:
        return

    if signum == signal.SIGUSR1:
        # print('K1 pressed')

        if display_is_on:
            if is_page(2):  # 选择待机或关机页--待机
                oled.sendCommand(oled.SeeedOLED_Display_Off_Cmd)
                display_is_on = False
                draw_page(0)
            elif is_page(3):  # 选择待机或关机页--关机
                draw_page(4)
            elif is_page(4):  # 选择是否关机--否
                draw_page(0)
            elif is_page(5):  # 选择是否关机--是
                draw_page(6)
                render.closing()
            else:
                draw_page(2)
        else:
            oled.sendCommand(oled.SeeedOLED_Display_On_Cmd)
            display_is_on = True

    if signum == signal.SIGUSR2:
        # print('K2 pressed')

        if display_is_on:
            if is_page(0):
                draw_page(1)
            elif is_page(2):
                draw_page(3)
            elif is_page(4):
                draw_page(5)

    if signum == signal.SIGALRM:
        # print('K3 pressed')

        if display_is_on:
            if is_page(1):
                draw_page(0)
            elif is_page(3):
                draw_page(2)
            elif is_page(5):
                draw_page(4)


"""页面"""
render = RenderPage(draw, drawing)

"""初始化屏幕"""
oled.init()  # initialze SEEED OLED display
oled.setNormalDisplay()  # Set display to normal mode (i.e non-inverse mode)
oled.setHorizontalMode()

"""显示开机图片"""
start_image = Image.open('friendllyelec.png').convert('1')
oled.drawImage(start_image)
time.sleep(2)

"""接收三个按钮信号"""
signal.signal(signal.SIGUSR1, receive_signal)
signal.signal(signal.SIGUSR2, receive_signal)
signal.signal(signal.SIGALRM, receive_signal)

"""监听，执行操作"""
while True:
    try:
        draw_page()

        lock.acquire()
        page_index = pageIndex
        lock.release()

        time.sleep(1)
    except KeyboardInterrupt:
        break
    except IOError:
        print ("Error")
