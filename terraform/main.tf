# === Final Cleaned main.tf ===

terraform {
  required_providers {
    proxmox = {
      source  = "telmate/proxmox"
      version = "3.0.1-rc8"
    }
  }
}

provider "proxmox" {
  pm_api_url      = "https://10.2.22.103:8006/api2/json"
  pm_api_token_id = "root@pam!terraform-token"
  pm_api_token_secret = var.pm_token_secret
  pm_tls_insecure = true
}


locals {
  web_vms = { for idx, ip in var.web_ips : ip => {
    ip    = ip
    vmid  = 211 + idx
    name  = "web-${replace(ip, ".", "-")}"
  } }
}

resource "proxmox_vm_qemu" "web_server" {
  for_each    = local.web_vms
  name        = each.value.name
  target_node = "cnap3"
  clone       = "web-server-template"
  full_clone  = true
  vmid        = each.value.vmid

  agent    = 1
  vm_state = "running"

  cores   = 1
  sockets = 1
  memory  = 2048
  scsihw  = "virtio-scsi-single"
  boot    = "order=scsi0"
  bootdisk = "scsi0"

  os_type = "cloud-init"

  ipconfig0 = "ip=${each.value.ip}/23,gw=10.2.22.1"

  cicustom = "user=local:snippets/user_data_ansible.yml"

  ssh_user         = "ansible"
  ssh_private_key  = file("~/.ssh/id_rsa")

  automatic_reboot = true
  ciupgrade        = true
  skip_ipv6        = true

  disks {
    scsi {
      scsi0 {
        disk {
          size    = "10G"
          storage = "local-lvm"
        }
      }
      scsi1 {
        cloudinit {
          storage = "local-lvm"
        }
      }
    }
  }

  network {
    id     = 0
    bridge = "vmbr0"
    model  = "virtio"
  }

  serial {
    id   = 0
    type = "socket"
  }

  lifecycle {
    ignore_changes = [
      bootdisk,         # abaikan perubahan bootdisk (biar terraform tidak usik)
      ssh_host,         # abaikan perubahan dynamic ssh_host
      ssh_port,         # abaikan perubahan dynamic ssh_port
      default_ipv4_address, # abaikan perubahan auto-generated ip
      default_ipv6_address, # abaikan perubahan auto-generated ipv6
    ]
  }
}


resource "proxmox_vm_qemu" "load_balancer" {
  name        = "lb-nginx"
  target_node = "cnap3"
  clone       = "ubuntu-cloudinit-template.v2"
  vmid        = 210

  agent             = 1
  cores             = 2
  memory            = 2048
  scsihw            = "virtio-scsi-single"
  boot              = "order=scsi0"
  bootdisk          = "scsi0"
  os_type           = "cloud-init"
  cicustom          = "user=local:snippets/user_data_lb.yml"
  ipconfig0         = "ip=10.2.22.20/23,gw=10.2.22.1"
  automatic_reboot  = true
  skip_ipv6         = true
  ciupgrade         = true

  disks {
    scsi {
      scsi0 {
        disk {
          size    = "8G"
          storage = "local-lvm"
        }
      }
    }
    ide {
      ide2 {
        cloudinit {
          storage = "local-lvm"
        }
      }
    }
  }

  network {
    id     = 0
    model  = "virtio"
    bridge = "vmbr0"
  }

  lifecycle {
    ignore_changes = [
      sshkeys,
      full_clone,
      clone,
      ciupgrade,
      skip_ipv6,
      bootdisk,
    ]
  }
}
