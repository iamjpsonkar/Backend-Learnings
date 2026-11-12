← [Previous: Terraform on GCP](../11-iac/terraform-gcp.md) | [Home](../../README.md) | [Next: Static Website →](./static-website.md)

---

# GCP Projects

Hands-on projects that combine multiple GCP services into complete, production-ready architectures.

---

## Project 1 — Static Website with Cloud CDN

**Goal:** Host a React/Vue/static site on Cloud Storage with Cloud CDN, a managed TLS certificate, and a global load balancer.

**Services:** Cloud Storage · Cloud CDN · Cloud Load Balancing · Cloud DNS · Cloud Armor

```bash
PROJECT_ID="my-website-production"
REGION="us-central1"
BUCKET_NAME="${PROJECT_ID}-www"
DOMAIN="www.example.com"

# 1. Create Cloud Storage bucket (no public access — served via load balancer)
gcloud storage buckets create gs://$BUCKET_NAME \
    --project=$PROJECT_ID \
    --location=$REGION \
    --uniform-bucket-level-access

# 2. Allow the load balancer's service account to read objects
gcloud storage buckets add-iam-policy-binding gs://$BUCKET_NAME \
    --member="serviceAccount:service-$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')@gs-project-accounts.iam.gserviceaccount.com" \
    --role="roles/storage.legacyObjectReader"

# 3. Upload website files
gcloud storage cp -r ./dist/* gs://$BUCKET_NAME/ \
    --cache-control="public, max-age=31536000"

# Override index.html with a short cache (quick deploy propagation)
gcloud storage cp ./dist/index.html gs://$BUCKET_NAME/index.html \
    --cache-control="public, max-age=60" \
    --content-type="text/html"

# 4. Reserve a global static IP
gcloud compute addresses create ip-www-global \
    --project=$PROJECT_ID \
    --global

STATIC_IP=$(gcloud compute addresses describe ip-www-global \
    --global --format="value(address)")
echo "Point DNS: $DOMAIN -> $STATIC_IP"

# 5. Create backend bucket (Cloud Storage backend with CDN enabled)
gcloud compute backend-buckets create bb-www \
    --project=$PROJECT_ID \
    --gcs-bucket-name=$BUCKET_NAME \
    --enable-cdn \
    --cache-mode=CACHE_ALL_STATIC \
    --default-ttl=3600 \
    --max-ttl=86400 \
    --compression-mode=AUTOMATIC

# 6. URL map with SPA fallback (serve index.html for all 404s)
gcloud compute url-maps import urlmap-www \
    --project=$PROJECT_ID \
    --global <<EOF
name: urlmap-www
defaultService: $(gcloud compute backend-buckets describe bb-www --project=$PROJECT_ID --format='value(selfLink)')
hostRules:
- hosts: ["${DOMAIN}"]
  pathMatcher: all
pathMatchers:
- name: all
  defaultService: $(gcloud compute backend-buckets describe bb-www --project=$PROJECT_ID --format='value(selfLink)')
  pathRules:
  - paths: ["/static/**", "/assets/**"]
    service: $(gcloud compute backend-buckets describe bb-www --project=$PROJECT_ID --format='value(selfLink)')
EOF

# 7. Managed SSL certificate
gcloud compute ssl-certificates create cert-www \
    --project=$PROJECT_ID \
    --domains=$DOMAIN \
    --global

# 8. HTTPS proxy + forwarding rule
gcloud compute target-https-proxies create proxy-www \
    --project=$PROJECT_ID \
    --url-map=urlmap-www \
    --ssl-certificates=cert-www \
    --global

gcloud compute forwarding-rules create fr-www-https \
    --project=$PROJECT_ID \
    --global \
    --ip-address=ip-www-global \
    --target-https-proxy=proxy-www \
    --ports=443

# HTTP → HTTPS redirect
gcloud compute url-maps import urlmap-http-redirect \
    --project=$PROJECT_ID \
    --global <<'EOF'
name: urlmap-http-redirect
defaultUrlRedirect:
  redirectResponseCode: MOVED_PERMANENTLY_DEFAULT
  httpsRedirect: true
EOF

gcloud compute target-http-proxies create proxy-www-http \
    --project=$PROJECT_ID \
    --url-map=urlmap-http-redirect \
    --global

gcloud compute forwarding-rules create fr-www-http \
    --project=$PROJECT_ID \
    --global \
    --ip-address=ip-www-global \
    --target-http-proxy=proxy-www-http \
    --ports=80

# 9. Purge CDN cache after deployment
gcloud compute url-maps invalidate-cdn-cache urlmap-www \
    --project=$PROJECT_ID \
    --path="/*" \
    --global
```

**Cost estimate:** ~$2–5/month (Cloud Storage + CDN egress, varies by traffic). Global load balancer: ~$18/month minimum.

