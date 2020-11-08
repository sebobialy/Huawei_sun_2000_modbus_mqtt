# Huawei_sun_2000_modbus_mqtt

Simple script to extract important runtime information from Huawei SUN2000 type of inverter.

Attach cheap chineese USB->RS485 converter, connect to 485A-1 signals in Huawei plug (pins 1 and 2) and start the script.

All information available as runtime data will be pushed into selected mqtt server.

Notice, there is no known way to access history data (yet), now only live values are extracted.

Todo:
a) figure out how to access history
b) add more live registers
c) try to connect via wifi

Sebastian Bialy.
