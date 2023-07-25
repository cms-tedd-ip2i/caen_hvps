#!/usr/bin/env python3

# *************************************************************************************
#   By: Jon Ringuette
#   Created: March 23 2020 - During the great plague
#   Purpose: Provide a wrapper for CAEN's C library to control the CAEN HVPS which biases
#            the HPGe's (8pi's and ULGe)
#   CAEN manaul and c-api : https://www.caen.it/products/caen-hv-wrapper-library/
# *************************************************************************************

import argparse
import sys
import time
from os.path import exists

from configobj import ConfigObj

from lib.hvps import (
    HVPS_Class,
)  # Class that contains high level wrapper functions for the HVPS,

# import mqtt as my_mqtt
import paho.mqtt.client as mqtt

# *************************************************************************************
# process_config_file:
# Process config file using the configparser library
# *************************************************************************************
class hvps_ctrl:
    def __init__(self, config_dict, args, my_slot):
        self.config_dict = config_dict
        self.my_slot = my_slot
        self.args = args
        self.default_hvps_key = None
        self.HVPS = []
        self.channel_selected = args.channel_selected
        self.hvps_name = args.hvps_name
        self.iset_current = 0
        self.vset_current = 0
        for mykey in self.config_dict.keys():
            if mykey.startswith("HVPS_"):
                self.default_hvps_key = mykey
                self.HVPS.append(HVPS_Class(self.config_dict[mykey]))

        if len(self.HVPS) == 0:
            print("Could not find HVPS entry in config file.")
            exit(1)
        # self.force = self.args.force
        self.force = getattr(args, "force", False)
        self.channel_entry = (
            self.find_channel_in_config()
        )  # Get the config entry for channel

    def confirm_channel(self, action, new_voltage):
        if self.force is True:
            return True
        # confirm_channel: Prompt user to confirm a change to the voltage applied to a channel, requires a 'yes' or 'no' answer
        channel_status_list = self.HVPS[0].status_channel(
            None, self.my_slot, int(self.channel_entry["chan_num"])
        )
        # Iterate over the status of channels until reaching the VSet parameter we're looking for which is the current voltage
        current_voltage = int(
            next(
                item
                for item in channel_status_list[0][0]["chan_info"]
                if item["parameter"] == "VSet"
            )["value"]
        )
        print("-------------------------------------")
        print("CHANNEL NUMBER : %i " % int(self.channel_entry["chan_num"]))
        print("DETECTOR NAME : %s" % self.channel_entry["detector_name"])
        # print("Detector Position : %i" % chan_obj.detector_position)
        print("MAX BIAS VOLTAGE : %i V" % int(self.channel_entry["max_bias_voltage"]))
        print("RAMP RATE : %i V/sec" % int(self.channel_entry["ramp_rate"]))
        print("CURRNET BIAS VOLTAGE : ", current_voltage)
        print("** NEW BIAS VOLTAGE : ", new_voltage)
        print("-------------------------------------")
        user_confirmation_input = input(
            "Are you sure you want to %s this channel? (y/n) : " % action.upper()
        )
        if user_confirmation_input.upper() == "Y":
            return True
        else:
            print("Could not confirm action, exiting ...")
            sys.exit(1)

    def get_max_voltage_ramp_rate(self):
        # get_max_voltage_ramp_rate: Pull out the Max Ramp Rate (RUp) from the config file for a channel
        #                            Also go ahead and check that the ramp rate set doesn't exceed the
        #                            max set in the config file
        my_ramp_rate = 0
        if int(self.channel_entry["ramp_rate"]) < int(
            self.config_dict["max_ramp_rate"]
        ):
            my_ramp_rate = int(self.channel_entry["ramp_rate"])
        else:
            my_ramp_rate = int(self.config_dict["max_ramp_rate"])
        return int(my_ramp_rate)

    def find_channel_in_config(self):
        # find_channel_in_config: Checks that there is a config entry for the channel before taking action on it and confirms if the channel is enabled
        my_config_dict = self.config_dict[self.default_hvps_key]
        channel_entry = None
        # for my_channel_key in my_config_dict.keys():
        #    if my_channel_key.startswith("CH_"):
        #        if(my_config_dict[my_channel_key]["chan_num"]==str(self.channel_selected) ) and my_config_dict[my_channel_key]["Enabled"].upper()=="True".upper():
        #            channel_entry = my_config_dict[my_channel_key]
        # return channel_entry
        for key, val in my_config_dict.items():
            if key.startswith("CH_"):
                # If channel exists in config file AND it is marked as ENABLED
                if (val["chan_num"] == str(self.channel_selected)) and (
                    val["Enabled"].upper() == "TRUE"
                ):
                    channel_entry = val
        return channel_entry  # Return the dict for the specified channel

    def compare_voltage(self, my_new_bias_voltage):
        # compare_voltage: Check what the current voltage of the channel and determine if it needs to be further biased on
        #                  user request.
        max_channel_bias_voltage = self.channel_entry["max_bias_voltage"]
        max_global_bias_voltage = self.config_dict["max_bias_voltage"]
        channel = self.channel_entry["chan_num"]
        perform_bias = False
        new_bias_voltage = int(my_new_bias_voltage)
        channel_status_list = self.HVPS[0].status_channel(
            None, self.my_slot, int(channel)
        )
        # Iterate over the status of channels until reaching the VSet parameter we're looking for which is the current voltage
        current_voltage = int(
            next(
                item
                for item in channel_status_list[0][0]["chan_info"]
                if item["parameter"] == "VSet"
            )["value"]
        )

        if int(new_bias_voltage) > int(max_channel_bias_voltage):
            print(
                "!! Can not exceed this channels maximum BIAS voltage set in the config file:",
                max_channel_bias_voltage,
            )
            exit(1)
        elif int(new_bias_voltage) > int(max_global_bias_voltage):
            print(
                "!! Can not exceed this global maximum BIAS voltage set in the config file:",
                max_global_bias_voltage,
            )
            exit(1)
        if current_voltage == int(
            new_bias_voltage
        ):  # Check if voltage is already the requested voltage
            print(
                "!! Channel:",
                channel,
                "is already set to bias voltage:",
                current_voltage,
            )
            exit(1)
        else:  # If it is not then we will prompt to confirm the change
            perform_bias = self.confirm_channel("BIAS", my_new_bias_voltage)
        return perform_bias

    def bias(self):
        # bias: Runs checks and calls appropriate functions to bias a channel
        max_ramp_rate = 10
        if (
            self.channel_selected is not None
        ):  # If we should go with the default voltage set in the config file
            if self.channel_entry is not None:
                if self.args.bias_voltage is not None:
                    my_new_bias_voltage = self.args.bias_voltage
                else:
                    my_new_bias_voltage = self.channel_entry["max_bias_voltage"]
                max_ramp_rate = (
                    self.get_max_voltage_ramp_rate()
                )  # Get the max volatage ramp rate RUp
                if (
                    self.compare_voltage(my_new_bias_voltage) is True
                ):  # Check if we need to actually change the voltage or if it is already set
                    self.HVPS[0].set_channel_param(
                        self.hvps_name,
                        self.my_slot,
                        int(self.channel_selected),
                        "RUp",
                        max_ramp_rate,
                    )  # Ensure the ramp up value is set to something safe
                    self.HVPS[0].set_channel_param(
                        self.hvps_name,
                        self.my_slot,
                        int(self.channel_selected),
                        "RDwn",
                        max_ramp_rate,
                    )  # Ensure the ramp up value is set to something safe
                    self.HVPS[0].set_channel_param(
                        self.hvps_name,
                        self.my_slot,
                        int(self.channel_selected),
                        "I1Set",
                        self.iset_current,
                    )  # Ensure we have 0 current set
                    self.HVPS[0].set_channel_param(
                        self.hvps_name,
                        self.my_slot,
                        int(self.channel_selected),
                        "V0Set",
                        self.vset_current,
                    )
                    # self.HVPS[0].set_channel_param(self.hvps_name, self.my_slot, int(self.channel_selected), 'V1Set', self.vset_current)  #
                    time.sleep(
                        1
                    )  # Sleep for a moment to make sure the setting has taken effect
                    self.HVPS[0].bias_channel(
                        self.hvps_name,
                        self.my_slot,
                        int(self.channel_selected),
                        int(my_new_bias_voltage),
                    )  # Bias the channel
            else:
                print(
                    "!! Must specify a BIAS voltage via --bias_voltage or put an entry for the channel in the config file and ensure Enabled is True"
                )
                exit(1)
        elif self.channel_selected is None:
            print("!! Must specify --chan")
            exit(1)
        return

    def unbias_channel(self):
        # unbias_channel: Drop VSet to 0 and also ensure RDwn (ramp down) voltage is set correctly
        max_ramp_rate = self.get_max_voltage_ramp_rate()
        if self.confirm_channel("UNBIAS", 0):
            self.HVPS[0].set_channel_param(
                self.hvps_name,
                self.my_slot,
                int(self.channel_selected),
                "RDwn",
                max_ramp_rate,
            )  # Ensure the ramp up value is set to something safe
            self.HVPS[0].unbias_channel(
                self.hvps_name, self.my_slot, int(self.channel_selected)
            )


