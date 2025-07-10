import requests
import subprocess
import time
import statistics
import os
import socket
from datetime import datetime
import json

# === Konfigurasi ===
PROMETHEUS_URL = "http://localhost:9090"
TFVARS_FILE = "terraform/terraform.tfvars"
TERRAFORM_DIR = "terraform"
INVENTORY_FILE = "ansible/inventory.ini"
MAX_INSTANCES = 5
MIN_INSTANCES = 2
WEB_IP_BASE = "10.2.22."
WEB_IP_START = 21

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
LOG_FILE = "/home/kyune/autoscaling-project/autoscaler.log"

# === Utilitas ===
def separator():
    with open(LOG_FILE, "a") as f:
        f.write("\n========================================\n")

def log(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{now}] {message}\n")
    print(f"[{now}] {message}")

def send_telegram_message(text):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                data={"chat_id": TELEGRAM_CHAT_ID, "text": text},
                timeout=10
            )
        except Exception as e:
            log(f"⚠️ Gagal kirim Telegram: {e}")

def query_prometheus(query):
    try:
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query}, timeout=10)
        response.raise_for_status()
        return response.json()["data"]["result"]
    except Exception as e:
        log(f"⚠️ Error query Prometheus: {e}")
        send_telegram_message(f"⚠️ Error query Prometheus:\n{e}")
        return []

def get_average_metrics():
    cpu_query = '100 - (avg by(instance)(rate(node_cpu_seconds_total{job="node_exporter_webserver",mode="idle"}[5m])) * 100)'
    mem_query = '(1 - (avg by(instance)(node_memory_MemAvailable_bytes{job="node_exporter_webserver"}) / avg by(instance)(node_memory_MemTotal_bytes{job="node_exporter_webserver"}))) * 100'
    cpu_result = query_prometheus(cpu_query)
    mem_result = query_prometheus(mem_query)
    cpu_avg = sum(float(item['value'][1]) for item in cpu_result) / len(cpu_result) if cpu_result else 0.0
    mem_avg = sum(float(item['value'][1]) for item in mem_result) / len(mem_result) if mem_result else 0.0
    return round(cpu_avg, 2), round(mem_avg, 2)

def get_response_time(url="http://10.2.22.20/", num_requests=5):
    latencies = []
    for _ in range(num_requests):
        try:
            start = time.time()
            response = requests.get(url, timeout=5)
            elapsed = time.time() - start
            if response.status_code == 200:
                latencies.append(elapsed)
        except Exception as e:
            log(f"⚠️ Error saat mengukur latency: {e}")
    
    if not latencies:
        return None  # jika semua request gagal

    # Ambil mean sebagai representasi latensi
    percentile_90 = statistics.quantiles(latencies, n=100)[89]
    return round(percentile_90 * 1000, 2)  # konversi ke ms

def read_current_ips():
    if not os.path.exists(TFVARS_FILE):
        return [f"{WEB_IP_BASE}{WEB_IP_START + i}" for i in range(MIN_INSTANCES)]
    with open(TFVARS_FILE) as f:
        for line in f:
            if "web_ips" in line:
                return json.loads(line.split("=")[1].strip())
    return [f"{WEB_IP_BASE}{WEB_IP_START + i}" for i in range(MIN_INSTANCES)]

