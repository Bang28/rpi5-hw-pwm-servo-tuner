# RPi5 Hardware PWM Servo Tuner

Tuner servo (pan/tilt) untuk **Raspberry Pi 5** yang menggunakan **hardware PWM kernel** — **tanpa pigpio**.  
Cocok untuk micro-servo 9g (180°), lengkap dengan **smoothing ala CCTV**, **REPL interaktif**, dan **panduan kalibrasi anti-jitter** (min/max pulse).

> Latar belakang: `pigpio` tidak mendukung Raspberry Pi 5 sehingga banyak pengguna mengalami **jitter** saat menggerakkan servo. Solusi ini memanfaatkan **device tree overlay** `pwm-2chan` (PWM hardware) dan library `rpi-hardware-pwm`.

---

## Fitur

- **Hardware PWM** (stabil 50 Hz; bebas jitter software).
- **REPL interaktif**: perintah `pan`, `tilt`, `speed`, `min_us`, `max_us`, `sweep`, `center`, dll.
- **Smoothing ala CCTV**: atur `speed` (°/s) & `update Hz` agar gerak cepat namun halus.
- **Kalibrasi anti-jitter**: set **min_us / max_us** sampai servo diam di 90° dan tidak mendecit di ujung.
- **Sweep** untuk cek rentang aman (10° ↔ 170°).
- **Tanpa pigpio daemon**; cocok untuk Raspberry Pi OS (Bookworm).

---

## Persyaratan

- **Raspberry Pi 5** + **Raspberry Pi OS (Bookworm)**.
- **Python 3.9+** (disarankan menggunakan virtualenv).
- Library Python: `rpi-hardware-pwm`.
- **Wiring (BCM numbering)**:
  - **PAN** → **GPIO12** (PWM0 / channel 0)
  - **TILT** → **GPIO13** (PWM1 / channel 1)
- **Catu daya 5V terpisah** untuk servo (≥ 2 A untuk 2 micro-servo), **GND servo harus disatukan** dengan GND Pi.

---

## Mengaktifkan Hardware PWM (Pi 5)

1. Edit konfigurasi boot (Pi OS modern biasanya di `/boot/firmware/config.txt`):

   ```ini
   [all]
   dtoverlay=pwm-2chan,pin=12,func=4,pin2=13,func2=4
   ```

2. **Reboot** Raspberry Pi.

3. **Verifikasi**:

   ```bash
   ls /sys/class/pwm/
   # biasanya muncul pwmchip2 (tergantung build bisa juga pwmchip0)
   ```

   Script tuner akan mencoba **chip 2 terlebih dahulu**, lalu **chip 0**.  
   Jalankan perintah `status` di REPL untuk melihat chip yang dipakai (`chip_pan`, `chip_tilt`).

---

## Instalasi

```bash
# (opsional) buat virtualenv
python3 -m venv .venv
source .venv/bin/activate

# instal dependensi
pip install rpi-hardware-pwm
```

Salin file **`hw_pwm_servo_tuner.py`** ke direktori proyek.

---

## Menjalankan

```bash
python3 hw_pwm_servo_tuner.py
```

Contoh output awal:

```
✅ PWM channel 0 @ chip 0, 50.0 Hz
✅ PWM channel 1 @ chip 0, 50.0 Hz
```

---

## Perintah REPL

Ketik `help` di dalam program untuk daftar perintah.

- `status` — tampilkan status (chip yang dipakai, speed, min_us/max_us, posisi saat ini)
- `center` — kedua servo ke 90°
- `pan <deg>` — set PAN ke 0..180°
- `tilt <deg>` — set TILT ke 0..180°
- `step pan <±deg>` — geser PAN relatif, contoh: `step pan +5`
- `step tilt <±deg>` — geser TILT relatif, contoh: `step tilt -10`
- `speed <deg_per_s>` — atur kecepatan (mis. `360`, `420`, `480`); rasa CCTV nyaman di **360–480°/s**
- `min_us <us>` — set pulse minimum (mis. `600`)
- `max_us <us>` — set pulse maksimum (mis. `2400`)
- `sweep pan` / `sweep tilt` — sapu 10° ↔ 170° untuk cek endpoint & bunyi
- `quit` / `exit` — keluar dari program

---

## Panduan Kalibrasi Anti-Jitter (Best Practice)

1. **Center**: jalankan `center` dan dengarkan di **90°**.  
   Jika **bergetar/dengung**, berarti pulse range terlalu agresif.
2. Naikkan **`min_us`** sedikit (mis. 600 → 620) **atau** turunkan **`max_us`** (mis. 2400 → 2380).  
   Jalankan `center` lagi. Ulangi sampai **benar-benar diam**.
3. **Sweep** untuk cek ujung: `sweep pan` dan `sweep tilt`.  
   Jika mendecit di ujung, persempit lagi (naikkan `min_us` / turunkan `max_us`).
4. Atur **`speed`** sesuai “rasa CCTV”: mulai `360`; jika masih lambat → `420` atau `480`.

**Tips hardware:**
- Gunakan **PSU 5V kuat** (≥ 2 A untuk 2 servo).
- **GND servo ↔ GND Pi** harus tersambung.
- Tambahkan **elco 470–1000 µF** di rail 5V servo + **0.1 µF** dekat masing-masing servo.
- Gunakan kabel sinyal **pendek & rapi**.

---

## Integrasi ke Proyek

Setelah menemukan pengaturan yang pas (mis. `min_us=620`, `max_us=2380`, `speed=420`):

- Terapkan nilai tersebut di modul servo proyek utama Anda.
- Jika mengendalikan via dashboard (mis. widget Step), **hindari “echo loop”**:
  - Jangan selalu `virtual_write()` balik setiap update nilai; cukup sync berkala (mis. saat `_sync_device_state`) atau saat event khusus seperti `center`.

---

## Troubleshooting

- **`/sys/class/pwm/` kosong**  
  Overlay belum aktif atau salah file config. Pastikan baris `dtoverlay=pwm-2chan,...` ada di `/boot/firmware/config.txt`, lalu reboot.
- **Servo tidak bergerak**  
  Cek `status`: `chip_pan`/`chip_tilt` harus 0 atau 2. Jika `None`, cek overlay & permission.
- **Masih jitter**  
  - Pastikan **PSU 5V** kuat dan **ground** tersambung.
  - Persempit rentang: naikkan `min_us`, turunkan `max_us`.
  - Coba `speed` lebih kecil (mis. 300) atau tingkatkan `UPDATE_HZ` (ubah di source).
- **Butuh kualitas paling stabil**  
  Pertimbangkan **PCA9685** (I²C, 16-channel, hardware PWM dedicated).


---

## Lisensi

**MIT License** — lihat file `LICENSE`.

---

## Referensi

- Thread: Raspberry Pi 5 GPIO (pigpio tidak mendukung) — openHAB Community  
  https://community.openhab.org/t/raspberry-pi-5-gpio-access-pigpio-binding/153681
- Issue: pigpio tidak berjalan di Raspberry Pi 5  
  https://github.com/joan2937/pigpio/issues/589
- MQTT-IO Project  
  https://mqtt-io.app/2.6.0/#/

---

## Kontribusi

PR dan issue sangat welcome:
- Preset kalibrasi untuk beberapa model micro-servo populer
- Opsi logging ke file
- Profil gerak (linear/expo)
- Driver eksternal PCA9685

---

Selamat tuning! 🚀
