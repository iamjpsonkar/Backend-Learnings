# Azurite Configuration

Azurite emulates Azure Blob, Queue, and Table storage locally.

## Connection Details

Use this connection string (also in `.env.example`):

```
DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://localhost:10000/devstoreaccount1;QueueEndpoint=http://localhost:10001/devstoreaccount1;TableEndpoint=http://localhost:10002/devstoreaccount1;
```

## Endpoints

- Blob: `http://localhost:10000/devstoreaccount1`
- Queue: `http://localhost:10001/devstoreaccount1`
- Table: `http://localhost:10002/devstoreaccount1`

## Azure CLI Usage

```bash
# Set connection string
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://localhost:10000/devstoreaccount1;QueueEndpoint=http://localhost:10001/devstoreaccount1;TableEndpoint=http://localhost:10002/devstoreaccount1;"

# List containers
az storage container list

# Create container
az storage container create --name mycontainer

# Upload blob
az storage blob upload --container-name mycontainer --file ./myfile.txt --name myfile.txt

# List blobs
az storage blob list --container-name mycontainer
```

## Python SDK Usage

```python
from azure.storage.blob import BlobServiceClient

conn_str = "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://localhost:10000/devstoreaccount1;"

client = BlobServiceClient.from_connection_string(conn_str)
container = client.create_container("my-container")
```

## What Is Not Supported

Azurite only emulates storage services. These require real Azure:
- Azure Functions
- Azure App Service
- Azure SQL / Cosmos DB
- Azure Active Directory (use Keycloak for local OIDC)
- Azure Monitor / Application Insights (use Prometheus/Grafana)
