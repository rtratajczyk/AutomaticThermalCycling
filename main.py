"""Written by RR. Used to control and synchronize a Keithley power supply and the Climatic Chamber to
conduct thermal cycling in a TVAC chamber using Peltier modules. Input temperatures and voltages are tailored
for SXA Power Splitter - other devices may need different values!"""

import pyvisa
import time
import socket


def check_chamber(sock):  # Sock is a stream socket connected to the climatic chamber.
    """This function asks the Climatic Chamber for its current temperature."""
    message = "$01I \r"  # This string asks the chamber for its current values.

    sock.sendall(message.encode("ascii"))
    response = sock.recv(4096).decode()
    # print("Response: " + str(response))

    split_response = response.split(" ")
    temperature = split_response[1]
    # print("Current temp is: " + str(temperature))
    return temperature


def set_chamber(sock, temperature):
    """This function sets the Climatic Chamber to a given temperature."""
    print("Now setting the temperature to " + str(temperature))
    message = "$01E " + str(temperature) + " 10 100 1200 010000000000000000000 \r"
    sock.sendall(message.encode("ascii"))
    if check_chamber(sock) == temperature:
        print("Temperature set properly!")


def single_cycle(sock, cycle_num):
    """This function performs a single thermal cycle."""
    set_chamber(sock, -40)  # Setting the CC to cool down to -40 deg C.
    while check_chamber(sock) != -40:   # Checking every 30 seconds if the temperature in CC has reached required -40 deg C.
        time.sleep(30)
    print("-40 degrees reached. Engaging peltier modules.")
    inst.write("inst:sel ch1")  # Channel 1 outputs voltage to cool down the Peltier modules to -55 deg C.
    inst.write("source:outp:enab on")
    inst.write("source:outp on")
    time.sleep(1200)  # Waiting for 20 minutes, during which Peltier modules should hopefully reach stable temperature.
    print("Reached -55 deg C. Waiting for dwell time (1h).")
    time.sleep(3600)  # Dwell time: after DUT reaches -55 deg C (which we have no way of knowing for sure), wait 1 hour.
    if cycle_num == 7:
        input("This is the last cycle, COLD state. Please take the S-parameter measurements and then press "
              " RETURN key to continue the test.")
    inst.write("source:outp:enab off")  # Afterwards, the Ch1 output must be turned off.
    inst.write(":outp off")
    time.sleep(2)  # To allow voltage to drop to 0 fully before switching to next channel.

    set_chamber(sock, 0)  # Setting the CC to heat up to 0 deg C, allowing to enter the HOT part of the cycle.
    while check_chamber(sock) != 0:  # Checking every 30 seconds if the temperature in CC has reached required 0 deg C.
        time.sleep(30)
    inst.write("inst:sel ch2")
    inst.write("source:outp:enab on")
    inst.write("source:outp on")
    time.sleep(900)  # Waiting for 15 minutes, during which Peltier modules should hopefully reach stable temperature.

    time.sleep(3600)  # Dwell time: after DUT reaches +85 deg C (which we have no way of knowing for sure), wait 1 hour.
    if (cycle_num == 7):
        input("This is the last cycle, HOT state. Please take the S-parameter measurements and then press "
              " RETURN key to continue the test.")
    inst.write("source:outp:enab off")  # Afterwards, the Ch2 output must be turned off.
    inst.write(":outp off")
    time.sleep(2)  # To allow voltage to drop to 0 fully before switching to next channel.


rm = pyvisa.ResourceManager()       # Creating a Resource Manager to contact with power supply
print("Attempting to connect with the Keithley Power Supply...")
try:
    inst = rm.open_resource('USB0::0x05E6::0x2230::9032591::INSTR')  # This address seems to be constant for our supply, but may change?...
