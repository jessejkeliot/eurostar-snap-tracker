from time import sleep

from src.workers.scheduler import handler

while True:
    handler()
    sleep(60)