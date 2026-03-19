Phrack-Net v12.0
EN: A professional network monitoring and analysis tool for Linux. Built for educational purposes and authorized network testing only.
TR: Linux için geliştirilmiş profesyonel ağ izleme ve analiz aracı. Yalnızca eğitim amaçlı ve yetkili ağ testleri için tasarlanmıştır.

Features / Özellikler
ModeENTR🔍 Deep ScanFull device analysis via Nmap (OS, ports, services, traceroute)Nmap ile kapsamlı cihaz analizi (OS, portlar, servisler, traceroute)👁️ WatchTransparent bridge — monitor traffic without interruption (Wireshark compatible)Şeffaf köprü — trafiği kesmeden izle (Wireshark uyumlu)🐢 SlowThrottle target device's connection speedHedef cihazın bağlantı hızını yavaşlat☠️ KillDisconnect target device from networkHedef cihazı ağdan kes📡 RescanRe-discover all devices on the networkAğdaki tüm cihazları yeniden tara

Requirements / Gereksinimler

Linux (CachyOS / Arch / Debian based)
Python 3.10+
Root / sudo privileges


Installation / Kurulum
bash# Install system packages / Sistem paketlerini kur
sudo pacman -S python python-pip nmap   # Arch/CachyOS
# sudo apt install python3 python3-pip nmap  # Debian/Ubuntu

# Install Python libraries / Python kütüphanelerini kur
sudo pip install scapy python-nmap --break-system-packages

Usage / Kullanım
bashsudo python Phrack.net.py

⚠️ Disclaimer / Yasal Uyarı
EN: This tool is intended for educational purposes and authorized penetration testing only. Use only on networks you own or have explicit written permission to test. The author is not responsible for any misuse.
TR: Bu araç yalnızca eğitim amaçlı ve yetkili sızma testleri için tasarlanmıştır. Yalnızca kendi ağınızda veya açık yazılı izin aldığınız ağlarda kullanın. Yazar, herhangi bir kötüye kullanımdan sorumlu değildir.

License / Lisans
MIT © 2025 — See LICENSE for details.
