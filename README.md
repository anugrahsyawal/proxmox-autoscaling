# 🔄 Proxmox Autoscaling Infrastructure with Terraform, Ansible, and Prometheus

This system implements an **on-premise virtual machine (VM) autoscaling infrastructure** using a combination of **Proxmox VE**, **Terraform**, **Ansible**, and **Prometheus**. It is designed to automatically scale in and scale out web server VMs based on CPU and memory usage metrics.

## 🔧 Technology Stack
- **Terraform**: VM provisioning on Proxmox VE.
- **Ansible**: Setup for web server, load balancer, database, and NFS services.
- **Prometheus** + **Node Exporter**: System metric monitoring.
- **Python Autoscaler**: Handles scaling logic based on Prometheus data.
- **Telegram Bot**: Sends notifications for every scaling event.

## 📁 Project Structure
```
autoscaling-project/
├── ansible/                  # All Ansible configuration
│   ├── inventory.ini         # List of managed hosts
│   ├── playbook.yml         # Main playbook
│   └── roles/               # Ansible roles: webserver, loadbalancer, etc
├── terraform/               # Terraform configuration files
│   ├── main.tf
│   ├── variables.tf
│   └── terraform.tfvars     # (Do not commit to Git, contains credentials)
├── autoscaler.py            # Python-based autoscaling script
├── autoscaler.log           # Autoscaling event logs
├── .gitignore               # Ignored files and directories for Git
└── README.md                # Project documentation
```

## 🛠️ How to Use

### 1. Clone the Repository
```bash
git clone https://github.com/username/autoscaling-project.git
cd autoscaling-project
```

### 2. Configure Terraform
Edit the `terraform/terraform.tfvars` file:
```hcl
pm_api_token = "your_proxmox_api_token"
web_ips      = ["10.2.22.21", "10.2.22.22"]
```
Make sure to add this file to `.gitignore` as it contains sensitive credentials.

### 3. Deploy VMs
```bash
cd terraform
terraform init
terraform apply
```

### 4. Provision Infrastructure with Ansible
```bash
cd ../ansible
ansible-playbook playbook.yml
```

### 5. Run the Autoscaler
```bash
cd ..
python3 autoscaler.py
```
The autoscaler will continuously monitor Prometheus metrics and perform autoscaling as needed.

## 📦 Infrastructure Components

- **Web Server (webserver)**
  - Nginx + PHP + WordPress
  - Serves static content from NFS
  - Monitored via Node Exporter

- **Load Balancer (loadbalancer)**
  - Routes traffic to active web servers
  - Automatically updated during scaling events

- **Database Server (db-server)**
  - MariaDB backend for WordPress
  - Remote access enabled with secure credentials

- **NFS Server (storage-nfs)**
  - Provides shared WordPress content directory
  - Mounted by all web servers

- **Prometheus**
  - Collects metrics from all web servers
  - Integrated with the Python autoscaler for decision-making

