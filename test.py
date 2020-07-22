from util.print_override import spikeprint;print = spikeprint
from spike import PrimeHub, LightMatrix, Button, StatusLight, ForceSensor, MotionSensor, Speaker, ColorSensor, App, DistanceSensor, Motor, MotorPair
from spike.control import wait_for_seconds, wait_until, Timer
import time
hub = PrimeHub()

hub.light_matrix.show_image('HAPPY')
wait_for_seconds(1)