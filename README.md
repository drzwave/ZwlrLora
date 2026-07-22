# Real-World Comparison of Z-Wave Long Range, LoRa, Wi-Fi HaLow sub-gigahertz wireless technologies

This repo contains the scripts and data captured as part of the White Paper Comparison of ZWLR/LoRa/Wi-Fi HaLow.

The purpose of this repo is to enable others to replicate my results.
This white paper is *not* a marketing review of the data sheets for each wireless protocol.
This project captured actual real-world data of the RF Range of each sub-GHz protocol. Many ancedotes on the effort required to setup and use each protocol are documented here. Many more than were published in the white paper due to limited space.

# Status

- ZWLR working
- LoRa - Need to speed up Position Requests - currently limited to 2+ min.
- Wi-Fi HaLow - Working but a bit fragile
- Paper
    - Basic outline completed
    - Paper will be available behind the ZWA website but available to all with an email
    - Presentations at The Things Conference and Z-Wave Alliance Summit 2026 will be available on the ZWA members portal

# Setup

- Z-Wave Equipment
- LoRa Equipment
    - Two [WIO Tracker L1 Pro]("https://www.seeedstudio.com/Wio-Tracker-L1-Pro-p-6454.html")
- Wi-Fi HaLow Equipment

## Lora Meshtastic Setup

1. Download the Meshtastic App for windows
2.	Connect to either USB or BLE – each unit must be setup with the same configuration
3.	Settings-> Radio Config -> LoRa
    1.	Region = US
    2.	Modem Preset = Short Turbo – this is the fastest rate = 27kbits
4.	Settings-> Radio Config -> Channels
    1.	Name = drzwave
    2.	Pre-shared 8-bit key = “AA==” - The default is AQ== so anything else makes it a private encrypted channel
    3.	Location = Precise (only required for the battery powered node)
5.	Settings-> Radio Config -> Security
    1.	Copy the public key from the USB node and paste it into the Primary Admin Key for the battery node
    2.	22b5 Pub Key = Om7L2+/X2T3TIb8ZFTBpM8FYjs8mwWZb4rN1jeyOp2s=
6.	Settings-> Device Config -> Device
    1.	Role = client mute (does not repeat other messages – we only want point-to-point)
7.	Settings-> Device Config -> Position (battery node only)
    1.	Turn off (gray) “enable Smart Position”
    2.	GPS Update Interval = 10 (pull GPS coordinates from the on-board GPS chip every 10s)
8.	Click on Save – Device will normally reboot – close and reopen meshtastic
a.	Must restart meshtastic after reboot or when it hangs which is often
9.	Configure the other node

# Folder Description

- ZWLR - Z-Wave Long Range scripts and data
- LoRa - LoRaWAN scripts and data
- HaLow - Wi-Fi HaLow scripts and data

# Sponsor

- The [Z-Wave Alliance](https://z-wavealliance.org) provided limited funding to offset the equipment cost and partial compensation to prioritize this effort. Much of the effort was donated by Eric Ryherd who is a Z-Wave enthusiast and long-time developer. However, ALL scripts, equipment and data are provided in this repo to enable others to replicate the results. Please contact Eric with comments, improvements, mistakes, and data from your own efforts. Please do NOT comment without actual data to back up your assertions.
