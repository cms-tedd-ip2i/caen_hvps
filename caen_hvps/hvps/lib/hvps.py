# *************************************************************************************
#   By: Jon Ringuette
#   Created: March 23 2020 - During the great plague
#   Purpose: Provide a higher level wrapper for the wrapped c-api provided by caen.py
#            If one is going to interface with the CAEN it should be via this wrapper layer
#            unless one needs direct access to the hardware which should be unusual.
# *************************************************************************************

# This is my low level wrapper for the actual C-Api
from lib.caen import CAEN_Controller as CC


# *************************************************************************************
# HVPS_Channel
# Setup a class of objects that represent one channel on the HVPS
# This allows one to easily create a list of these objects which can represent all the
# channels on the HVPS
# *************************************************************************************


class HVPS_Class:
    def __init__(self, caen_system_info_dict, max_bias_voltage=12, max_ramp_rate=1):
        self.max_bias_voltage = max_bias_voltage
        self.max_ramp_rate = max_ramp_rate
        self.hvps_systems_objects_list = []
        self.caen_system_info_dict = caen_system_info_dict
        self.init_hvps()

    def __del__(self):
        self.deinit_all_hvps()

    def init_hvps(self):
        # init_hvps: Intialize and get a handle for the HVPS, this automatically happens when you instantiate the object
        self.hvps_systems_objects_list.append(
            CC(
                int(self.caen_system_info_dict["system_type"]),
                self.caen_system_info_dict["hostname"],
                self.caen_system_info_dict["username"],
                self.caen_system_info_dict["password"],
                self.caen_system_info_dict["device_name"],
                int(self.caen_system_info_dict["link_type"]),
            )
        )

        return 0

    def deinit_all_hvps(self):
        # deinit_all_hvps: Loop though all devices and deinit them all
        for hvps_device in self.hvps_systems_objects_list:
            hvps_device.deinit()

    @staticmethod
    def decode_chstatus(chstatus):
        # decode_chstatus: Fun with binary, the chstatus comes in the form of a binary number with each position in the
        #                  sequence that is a 1 represents a different status.  Such as 0b0000000000001 would read as 0 bit is 1
        #                  which would indicate that the channel is ON
        chstatus_dict = {
            "on": chstatus & (1 << 0),
            "rup": chstatus & (1 << 1),
            "rdown": chstatus & (1 << 2),
            "overcurrent": chstatus & (1 << 3),
            "overvoltage": chstatus & (1 << 4),
            "undervoltage": chstatus & (1 << 5),
            "ext_trip": chstatus & (1 << 6),
            "maxv": chstatus & (1 << 7),
            "ext_disable": chstatus & (1 << 8),
            "int_trip": chstatus & (1 << 9),
            "inhibit_trip": chstatus & (1 << 10),
            "unplugged": chstatus & (1 << 11),
            "overvoltage_protection": chstatus & (1 << 13),
            "power_fail": chstatus & (1 << 14),
            "temp_error": chstatus & (1 << 15)
        }
        return chstatus_dict

    def get_object_entry_for_hvps_by_name(self, hvps_name):
        # get_object_entry_for_hvps_by_name: Runs though the object list looking for an HVPS with the name and
        #                                    returns that object.  Keep in mind that I didn't not complete all the work
        #                                    on supporting multiple HVPS's but quite a bit of it is in here.

        # If we have only one, the normal case, just return the first item
        if (len(self.hvps_systems_objects_list) == 1) and (hvps_name is None):
            hvps_entry = self.hvps_systems_objects_list[0]
        else:
            hvps_entry = next(
                (hvps_entry for hvps_entry in self.hvps_systems_objects_list if hvps_entry.device_name == hvps_name),
                None,
            )
        return hvps_entry

    def bias_channel(self, hvps_name, slot, channel, bias_voltage):
        # bias_channel: You guessed it, this allows us to specify a channel and what voltage we would like to set it at
        hvps_entry = self.get_object_entry_for_hvps_by_name(hvps_name)
        print(
            "BIAS - DEVICE:",
            hvps_entry.device_name,
            " CHANNEL:",
            channel,
            "SLOT:",
            slot,
        )
        hvps_entry.set_channel_parameter(slot, channel, "Pw", 1)  # Enable the channel first
        hvps_entry.set_channel_parameter(slot, channel, "VSet", bias_voltage)  # Then set the voltage

    def set_channel_param(self, hvps_name, slot, channel, param, param_value):
        # set_channel_param: Sets the channel parameter such as RUp, RDown, ISet, etc..
        hvps_entry = self.get_object_entry_for_hvps_by_name(hvps_name)
        print(
            "SET PARAM - DEVICE:",
            hvps_entry.device_name,
            " CHANNEL:",
            channel,
            "SLOT:",
            slot,
            "Parameter:",
            param,
            "=",
            param_value,
        )
        hvps_entry.set_channel_parameter(slot, channel, param, param_value)

    def unbias_channel(self, hvps_name, slot, channel):
        # unbias_channel: yup, unbias a specific channel by setting it's VSet parameter to 0
        hvps_entry = self.get_object_entry_for_hvps_by_name(hvps_name)
        print(
            "UNBIAS - DEVICE:",
            hvps_entry.device_name,
            "CHANNEL:",
            channel,
            "SLOT:",
            slot,
        )
        hvps_entry.set_channel_parameter(slot, channel, "VSet", 0)

    def get_channel_parameters(self, hvps_name, slot, channel):
        # get_channel_parameters: Get all the parameters for a specific channel and return them
        hvps_entry = self.get_object_entry_for_hvps_by_name(hvps_name)
        parameter_list = hvps_entry.get_channel_paramters(slot, channel)
        return parameter_list

    def show_channel_status(self, channel_status_list):
        # show_channel_status: Display all the parameter values for channels passed to it
        for channel_dict in channel_status_list[0]:
            channel_status_result = {
                "slot": channel_dict["slot"],
                "chan_name": channel_dict["chan_name"],
                "chan_num": channel_dict["chan_num"],
                "chan_info": {},
            }
            my_status = ""
            print("Slot:", channel_dict["slot"], end=" | ")
            print("Channel Name:", channel_dict["chan_name"], end=" | ")
            print("Channel#:", channel_dict["chan_num"], end=" | ")
            counter = 0
            channel_status_result["chan_info"] = []
            for channel_params in channel_dict["chan_info"]:
                if channel_params["parameter"] == "Status":
                    # Attempt to decode the channel status, I'm not sure if this is working correctly
                    status_code_dict = self.decode_chstatus(channel_params["value"])
                    for my_status_code in status_code_dict:
                        if status_code_dict[my_status_code] >= 1:
                            # We can have multiple channel status messages, I think...
                            my_status = (my_status + my_status_code + ",")
                else:
                    try:
                    
                        channel_status_result["chan_info"].append({"parameter": channel_dict["chan_info"][counter]["parameter"]})
                        channel_status_result["chan_info"][counter]["parameter"] = channel_dict["chan_info"][counter]["parameter"]
                        channel_status_result["chan_info"].append({"value": channel_dict["chan_info"][counter]["value"]})
                        channel_status_result["chan_info"][counter]["value"] = channel_dict["chan_info"][counter]["value"]
                    
                        print(
                            channel_dict["chan_info"][counter]["parameter"],
                            ":",
                            channel_dict["chan_info"][counter]["value"],
                            end=" | ",
                        )
                    except IndexError:
                        pass
                counter +=1 
            if my_status == "":
                my_status = "Off"
            print("Status :", my_status)
            channel_status_result["status"]: my_status
            #channel_status_result["chan_info"]["parameter"] =  channel_dict["chan_info"][0]["parameter"]
            #channel_status_result["chan_info"]["value"] =  f"{channel_dict["chan_info"][0]['value']:.1f}"
            #channel_status_result["chan_info"]["value"] =  channel_dict["chan_info"][0]['value']
            return channel_status_result
                   
                
                #else:
                #    channel_status_result["chan_info"]["parameter"] = channel_params["parameter"]
                #    channel_status_result["chan_info"]["value"] = f"{channel_params['value']:.1f}"
                #    print(
                #        channel_params["parameter"],
                #        ":",
                #        f"{channel_params['value']:.1f}",
                #        end=" | ",
                #    )
            #if my_status == "":
            #    my_status = "Off"
            #print("Status :", my_status)
            #channel_status_result["status"]: my_status
            #return channel_status_result

    def status_channel(self, hvps_name, slot, channel):
        # status_channel: Get the parameters and values for an individual channel
        channel_status_list = []
        hvps_entry = self.get_object_entry_for_hvps_by_name(hvps_name)
        channel_status_list.append(
            hvps_entry.get_all_info_for_channels(slot, [channel])
        )
        return channel_status_list

    def set_channel_name(self, hvps_name, slot, channel, channel_name):
        # set_channel_name: Attempts to set the channel name, I don't think our HVPS likes this..
        hvps_entry = self.get_object_entry_for_hvps_by_name(hvps_name)
        hvps_entry.set_channel_name(slot, channel, channel_name)
        return

    def get_all_crates_info(self):
        # get_all_crates_info: Attempt to get all the information such as slot # and firmware version for all crates used by
        #                      the configured HVPS's
        crate_info_list = []
        for hvps_entry in self.hvps_systems_objects_list:  # Loop over all the HVPS's
            device_info_dict = {
                "device_name": hvps_entry.device_name,
                "hostname": hvps_entry.hostname,
            }  # Throw in a couple extra pieces of data
            device_info_dict.update(hvps_entry.get_crate_info())  # combine dict's
            crate_info_list.append(device_info_dict)
        return crate_info_list

    def get_all_channel_names(self):
        # get_all_channel_names: Loops over all HVPS's and gets the channel names for them all
        full_list_of_channel_names = []
        crate_info_list = self.get_all_crates_info()  # Get all the crates
        for my_crate in crate_info_list:  # Loop over all the crates
            list_of_channel_names = []
            hvps_entry = self.get_object_entry_for_hvps_by_name(my_crate["device_name"])
            for my_slot in range(0, my_crate["num_of_slots"]):  # Loop over all the slots in the crates
                list_of_channel_names.extend(
                    hvps_entry.get_channel_names(
                        my_slot, list(range(0, my_crate["num_of_channels"]))
                    )
                )  # Get all channel names
            # Put all the info into a list of dicts
            device_and_channel_dict = {
                "device_name": my_crate["device_name"],
                "channel_names": list_of_channel_names,
            }
            full_list_of_channel_names.append(device_and_channel_dict)
        return full_list_of_channel_names

    @staticmethod
    def get_all_crate_channel_statuses(my_hpvs_crate):
        # get_all_crate_channel_statuses: big aggragate function that tries to get all the channel info for every configured HVPS
        channel_status_list = []
        crate_info_dict = my_hpvs_crate.get_crate_info()
        for my_slot in range(0, crate_info_dict["num_of_slots"]):
            channel_status_list.append(
                my_hpvs_crate.get_all_info_for_channels(
                    my_slot, list(range(0, crate_info_dict["num_of_channels"]))
                )
            )
        return channel_status_list

    def status_all_channels(self, hvps_name):
        # status_all_channels: Go though all crates, hvps's and get status for every available channel
        channel_status_list = []
        if hvps_name is not None:
            hvps_entry = next(
                (hvps_entry for hvps_entry in self.hvps_systems_objects_list if hvps_entry.device_name == hvps_name),
                None,
            )
            if hvps_entry is None:
                print("Could not find HVPS name:", hvps_name)
                exit(1)
            channel_status_list.append(self.get_all_crate_channel_statuses(hvps_entry))  # List of dict's
        else:
            for my_hvps in self.hvps_systems_objects_list:
                channel_status_list.append(
                    self.get_all_crate_channel_statuses(my_hvps)
                )  # list of dict's (you should sense a theme by now)
        for hvps_entry in channel_status_list:
            self.show_channel_status(hvps_entry)
        return channel_status_list

    def find_channel_by_name(self, chan_name):
        # find_channel_by_name:  I haven't found a good enough of a use case to actually impliment this.
        return