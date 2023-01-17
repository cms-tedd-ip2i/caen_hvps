wifi connection should be IPNL !
(base) 15:36:50:~/Desktop/CAENHV/HVPS/caenlib $ java -jar ChannelsController.jar 10.2.2.20 admin admin 
(base) 16:40:57:~/Desktop/CAENHV/HVPS $ docker exec -it caencontainer bash 
[root@c6b44ea28417 hvps]# python3 hvps_ctrl.py --status  --chan 0
Could get the IP address for the hostname : 10.2.2.20 ip address: b'10.2.2.20'
Initilizing HVPS...
DEBUG_INIT::::: admin admin b'10.2.2.20' 10.2.2.20 ds-hvps 2 0
Initialized Connection to : 10.2.2.20
communicating with HVPS, Hostname IP : b'10.2.2.20', ERROR code : 0x0
Channel#: 0 | V0Set : 0.0 | I0Set : 355.0 | V1Set : 0.0 | I1Set : 355.0 | RUp : 50.0 | RDWn : 50.0 | Trip : 10.0 | SVMax : 3500.0 | VMon : 0.0 | IMon : 0.0 | Pw : 0.0 | POn : 0.0 | PDwn : 0.0 | ImRange : 0.0 | TripInt : 0.0 | TripExt : 0.0 | ZCDetect : 0.0 | Status : Off