---

## Project 2 — Secure VPC with Private GKE

**Goal:** Private GKE Autopilot cluster with no public node IPs, Cloud NAT for egress, IAP for SSH access, and Cloud Armor protecting the ingress.

**Services:** VPC · GKE Autopilot · Cloud NAT · Cloud Armor · Identity-Aware Proxy · Cloud DNS

```bash
PROJECT_ID="my-app-production"
REGION="us-central1"

# Enable APIs
gcloud services enable \
    container.googleapis.com \
    compute.googleapis.com \
    iap.googleapis.com \
    --project=$PROJECT_ID

# Create VPC
gcloud compute networks create vpc-my-app-prod \
    --project=$PROJECT_ID \
    --subnet-mode=custom

# GKE subnet with secondary ranges
gcloud compute networks subnets create snet-gke-us-central1 \
    --project=$PROJECT_ID \
    --network=vpc-my-app-prod \
    --region=$REGION \
    --range=10.0.31.0/24 \
    --secondary-range=pods=10.1.0.0/16,services=10.2.0.0/20 \
    --enable-private-ip-google-access

# App subnet (for non-GKE workloads)
gcloud compute networks subnets create snet-app-us-central1 \
    --project=$PROJECT_ID \
    --network=vpc-my-app-prod \
    --region=$REGION \
    --range=10.0.11.0/24 \
    --enable-private-ip-google-access

# Cloud NAT (outbound internet for private nodes)
gcloud compute routers create router-us-central1 \
    --project=$PROJECT_ID \
    --network=vpc-my-app-prod \
    --region=$REGION

gcloud compute routers nats create nat-us-central1 \
    --project=$PROJECT_ID \
    --router=router-us-central1 \
    --region=$REGION \
    --nat-all-subnet-ip-ranges \
    --auto-allocate-nat-external-ips \
    --enable-logging

# Firewall: allow IAP SSH
gcloud compute firewall-rules create fw-allow-iap \
    --project=$PROJECT_ID \
    --network=vpc-my-app-prod \
    --direction=INGRESS \
    --action=ALLOW \
    --rules=tcp:22 \
    --source-ranges=35.235.240.0/20 \
    --target-tags=iap-access

# Firewall: allow GKE health checks
gcloud compute firewall-rules create fw-allow-health-checks \
    --project=$PROJECT_ID \
    --network=vpc-my-app-prod \
    --direction=INGRESS \
    --action=ALLOW \
    --rules=tcp:8080 \
    --source-ranges=130.211.0.0/22,35.191.0.0/16 \
    --target-tags=allow-health-check

# GKE Autopilot (private nodes, Workload Identity)
gcloud container clusters create-auto gke-my-app-prod-us-central1 \
    --project=$PROJECT_ID \
    --region=$REGION \
    --network=vpc-my-app-prod \
    --subnetwork=snet-gke-us-central1 \
    --cluster-secondary-range-name=pods \
    --services-secondary-range-name=services \
    --enable-private-nodes \
    --master-ipv4-cidr=172.16.0.0/28 \
    --enable-master-authorized-networks \
    --master-authorized-networks=10.0.0.0/8

echo "Cluster ready. Get credentials:"
echo "gcloud container clusters get-credentials gke-my-app-prod-us-central1 --project=$PROJECT_ID --region=$REGION"
```

---

## Project 3 — Cloud Run Microservice

**Goal:** Deploy a Python API to Cloud Run with Secret Manager integration, Pub/Sub for async processing, Cloud Monitoring alerts, and a global HTTPS load balancer.

**Services:** Cloud Run · Secret Manager · Pub/Sub · Cloud Monitoring · Cloud Load Balancing · Artifact Registry

```bash
PROJECT_ID="my-app-production"
REGION="us-central1"
SA_EMAIL="my-app-workload@${PROJECT_ID}.iam.gserviceaccount.com"

# Create service account
gcloud iam service-accounts create my-app-workload \
    --project=$PROJECT_ID \
    --display-name="My App Cloud Run Workload"

# Grant minimum permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/pubsub.publisher"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/cloudtrace.agent"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/monitoring.metricWriter"

# Create secrets
echo -n "postgres://user:pass@host/db" | gcloud secrets versions add api-database-url \
    --project=$PROJECT_ID \
    --data-file=-

# Create Artifact Registry repo and build image
gcloud artifacts repositories create my-app \
    --project=$PROJECT_ID \
    --location=$REGION \
    --repository-format=docker

gcloud builds submit \
    --project=$PROJECT_ID \
    --region=$REGION \
    --tag=${REGION}-docker.pkg.dev/${PROJECT_ID}/my-app/api:v1.0.0 \
    .

# Deploy to Cloud Run
gcloud run deploy my-app-api \
    --project=$PROJECT_ID \
    --region=$REGION \
    --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/my-app/api:v1.0.0 \
    --service-account=$SA_EMAIL \
    --no-allow-unauthenticated \
    --memory=512Mi \
    --cpu=1 \
    --min-instances=1 \
    --max-instances=50 \
    --concurrency=80 \
    --timeout=30 \
    --set-env-vars=GCP_PROJECT_ID=$PROJECT_ID,APP_ENV=production \
    --set-secrets=DATABASE_URL=api-database-url:latest

# Create global HTTPS load balancer (see 03-networking/README.md for full steps)
# Create Serverless NEG → Backend Service → URL Map → HTTPS Proxy → Forwarding Rule

# Create monitoring alert for error rate
gcloud logging metrics create cloud-run-5xx \
    --project=$PROJECT_ID \
    --log-filter='resource.type="cloud_run_revision" AND httpRequest.status>=500'
```

