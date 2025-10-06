# RPi5 Hardware PWM Servo Tuner

A **servo (pan/tilt) tuner for Raspberry Pi 5** powered by the **kernel’s hardware PWM** — **no pigpio** required.  
Built for 9g micro-servos (180°), featuring **CCTV-like smoothing**, an **interactive REPL**, and an **anti‑jitter calibration workflow** (min/max pulse).

> Background: `pigpio` does not support Raspberry Pi 5, which often results in severe **jitter** when driving servos. This project relies on the **`pwm-2chan` device tree overlay** (hardware PWM) and the `rpi-hardware-pwm` Python library.

---

## Features

- **Hardware PWM** (stable 50 Hz; no software‑PWM jitter).
- **Interactive REPL**: commands `pan`, `tilt`, `speed`, `min_us`, `max_us`, `sweep`, `center`, etc.
- **CCTV‑like smoothing**: control `speed` (°/s) & update rate for fast yet smooth motion.
- **Anti‑jitter calibration**: tune **min_us / max_us** until the servo stays quiet at 90° and doesn’t squeal at the endpoints.
- **Sweep** to verify safe range (10° ↔ 170°).
- **No pigpio daemon**; ideal for Raspberry Pi OS (Bookworm).

---

## Requirements

- **Raspberry Pi 5** + **Raspberry Pi OS (Bookworm)**
- **Python 3.9+** (virtualenv recommended)
- Python lib: `rpi-hardware-pwm`
- **Wiring (BCM numbering)**:
  - **PAN** → **GPIO12** (PWM0 / channel 0)
  - **TILT** → **GPIO13** (PWM1 / channel 1)
- **Dedicated 5V supply** for servos (≥ 2 A for two micro‑servos), and **servo GND must be tied** to Pi GND.

---

## Enable Hardware PWM (Pi 5)

1. Edit the boot config (on modern Pi OS it’s usually `/boot/firmware/config.txt`):

   ```ini
   [all]
   dtoverlay=pwm-2chan,pin=12,func=4,pin2=13,func2=4
   ```

2. **Reboot** the Raspberry Pi.

3. **Verify**:

   ```bash
   ls /sys/class/pwm/
   # typically shows pwmchip2 (could be pwmchip0 depending on build)
   ```

   The tuner will try **chip 2 first**, then **chip 0**.  
   In the REPL, run `status` to see which chips are used (`chip_pan`, `chip_tilt`).

---

## Installation

```bash
# (optional) create a virtualenv
python3 -m venv .venv
source .venv/bin/activate

# install dependency
pip install rpi-hardware-pwm
```

Copy **`hw_pwm_servo_tuner.py`** into your project directory.

---

## Run

```bash
python3 hw_pwm_servo_tuner.py
```

Example startup output:

```
✅ PWM channel 0 @ chip 0, 50.0 Hz
✅ PWM channel 1 @ chip 0, 50.0 Hz
```

---

## REPL Commands

Type `help` inside the program to list commands.

- `status` — show current status (chips, speed, min_us/max_us, current positions)
- `center` — both servos to 90°
- `pan <deg>` — set PAN to 0..180°
- `tilt <deg>` — set TILT to 0..180°
- `step pan <±deg>` — relative PAN, e.g. `step pan +5`
- `step tilt <±deg>` — relative TILT, e.g. `step tilt -10`
- `speed <deg_per_s>` — set motion speed (e.g. `360`, `420`, `480`); **360–480°/s** feels CCTV‑like
- `min_us <us>` — set minimum pulse (e.g. `600`)
- `max_us <us>` — set maximum pulse (e.g. `2400`)
- `sweep pan` / `sweep tilt` — sweep 10° ↔ 170° to verify endpoints
- `quit` / `exit` — leave the program

---

## Anti‑Jitter Calibration (Best Practice)

1. **Center**: run `center` and listen at **90°**.  
   If you hear **buzzing**, your pulse range is too aggressive.
2. Slightly increase **`min_us`** (e.g. 600 → 620) **or** lower **`max_us`** (e.g. 2400 → 2380).  
   Run `center` again. Repeat until it’s **quiet**.
3. **Sweep** to check endpoints: `sweep pan` and `sweep tilt`.  
   If you hear squeals near the ends, narrow the range a bit more.
4. Adjust **`speed`** to taste: start at `360`; if still slow try `420` or `480`.

**Hardware tips:**
- Use a **solid 5V PSU** (≥ 2 A for two micro‑servos).
- **Tie servo GND to Pi GND**.
- Add a **470–1000 µF electrolytic** at the 5V servo rail + **0.1 µF** near each servo.
- Keep signal wires **short and tidy**.

---

## Integrating into Your Project

After you find the sweet spot (e.g. `min_us=620`, `max_us=2380`, `speed=420`):

- Apply these values in your main servo module.
- If controlling via a dashboard (e.g. Step widgets), **avoid “echo loops”**:
  - Don’t `virtual_write()` back on every update; synchronize periodically (e.g. at `_sync_device_state`) or on special events like `center`.

---

## Troubleshooting

- **`/sys/class/pwm/` is empty**  
  The overlay isn’t active or the wrong config file is edited. Ensure `dtoverlay=pwm-2chan,...` is in `/boot/firmware/config.txt`, then reboot.
- **Servos don’t move**  
  Run `status`: `chip_pan`/`chip_tilt` must be 0 or 2. If `None`, check overlay & permissions.
- **Still jittery**  
  - Ensure a strong **5V PSU** and common ground.  
  - Narrow the pulse range: raise `min_us`, lower `max_us`.  
  - Try a smaller `speed` (e.g. 300) or increase `UPDATE_HZ` (tweak in source).
- **Need rock‑solid output**  
  Consider **PCA9685** (I²C, 16‑channel, dedicated PWM hardware).

---

## License

**MIT License** — see `LICENSE`.

---

## References

- Thread: Raspberry Pi 5 GPIO (pigpio unsupported) — openHAB Community  
  https://community.openhab.org/t/raspberry-pi-5-gpio-access-pigpio-binding/153681
- Issue: pigpio doesn’t run on Raspberry Pi 5  
  https://github.com/joan2937/pigpio/issues/589
- MQTT-IO Project  
  https://mqtt-io.app/2.6.0/#/

---

## Contributing

PRs and issues are welcome:
- Add presets for popular micro‑servos
- File logging option
- Motion profiles (linear/expo)
- External driver support (PCA9685)

---

Happy tuning! 🚀
