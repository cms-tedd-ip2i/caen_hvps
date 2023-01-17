#!/bin/sh

DEST_DIR="/usr/share/CAEN/HVWrapper"

VERSION=`ls bin/x86/libcaenhvwrapper.so.* | grep -Po '\.so\.\K([0-9]+\.)*[0-9]+'`
LIBNAME="libcaenhvwrapper.so.$VERSION"

DEST_INCLUDE_DIR="/usr/include"

if [ `getconf LONG_BIT` = "64" ]
then
	echo "64 bit version detected"
	DEST_LIB_DIR="/usr/lib64"
	LIB_DIR="./bin/x86_64"
	
	if [ ! -d $DEST_LIB_DIR ]; then
		DEST_LIB_DIR="/usr/lib"
	fi
else
	echo "32 bit version detected"
	DEST_LIB_DIR="/usr/lib"
	LIB_DIR="./bin/x86"
fi

ERROR="Please ensure you have the rights to execute this command."

set -e

echo "Installing library $LIBNAME..."

if ! [ $(id -u) = 0 ]; then
	echo
	echo "Unable to get root privileges."   
	echo $ERROR
	exit 1
fi

if [ -d $DEST_DIR ]; then
	echo "Removing old version..."
	rm -rf $DEST_DIR/* || { echo $ERROR ; exit 1; }
fi

install $LIB_DIR/$LIBNAME $DEST_LIB_DIR
ln -sf $DEST_LIB_DIR/$LIBNAME $DEST_LIB_DIR/libcaenhvwrapper.so

echo "Creating directories..."

if [ ! -d $DEST_DIR ]; then
	mkdir -p $DEST_DIR || { echo $ERROR ; exit 1; }
fi

echo "Copying files..."

cp -vf ./include/CAENHVWrapper.h $DEST_INCLUDE_DIR/CAENHVWrapper.h || { echo $ERROR ; exit 1; }
chmod +r $DEST_INCLUDE_DIR/CAENHVWrapper.h || { echo $ERROR ; exit 1; }

cp -vf ./doc/CAENHVWrapper.pdf $DEST_DIR/ || { echo $ERROR ; exit 1; }
cp -vf ./CAENHVWrapperReadme.txt $DEST_DIR/ || { echo $ERROR ; exit 1; }
cp -vf ./CAENHVWrapperReleaseNotes.txt $DEST_DIR/ || { echo $ERROR ; exit 1; }
cp -vf ./CAEN_License_Agreement.txt $DEST_DIR/ || { echo $ERROR ; exit 1; }
chmod +r $DEST_DIR/* || { echo $ERROR ; exit 1; }

echo "Running post-installation triggers..."
ldconfig

echo "Installation completed."
