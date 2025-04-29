# Proxmox Autoscaling Infrastructure with Terraform, Ansible, and Prometheus

Sistem ini merupakan implementasi **autoscaling virtual machine (VM)** berbasis on-premise menggunakan kombinasi **Proxmox VE**, **Terraform**, **Ansible**, dan **Prometheus**. Sistem ini dirancang untuk secara otomatis melakukan scale in dan scale out VM web server berdasarkan metrik penggunaan CPU dan memori.

## 🔧 Teknologi yang Digunakan
- **Terraform**: Provisioning VM di Proxmox VE.
- **Ansible**: Setup layanan web server, load balancer, database, dan NFS.
- **Prometheus** + **Node Exporter**: Monitoring metrik.
- **Python Autoscaler**: Logika scaling otomatis.
- **Telegram Bot**: Notifikasi setiap event autoscaling.

## 📁 Struktur Proyek
```
autoscaling-project/
├── ansible/                  # Semua konfigurasi Ansible
│   ├── inventory.ini         # Daftar host yang dikelola
│   ├── playbook.yml         # Main playbook
│   └── roles/               # Role Ansible: webserver, loadbalancer, etc
├── terraform/               # File konfigurasi Terraform
│   ├── main.tf
│   ├── variables.tf
│   └── terraform.tfvars     # (Jangan diunggah ke Git, ada credential)
├── autoscaler.py            # Script autoscaling berbasis Python
├── autoscaler.log           # Log autoscaling
├── .gitignore               # File dan folder yang diabaikan Git
└── README.md                # Dokumentasi proyek
```

## 🛠️ Cara Menggunakan

### 1. Clone Repository
```bash
git clone https://github.com/username/autoscaling-project.git
cd autoscaling-project
```

### 2. Konfigurasi Terraform
Edit file `terraform/terraform.tfvars`:
```hcl
pm_password = "YOUR_PASSWORD"
web_ips     = ["10.2.22.21", "10.2.22.22"]
```
Pastikan file ini ditambahkan ke `.gitignore` karena berisi informasi sensitif.

### 3. Deploy VM
```bash
cd terraform
terraform init
terraform apply
```

### 4. Provisioning Infrastruktur
```bash
cd ../ansible
ansible-playbook playbook.yml
```

### 5. Jalankan Autoscaler
```bash
cd ..
python3 autoscaler.py
```
Autoscaler akan memantau metrik dari Prometheus dan melakukan autoscaling jika diperlukan.

## 📦 Komponen Infrastruktur

- **Web Server (webserver)**
  - Nginx + PHP + WordPress
  - Mengakses konten statis dari NFS
  - Dipantau oleh Node Exporter

- **Load Balancer (loadbalancer)**
  - Mengarahkan traffic ke web server aktif
  - Diperbarui otomatis saat scaling

- **Database Server (db-server)**
  - MariaDB untuk backend WordPress
  - Konfigurasi remote user dan remote bind

- **NFS Server (storage-nfs)**
  - Menyediakan konten WordPress yang shared
  - Dikonfigurasi sekali, dan dimount oleh setiap web server

- **Prometheus**
  - Mengumpulkan metrik dari semua web server
  - Terintegrasi dengan autoscaler Python