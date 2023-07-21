FROM centos:centos7
#for Mac m1 --> FROM  --platform=linux/amd64 centos:centos7

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
 

WORKDIR /usr/app/caen_hvps/
COPY caen_hvps/hvps .

# install dependencies
COPY requirements ./requirements
RUN python3 -m pip install --no-cache-dir -r requirements/docker.txt

COPY caen_hvps/caenlib ./caenlib
WORKDIR /usr/app/caen_hvps/caenlib/
RUN tar -xzf CAENHVWrapper-6.3.tgz
RUN rm CAENHVWrapper-6.3.tgz

WORKDIR /usr/app/caen_hvps/caenlib/CAENHVWrapper-6.3/
RUN ./install.sh && \
    rm *.txt && \
    rm -rf HVWrapperDemo/

#WORKDIR /usr/lib
#CMD pwd && ls
#RUN ldconfig -l libcaenhvwrapper.so.6.3
#RUN export LD_LIBRARY_PATH="/usr/lib"

ENV LD_LIBRARY_PATH="/usr/lib"

WORKDIR /usr/app/caen_hvps/