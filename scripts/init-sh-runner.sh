#!/bin/bash

# install necessary packages
sudo apt update
sudo apt install -y jq \
  python3 \
  python-is-python3 \
  libmpc-dev \
  libmpfr-dev \
  libgmp-dev \
  gawk \
  build-essential \
  bison \
  flex \
  texinfo \
  gperf \
  libtool \
  patchutils \
  bc \
  zlib1g-dev \
  libexpat-dev \
  ninja-build \
  git \
  cmake \
  libglib2.0-dev \
  zip \
  wget \
  software-properties-common

# fix openssl issues
sudo apt remove python3-pip
wget https://bootstrap.pypa.io/get-pip.py
sudo python3 get-pip.py
pip install -U pyopenssl cryptography
pip install pygithub==1.59.1 requests

# for precommit-runners (need git --drop-empty)
sudo add-apt-repository ppa:git-core/ppa
sudo apt update
sudo apt upgrade -y

