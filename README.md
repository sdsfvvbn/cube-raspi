# MeArm Pro - IoT Smart Robotic Arm with Raspberry Pi

## Overview

This is a **Smart Robotic Arm System** controlled via a Web Interface.

Physical computing can be tricky. Beginners often struggle with motor jitter, complex wiring, and unstable power supplies.
The **MeArm Pro** solves these problems by integrating **industrial-grade smoothing algorithms** and **IoT web technologies**. It turns a cheap acrylic arm into a precise, stable, and easy-to-use robot.

The Best helper for Makers and Educators\! Using a smartphone, we can communicate with the MeArm via a local web server. Whether you want to test manual movements or execute complex **Auto-Stacking** tasks (like building a pyramid), just tap a button on your phone screen\!

## Core functions
  * Auto Stacking: Users simply select a shape on the mobile web interface, and the arm automatically executes a complex sequence of movements to complete the stacking task.
* Manual Control: Allows users to manually maneuver the robotic arm using on-screen buttons.

* Web Control Interface: Built with a Python Flask server, enabling control via any smartphone or computer connected to the same Wi-Fi network.

* Smooth Motion Control: Optimized PWM signals specifically for SG90 servo motors, featuring "Gripper Acceleration" and "Arm Stabilization" to prevent jittering.


## What it is

### The Appearance

### Demo Video

https://youtu.be/oo5ojWQWFH8

### Component

#### Hardware

| Name | Quantity |
| :--- | :---: |
| Raspberry Pi 4 | 1 |
| MeArm or other 4do robot | 1 |
| **SG90 Servo Motor** | **4** |
| External 5V/3A Power Supply | 1 |
| Breadboard | 1 |
| Dupont Wires (M-M, M-F) | Many |

#### Software

| Icon | Name | Description |
| :---: | :--- | :--- |
| 🐍 | **Python 3** | The core programming language. |
| 🌐 | **Flask** | Web server framework. |
| ⚙️ | **Pigpio** | Hardware PWM driver (Anti-Jitter). |

-----

## Let's make it

### System Logic

The system uses **Flask** to host a web page. When a user clicks a button, the command is sent to the backend. A background **Thread** executes the motor movements using **Pigpio** to ensure smooth operation.