def process_cli_args(args, config_dict):
    # process_cli_args: Mostly does just that, processes command line arguements and runs appropriate tests
    if "default_slot" in config_dict.keys():
        my_slot = int(config_dict["default_slot"])
    else:
        my_slot = args.slot_selected

    my_hvps_ctrl = hvps_ctrl(config_dict, args, my_slot)
    my_hvps_ctrl.iset_current = args.iset_current
    my_hvps_ctrl.vset_current = args.vset_current

    if args.status == True:
        if args.channel_selected is None:
            my_hvps_ctrl.HVPS[0].status_all_channels(args.hvps_name)
        else:
            channel_status_list = my_hvps_ctrl.HVPS[0].status_channel(
                args.hvps_name, my_slot, args.channel_selected
            )
            # TODO: check if it is true
            # msg = my_hvps_ctrl.HVPS[0].show_channel_status(channel_status_list)
            # print("status channels ===== " , msg)

    elif args.bias_voltage != None:
        my_hvps_ctrl.bias()
    elif args.unbias == True:
        if args.channel_selected is None:
            print("Must specify --chan")
        else:
            my_hvps_ctrl.unbias_channel()
    elif args.action == "set_param":
        if args.channel_selected is None:
            print("Must specify --chan")
        else:
            if args.param in ["Pon", "Pw", "PDwn", "TripInt", "TripExt"]:
                args.param_value = int(args.param_value)
            else:
                args.param_value = float(args.param_value)

            my_hvps_ctrl.HVPS[0].set_channel_param(
                args.hvps_name,
                my_slot,
                int(args.channel_selected),
                args.param,
                args.param_value,
            )
    elif args.chan_enable is not None:
        my_hvps_ctrl.HVPS[0].set_channel_param(
            args.hvps_name, my_slot, int(args.chan_enable), "Pw", 1
        )  # Ensure we have 0 current set
    elif args.chan_disable is not None:
        my_hvps_ctrl.HVPS[0].set_channel_param(
            args.hvps_name, my_slot, int(args.chan_enable), "Pw", 0
        )  # Ensure we have 0 current set
    else:
        my_hvps_ctrl.HVPS[0].status_all_channels(args.hvps_name)

    del my_hvps_ctrl.HVPS[0]
    # print("Time 2")  # Uncommented this and the next line to try init'ing again.  This should work if CAEN ever fixes their CApi which they promised back in Nov2020
    # HVPS = HVPS_Class(caen_system_info_list)

    return


