#/bin/bash

anaconda_script_uri="https://repo.anaconda.com/archive/Anaconda3-5.3.0-Linux-x86_64.sh"

ANACONDA_HOME="$HOME/anaconda3"

if which conda &> /dev/null
then
    echo "Anaconda is already installed."
else
    if [ ! -d $ANACONDA_HOME ]
    then
        wget --no-clobber "$anaconda_script_uri"
        bash "$(basename $anaconda_script_uri)" -b -p "$ANACONDA_HOME"
	if [ -f /etc/debian_version ]
        then
            echo "export PATH=$ANACONDA_HOME:\$PATH" \
            >> "$HOME/.profile"
        fi
    fi
fi
