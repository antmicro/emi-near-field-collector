# Near-field collector - automated EMI measurement flow

Copyright (c) 2024 Antmicro

This project's goal is to extend hardware troubleshooting capabilities by automating the process of measuring and visualizing physical boards' electric and magnetic fields. It involves a CNC machine, spectrum analyser, near-field electric and magnetic field probes. It takes the size of a board and the PCB's blend file as an input, measures the emissions in evenly distributed points and provides a 3D visualization of the near-field. 

## Installation 

To generate 3D visualization, you need to have **Blender** installed. For installation instructions, go [here](https://docs.blender.org/manual/en/latest/getting_started/installing/index.html). Flow was tested on Blender 3.2 and Ubuntu/Debian. 

All scripts are written in Python. After cloning the repo, create a venv environment with Python packages used in all of them: 

* install virtualenv package 
    
    ```bash
    sudo apt install python3-venv
    ```
* create a virtual environment
    
    ```bash
    python3 -m venv .venv
    ```
* activate the environment 
    
    ```bash
    source .venv/bin/activate
    ```
* install the necessary packages
    
    ```bash
    pip install -r requirements.txt
    ```

## Usage 

### Connecting hardware 

First, connect your hardware to a PC. This flow requires usage of a CNC 2.5 axis machine and a spectrum analyzer with an LXI communication protocol (tested with Rigol DSA815). 

A plotter used for the measurements should be connected through a serial port. You can check the name of the port taken by the plotter in 

```
sudo dmesg 
```
or 
```
ls /dev/tty*
```

The spectrum analyser uses a TCP/IP protocol called LXI-11, which requires a configured LAN connection. 
The simplest way is to enable DHCP on the device, connect it to the same network as the PC and check its IP in settings.
* Go to **System -> I/O settings** and set **Remote I/O** to LAN
* Enable **DHCP**
* Read the acquired IP address

### Running the scripts 

The scripts should be run in the following order, with active virtual environment created in the previous steps. 

#### 1. Taking the measurement with `measure.py`

Use the following:

```bash
python3 src/near-field-emi/measure.py x y IPaddress serial_port path_for_measurements
```
where
* **x** and **y** are dimensions of the device under test in mm
* **IPaddress** is an address of the SA - for example `171.19.254.200`
* **serial_port** of the printer - for example `/dev/ttyUSB1`
* **path_for_measurements** - a path to save the measurement data

There are more options to modify the measurement taking process: 
* `--step` - define the distance between measurement points in both x and y coordinates in mm
* `--offset` - define offset in mm of the DUT placement in relation to the plotter's home 
* `--frequency_range` - define the frequency band in Hz on which the measurement will be taken
* `--units` - choose the measurement unit
* `--detectors` - choose the kind of peak detector

Example call:

```bash
python3 src/near-field-emi/measure.py 20 30  <IP_ADDRESS> <SERIAL_DEVICE_NAME> ~/emi-near-field-collector/measurements --offset 0 0 5 --step 10 10 --frequency_range 100000000 400000000
```

An error similar to:
`[Errno 13] Permission denied: '/dev/ttyUSB1'`
means that your user doesn't have permission to use the device. You can change this by creating a [udev rule](https://wiki.archlinux.org/title/udev).

#### 2. EM field plotting with `data_process.py`

In order to get an interference map of the measured field, use the post-processing script on data obtained in the previous step. 

Here's an example of basic usage: 

```bash
python3 src/near-field-emi/data_process.py path_to_measurements
```
where **path_to_measurements** is the path to a folder with data received from `measure.py`. 

The call will process the measurements and plot a set of heatmaps with a step of 50MHz, representing field strength distribution in the actual board coordinates and save the heatmaps as `.png` in two color spaces for 3D visualization. 

The following flags can be used to modify output to your needs: 

* `--remove_background` - if the `measure.py` script is used for collecting a separate set of data on the DUT in an idle state or even without the DUT to obtain the background noise of local environment, this flag along with a path to the background measurement folder can be used to remove the noise from a displayed field map

* `--heatmap-path` - use this flag and provide a path to save generated plots in `png` format in a chosen directory

* `--aggregation` - choose a method of aggregating data for heatmaps; there are currently two options, integrating over signal amplitude or squared amplitude. 

* `--step` - choose a step for intervals to be aggregated, it specifies the amount of data and a frequency band displayed in a single heatmap; changing this parameter allows you to choose a compromise between the number of outputted heatmaps and amount of information on field strength visible on the plots

Example call:

```bash
python3 src/near-field-emi/data_process.py ~/emi-near-field-collector/measurements/DUT_ON/ --heatmap-path ~/emi-near-field-collector/heatmaps --remove-background ~/emi-near-field-collector/measurements/DUT_IDLE/ -ag amplitude --step 40000000.0
```

#### 3. Generating a 3D visualization with Blender using `render_emimap.py`

This scripts takes 3 input arguments 

* a Device Under Test (DUT) `*.blend` model
* heatmaps generated in `data_process.py`
* a shader material available under `assets/emi_material.blend`

The DUT model must meet the following requirements: 

* match in size with heatmap plots - ratio of x and y coordinates given in the previous scripts 
* orientation of the model inside a `*.blend` file has to match the orientation of a heatmap
* there must be at least one camera object in `*.blend` - Blender uses a camera to capture a frame for render from the scene; put the cameras to achieve specific views you'd like to see.

Here's a call of the script using Blender for basic usage: 
```bash
blender path_to_DUT -b -P src/near-field-emi/render_emimap.py -- path_to_heatmaps
```
where **path_to_DUT_model** is a directory where the `DUT.blend` file is kept, **path_to_heatmaps** is a directory with both colorful and greyscale heatmaps. 

There are optional flags: 
* `--camera` - put names of cameras from `DUT.blend` you want to use for rendering; minimum is one name,
* `--render_path` - specify where to save rendered images. 

Example call: 

```bash
blender ~/emi-near-field-collector/DUT.blend -b -P src/near-field-emi/render_emimap.py -- ~/emi-near-field-collector/heatmaps --render_path ~/emi-near-field-collector/renders --camera Camera
```

### Samples 

There's a dedicated folder with samples to use in each step of the flow under `src/examples/` directory. 

```
python3 src/near-field-emi/measure.py 70 40 <IP_ADDRESS> <SERIAL_DEVICE_NAME> src/examples/measurement/SDI-MIPI-Bridge_P2_RMS_dbuV -u dBuV -d RMS -o 0 0 10
```

* **measurement** folder contains a measurement of the SDI-MIPI Bridge board performed with Rigol NFP-series3 P2 probe and a measurement of background noise; you can run `data_process.py` to receive plotted field maps


```
python3 src/near-field-emi/data_process.py src/examples/measure/SDI-MIPI-Bridge_P2_RMS_dbuV/ --heatmap-path src/examples/data-process --remove-background src/examples/measure/SDI-MIPI-Bridge_P2_background/ -ag amplitude
```
* **data-process** - is a folder with a set of maps received from processing the data from the previous step, can be used as input for `render_emimap.py`
* **render**  a blend file of SDI-MIPI Bridge for `render_emimap.py` input argument

```
blender src/examples/render/sdi-mipi-bridge.blend -b -P src/near-field-emi/render_emimap.py -- src/examples/render/ -rp src/examples/outputs/
```

* **outputs** - a folder containing a set of renders obtained from data in the `render` folder
