# Vault configuration — dev mode
# WARNING: Dev mode stores data in memory only.
# Data is lost when Vault restarts.
# NOT for production use.

ui = true

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1
}

# Dev mode uses in-memory storage
storage "inmem" {}

api_addr = "http://0.0.0.0:8200"
cluster_addr = "http://0.0.0.0:8201"

# Disable mlock (needed in Docker)
disable_mlock = true