except pyvisa.errors.VisaIOError:  # This error is raised if the Resource Manager can't find a device with that address.
    print("Keithley Power Supply not found. Please make sure that it is powered, "
          "connected to this computer and turned on, then run the script again.")
    time.sleep(10)  # To give user time to read the error message.
    quit()
print("Successfully connected to the supply!")
supply_id = inst.query("*IDN?")
print("The connected device identifies as: " + supply_id)     # This here is just to make sure.
if "Keithley" in supply_id:     # Checking if the ID contains "Keithley", which means that the ID is proper.
    print("This ID is correct.")
else:
    print("It doesn't seem to be the correct device, though. Please check the supply and run again.")
    time.sleep(10)  # To give user time to read the error message.
    quit()

# Connecting to the Climatic Chamber
print("Now attempting to connect with the climatic chamber...")
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Creating the stream socket.
s.settimeout(5)  # Setting the timeout to generous 5 seconds.
try:
    s.connect(('10.10.21.238', 2049))  # Attempting to connect to the socket to the climatic chamber. Address hardcoded.
except socket.timeout:
    print("Cannot connect to the climatic chamber. Please make sure that it is turned on, " 
          " connected to the network, set to external control and then run the script again.")
    time.sleep(10)  # To give user time to read the error message.
    quit()
if s.getpeername() == ('10.10.21.238', 2049):  # Double check if we are definitely connected to the chamber.
    print("Successfully connected with the climatic chamber!")
else:
    print("Connected to something, but the IP address is not what was expected. Please investigate this problem"
          " and retry.")
    time.sleep(10)  # To give user time to read the error message.
    quit()

# Setting the initial voltages and currents for both channels below:
inst.write("inst:sel ch1")      # Selecting channel 1 to change its parameters.
inst.write("source:outp:enab off")  # Turns the output off, in case it was on.
inst.write("source:volt 5V")  # This voltage gives a temperature of -55 deg C in -40 deg C ambient.
inst.write("source:curr MAX")  # Peltier modules can handle 3A max. Power supply outputs 1.5A max, so no danger here.
print("Voltage set for Channel 1 is [V]: " + inst.query("source:volt?"))  # To make sure it's set up properly.
print("Current set for Channel 1 is [A]: " + inst.query("source:curr?"))

inst.write("inst:sel ch2")      # Selecting channel 2 to change its parameters.
inst.write("source:outp:enab off")  # Turns the output off, in case it was on.
inst.write("source:volt 10.25V")    # This voltage gives a temperature of +85 deg C in 20 deg C ambient.
inst.write("source:curr MAX")  # Peltier modules can handle 3A max. Power supply outputs 1.5A max, so no danger here.
print("Voltage set for Channel 2 is [V]: " + inst.query("source:volt?"))  # To make sure it's set up properly.
print("Current set for Channel 2 is [A]: " + inst.query("source:curr?"))

# This optional block allows to test the outputs, briefly flashing one after the other. Uncomment if needed.
inst.write("inst:sel ch1")
inst.write("source:outp:enab on")
inst.write("source:outp on")
time.sleep(1)
inst.write("source:outp:enab off")
inst.write(":outp off")
time.sleep(2)  # To allow voltage to drop to 0 fully before switching to next channel.

inst.write("inst:sel ch2")
inst.write("source:outp:enab on")
inst.write("source:outp on")
time.sleep(1)
inst.write("source:outp:enab off")
inst.write(":outp off")
time.sleep(2)  # To allow voltage to drop to 0 fully before switching to next channel.


cycle_counter = 0  # This variable indicates the number of COMPLETED thermal cycles, which is why it starts at 0.

while cycle_counter < 8:   # 8 cycles need to be completed.
    print("Current cycle is: " + str(cycle_counter))  # Helps to keep track of the conditioning progress.
    single_cycle(s, cycle_counter)         # We pass the connected socket to the function.
    cycle_counter += 1

# SET_CC_TO+20degC  # Return the CC to ambient temperature.
print("All eight cycles were completed. Conditioning over.")
