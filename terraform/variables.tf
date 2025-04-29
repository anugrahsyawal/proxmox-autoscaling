variable "pm_token_secret" {
  type        = string
  description = "Proxmox API token secret"
}


variable "web_ips" {
  description = "List of IP addresses for web server instances"
  type        = list(string)
}
