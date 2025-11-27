# Raeburn Brain Helm Chart

This chart deploys the Raeburn Brain AI service and its monitoring components.

```bash
helm repo add raeburn https://example.com/helm-charts
helm install brain raeburn/raeburn-brain

Secret values such as dashboard credentials are provided via chart parameters:

```bash
helm install brain raeburn/raeburn-brain \
  --set secret.dashboardToken=token \
  --set secret.databaseUrl="sqlite:///raeburn.db" \
  --set secret.oauthUser=admin \
  --set secret.oauthPass=password \
  --set secret.configSecret=changeme
```
```
