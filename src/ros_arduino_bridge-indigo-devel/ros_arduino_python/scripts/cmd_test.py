import serial
import time
ser = serial.Serial('/dev/ttyACM0', 57600, timeout=1)

time.sleep(1)

ser.write(b'm -50 -50 -50 -50\r')  
# ser.write(b'e\r')
# ser.write(b'r\r')

time.sleep(1)          
response = ser.readline()
print(response)
