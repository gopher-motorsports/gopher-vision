import serial
import time
import go4v

PORT = "COM4"
BAUD = 230400
BLOCK_SIZE = 1000
DELAY = 1

port = serial.Serial(PORT, BAUD, timeout=0)

ids = list(go4v.parameters.keys())

print('Transmitting data...')
while True:
    data = go4v.generate_data(ids, BLOCK_SIZE)
    port.write(data)
    time.sleep(DELAY)