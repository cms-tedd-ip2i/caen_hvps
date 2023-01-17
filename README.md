# caen_hvps
integrate caen SY4527 power supply to tracker dcs
Interface to control CAEN power supplies using a python wrapper to the CAEN C API

## CAEN prerequisite
In order to use the CAEN power supplies it is necessary to install the CAEN HV Wrapper Library:

CAENHVWRAPPER https://www.caen.it/download/?filter=CAEN%20HV%20Wrapper%20Library
You need to signup to download. 

CAEN HV Wrapper is a set of ANSI C functions which allows to control CAEN devices. It contains a generic software interface independent by the Power Supply models and by the communication path used to exchange data with them.

### caenlib
Detalied information can be found in CAENHVWrapper-6.3/CAENHVWrapperReadme.txt
To install the necessary libraries execute:
    
    ./install.sh 
 
The installation copies and installs the library in /usr/lib, and installs it in the work directory.

### hvps 
 lib/caen.py : Contains CAEN controller class. Provide low level wrapper for CAEN's c-api via Python's cdll functionality and is accessed via hvps.py
 
 lib/hvps.py : Contains  a class of objects that represent all the channels for the HVPS and provides a nicer interface to the CAEN C-wrapper and should be used for all programatic iteractions with the power supply
 
 hvps_ctrl.py :  Main interface to the control software. Handles all user interactions
 
 hvps.cfg : CAEN HV modules can be setup automatically using a configuration file.
 
 * Global Section :
 Should be defined 
    * max_bias_voltage 
    * max_ramp_rate : max_ramp_rate V/sec, probably want to keep this under <=50
    * default_slot (Mandatory): slot number where the boards are located
    
 * Power supply section : Contains Mandatory informations:
     * Hostname or IP address 
     * username and password
     * system_type : CAENHV_BOARD_TYPE (SY4527) for our case it should be 2 
     * link_type : CAENHV_LINK_TYPE if TCP/IP then it should be 0
    
  * Channels section: All channels must start with CH_. should be defined the following info for each channel;
     * channel_num (Mandatory)
     * chanel enable/disable (Mandatory)
     * max_bias_voltage 
     * ramp_rate 

### Dockerfile
Create an image and Install all the necessary tools.

#### Running
To create an image:
    
    docker build -t centos:caen_hvps_test .
    
    
To run the image as a container:

    docker run --platform linux/amd64 -it --name=caen_hvps centos:caen_hvps_test bash
        

To run the python file inside the container:
check the status of the channel 0 :

    hvps_ctrl.py --status  --chan 0
           
         
You will see the following statement:
    
    Could get the IP address for the hostname :%s 10.2.2.20
    Initilizing HVPS...
    DEBUG_INIT::::: admin admin b'10.2.2.20' 10.2.2.20 ds-hvps 2 0
    Initialized Connection to : 10.2.2.20
    communicating with HVPS, check SLOT # and Channel #, IP : b'10.2.2.20', ERROR code : 0x0
    Slot: 4 | Channel Name: LV_1-0 | Channel#: 0 | V0Set : 5.0 | I0Set : 1.1 | RUpTime : 100.0 | RDwTime : 100.0 | Trip : 0.1 | UNVThr : 0.0 | OVVThr : 7.0 | VMon : 0.0 | VCon : 0.4 | IMon : 0.0 | Temp : 0.0 | Pw : 0.0 | TripInt : 0.0 | TripExt : 0.0 | ChToGroup : 0.0 | OnGrDel : 0.0 | Status : Off
        


     
