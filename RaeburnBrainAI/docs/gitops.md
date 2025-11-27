# Kubernetes Deployment and GitOps Plan

This project uses Kubernetes to run the Raeburn Brain AI stack. Configuration is
stored in the `k8s/` directory and applied through Argo CD. A GitHub Actions
workflow runs tests and builds the container image before Argo CD syncs the
cluster, enabling an automated GitOps pipeline.

## Argo CD Integration

The Argo CD application manifest in `argocd/app.yaml` points Argo CD to the `k8s/` folder in this repository. When changes are pushed to the `main` branch, Argo CD syncs the cluster state, pruning resources that no longer exist and self‑healing drift.

## Continuous Delivery Workflow

1. Developers open pull requests with Kubernetes manifests.
2. GitHub Actions installs dependencies and runs the test suite.
3. The Docker image is built and, if on `main`, pushed to the registry.
4. Argo CD fetches the latest revision and applies the manifests.
5. Pods are recreated using the updated container images.

## Helm Chart

A minimal Helm chart lives in `helm/raeburn-brain`. GitHub Actions packages and
releases the chart whenever a tag is pushed. To deploy to a specific environment
you can override values such as the image tag and ingress host:

```bash
helm install brain ./helm/raeburn-brain \
  --set image.tag=v0.1.0 --set ingress.host=brain.dev.example.com
```

Alternatively, Kustomize overlays can be created under `k8s/overlays/` for
environment-specific manifests.

## Observability

Prometheus collects metrics from the `ServiceMonitor` defined in `k8s/base/prometheus.yaml`. Alertmanager triggers notifications using the Slack webhook configuration found in `k8s/base/alertmanager.yaml`.
Grafana dashboards are provided via the ConfigMap at `k8s/base/grafana-dashboard.yaml` and automatically discover metrics from Prometheus.

The `Deployment` defines liveness and readiness probes on `/healthz` so Kubernetes can monitor the application's health.

## Folder Structure

- `k8s/base/` – Deployment, Service, and monitoring manifests.
- `argocd/app.yaml` – Argo CD Application definition.
- `docs/` – Supplemental documentation.

With this setup, the stack is deployed via GitOps and remains fully observable through Prometheus and Alertmanager.

## Security

Secrets such as dashboard credentials and the database URL are provided via a Kubernetes `Secret`. They can be rotated at any time without redeploying the application. TLS termination is handled by an `Ingress` resource annotated for cert-manager which issues certificates automatically.
