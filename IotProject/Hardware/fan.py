import RPi.GPIO as GPIO
from threading import Lock


ENABLE_PIN = 22  # Enable pin on the motor driver
IN1_PIN = 27     # Input pin 1
IN2_PIN = 18     # Input pin 2


class Fan:
    """Simulates the fan with a DC motor wired through a motor driver on the Raspberry Pi."""

    def __init__(self, enable_pin=ENABLE_PIN, in1_pin=IN1_PIN, in2_pin=IN2_PIN):
        self.enable_pin = enable_pin
        self.in1_pin = in1_pin
        self.in2_pin = in2_pin
        self._is_on = False
        self._lock = Lock()  # Flask can handle requests in several threads

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup([self.enable_pin, self.in1_pin, self.in2_pin], GPIO.OUT, initial=GPIO.LOW)

    # function to turn on the fan
    def on(self):
        with self._lock:
            GPIO.output(self.in1_pin, GPIO.LOW)
            GPIO.output(self.in2_pin, GPIO.HIGH)
            GPIO.output(self.enable_pin, GPIO.HIGH)
            self._is_on = True

    # function to turn off the fan
    def off(self):
        with self._lock:
            GPIO.output(self.enable_pin, GPIO.LOW)
            GPIO.output(self.in1_pin, GPIO.LOW)
            GPIO.output(self.in2_pin, GPIO.LOW)
            self._is_on = False

    def is_on(self):
        return self._is_on

    def status(self):
        return "ON" if self._is_on else "OFF"

    def cleanup(self):
        self.off()
        GPIO.cleanup()


# One shared instance for the whole app
fan = Fan()


if __name__ == "__main__":
    # Quick hardware test: python3 Hardware/fan.py
    from time import sleep
    print("Fan ON")
    fan.on()
    sleep(5)
    print("Fan OFF")
    fan.off()
    sleep(2)
    fan.cleanup()