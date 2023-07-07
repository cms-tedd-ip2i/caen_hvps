# *************************************************************************************
#   By: Jon Ringuette
#   Created: March 23 2020 - During the great plague
#   Purpose:  Provide low level wrapper for CAEN's c-api via Python's cdll functionality.
#             One should use hvps.py to interface with the power supply unless you need very low
#             level access to the hardware without any safety checks
#   CAEN manaul and c-api : https://www.caen.it/products/caen-hv-wrapper-library/
# *************************************************************************************

import socket
import sys
from ctypes import (
    c_int,
    c_float,
    c_void_p,
    c_char_p,
    c_char,
    c_ushort,
    pointer,
    cdll,
    cast,
    POINTER,
    byref,
)


class CAEN_Controller:
    def __init__(self, system_type, hostname, username, password, device_name, link_type=0):
        self.MAX_CHANNEL_NAME_LENGHT = 12  # This is hardcoded at this time in the CAEN C-API
        self.MAX_PARAM_LENGTH = 10  # this too is hardcoded and needed for nasty pointer indexing caused by the char ** they like to use
        self.PARAM_TYPE = {
            0: "numeric",
            1: "onoff",
            2: "chstatus",
            3: "bdstatus",
            4: "binary",
            5: "string",
            6: "enum",
        }
        try:
            self.libcaenhvwrapper_so = cdll.LoadLibrary("libcaenhvwrapper.so")  # Load CAEN's c-api shared library
        except:
            print("Could not load CAEN's C library : libcaenhvwrapper.so")
            print("It needs to be in in one of the directories listed in your LD_LIBRARY_PATH environment variable")
            exit(1)
        self.device_name = device_name
        self.system_type = system_type
        self.hostname = hostname
        self.username = username
        self.password = password
        self.link_type = link_type
        try:
            self.ip_address = socket.gethostbyname(hostname).encode(
                "utf-8"
            )  # We need to pass the IP addresss to the C API, and we need it in utf8
            print("Could get the IP address for the hostname :%s", (hostname))
        except:
            print("Could not get the IP address for the hostname :%s", (hostname))
            print("Or the IP address is improperly formatted")
        self.handle = c_int(0)
        print("Initilizing HVPS...")
        self.init()

    def check_return_code(self, return_code):
        # check_return_code:  Check if the return code passed back from an api call had an issue and attempt to print what it was
        if hex(return_code) != hex(0):
            print(
                "Problem communicating with HVPS, check SLOT # and Channel #, IP : %s, ERROR code : %s"
                % (self.ip_address, hex(return_code))
            )
            # print(cast(self.libcaenhvwrapper_so.CAENHV_GetError(self.handle), c_char_p).raw)  # this didn't work the first time, maybe i'll come back to it
            print("Calling Function:", sys._getframe(1).f_code.co_name)
            exit(1)
        else:
            return return_code

    def init(self):
        # init: Initialize the connection to the HVPS and return the handle as a pointer to a structure if successful.
        #       This handle must be used for all subsequent calls to the API for this session
        print(
            "DEBUG_INIT:::::",
            self.username,
            self.password,
            self.ip_address,
            self.ip_address.decode("utf-8"),
            self.device_name,
            self.system_type,
            self.link_type,
        )
        return_code = self.libcaenhvwrapper_so.CAENHV_InitSystem(
            c_int(self.system_type),
            c_int(self.link_type),
            self.ip_address,
            self.username.encode(),
            self.password.encode(),
            pointer(self.handle),
        )
        self.check_return_code(return_code)
        print("Initialized Connection to : %s" % (self.hostname))
        print(
            "communicating with HVPS, check SLOT # and Channel #, IP : %s, ERROR code : %s"
            % (self.ip_address, hex(return_code))
        )

    def deinit(self):
        # deinit: De-initilize the connection to the HVPS.
        try:
            return_code = self.libcaenhvwrapper_so.CAENHV_DeinitSystem(self.handle)
        except:
            print(
                "Something didn't go well with de-init'ing, I wish I could tell you more but it's probably not the end of the world."
            )
            return_code = 1  # different from 0
        return return_code

    def get_channel_paramters(self, slot, channel):
        # get_channel_parameters: For a specific channel we want to gather all the available channel parameters such as VSet, ISet RUp etc..
        full_channel_parameters_list = []
        c_channel_info_list = c_char_p()  # char pointer
        c_channel_params_num = (
            c_int * 1
        )()  # single value int array, it's just what it needs, don't think about it too hard...

        # Call CAENHV_GETChParamInfo from the c-api, passing the single channel entry by reference, will return c_channel_params_num with the
        # number of parameters returned and c_channel_info_list will be an array of channael parameters available (not values of parameters)
        return_code = self.libcaenhvwrapper_so.CAENHV_GetChParamInfo(
            self.handle, slot, channel, byref(c_channel_info_list), c_channel_params_num
        )
        self.check_return_code(return_code)
        # print("parameter num  :",c_channel_params_num)

        # This is an array and even using only one channel here have to treat it as such
        num_parameters_for_channel = c_channel_params_num[0]

        channel_parameter_list = []

        # For this we must do weird pointer indexing
        for i in range(0, num_parameters_for_channel - 1):
            pointer_to_param = cast(c_channel_info_list, c_void_p).value + (
                i * self.MAX_PARAM_LENGTH
            )  # So we cast to type void_p then incriment the pointer value to move to the next actual value
            channel_parameter_list.append(
                cast(
                    pointer_to_param, POINTER(c_char * self.MAX_PARAM_LENGTH)
                ).contents.value
            )  # then we need to cast back to an array and deference the pointer and get the array value..

            property_type = c_void_p()
            # Here we call CaenHV_GetChParamProp to actually get the value of each of the channel properties one at a time
            return_code = self.libcaenhvwrapper_so.CAENHV_GetChParamProp(
                self.handle,
                slot,
                channel,
                channel_parameter_list[-1],
                "Type".encode("utf-8"),
                byref(property_type),
            )
            self.check_return_code(return_code)

            my_property_type = 0

            # I don't know why it comes out as None instead of 0 but whatever..
            if property_type.value is not None:
                my_property_type = property_type.value
            # Set a dict with the parameter name and value type and value and then go ahead and append it to a list of dict's
            parameter_dict = {
                "parameter": channel_parameter_list[-1].decode("utf-8"),
                "type": self.PARAM_TYPE[my_property_type],
                "value": None,
            }
            full_channel_parameters_list.append(parameter_dict)
        return full_channel_parameters_list

    def get_channel_names(self, slot, list_of_channels):
        # get_channel_names: Get a list of all the channel names on a SLOT given a list of channels.
        #                    Keep in mind that channel names aren't super useful as they really don't appear to be setable, I tried.. and failed..
        channel_names = []
        num_of_channels = len(list_of_channels)
        c_channels_list = (c_ushort * num_of_channels)(*list_of_channels)  # Setup array

        # Setup multidimentional array c_channel_names[num_channels][MaxLength]
        c_channel_names = (c_char * self.MAX_CHANNEL_NAME_LENGHT * num_of_channels)()
        # Call CAENHV_GetChName from c-api to get the name of each of the channels list in list_of_channels
        return_code = self.libcaenhvwrapper_so.CAENHV_GetChName(
            self.handle, slot, num_of_channels, c_channels_list, c_channel_names
        )
        self.check_return_code(return_code)

        for channel_name in c_channel_names:
            channel_names.append(channel_name.value.decode("utf-8"))  # append the name to a list
        return channel_names

    def get_all_info_for_channels(self, slot, channels):
        # get_all_info_for_channels:  This is a big one where we loop over all the channels and parameters to build up a big list
        #                             of dicts containing all the information for the channels
        all_channels_info_list = []
        for my_channel in channels:  # loop over all the channels
            # Might as well grab the channel name, wonder what it'll be...
            channel_name = self.get_channel_names(slot, [my_channel])

            # get list of all available parameters
            full_channel_parameters_list = self.get_channel_paramters(slot, my_channel)

            # Iterate over all the parameters to get all the values, yes there is a little code redundency here but you can fix it ;)
            for my_parameter in full_channel_parameters_list:
                c_channels_list = (c_ushort * 1)(
                    *[my_channel]
                )  # multi-dimentional c array again
                param_value = (c_void_p * 1)()
                # Call to CAENHV_GetChParam to get the parameter value of the channel
                return_code = self.libcaenhvwrapper_so.CAENHV_GetChParam(
                    self.handle,
                    slot,
                    my_parameter["parameter"].encode("utf-8"),
                    1,
                    c_channels_list,
                    byref(param_value),
                )
                self.check_return_code(return_code)

                cast_param_value = 0
                # Check what type of value we should be getting and cast the c_void_p accordingly
                if my_parameter["type"] == "numeric":
                    cast_param_value = cast(param_value, POINTER(c_float)).contents.value
                elif my_parameter["type"] == "onoff" or my_parameter["type"] == "chstatus":
                    cast_param_value = cast(param_value, POINTER(c_int)).contents.value
                    # if (cast_param_value & (1<<n)):  # Checks if bit n is set to 1

                my_parameter["value"] = cast_param_value
            # Put all the information for a channel together into a dict and then append that to a list of all the channels
            channel_info_dict = {
                "chan_name": channel_name[0],
                "chan_num": my_channel,
                "slot": slot,
                "chan_info": full_channel_parameters_list,
            }
            all_channels_info_list.append(channel_info_dict)
        return all_channels_info_list

    def set_channel_parameter(self, slot, channel, parameter, new_value):
        # set_channel_parameter: Set many common channel parameter :
        #                        VSet, ISet, RUp, RDwn, PDwn, IMRange, Trip, all most all are float, except PDwn and IMRange (int)
        c_channels_list = (c_ushort * 1)(
            *[channel]
        )  # Array of 1 as we do this one at a time in this code
        c_new_value = c_float(new_value)
        # Call CAENHV_SetChParam from c-api to set one parameter value at a time for a single channel
        return_code = self.libcaenhvwrapper_so.CAENHV_SetChParam(
            self.handle,
            slot,
            parameter.encode("utf-8"),
            1,
            c_channels_list,
            byref(c_new_value),
        )
        self.check_return_code(return_code)

        return

    def set_channel_name(self, slot, channel, channel_name):
        #  set_channel_name: Change the name of a single channel, I know the API allows multiple but I just don't care.
        #                    This doesn't seem to actually work.  I don't believe the names are actually setable on our
        #                    HVPS or I screwed something up either way no biggie..
        c_channels_list = (c_ushort * 1)(
            *[channel]
        )  # again array of 1 as we do these 1 at a time
        print("Channel Name:", channel_name)
        # attempt to call CAENHV_SetChName to set the channel name which seems to do nothing
        return_code = self.libcaenhvwrapper_so.CAENHV_SetChName(
            self.handle, slot, 1, c_channels_list, channel_name.encode("utf-8")
        )
        self.check_return_code(return_code)
        return

    def get_crate_info(self):
        # get_crate_info: Used to get number of slots and channels in a crate.  It grabs other things as well
        #                 but they aren't super useful besides mybe the firmware version?
        c_num_of_slots = c_ushort()
        c_num_of_channels = POINTER(c_ushort)()
        c_description_list = c_char_p()
        c_model_list = c_char_p()
        c_serial_num_list = POINTER(c_ushort)()
        c_firmware_release_min_list = c_char_p()
        c_firmware_releae_max_list = c_char_p()
        # Call CAENHV_GetCrateMap to get info on the actual crate, means more with other HVPS's not so much with our R81xx
        return_code = self.libcaenhvwrapper_so.CAENHV_GetCrateMap(
            self.handle,
            byref(c_num_of_slots),
            byref(c_num_of_channels),
            byref(c_model_list),
            byref(c_description_list),
            byref(c_serial_num_list),
            byref(c_firmware_release_min_list),
            byref(c_firmware_releae_max_list),
        )

        self.check_return_code(return_code)
        crate_info_dict = {
            "num_of_slots": c_num_of_slots.value,
            "num_of_channels": c_num_of_channels.contents.value,
            "model": c_model_list.value.decode("utf-8"),
        }
        return crate_info_dict