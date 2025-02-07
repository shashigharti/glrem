#!/bin/bash

# Update the package list and install essential packages
sudo apt update
sudo apt-get install build-essential

# GDal
sudo apt install gdal-bin libgdal-dev

# Install unzip
sudo apt install python3-dev # necessary header files for compiling Pytgib C extensions
sudo apt-get install unzip

# Check if Ngrok is already installed
if ! command -v ngrok &> /dev/null; then
    echo "Ngrok not found. Installing Ngrok..."

    # Download the Ngrok zip file
    wget https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-3.2.0-linux-amd64.zip

    # Unzip the Ngrok file
    unzip ngrok-stable-3.2.0-linux-amd64.zip

    # Move ngrok binary to /usr/local/bin to make it accessible globally
    sudo mv ngrok /usr/local/bin/

    # Clean up the zip file
    rm ngrok-stable-3.2.0-linux-amd64.zip

    # Optionally authenticate Ngrok (replace with your auth token)
    # ngrok authtoken <your-auth-token>

    echo "Ngrok installation completed."
else
    echo "Ngrok is already installed."
fi

# Check if GMTSAR is already installed
if ! ls /usr/local | grep -q GMTSAR; then
    echo "GMTSAR not found. Installing dependencies and GMTSAR..."
    export DEBIAN_FRONTEND=noninteractive

    # Update package list
    apt-get update > /dev/null

    # Install required packages
    apt-get install -y csh autoconf gfortran \
        libtiff5-dev libhdf5-dev liblapack-dev libgmt-dev gmt > /dev/null

    # Install GCC-9 for compatibility with GMTSAR
    apt-get install -y gcc-9 > /dev/null
    update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-9 10
    update-alternatives --set gcc /usr/bin/gcc-9
    echo "GCC version: $(gcc --version | head -n 1)"

    # Clone the GMTSAR repository
    git config --global advice.detachedHead false
    echo "Cloning GMTSAR repository..."
    git clone -q --branch master https://github.com/gmtsar/gmtsar /usr/local/GMTSAR

    # Checkout to a stable commit to avoid issues with recent changes
    echo "Checking out stable commit..."
    cd /usr/local/GMTSAR && git checkout e98ebc0f4164939a4780b1534bac186924d7c998 > /dev/null

    # Configure and build GMTSAR
    echo "Configuring GMTSAR..."
    cd /usr/local/GMTSAR && autoconf > /dev/null
    ./configure --with-orbits-dir=/tmp > /dev/null

    echo "Building GMTSAR..."
    make > /dev/null 2>&1
    make install > /dev/null

    # Test GMTSAR binary
    echo "Testing GMTSAR installation..."
    /usr/local/GMTSAR/bin/make_s1a_tops 2>&1 | head -n 2
else
    echo "GMTSAR is already installed. Skipping installation."
fi

# Install additional tools and Python dependencies
echo "Installing additional tools and Python libraries..."
apt-get install -y xvfb > /dev/null

echo "Installation process completed."
