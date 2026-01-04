ESPHome notes
#############


Applications
============

* 433 MHz weather station receiver/decoder/display
    * 433 MHz receiver
        * OOK/ASK receiver module
        * SX127x module with 433 MHz front end (eg. slightly modified M5Stack LoRa 433 Module
    * Pressure sensor, if the outdoor unit does not have one
        * LPS22 or LPS25
        * BMP105 or similar
    * Display
    
* IR heat-pump controller
* Garage door controller/monitor

* Various displays
    * Weather station data
    * Weather forecast
    * Bus arrival time
    * Calendar


Hardware devices
================

* M5Stack Core Basic
* M5Stick-C
* Heltec ESP32 LoRa module
* NodeMCU or bare AIThinker ESP8266MOD
* CB2S (Arlec switch/power-monitor)


433 MHz weather station decoder
===============================

Hardware
--------

* M5Stack Core Basic
* LoRa 433 MHz module

Overview
--------

* LoRa 433 MHz module has an AI Thinker Ra-02 module
* This uses an SX127x LoRa module
* SX127x can also do OOK and FSK modulation
* When decoding OOK and FSK, SX127x generates output on DIO2
* This signal (SX127x.DIO2, Ra-02.7) is not connected in the LoRa 433 MHz module
* Choose a suitable GPIO on the M5Bus to connect it to
* I chose GPIO13


ESPHome
=======

* ESPHome has turned out to be very easy to make sensor-type things
* Easy to configure
* Easy to build
* Relatively good documentation
* Lots of useful drivers, filters, etc
* Seems faster than my ESP32 build system
* But does a full rebuild far more often than I would like


Device identification
=====================

* Manufacture, model number, serial number
* Complete hardware configuration
    * Base module
    * Extra hardware
* Asset number
* Friendly name
* Function
* Locations
    * Installed location
    * Controlling/sensing location


Fonts
=====

* Font choices depend on
    * Display resolution (dpi)
    * Expected viewing distance
    * Purpose
        * Heading: slightly larger, bold
        * Labels: slightly smaller, not bold
        * Values: standard size, bold, with fixed-width digits and decimal point for easy alignment
        * Log data: tiny, fixed-width font
        * Descriptive text: tiny, proporational font
* Suggestions
    * At low resolution, avoid serif fonts
    * Use X11 bitmap fonts: scalable fonts don't work well at 1BPP
        * Alternative, use 4BPP, but this makes the rasterised fonts much bigger
    
* Font sources
    * X11 bitmap fonts (75dpi gives pixel-size ~ point-size)
    * TTF/OTF fonts

* M5 Stick C
    * LCD: 160x80,  0.96", ~190 dpi
    * These fonts give a heading row and 4 normal display rows
        * Text normal: X11/75dpi/helvR10.bdf
        * Text bold: X11/75dpi/helvB10.bdf
        * Heading: X11/75dpi/helvB12.bdf
        * Text tiny: X11/75dpi/helvR08.bdf
        * Text log: misc/5x8.pcf.gz

* M5 Stack Core Basic
    * LCD: 320x240, 2", ~190 dpi

