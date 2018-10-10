#!/bin/bash

convert \
    -background transparent \
    -colorspace sRGB \
    favicon.ai \
    -define icon:auto-resize=16,32,48,152 \
    favicon.ico
