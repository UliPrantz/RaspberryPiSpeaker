#!/usr/bin/env python3


# This script must be run as root (sudo is not sufficient enough!) and with the -u flag in python to avoid buffering (when running as a service)
# python3 -u BluetoothSpeakerScript.py


from gi.repository import GLib
import dbus
import dbus.service
import dbus.mainloop.glib
import subprocess


PIN = 6969


BLUEZ_SERVICE = 'org.bluez'
AGENT_INTERFACE = "org.bluez.Agent1"

AGENT_PATH = "/org/bluez/CustomAuthenticationAgent"
CAPABILITY = "NoInputNoOutput"
DEVICE_NAME = "KitchenBeats"

A2DP_UUID = "0000110d-0000-1000-8000-00805f9b34fb"
AVRCP_UUID = "0000110e-0000-1000-8000-00805f9b34fb"


class Rejected(dbus.DBusException):
    _dbus_error_name = "org.bluez.Error.Rejected"


class Agent(dbus.service.Object):
    def __init__(self, bus, path):
        super().__init__(bus, path)


    @dbus.service.method(AGENT_INTERFACE, in_signature="", out_signature="")
    def Release(self):
        print("Agent released")

    @dbus.service.method(AGENT_INTERFACE, in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):
        print("AuthorizeService (%s, %s)" % (device, uuid))
        authorized_uuids = [A2DP_UUID, AVRCP_UUID]
        
        if uuid in authorized_uuids:
            print(f"Authorized {uuid} Service")
            return
          
        print(f"Rejecting {uuid} Service")
        raise Rejected("Connection rejected")


    @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        print("RequestPinCode (%s)" % (device))
        return str(PIN)


    @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        print("RequestPasskey (%s)" % (device))
        return dbus.UInt32(PIN)


    @dbus.service.method(AGENT_INTERFACE, in_signature="", out_signature="")
    def Cancel(self):
        print("Cancel")


def setup():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    
    mainloop = GLib.MainLoop()
    bus = dbus.SystemBus()

    obj = bus.get_object("org.bluez", "/org/bluez")
    adapter = dbus.Interface(bus.get_object("org.bluez", "/org/bluez/hci0"), "org.freedesktop.DBus.Properties")
    
    agent = Agent(bus, AGENT_PATH)
    
    manager = dbus.Interface(obj, "org.bluez.AgentManager1")
    manager.RegisterAgent(AGENT_PATH, CAPABILITY)

    print("Agent registered")
    
    adapter.Set("org.bluez.Adapter1", "Alias", DEVICE_NAME)
    adapter.Set("org.bluez.Adapter1", "DiscoverableTimeout", dbus.UInt32(0))
    adapter.Set("org.bluez.Adapter1", "Discoverable", dbus.Boolean(True))
    adapter.Set('org.bluez.Adapter1', 'Pairable', True)

    print(f"Bluetooth device set up with name: '{DEVICE_NAME}' with pin: '{PIN}'")

    manager.RequestDefaultAgent(AGENT_PATH)

    # make sure this is executed somehow before to disable the automated pin negotiation
    # hciconfig hci0 sspmode 0
    subprocess.run(["hciconfig", "hci0", "sspmode", "0"], check=True)
    
    # also make sure this is executed before connecting other connection somehow always fails with:
    # src/device.c:device_bonding_complete() bonding (nil) status 0x0e
    # src/device.c:device_bonding_failed() status 14
    # echo 1 > /sys/module/bluetooth/parameters/disable_ertm
    with open('/sys/module/bluetooth/parameters/disable_ertm', 'w') as file:
        file.write('1')

    mainloop.run()  


if __name__ == '__main__':
    setup()
    