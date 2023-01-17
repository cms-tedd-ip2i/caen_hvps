FROM  --platform=linux/amd64 centos:centos7
# Update packages and install tools 

WORKDIR /usr/app
RUN yum update -y
RUN yum install -y python3
RUN yum install -y iputils
RUN python3 -m pip install --upgrade
RUN python3 -m pip install configobj
RUN yum install -y unzip 
RUN yum install -y java-11-openjdk java-11-openjdk-devel 
RUN yum install -y wget
 

#RUN apt-get update && apt-get install -y --no-install-recommends apt-utils

#WORKDIR /usr/local/lib
#COPY caenlib/CAENHVWrapper-6.3 ./CAENHVWrapper-6.3
#WORKDIR /usr/local/lib/CAENHVWrapper-6.3/
#RUN cd CAENHVWrapper-6.3/


# install dependencies
COPY requirements ./requirements

RUN python3 -m pip install --no-cache-dir -r requirements/docker.txt

COPY caenlib ./caenlib 
WORKDIR /usr/app/caenlib/
RUN tar -xzf CAENHVWrapper-6.3.tgz
RUN rm CAENHVWrapper-6.3.tgz

RUN unzip CAEN_HVPSS_ChannelsController.zip
RUN rm CAEN_HVPSS_ChannelsController.zip

WORKDIR /usr/app/caenlib/CAENHVWrapper-6.3/
RUN pwd && ls

RUN ./install.sh
RUN rm *.txt
RUN rm -rf HVWrapperDemo/
RUN pwd && ls



WORKDIR /usr/lib
CMD pwd && ls
RUN ldconfig -l libcaenhvwrapper.so.6.3
RUN export LD_LIBRARY_PATH="/usr/lib"

WORKDIR /usr/app
COPY hvps ./hvps 
WORKDIR /usr/app/hvps/