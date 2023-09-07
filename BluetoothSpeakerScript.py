#!/usr/bin/env python3

from gi.repository import GLib
import dbus
import dbus.service
import dbus.mainloop.glib


AGENT_INTERFACE = "org.bluez.Agent1"
AGENT_PATH = "/test/agent"
CAPABILITY = "NoInputNoOutput"
DEVICE_NAME = "KitchenBeats"
A2DP_UUID = "0000110d-0000-1000-8000-00805f9b34fb"
AVRCP_UUID = "0000110e-0000-1000-8000-00805f9b34fb"


class Rejected(dbus.DBusException):
    _dbus_error_name = "org.bluez.Error.Rejected"


class Agent(dbus.service.Object):
    exit_on_release = True

    def set_exit_on_release(self, exit_on_release):
        self.exit_on_release = exit_on_release


    @dbus.service.method(AGENT_INTERFACE, in_signature="", out_signature="")
    def Release(self):
        print("Release")
        if self.exit_on_release:
            mainloop.quit()


    @dbus.service.method(AGENT_INTERFACE, in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):
        print("AuthorizeService (%s, %s)" % (device, uuid))
        authorized_uuids = [A2DP_UUID, AVRCP_UUID]
        if uuid in authorized_uuids:
            print(f"Authorized {uuid} Service")
            return
        print(f"Rejecting {uuid} Service")
        raise Rejected("Connection rejected")


    # @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="s")
    # def RequestPinCode(self, device):
    #     print("RequestPinCode (%s)" % (device))
    #     return "6969"


    # @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="u")
    # def RequestPasskey(self, device):
    #     print("RequestPasskey (%s)" % (device))
    #     return dbus.UInt32(6969)
    
    
    @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="")
    def RequestAuthorization(self, device):
        print("RequestAuthorization (%s)" % (device))
        return


    @dbus.service.method(AGENT_INTERFACE, in_signature="", out_signature="")
    def Cancel(self):
        print("Cancel")


if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    
    bus = dbus.SystemBus()

    agent = Agent(bus, AGENT_PATH)

    obj = bus.get_object("org.bluez", "/org/bluez")
    manager = dbus.Interface(obj, "org.bluez.AgentManager1")
    manager.RegisterAgent(AGENT_PATH, CAPABILITY)

    print("Agent registered")

    adapter_props = dbus.Interface(bus.get_object("org.bluez", "/org/bluez/hci0"), "org.freedesktop.DBus.Properties")
    adapter_props.Set("org.bluez.Adapter1", "Alias", DEVICE_NAME)
    adapter_props.Set("org.bluez.Adapter1", "DiscoverableTimeout", dbus.UInt32(0))
    adapter_props.Set("org.bluez.Adapter1", "Discoverable", dbus.Boolean(True))

    print(f"Bluetooth device set up with name '{DEVICE_NAME}' and PIN '6969'. Ready to pair and connect.")

    manager.RequestDefaultAgent(AGENT_PATH)

    mainloop = GLib.MainLoop()
    mainloop.run()
