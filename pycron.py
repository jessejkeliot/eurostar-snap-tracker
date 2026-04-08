from time import sleep

from scheduler import handler

while True:
    handler()
    sleep(60 * 18)