'''def process_config_file_configobj(config_file="hvps.cfg"):
    # process_config_file_configobj: Using ConfigObj to process config file into nested dict's
    if exists(config_file):
        config_dict = ConfigObj(config_file)  # Change this to config_file after testing
        return config_dict
    else:
        print("Could not open config file:", config_file)
        print("Please specify using --config <config file name>")
        exit(1)'''

def process_config_file_configobj(config_file=None):
    # process_config_file_configobj: Using ConfigObj to process config file into nested dict's
    if config_file is not None and exists(config_file):
        config_dict = ConfigObj(config_file)
        print(f"Using config file: {config_file}")
        for section, section_value in config_dict.items():
            if isinstance(section_value, dict):
                print(f"[{section}]")
                for key, value in section_value.items():
                    print(f"{key} = {value}")
            else:
                print(f"{section} = {section_value}")
    else:
        # Default configuration in case the config file is not provided or doesn't exist
        config_dict = {
            "default_slot": "0",
            "default_hvps":"HVPS_SY4527",
            "HVPS_SY4527": {
                "device_name": "SY4527",
                "system_type": "2",
                "link_type": "0",
                "hostname": "192.168.1.210",
                "username":"admin",
                "password" : "admin",
            },

            # Add more default configuration entries as needed
        }
        print("No config file provided or config file does not exist. Using default configuration.")
        print("Default Configuration:")
        for section, section_value in config_dict.items():
            if isinstance(section_value, dict):
                print(f"[{section}]")
                for key, value in section_value.items():
                    print(f"{key} = {value}")
            else:
                print(f"{section} = {section_value}")
    return config_dict
