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

# for gh cli
# https://github.com/cli/cli/blob/trunk/docs/install_linux.md#debian
(type -p wget >/dev/null || (sudo apt update && sudo apt install wget -y)) \
	&& sudo mkdir -p -m 755 /etc/apt/keyrings \
	&& out=$(mktemp) && wget -nv -O$out https://cli.github.com/packages/githubcli-archive-keyring.gpg \
	&& cat $out | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
	&& sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
	&& sudo mkdir -p -m 755 /etc/apt/sources.list.d \
	&& echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
	&& sudo apt update \
	&& sudo apt install gh -y

############################################################################################################
# Note sometimes this doesn't actually work properly. Need to run `sudo apt install python3-pip` again to fix
############################################################################################################

# for precommit-runners (need git --drop-empty)
sudo add-apt-repository -y ppa:git-core/ppa
sudo apt update
sudo apt upgrade -y
