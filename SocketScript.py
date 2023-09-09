#!/usr/bin/env python3


# This script must be run with the -u flat in python3 to avoid buffering (when running as a service) and 
# also in the same user space as PulseAudio (e. g. systemctl --user!)
# python3 -u SocketScript.py


import pulsectl
import requests
from time import sleep, time


TASMOTA_SOCKET_IP = "192.168.1.226"
TASMOTA_SOCKET_USERNAME = "admin"
TASMOTA_SOCKET_PASSWORD = "admin"
TURN_OFF_DELAY_SECONDS = 10


class SocketManager():
    def __init__(self, socket_ip, socket_username, socket_password, turn_off_delay) -> None:
        self.SOCKET_IP = socket_ip
        self.SOCKET_USERNAME = socket_username
        self.SOCKET_PASSWORD = socket_password
        self.TURN_OFF_DELAY = turn_off_delay
        
        # we want to always start with the socket off
        self._turn_socket_off_initially()
        self.current_socket_status = False
        self.first_turn_off_event_time = None
    
    
    def _turn_socket_off_initially(self) -> None:
        for _ in range(10):
            try:
                response_status = self._turn_socket_off()
                if response_status == 200:
                    print("Socket turned off initially")
                    return
                
                print(f"Turning socket off initially failed with status code {response_status}")
                
            
            except Exception as e:
                print(f"Turning socket off initially failed with error: {e}")
            
            sleep(10)
      
    
    def manage_socket_status(self, audio_playing: bool) -> None:
        """Manage socket status with delay based on audio status. Function must be called periodically!
        This function can throw an error (requests.exceptions.ConnectionError) if the socket is not reachable, etc.)"""
        
        # if we already have the desired socket status, do nothing
        if (audio_playing and self.current_socket_status) or (not audio_playing and not self.current_socket_status):
            self.first_turn_off_event_time = None
            return
        
        # when audio is playing and socket is off, turn the socket on
        if (audio_playing):
            response_status = self._turn_socket_on()
            if response_status == 200:
                self.current_socket_status = True
                self.first_turn_off_event_time = None
                print("Socket turned on")
            else:
                print(f"Socket turn on failed with status code {response_status}")
        
        # when audio is not playing and socket is on, turn the socket on after the delay
        else:
            if self.first_turn_off_event_time is None:
                self.first_turn_off_event_time = time()
            
            if (time() - self.first_turn_off_event_time) > self.TURN_OFF_DELAY:
                response_status = self._turn_socket_off()
                if response_status == 200:
                    self.current_socket_status = False
                    self.first_turn_off_event_time = None
                    print("Socket turned off")
                else:
                    print(f"Socket turn off failed with status code {response_status}")
    
    
    def _turn_socket_on(self) -> int:
        url = f"http://{self.SOCKET_IP}/cm?user={self.SOCKET_USERNAME}&password={self.SOCKET_PASSWORD}&cmnd=Power%20On"
        response = requests.get(url, timeout=5)
            
        return response.status_code


    def _turn_socket_off(self) -> int:
        url = f"http://{self.SOCKET_IP}/cm?user={self.SOCKET_USERNAME}&password={self.SOCKET_PASSWORD}&cmnd=Power%20Off"
        response = requests.get(url, timeout=5)
            
        return response.status_code


def get_default_sink_index() -> int:
    """Get the default sink index"""
    
    with pulsectl.Pulse("find-sink") as pulse:
        server_info = pulse.server_info()
        default_sink_name = server_info.default_sink_name
        
        sink_list = pulse.sink_list()
        sink_index = next(
            # Find the sink with default_sink_name
            (sink.index for sink in sink_list if sink.name == default_sink_name),
            
            # Returns the first from the list as fallback
            0,
        )
        
        return sink_index


def check_audio_status(pulse_instance, default_sink_index) -> bool:
    """Get audio status (playing or not)"""
    
    # Get all sink inputs (audio streams)
    sink_inputs = pulse_instance.sink_input_list()

    # Check if any of the sink inputs are connected to the default sink
    audio_playing = any(
        sink_input.sink == default_sink_index for sink_input in sink_inputs
    )

    return audio_playing


def main():
    socket_manager = SocketManager(TASMOTA_SOCKET_IP, TASMOTA_SOCKET_USERNAME, TASMOTA_SOCKET_PASSWORD, TURN_OFF_DELAY_SECONDS)
    
    # outer loop to handle PulseAudio errors and other exceptions
    while True:
        try:
            default_sink_index = get_default_sink_index()
            
            with pulsectl.Pulse('check-audio-status') as pulse:
                while True:
                    audio_playing = check_audio_status(pulse, default_sink_index)
                    
                    try:
                        socket_manager.manage_socket_status(audio_playing)
                    except Exception as e:
                        print(f"An error occurred during socket management: {e}")
                    
                    sleep(1)
        
        except pulsectl.PulseError as pe:
            print(f"PulseAudio error occurred: {pe}")
        except Exception as e:
            print(f"An unknown error occurred: {e}")


if __name__ == '__main__':
    main()