#jandan added this function to print all channels status
def print_all_channel_status(self):
        for channel_num in range(1, 33):  # Assuming there are 32 channels in total
            channel_status_list = self.HVPS[0].status_channel(
                self.hvps_name, self.my_slot, channel_num
            )
            if channel_status_list:
                channel_info = channel_status_list[0][0]["chan_info"]
                print(f"Channel {channel_num} Status:")
                for item in channel_info:
                    if "parameter" in item and "value" in item:
                        parameter = item["parameter"]
                        value = item["value"]
                        print(f"  {parameter}: {value}")
            else:
                print(f"Channel {channel_num} not found or not enabled in the config.")
parser = argparse.ArgumentParser(
    description="HVPS Controller",
    usage="%(prog)s --action [bias, unbias, status, set_name] --chan [channel num]",
)


def main():
    # parser = argparse.ArgumentParser(
    #    description="HVPS Controller",
    #    usage="%(prog)s --action [bias, unbias, status, set_name] --chan [channel num]",
    # )
    parser.add_argument("--hvps_name", dest="hvps_name", default=None, required=False)
    parser.add_argument(
        "--status",
        action="store_true",
        default=False,
        required=False,
        help="Show status of channels (can specify --chan)",
    )
    parser.add_argument(
        "--unbias",
        action="store_true",
        default=False,
        required=False,
        help="Unbias channel specified with --chan #",
    )
    parser.add_argument(
        "--action", choices=("unbias", "set_param"), required=False, default=None
    )

    parser.add_argument(
        "--param",
        dest="param",
        choices=(
            "I1Set",
            "V0Set",
            "RUp",
            "RDwn",
            "Pon",
            "Pw",
            "TripInt",
            "TripExt",
            "PDwn",
            "IMRange",
            "Trip",
        ),
        required=False,
        default=None,
        help="Specify parameter to modify for channel, must specify with --action set_param",
    )
    parser.add_argument(
        "--param_value",
        dest="param_value",
        required=False,
        default=None,
        help="Specify parameter value, must specify --action set_param and --param",
    )
    parser.add_argument(
        "--bias",
        dest="bias_voltage",
        type=int,
        required=False,
        default=None,
        help="Specify new bias voltage for a channel specified with --chan #",
    )
    parser.add_argument(
        "--iset_current",
        dest="iset_current",
        type=float,
        required=False,
        default=0.0,
        help="Specify current (I1SET)",
    )
    parser.add_argument(
        "--vset_current",
        dest="vset_current",
        type=float,
        required=False,
        default=0.0,
        help="Specify current (VSET)",
    )
    parser.add_argument(
        "--slot",
        dest="slot_selected",
        type=int,
        required=False,
        default=None,
        help="Specify slot to take action against",
    )

    parser.add_argument(
        "--chan_enable",
        dest="chan_enable",
        required=False,
        type=int,
        default=None,
        help="Specify channel to turn on",
    )
    parser.add_argument(
        "--chan_disable",
        dest="chan_disable",
        required=False,
        type=int,
        default=None,
        help="Specify channel to turn off",
    )

    parser.add_argument(
        "--chan",
        dest="channel_selected",
        required=False,
        type=int,
        default=None,
        help="Specify channel to take action against, specify channel number or ALL",
    )

    parser.add_argument(
        "--config_file",
        dest="config_file",
        required=False,
        default="hvps.cfg",
        help="Specify the complete path to the config file, by default we'll use hvps.cfg",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        required=False,
        help="If used than no confirmation will be asked.. !!BE CAREFUL!!",
    )

    args, unknown = parser.parse_known_args()
    # print("args==", args)
    config_dict = process_config_file_configobj(args.config_file)
    process_cli_args(args, config_dict)


