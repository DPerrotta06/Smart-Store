import RPi.GPIO as GPIO
import time

blue = 17
red = 18
buzzer = 24

GPIO.setmode(GPIO.BCM)
GPIO.setup(blue, GPIO.OUT)
GPIO.setup(red, GPIO.OUT)
GPIO.setup(buzzer, GPIO.OUT)

def success():
    GPIO.output(blue, GPIO.HIGH)
    time.sleep(3)
    GPIO.output(blue, GPIO.LOW)

def failure():
    GPIO.output(red, GPIO.HIGH)
    GPIO.output(buzzer, GPIO.HIGH)
    time.sleep(3)
    GPIO.output(red, GPIO.LOW)
    GPIO.output(buzzer, GPIO.LOW)





