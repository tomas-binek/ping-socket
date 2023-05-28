import network
import uping
import time
from machine import Pin

TARGET_HOST = "192.168.0.6"
NETWORK_NAME = "Binek"
NETWORK_PASSWORD = ""
NETWORK_CONNECTION_TIMEOUT = 5 # seconds
LOST_PINGS_BEFORE_OFF = 3
RELAY_PIN = "GP28"

class WiFi:
    def __init__(self, ssid: str, psk: str):
        self.ssid = ssid
        self.psk = psk
        self.wlan = network.WLAN(network.STA_IF)
        
    def connect(self, connectionTimeoutInSeconds: int, led = None):
        elapsedSeconds = 0
        checkIntervalInSeconds = 1
        
        while True:
            if (elapsedSeconds >= connectionTimeoutInSeconds):
                raise Exception("Timeout after %i seconds when connecting to network '%s'" % (connectionTimeoutInSeconds, self.ssid))
            
            self.wlan.active(True)
            self.wlan.connect(self.ssid, self.psk)
            
            for _ in range(0, 10):
                if self.wlan.status() == 3:
                    return
                
                elapsedSeconds += checkIntervalInSeconds
                time.sleep(checkIntervalInSeconds)
                
            self.wlan.disconnect()
            
            if led:
                led.blink(50, 100, 3)
            
        

class LedOnPin:
    def __init__(self, pinSpec):
        self.pin = Pin(pinSpec, Pin.OUT)
    
    def on(self):
        self.pin.value(1)
        
    def off(self):
        self.pin.value(0)
        
    def blink(self, onTimeMs: int, offTimeMs: int, repeat: int = None):
        if repeat is None or repeat == 0:
            self.on()
            time.sleep(onTimeMs / 1000)
            self.off()
            time.sleep(offTimeMs / 1000)
        #
        elif repeat == -1:
            while True:
                self.blink(onTimeMs, offTimeMs)
        else:
            for _ in range(0, repeat, 1):
                self.blink(onTimeMs, offTimeMs)
            
class StatusIndicator:
    def nothing(self):
        pass
    def connectedToNetwork(self):
        pass
    def pingSuccessful(self):
        pass
    def pingFailed(self):
        pass
    def exception(self):
        pass

class OnboardLedStatusIndicator(StatusIndicator):
    def __init__(self):
        self.led = LedOnPin("LED")
    
    def nothing(self):
        self.led.off()
        
    def connectedToNetwork(self):
        self.led.blink(150, 150, 2)
        
    def pingSuccessful(self):
        self.led.blink(5, 0)
        
    def pingFailed(self):
        pass
    
    def exception(self):
        self.led.blink(100, 100, 20)

class RelayOnPin:
    def __init__(self, pinSpec):
        self.pin = Pin(pinSpec, Pin.OUT)
    
    def on(self):
        self.pin.value(0)
        
    def off(self):
        self.pin.value(1)

indicate = OnboardLedStatusIndicator()
relay = RelayOnPin(RELAY_PIN)
homeWifi = WiFi(NETWORK_NAME, NETWORK_PASSWORD)

# Prepare
indicate.nothing()
relay.off()

# Retry loop
while True:
    try:
        # Connect
        homeWifi.connect(NETWORK_CONNECTION_TIMEOUT)
        indicate.connectedToNetwork()
        print(homeWifi.wlan.ifconfig())
        
        noRecieved = 0
        while True:
            # Ping
            _, recieved = uping.ping(TARGET_HOST, count = 1, timeout = 1000)
            
            # Check response
            if recieved == 1:
                # Got response
                print("Got ping")
                indicate.pingSuccessful()
                noRecieved = 0
                relay.on()
            else:
                # No response
                print("No ping")
                indicate.pingFailed()
                noRecieved += 1
            
            # Adjust relay
            if noRecieved >= LOST_PINGS_BEFORE_OFF:
                relay.off()
            
            # Wait
            if recieved == 1:
                time.sleep(1)
                
    except Exception as e:
        print(e)
        indicate.exception()
        time.sleep(60)
#/while    

