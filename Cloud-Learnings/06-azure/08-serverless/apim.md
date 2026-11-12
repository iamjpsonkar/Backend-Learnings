← [Previous: Event Grid](./event-grid.md) | [Home](../../README.md) | [Next: Azure Security →](../09-security/README.md)

---

# Azure API Management (APIM)

APIM is a fully managed API gateway. It sits in front of your backend APIs and provides authentication, rate limiting, transformation, caching, analytics, and developer portal features.

---

## Architecture

```
Client
  │
  ▼
Azure API Management (Gateway)
  ├── Policies: auth, rate-limit, transform, cache
  ├── Developer Portal (self-service API discovery)
  └── Built-in analytics
  │
  ▼
Backend APIs (Azure Functions, AKS, App Service, External)
```

---

## SKU Comparison

| SKU | Throughput | VNet | Self-hosted gateway | Use Case |
|-----|-----------|------|---------------------|----------|
| **Consumption** | Per-request billing | No | No | Low-volume, dev/test |
| **Developer** | Fixed, limited | VNet injection | No | Dev, non-production |
| **Basic** | 1 unit | No | No | Simple APIs |
| **Standard** | 1 unit | No | No | Production |
| **Premium** | N units | VNet injection | Yes | Enterprise, multi-region |

---

## Creating an APIM Instance

```bash
RESOURCE_GROUP="rg-my-app-prod-eastus"
APIM_NAME="apim-my-app-prod-eastus"
PUBLISHER_EMAIL="api-admin@example.com"
PUBLISHER_NAME="My App Platform"

# Create Standard tier APIM (takes ~30–45 minutes)
az apim create \
    --resource-group $RESOURCE_GROUP \
    --name $APIM_NAME \
    --location eastus \
    --sku-name Standard \
    --publisher-email $PUBLISHER_EMAIL \
    --publisher-name "$PUBLISHER_NAME" \
    --enable-managed-identity true \
    --tags Environment=production Service=my-app

# Get the gateway URL
az apim show \
    --resource-group $RESOURCE_GROUP \
    --name $APIM_NAME \
    --query '{Gateway:gatewayUrl,Portal:developerPortalUrl,Management:managementApiUrl}' \
    --output json
```

---

## Importing an API

```bash
# Import OpenAPI spec from a URL
az apim api import \
    --resource-group $RESOURCE_GROUP \
    --service-name $APIM_NAME \
    --api-id orders-api \
    --path /orders \
    --display-name "Orders API" \
    --specification-format OpenApi \
    --specification-url "https://my-app.example.com/openapi.json"

# Import OpenAPI spec from a local file
az apim api import \
    --resource-group $RESOURCE_GROUP \
    --service-name $APIM_NAME \
    --api-id orders-api \
    --path /orders \
    --display-name "Orders API" \
    --specification-format OpenApi \
    --specification-path ./openapi.yaml

# Create API manually
az apim api create \
    --resource-group $RESOURCE_GROUP \
    --service-name $APIM_NAME \
    --api-id products-api \
    --path /products \
    --display-name "Products API" \
    --protocols https \
    --service-url https://func-my-app-prod-eastus.azurewebsites.net/api
```

---

## Policies

APIM policies are XML-based rules applied at four scopes: global, product, API, operation.

### Key Policies