### Circuit Diagram
![12DE9A6C-1833-4292-89D1-277F71979283](https://github.com/user-attachments/assets/e76ca700-0b64-41b7-80c8-070696d08184)
-----

### Before Getting Started

#### 1\. Set up Raspberry Pi OS

Ensure your Raspberry Pi is running the latest OS and connected to Wi-Fi.

#### 2\. Build the environment for this project

**Basic environments**
Go to your Raspberry Pi terminal and enter:

```bash
sudo apt-get update
sudo apt-get install python3-flask
sudo apt-get install pigpio python3-pigpio
sudo pip3 install qrcode[pil]
```

**Pigpio Daemon**
**Every time you reboot**, you must run:

```bash
sudo pigpiod
```

#### 3\. Hardware Assembly & Wiring

**Mechanical Structure**

  * **MeArm v1.0:** Assemble the acrylic arm carefully.
  * **Servo Centering:** **IMPORTANT\!** Set all servos to 90 degrees before assembly.

**Wiring the SG90 Motors**

I use **SG90 Micro Servos** for the joints. Each motor has 3 wires. It is crucial to connect them correctly to avoid damaging the Raspberry Pi.

Wiring the SG90 Motors

I use SG90 Micro Servos for the joints. Each motor has 3 wires. It is crucial to connect them correctly to avoid damaging the Raspberry Pi.
![sg](https://hackmd.io/_uploads/rkU09Tsfbe.jpg)
⚠️ Critical Warning (Safety First)
If you hear ANY strange noises (buzzing, clicking, or grinding) immediately after powering on:

👉 DISCONNECT THE POWER IMMEDIATELY!

This usually means:

Short Circuit: Wiring is incorrect.

Motor Stall: The arm is mechanically stuck and cannot move.

Do not force it. Check your wiring and mechanical joints before turning it on again.

**1. The 3 Wires of SG90**

  * **Orange/Yellow (Signal):** Connects to the Raspberry Pi GPIO pins.
  * **Red (VCC):** Connects to the **External Power Supply Positive (+)**.
  * **Brown (GND):** Connects to the **External Power Supply Negative (-)**.
![sg](https://hackmd.io/_uploads/rkU09Tsfbe.jpg)
**2. GPIO Pin Mapping (BCM)**
Connect the **Orange wires** to these specific pins:

| Motor Part | GPIO Pin | Physical Pin |
| :--- | :---: | :---: |
| **Gripper** | **GPIO 18** | Pin 12 |
| **Elbow** | **GPIO 12** | Pin 32 |
| **Shoulder** | **GPIO 13** | Pin 33 |
| **Base** | **GPIO 19** | Pin 35 |

**3. Common Ground (The Most Important Step)**
You generally need an external power supply (like a battery pack) for the motors because the Pi cannot provide enough current.
However, for the signal to work, **you must connect the grounds together.**

> **How to connect:**
>
> 1.  Connect Battery Negative (-) to the Breadboard Negative Rail.
> 2.  Connect **Raspberry Pi GND** to the **SAME** Breadboard Negative Rail.

*(Ensure your breadboard ground rail connects both the Battery and the Pi)*

-----

### Build up the Web Controller

My Controller: `app.py`

#### STEP 1: Motor Control with Pigpio

I use **Pigpio** to generate hardware PWM signals.

**Motor Setup Code:**

```python
import pigpio
import time

# Initialize Pigpio
pi = pigpio.pi()

# Define Pins
PINS = {'base': 19, 'shoulder': 13, 'elbow': 12, 'gripper': 18}
```

#### STEP 2: Multi-threading for Safety

To make the **Emergency Stop** button work instantly, I put the stacking tasks into a background thread.

**Threading Logic:**

```python
import threading
STOP_FLAG = False

def auto_stack():
    # Run the stacking task in background
    threading.Thread(target=task).start()
```

#### STEP 3: Auto-Stacking Algorithms

I designed specific coordinates for different shapes.

**Config Code (`config.py`):**

```python
# Pyramid Strategy
PYRAMID_POSITIONS = [
    {'name': 'Far',  'hover': ..., 'down': ...},
    {'name': 'Near', 'hover': ..., 'down': ...},
    {'name': 'Top',  'hover': ..., 'down': ...}
]
```

#### STEP 4: Web Interface (Flask)

The Flask app serves an HTML page (`index.html`) that works on any smartphone. It generates a **QR Code** on startup.

-----

### Let's Coding

Here is my code for the whole project.
**Link here:** [Your GitHub Repository Link]

-----

### Reference

**Servo Motor Control**

  * **SG90 Datasheet:** [http://www.ee.ic.ac.uk/pcheung/teaching/DE1\_EE/stores/sg90\_datasheet.pdf](http://www.ee.ic.ac.uk/pcheung/teaching/DE1_EE/stores/sg90_datasheet.pdf)

**Web Framework**

  * **Flask Documentation:** [https://flask.palletsprojects.com/](https://flask.palletsprojects.com/)

**Mechanical Assembly**

  * **MeArm Instructables:** [https://www.instructables.com/MeArm-Robot-Arm-Your-Robot-V10/](https://www.instructables.com/MeArm-Robot-Arm-Your-Robot-V10/)

1.  **Raspberry Pi GPIO Scripting**: [https://www.instructables.com/Raspberry-Pi-Python-scripting-the-GPIO/](https://www.instructables.com/Raspberry-Pi-Python-scripting-the-GPIO/)
2.  **IoT Core Kit Examples**: [https://github.com/ARM-software/Cloud-IoT-Core-Kit-Examples](https://github.com/ARM-software/Cloud-IoT-Core-Kit-Examples)
3.  **MeArm Robot Arm Open Source Project**: [https://shop.mearm.com/](https://shop.mearm.com/) (Mechanical structure reference)
4.  **pigpio Python Library**: [http://abyz.me.uk/rpi/pigpio/python.html](http://abyz.me.uk/rpi/pigpio/python.html) (PWM control implementation)


-----

### Troubleshooting

**Q: Motors are jittering?**

  * **Solution:** Check **Common Ground**. Make sure you ran `sudo pigpiod`.
  * **Solution:** **Change Battery**. 
  *  **Solution:** Check servo motor.

**Q: Web page stuck?**

  * **Solution:** Ensure you are using the multi-threaded version of `app.py`.

**Q: Gripper not holding blocks?**

  * **Solution:** Add a rubber band inside the gripper or lower `GRIPPER_CLOSE` value in `config.py`.


