# 🔐 Phrack-Net v12.0

> **EN:** Professional network monitoring & analysis tool for Linux.
> **TR:** Linux için profesyonel ağ izleme ve analiz aracı.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![Platform](https://img.shields.io/badge/Platform-Linux-orange?style=flat-square&logo=linux)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Root](https://img.shields.io/badge/Requires-root-red?style=flat-square)

---

## 📋 Features / Özellikler

| Mode | Description (EN) | Açıklama (TR) |
|------|-----------------|---------------|
| 🔍 **Deep Scan** | Full device analysis via Nmap (OS, ports, services, traceroute) | Nmap ile kapsamlı cihaz analizi |
| 👁️ **Watch** | Transparent bridge — monitor traffic without interruption (Wireshark compatible) | Şeffaf köprü — trafiği kesmeden izle |
| 🐢 **Slow** | Throttle target device's connection speed | Hedef cihazın bağlantı hızını yavaşlat |
| ☠️ **Kill** | Disconnect target device from network | Hedef cihazı ağdan kes |
| 📡 **Rescan** | Re-discover all devices on the network | Ağdaki tüm cihazları yeniden tara |

---

## ⚙️ Requirements / Gereksinimler

- 🐧 Linux (CachyOS / Arch / Debian based)
- 🐍 Python 3.10+
- 🔑 Root / sudo privileges
- 📡 nmap

---

## 📦 Installation / Kurulum

**Arch / CachyOS:**
```bash
sudo pacman -S python python-pip nmap
sudo pip install scapy python-nmap --break-system-packages
```

**Debian / Ubuntu:**
```bash
sudo apt install python3 python3-pip nmap
sudo pip install scapy python-nmap --break-system-packages
```

---

## 🚀 Usage / Kullanım

```bash
sudo python Phrack.net.py
```

---

## ⚠️ Disclaimer / Yasal Uyarı

> **EN:** This tool is intended **for educational purposes and authorized penetration testing only**.
> Use only on networks you own or have explicit written permission to test.
> The author is **not responsible** for any misuse.

> **TR:** Bu araç yalnızca **eğitim amaçlı ve yetkili sızma testleri** için tasarlanmıştır.
> Yalnızca kendi ağınızda veya açık yazılı izin aldığınız ağlarda kullanın.
> Yazar, herhangi bir kötüye kullanımdan **sorumlu değildir**.

---

## 📄 License / Lisans

MIT © 2025 — See [LICENSE](LICENSE) for details.
