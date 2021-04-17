#!/bin/sh
cd /home/pi/bundabergmixer_9000/
python3 main.py --config input:touch:mtdev,/dev/input/by-id/usb-Fondar_Fondar_USB_Touch_00000000001A-event-if00 --config graphics:show_cursor:0