def on_connect(client, userdata, flags, rc):
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    # client.subscribe(f"/{client.device.name}/cmd/#")
    client.subscribe("/SY4527/status/#")
    # client.subscribe(f"/{my_hvps_ctrl.hvps_name}/cmd/#")
    """Mqtt client on connect method"""
    if rc == 0:
        print("Connected to MQTT Broker!")
    else:
        print("Failed to connect, return code %d\n", rc)


def on_message(client, userdata, msg):
    """Subscribed topic on message action"""
    # print("recv", msg.topic, msg.payload)
    # client.device.command(msg.topic, msg.payload)
    print("RECEIVE message:")
    print("Topic: " + msg.topic, msg.payload.decode())


def run(device, mqtt_host):
    import json

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.device = device
    client.connect(mqtt_host, 1883, 60)
    # config_dict = process_config_file_configobj(config_file="hvps.cfg")
    # print("config ", config_dict)
    args, unknown = parser.parse_known_args()
    config_dict = process_config_file_configobj(args.config_file)

    if "default_slot" in config_dict.keys():
        my_slot = int(config_dict["default_slot"])
    else:
        my_slot = args.slot_selected

    my_hvps_ctrl = hvps_ctrl(config_dict, args, my_slot)
    my_hvps_ctrl.iset_current = args.iset_current
    my_hvps_ctrl.vset_current = args.vset_current
    # client.subscribe(f"/{my_hvps_ctrl.hvps_name}/status/#")

    if args.status == True:
        if args.channel_selected is None:
            my_hvps_ctrl.HVPS[0].status_all_channels(args.hvps_name)
            #my_hvps_ctrl.print_all_channel_status() #to print all channels status
        else:
            channel_status_list = my_hvps_ctrl.HVPS[0].status_channel(
                args.hvps_name, my_slot, args.channel_selected
            )
            # TODO: check if it is true
        msg = my_hvps_ctrl.HVPS[0].show_channel_status(channel_status_list)
        slot = msg["slot"]
        channel_name = msg["chan_name"]
        channel_number = msg["chan_num"]
        channel_info = msg["chan_info"]

    client.loop_start()
    topic = "/SY4527/status"
    client.subscribe(topic)
    while 1:
        formatted_msg = f"Message:\nSlot: {slot} | Channel Name: {channel_name} | Channel#: {channel_number} | "
        # formatted_msg = "Message:\n"
        for item in channel_info:
            if "parameter" in item and "value" in item:
                parameter = item["parameter"]
                value = item["value"]
                formatted_msg += f"{parameter}: {value} | "

        client.publish(topic, str(formatted_msg))
        print(f"SEND `{formatted_msg}` to topic `{topic}`")
        # client.publish("/{}/status".format(my_hvps_ctrl.hvps_name), json.dumps(msg))
        # client.publish(topic,json.dumps(msg))
        # print(f"SEND `{msg}` to topic `{topic}`")

        time.sleep(4)
    time.sleep(4)
    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
    # mqtt_host = "docker.for.mac.host.internal" # if you are working locally
    mqtt_host = "lyovis12.in2p3.fr"  # or with hostaname:mqtt_host = "lyovis12.in2p3.fr"
    # mqtt_port = 1883
    run(hvps_ctrl, mqtt_host)