def update_tfvars(ip_list):
    try:
        with open(TFVARS_FILE, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = []
    ip_list_str = "[" + ", ".join(f'\"{ip}\"' for ip in ip_list) + "]"
    updated = False
    new_lines = []
    for line in lines:
        if line.strip().startswith("web_ips"):
            new_lines.append(f"web_ips = {ip_list_str}\n")
            updated = True
        else:
            new_lines.append(line)
    if not updated:
        new_lines.append(f"web_ips = {ip_list_str}\n")
    with open(TFVARS_FILE, "w") as f:
        f.writelines(new_lines)
    log(f"✅ terraform.tfvars updated: web_ips = {ip_list}")

def run_terraform_apply():
    log("🚀 Menjalankan terraform apply...")
    try:
        subprocess.run(["terraform", "apply", "-auto-approve"], cwd=TERRAFORM_DIR, check=True)
        log("✅ Terraform Apply Berhasil")
        return True
    except subprocess.CalledProcessError as e:
        log(f"❌ Terraform Apply Gagal: {e}")
        send_telegram_message(f"❌ Terraform Apply Gagal!\nError: {e}\nWaktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return False

def wait_for_ssh(ip_list, port=22, timeout=300):
    for ip in ip_list:
        log(f"⏳ Menunggu SSH {ip}:{port} bisa diakses...")
        start = time.time()
        while time.time() - start < timeout:
            try:
                s = socket.create_connection((ip, port), timeout=5)
                s.close()
                log(f"✅ SSH pada {ip}:{port} sudah bisa diakses.")
                break
            except (socket.timeout, ConnectionRefusedError, OSError):
                time.sleep(5)
        else:
            log(f"❌ Timeout: SSH {ip}:{port} tidak bisa diakses setelah {timeout} detik.")

def update_inventory(ip_list):
    content = "[webserver]\n"
    for ip in ip_list:
        content += f"{ip} ansible_user=ansible ansible_ssh_private_key_file=~/.ssh/id_rsa ansible_python_interpreter=/usr/bin/python3\n"
    content += "\n[loadbalancer]\n10.2.22.20 ansible_user=ansible ansible_ssh_private_key_file=~/.ssh/id_rsa ansible_python_interpreter=/usr/bin/python3\n"
    content += "\n[nfsserver]\n10.2.22.26 ansible_user=ansible ansible_ssh_private_key_file=~/.ssh/id_rsa ansible_python_interpreter=/usr/bin/python3\n"
    content += "\n[dbserver]\n10.2.22.27 ansible_user=ansible ansible_ssh_private_key_file=~/.ssh/id_rsa ansible_python_interpreter=/usr/bin/python3\n"
    with open(INVENTORY_FILE, "w") as f:
        f.write(content)
    log("📄 inventory.ini berhasil diupdate.")

def run_ansible_playbook(new_ips):
    if not new_ips:
        return True
    try:
        log(f"📦 Menjalankan Ansible playbook untuk: {new_ips}")
        subprocess.run(["ansible-playbook", "playbook.yml", "--limit", ",".join(new_ips)], cwd="ansible", check=True)
        log("✅ Ansible playbook berhasil.")
        return True
    except subprocess.CalledProcessError as e:
        log(f"❌ Ansible playbook gagal: {e}")
        send_telegram_message(f"❌ Ansible Playbook Gagal!\nError: {e}\nWaktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return False

def update_load_balancer(ip_list):
    nginx_conf = "upstream backend {\n" + "\n".join(f"    server {ip};" for ip in ip_list) + "\n}\n\nserver {\n    listen 80;\n    server_name _;\n    location /wordpress {\n        proxy_pass http://backend;\n    }\n}\n"
    with open("ansible/roles/loadbalancer/templates/nginx-lb.conf.j2", "w") as f:
        f.write(nginx_conf)
    log("📄 nginx-lb.conf berhasil dibuat.")
    try:
        subprocess.run(["ansible", "10.2.22.20", "-m", "copy", "-a", "src=./roles/loadbalancer/templates/nginx-lb.conf.j2 dest=/etc/nginx/sites-available/default mode=0644", "--become"], cwd="ansible", check=True)
        log("✅ nginx config berhasil disalin.")
        subprocess.run(["ansible", "10.2.22.20", "-m", "shell", "-a", "sudo systemctl reload nginx"], cwd="ansible", check=True)
        log("✅ nginx berhasil reload.")
        return True
    except subprocess.CalledProcessError as e:
        log(f"❌ Gagal update nginx: {e}")
        send_telegram_message(f"❌ Load Balancer Reload Gagal!\nError: {e}\nWaktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return False
    
def update_prometheus_config(ip_list):
    prometheus_config_path = "/etc/prometheus/prometheus.yml"
    temp_path = "/tmp/prometheus.yml"

    new_scrape_config = [
        "scrape_configs:\n",
        "  - job_name: 'prometheus'\n",
        "    static_configs:\n",
        "      - targets: ['localhost:9090']\n",
        "\n",
        "  - job_name: 'node_exporter_webserver'\n",
        "    static_configs:\n",
        "      - targets:\n",
    ]
    for ip in ip_list:
        new_scrape_config.append(f"          - '{ip}:9100'\n")

    try:
        with open(prometheus_config_path, "r") as f:
            lines = f.readlines()

        start_idx = None
        for idx, line in enumerate(lines):
            if "scrape_configs:" in line:
                start_idx = idx
                break

        if start_idx is None:
            raise Exception("scrape_configs: tidak ditemukan di prometheus.yml!")

        new_lines = lines[:start_idx] + new_scrape_config

        with open(temp_path, "w") as f:
            f.writelines(new_lines)

        # Copy dan Restart dengan passwordless sudo
        subprocess.run(["sudo", "cp", temp_path, prometheus_config_path], check=True)
        log("📄 prometheus.yml berhasil diperbarui.")

        subprocess.run(["sudo", "systemctl", "restart", "prometheus"], check=True)
        log("✅ Prometheus berhasil direstart.")

    except Exception as e:
        log(f"❌ Error update prometheus.yml: {e}")
        send_telegram_message(f"❌ Error update prometheus.yml:\n{e}")


def autoscaling_decision():
    separator()
    cpu, mem = get_average_metrics()
    current_ips = read_current_ips()
    current_count = len(current_ips)
    response_time = get_response_time()

    log(f"📊 CPU: {cpu}% | Memory: {mem}% | Web Servers: {current_count}")
    log(f"⏱️ Response Time: {response_time} ms")

    decision = None
    # Threshold yang disesuaikan dengan praktik industri
    CPU_THRESHOLD_HIGH = 80
    MEM_THRESHOLD_HIGH = 80
    RESPONSE_TIME_HIGH = 5000  # dalam ms, berdasarkan SLA umum 5 detik untuk web statis
    CPU_THRESHOLD_LOW = 30
    MEM_THRESHOLD_LOW = 30
    RESPONSE_TIME_LOW = 800

    # Keputusan Scale Out jika ada beban tinggi dari salah satu metrik
    if (
        (cpu > CPU_THRESHOLD_HIGH or mem > MEM_THRESHOLD_HIGH or (response_time and response_time > RESPONSE_TIME_HIGH))
        and current_count < MAX_INSTANCES
    ):
        decision = "Scale OUT"

    # Keputusan Scale In jika semua metrik berada di bawah ambang rendah
    elif (
        cpu < CPU_THRESHOLD_LOW
        and mem < MEM_THRESHOLD_LOW
        and (response_time is None or response_time < RESPONSE_TIME_LOW)
        and current_count > MIN_INSTANCES
    ):
        decision = "Scale IN"

    if decision:
        log(f"📈 Decision: {decision}")
        if decision == "Scale OUT":
            new_ips = [f"{WEB_IP_BASE}{WEB_IP_START + i}" for i in range(current_count + 1)][:MAX_INSTANCES]
        else:
            new_ips = current_ips[:-1]

        update_tfvars(new_ips)
        if not run_terraform_apply():
            return

        wait_for_ssh(new_ips)  # Tunggu VM siap SSH
        update_inventory(new_ips)
        update_prometheus_config(new_ips)
        if not update_load_balancer(new_ips):
            return

        if decision == "Scale OUT":
            baru = list(set(new_ips) - set(current_ips))
            if not run_ansible_playbook(baru):
                return

        send_telegram_message(
            f"📢 [{decision}]\nJumlah VM: {current_count} ➔ {len(new_ips)}\n"
            f"CPU: {cpu}% | Memory: {mem}% | RespTime: {response_time} ms\n"
            f"Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        log("📢 Scaling sukses diselesaikan!")
    else:
        log("✅ Decision: No Action")


if __name__ == "__main__":
    autoscaling_decision()
