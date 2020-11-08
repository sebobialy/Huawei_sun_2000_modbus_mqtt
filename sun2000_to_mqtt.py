#! /usr/bin/env python3
# -*- coding: utf-8

import minimalmodbus
import paho.mqtt.client as mqtt
import time
from enum import Enum

class mqttClient:
	def onConnect( this, client, userdata, flags, rc ):
		print( "Broker %s connected" % this.m_server )
		this.m_isConnected = True
		
	def onDisconnect( this, client, userdata, rc ):
		print( "Broker %s disconnected" % this.m_server )
		this.m_isConnected = False
		this.m_cache = {}

	def __init__( this, server, username, password, prefix ):
		this.m_client = mqtt.Client()
		this.m_server = server
		this.m_prefix = prefix
		this.m_client.on_connect = this.onConnect
		this.m_client.on_disconnect = this.onDisconnect
		this.m_client.username_pw_set( username, password )
		this.m_cache = {}
		this.m_isConnected = False
		
	def publish( this, register, value ):
		if this.m_isConnected == False:
			print("Connecting broker", this.m_server)
			try:
				this.m_client.connect( this.m_server )
				this.m_client.loop(timeout=5.0, max_packets=100)
			except:
				pass
		
		if this.m_isConnected == False:
			return False

		if register not in this.m_cache or this.m_cache[ register] != value:
			this.m_cache[ register ] = value
			this.m_client.publish( this.m_prefix + register, value, retain=True )
			print( "publishing", this.m_prefix + register )

		return True

	def loop( this ):
		this.m_client.loop()
		
	def clearCache( this ):
		this.m_cache = {}

brokers = (
	( mqttClient( "broker.shiftr.io", "1234567", "123456789abcdef", "my/inverter" ) ),
	)

statusMap = { 
    0 : "Idle Initialising",
    1 : "Idle ISO Detecting",
    2 : "Idle Irradiation Detecting",
    256 : "Starting",
    512 : "On-grid",
    513 : "On-grid Limited",
    768 : "Shutdown Abnormal",
    769 : "Shutdown Forced",
    1025 : "Grid Dispatch: cosψ-P Curve",
    1026 : "Grid Dispatch: Q-U Curve",
    40960 : "Idle: No Irradiation"
    }

class RegisterType(Enum):
	DefaultSigned = 1
	DefaultUnsigned = 2
	Long = 3

def translateStatus( status ):
	try:
		return statusMap[status]
	except ( KeyError ):
		return status


registerMap = {
	"dc1_voltage" : ( 32016, 0.1, RegisterType.DefaultSigned,None ),
	"dc1_current" : ( 32017, 0.01, RegisterType.DefaultSigned,None ),
	"dc2_voltage" : ( 32018, 0.1, RegisterType.DefaultSigned,None ),
	"dc2_current" : ( 32019, 0.01, RegisterType.DefaultSigned,None ),

	"p1_voltage" : ( 32069, 0.1, RegisterType.DefaultSigned,None ),
	"p2_voltage" : ( 32070, 0.1, RegisterType.DefaultSigned,None ),
	"p3_voltage" : ( 32071, 0.1, RegisterType.DefaultSigned,None ),

	"p1_current" : ( 32072, 0.001, RegisterType.Long,None ),
	"p2_current" : ( 32074, 0.001, RegisterType.Long,None ),
	"p3_current" : ( 32076, 0.001, RegisterType.Long,None ),
	
	"energy_daily" : ( 32114, 0.01, RegisterType.Long,None ),
	"input_power" : ( 32064, 0.001, RegisterType.Long,None ),
	"output_power" : ( 32080, 0.001, RegisterType.Long,None ),
	"output_reactive_power" : ( 32082, 0.001, RegisterType.Long,None ),
	"output_power_factor" : ( 32084, 0.001, RegisterType.DefaultSigned,None ),
	"frequency" : ( 32085, 0.01, RegisterType.DefaultSigned,None ),
	"status" : ( 32089, 1, RegisterType.DefaultUnsigned, translateStatus ),
	"efficiency" : ( 32086, 0.01, RegisterType.DefaultSigned,None ),
	}

def readRegister( instrument, register ):
	
	for i in range(1, 20):
		try:
			if register[2] == RegisterType.DefaultSigned:
				value = instrument.read_register( register[0], signed=True )
			elif register[2] == RegisterType.DefaultUnsigned:
				value = instrument.read_register( register[0], signed=False )
			elif register[2] == RegisterType.Long:
				value = instrument.read_long( register[0], signed=True)
			else:
				return None
			
			value = value * register[1]
			if register[3] != None:
				value = register[3]( value )
			else:
				if register[1] == .1:
					value = "{:.1f}".format(value)
				elif register[1] == .01:
					value = "{:.2f}".format(value)
				elif register[1] == .001:
					value = "{:.3f}".format(value)

			return value

		except ( minimalmodbus.NoResponseError ):
			pass
		except ( minimalmodbus.InvalidResponseError ):
			pass
		except ( minimalmodbus.SlaveReportedException ):
			pass
	
	return None

instrument = minimalmodbus.Instrument('/dev/ttyUSB0', 1)
instrument.serial.baudrate = 9600
instrument.timeout = 0.05

flushCacheTimeout = 60


lastTime = time.time()
while( True ):
	for register in registerMap:
		registerName = registerMap[register]
		value = readRegister( instrument, registerName )
		if value == None:
			continue
		for broker in brokers:
			broker.publish( register, value )
		print( register, " ", value )
	
	shouldClearCache = False
	if time.time() > lastTime + flushCacheTimeout:
		shouldClearCache = True
		lastTime = time.time()
	
	for broker in brokers:
		broker.loop()
		if shouldClearCache == True:
			broker.clearCache()
	time.sleep( 10 )