```xml
<!-- policies/orders-api-inbound.xml -->
<policies>
  <inbound>
    <!-- Validate JWT from Entra ID -->
    <validate-jwt header-name="Authorization" failed-validation-httpcode="401" require-expiration-time="true">
      <openid-config url="https://login.microsoftonline.com/{tenant-id}/v2.0/.well-known/openid-configuration" />
      <required-claims>
        <claim name="aud" match="any">
          <value>api://my-app-api</value>
        </claim>
      </required-claims>
    </validate-jwt>

    <!-- Rate limiting: 100 calls per minute per subscription key -->
    <rate-limit-by-key calls="100" renewal-period="60"
        counter-key="@(context.Subscription.Id)" />

    <!-- Quota: 10,000 calls per day per subscription -->
    <quota-by-key calls="10000" renewal-period="86400"
        counter-key="@(context.Subscription.Id)" />

    <!-- Add correlation ID for tracing -->
    <set-header name="X-Correlation-Id" exists-action="skip">
      <value>@(context.RequestId.ToString())</value>
    </set-header>

    <!-- Forward managed identity token to backend -->
    <authentication-managed-identity resource="https://management.azure.com/" />
  </inbound>

  <backend>
    <!-- Retry failed backend calls -->
    <retry condition="@(context.Response.StatusCode >= 500)" count="3" interval="2">
      <forward-request timeout="30" />
    </retry>
  </backend>

  <outbound>
    <!-- Cache GET responses for 5 minutes -->
    <cache-store duration="300" />

    <!-- Remove internal headers before returning to client -->
    <set-header name="X-Powered-By" exists-action="delete" />
    <set-header name="Server" exists-action="delete" />

    <!-- Transform response — add pagination headers -->
    <set-header name="X-Total-Count" exists-action="override">
      <value>@(context.Variables.GetValueOrDefault("totalCount", "0"))</value>
    </set-header>
  </outbound>

  <on-error>
    <return-response>
      <set-status code="@(context.Response.StatusCode)" />
      <set-body>@{
        return new JObject(
          new JProperty("error", context.LastError.Message),
          new JProperty("correlationId", context.RequestId)
        ).ToString();
      }</set-body>
    </return-response>
  </on-error>
</policies>
```

```bash
# Apply policy to an API
az apim api policy create \
    --resource-group $RESOURCE_GROUP \
    --service-name $APIM_NAME \
    --api-id orders-api \
    --value @policies/orders-api-inbound.xml \
    --format xml
```

---

## Products and Subscriptions

Products group APIs and control access via subscription keys.

```bash
# Create a product
az apim product create \
    --resource-group $RESOURCE_GROUP \
    --service-name $APIM_NAME \
    --product-id standard-plan \
    --product-name "Standard Plan" \
    --description "100 calls/minute, 10k calls/day" \
    --state published \
    --subscription-required true \
    --approval-required false

# Add APIs to the product
az apim product api add \
    --resource-group $RESOURCE_GROUP \
    --service-name $APIM_NAME \
    --product-id standard-plan \
    --api-id orders-api

# Create a subscription (provides subscription key)
az apim subscription create \
    --resource-group $RESOURCE_GROUP \
    --service-name $APIM_NAME \
    --subscription-id sub-partner-001 \
    --display-name "Partner 001 Subscription" \
    --product-id /products/standard-plan \
    --state active

# Get subscription keys
az apim subscription keys show \
    --resource-group $RESOURCE_GROUP \
    --service-name $APIM_NAME \
    --subscription-id sub-partner-001 \
    --query '{Primary:primaryKey,Secondary:secondaryKey}'
```

---

## Named Values (Secrets)

```bash
# Store a secret in APIM backed by Key Vault
az apim nv create \
    --resource-group $RESOURCE_GROUP \
    --service-name $APIM_NAME \
    --named-value-id backend-api-key \
    --display-name "Backend API Key" \
    --secret true \
    --key-vault-secret-identifier "https://kv-my-app-prod-eastus.vault.azure.net/secrets/backend-api-key"

# Reference in policy: {{backend-api-key}}
```

---

## Diagnostics and Monitoring

```bash
# Enable Application Insights logging
APPINSIGHTS_ID=$(az monitor app-insights component show \
    --resource-group rg-platform-monitoring-eastus \
    --app appi-my-app-prod-eastus \
    --query id -o tsv)

az apim update \
    --resource-group $RESOURCE_GROUP \
    --name $APIM_NAME \
    --set properties.notificationSenderEmail=$PUBLISHER_EMAIL

# View API analytics in the portal — or use Log Analytics:
# AzureDiagnostics | where ResourceType == "APIMANAGEMENT SERVICES"
```

---

## References

- [Azure API Management documentation](https://docs.microsoft.com/azure/api-management/)
- [APIM policies reference](https://docs.microsoft.com/azure/api-management/api-management-policies)
- [JWT validation policy](https://docs.microsoft.com/azure/api-management/validate-jwt-policy)

---

← [Previous: Event Grid](./event-grid.md) | [Home](../../README.md) | [Next: Azure Security →](../09-security/README.md)
