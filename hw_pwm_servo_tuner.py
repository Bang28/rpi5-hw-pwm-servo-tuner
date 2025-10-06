"""
hw_pwm_servo_tuner.py
Tuner servo untuk Raspberry Pi 5 (hardware PWM kernel, tanpa pigpio).
- PAN  -> GPIO12 (PWM channel 0)
- TILT -> GPIO13 (PWM channel 1)
- Frekuensi 50 Hz, duty cycle dipetakan ke pulse width (us)
- Smoothing (CCTV-like) + deadband anti-jitter
Perintah interaktif: help, status, center, pan <deg>, tilt <deg>, step pan <±deg>, step tilt <±deg>,
speed <deg_per_s>, min_us <us>, max_us <us>, sweep pan|tilt, quit
"""

import time, threading
from math import isfinite

# ===== parameter default (bisa kamu sesuaikan) =====
MIN_US = 600           # mulai agak aman (banyak SG90 nyaman 600..2400 us)
MAX_US = 2400
INIT_ANGLE = 90
FREQ_HZ = 50          # servo standard
MOVE_SPEED_DEG_S = 420.0  # rasa CCTV (300..480 nyaman)
UPDATE_HZ = 100.0
APPLY_DEADBAND_DEG = 0.3
TARGET_EPS_DEG = 0.5

PAN_CHANNEL  = 0      # Pi 5: GPIO12 = channel 0
TILT_CHANNEL = 1      # Pi 5: GPIO13 = channel 1
# Di Pi 5, chip biasanya 2. Kita coba auto: prefer chip=2, fallback chip=0.
PREFERRED_CHIP = 2

# ===== library hardware PWM =====
try:
    from rpi_hardware_pwm import HardwarePWM
    HAVE_HW = True
except Exception as e:
    print(f"❌ rpi_hardware_pwm tidak tersedia: {e}")
    HAVE_HW = False


def us_to_duty(us: float, freq_hz: float) -> float:
    # duty% = (pulse_us / period_us) * 100
    period_us = 1_000_000.0 / float(freq_hz)
    return (float(us) / period_us) * 100.0


def angle_to_us(angle: float, min_us: float, max_us: float) -> float:
    a = 0.0 if angle < 0 else (180.0 if angle > 180 else float(angle))
    return min_us + (a / 180.0) * (max_us - min_us)


class HWServo:
    def __init__(self, pwm_channel: int, chip_guess=(PREFERRED_CHIP, 0), freq=FREQ_HZ,
                 min_us=MIN_US, max_us=MAX_US, init_angle=INIT_ANGLE):
        self.freq = float(freq)
        self.min_us = float(min_us)
        self.max_us = float(max_us)
        self.angle = float(init_angle)
        self.target = float(init_angle)
        self.ok = False
        self.pwm = None

        # coba chip secara berurutan: (2, lalu 0)
        for chip in chip_guess:
            try:
                self.pwm = HardwarePWM(pwm_channel=pwm_channel, hz=int(self.freq), chip=int(chip))
                self.pwm.start(us_to_duty(angle_to_us(self.angle, self.min_us, self.max_us), self.freq))
                self.ok = True
                self.chip = chip
                print(f"✅ PWM channel {pwm_channel} @ chip {chip}, {self.freq} Hz")
                break
            except Exception as e:
                self.pwm = None
                continue
        if not self.ok:
            print(f"❌ Gagal buka HardwarePWM channel {pwm_channel} (coba chip={chip_guess})")

    def set_angle(self, angle: float):
        a = 0.0 if angle < 0 else (180.0 if angle > 180 else float(angle))
        self.target = a

    def write_now(self, angle: float):
        if not self.ok or self.pwm is None: return
        pulse = angle_to_us(angle, self.min_us, self.max_us)
        duty = us_to_duty(pulse, self.freq)
        try:
            self.pwm.change_duty_cycle(duty)
        except Exception as e:
            print(f"⚠️ change_duty_cycle error: {e}")

    def set_range(self, min_us: float=None, max_us: float=None):
        if min_us is not None: self.min_us = float(min_us)
        if max_us is not None: self.max_us = float(max_us)

    def stop(self):
        try:
            if self.pwm: self.pwm.stop()
        except Exception: pass