---

## Project 4 — BigQuery Analytics Pipeline

**Goal:** Ingest application events from Pub/Sub into BigQuery via Dataflow, query with SQL, and visualize in Looker Studio.

**Services:** Pub/Sub · Dataflow · BigQuery · Cloud Storage · Cloud Scheduler

```bash
PROJECT_ID="my-app-production"
REGION="us-central1"

gcloud services enable \
    dataflow.googleapis.com \
    bigquery.googleapis.com \
    pubsub.googleapis.com \
    --project=$PROJECT_ID

# Create a Pub/Sub topic for events
gcloud pubsub topics create app-events --project=$PROJECT_ID

# Create BigQuery dataset and table
bq mk --project_id=$PROJECT_ID --location=$REGION --dataset analytics

bq mk \
    --project_id=$PROJECT_ID \
    --table analytics.events \
    --schema 'event_id:STRING,user_id:STRING,event_type:STRING,properties:JSON,timestamp:TIMESTAMP' \
    --time_partitioning_field timestamp \
    --time_partitioning_type DAY \
    --clustering_fields event_type,user_id

# GCS bucket for Dataflow temp files
gcloud storage buckets create gs://${PROJECT_ID}-dataflow-temp \
    --project=$PROJECT_ID \
    --location=$REGION \
    --uniform-bucket-level-access

# Launch Pub/Sub → BigQuery Dataflow streaming pipeline (Google-provided template)
gcloud dataflow jobs run pubsub-to-bq-events \
    --project=$PROJECT_ID \
    --region=$REGION \
    --gcs-location=gs://dataflow-templates-us-central1/latest/PubSub_to_BigQuery \
    --parameters=\
inputTopic=projects/${PROJECT_ID}/topics/app-events,\
outputTableSpec=${PROJECT_ID}:analytics.events,\
outputDeadletterTable=${PROJECT_ID}:analytics.events_errors \
    --temp-location=gs://${PROJECT_ID}-dataflow-temp/dataflow-temp \
    --service-account-email=$SA_EMAIL

# Query the table with BigQuery SQL
bq query --use_legacy_sql=false --project_id=$PROJECT_ID \
"SELECT
   event_type,
   DATE(timestamp) AS date,
   COUNT(*) AS event_count,
   COUNT(DISTINCT user_id) AS unique_users
 FROM analytics.events
 WHERE DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
 GROUP BY 1, 2
 ORDER BY 2 DESC, 3 DESC"
```

**Cost estimate:** ~$10–30/month (BigQuery storage + queries + Pub/Sub + Dataflow streaming at low volume).

---

## Project Cost Summary

| Project | Key Services | Estimated Monthly Cost |
|---------|-------------|----------------------|
| Static Website CDN | Cloud Storage + CDN + GLB | ~$20 (GLB dominates) |
| Secure Private GKE | GKE Autopilot + Cloud NAT + Cloud Armor | ~$100–300 (traffic-dependent) |
| Cloud Run Microservice | Cloud Run + Secret Manager + Pub/Sub | ~$5–30 (traffic-dependent) |
| BigQuery Analytics | Pub/Sub + Dataflow + BigQuery | ~$10–50 (data volume-dependent) |

> Costs are approximate. Use the [GCP Pricing Calculator](https://cloud.google.com/products/calculator) for accurate estimates.

---

## References

- [GCP Architecture Center](https://cloud.google.com/architecture)
- [GCP reference architectures](https://cloud.google.com/architecture/framework)
- [GCP pricing calculator](https://cloud.google.com/products/calculator)
- [Well-Architected Framework on GCP](https://cloud.google.com/architecture/framework)
---

← [Previous: Terraform on GCP](../11-iac/terraform-gcp.md) | [Home](../../README.md) | [Next: Static Website →](./static-website.md)