class ServoPairSmoother:
    def __init__(self):
        self.pan  = HWServo(PAN_CHANNEL)
        self.tilt = HWServo(TILT_CHANNEL)
        self.speed = float(MOVE_SPEED_DEG_S)
        self.dt = 1.0 / float(UPDATE_HZ if UPDATE_HZ>0 else 100.0)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._th = threading.Thread(target=self._loop, daemon=True)
        self._th.start()

    def set_speed(self, deg_s: float):
        with self._lock:
            self.speed = max(60.0, float(deg_s))

    def set_pan(self, angle: float):
        with self._lock:
            if abs(angle - self.pan.target) < TARGET_EPS_DEG: return
            self.pan.set_angle(angle)

    def set_tilt(self, angle: float):
        with self._lock:
            if abs(angle - self.tilt.target) < TARGET_EPS_DEG: return
            self.tilt.set_angle(angle)

    def set_min_us(self, us: float):
        with self._lock:
            self.pan.set_range(min_us=us)
            self.tilt.set_range(min_us=us)

    def set_max_us(self, us: float):
        with self._lock:
            self.pan.set_range(max_us=us)
            self.tilt.set_range(max_us=us)

    def center(self):
        self.set_pan(90); self.set_tilt(90)

    def sweep(self, which="pan", low=10, high=170, step=10, dwell=0.2):
        low=max(0,int(low)); high=min(180,int(high))
        seq=list(range(low,high+1,step))+list(range(high,low-1,-step))
        if which=="pan":
            for a in seq: self.set_pan(a); time.sleep(dwell)
        else:
            for a in seq: self.set_tilt(a); time.sleep(dwell)

    def status(self):
        with self._lock:
            return {
                "chip_pan": getattr(self.pan, "chip", None),
                "chip_tilt": getattr(self.tilt, "chip", None),
                "speed_deg_s": self.speed,
                "min_us": self.pan.min_us,
                "max_us": self.pan.max_us,
                "pan": self.pan.angle,
                "tilt": self.tilt.angle
            }

    def stop(self):
        self._stop.set()
        try: self._th.join(timeout=1.0)
        except Exception: pass
        self.pan.stop(); self.tilt.stop()

    @staticmethod
    def _step(cur, tgt, step):
        d=tgt-cur
        if d>0: return cur+step if d>step else tgt
        if d<0: return cur-step if -d>step else tgt
        return cur

    def _loop(self):
        while not self._stop.is_set():
            with self._lock:
                step = self.speed * self.dt
                p_cur, t_cur = self.pan.angle, self.tilt.angle
                p_tgt, t_tgt = self.pan.target, self.tilt.target

            p_new = self._step(p_cur, p_tgt, step)
            t_new = self._step(t_cur, t_tgt, step)

            if abs(p_new - p_cur) > APPLY_DEADBAND_DEG:
                self.pan.write_now(p_new)
            if abs(t_new - t_cur) > APPLY_DEADBAND_DEG:
                self.tilt.write_now(t_new)

            # commit posisi sekarang
            with self._lock:
                self.pan.angle = p_new
                self.tilt.angle = t_new

            time.sleep(self.dt)


HELP = """
Perintah:
  help                 : bantuan
  status               : tampilkan status
  center               : kedua servo ke 90°
  pan <deg>            : atur PAN 0..180
  tilt <deg>           : atur TILT 0..180
  step pan <±deg>      : geser PAN relatif (contoh: step pan +5)
  step tilt <±deg>     : geser TILT relatif
  speed <deg_per_s>    : ubah kecepatan (mis. 360, 420, 480)
  min_us <us>          : set pulse minimum (mis. 600)
  max_us <us>          : set pulse maksimum (mis. 2400)
  sweep pan|tilt       : sapu untuk cek endpoint & bunyi
  quit/exit            : keluar

Tips:
- Jika servo bergetar di 90°, naikkan min_us (mis. 620) atau turunkan max_us (mis. 2380), lalu 'center'.
- Pastikan GND servo dan GND Pi tersambung. Gunakan PSU 5V yang kuat (≥2A untuk 2 servo).
- Tambah elco 470–1000 µF di rail 5V servo dapat membantu meredam noise.
"""

def main():
    if not HAVE_HW:
        print("rpi-hardware-pwm belum terpasang / tidak bisa dipakai. Lihat instruksi di header.")
        return
    s = ServoPairSmoother()
    print(HELP)
    try:
        while True:
            cmd = input("hw-tuner> ").strip()
            if not cmd: continue
            parts = cmd.split()
            op = parts[0].lower()
            if op in ("quit","exit"): break
            elif op == "help": print(HELP)
            elif op == "status": print(s.status())
            elif op == "center": s.center()
            elif op == "pan" and len(parts)==2: s.set_pan(float(parts[1]))
            elif op == "tilt" and len(parts)==2: s.set_tilt(float(parts[1]))
            elif op == "step" and len(parts)==3 and parts[1].lower() in ("pan","tilt"):
                delta = float(parts[2])
                st = s.status()
                if parts[1].lower()=="pan": s.set_pan(st["pan"]+delta)
                else: s.set_tilt(st["tilt"]+delta)
            elif op == "speed" and len(parts)==2:
                s.set_speed(float(parts[1])); print("OK")
            elif op == "min_us" and len(parts)==2:
                s.set_min_us(float(parts[1])); print("OK")
            elif op == "max_us" and len(parts)==2:
                s.set_max_us(float(parts[1])); print("OK")
            elif op == "sweep" and len(parts)==2:
                target = parts[1].lower()
                if target in ("pan","tilt"): s.sweep(which=target)
            else:
                print("Perintah tidak dikenali. Ketik 'help'.")
    except KeyboardInterrupt:
        pass
    finally:
        s.stop()
        print("Bye.")

if __name__ == "__main__":
    main()
