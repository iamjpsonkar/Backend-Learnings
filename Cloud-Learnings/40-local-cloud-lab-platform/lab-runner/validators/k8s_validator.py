"""
lab-runner/validators/k8s_validator.py — Kubernetes validation helpers
"""

import subprocess
import sys
import json


CONTEXT = "kind-cloud-lab"


def _kubectl(*args: str, namespace: str = "default") -> tuple[int, str, str]:
    """Run kubectl with the lab cluster context."""
    cmd = ["kubectl", "--context", CONTEXT, "-n", namespace, *args]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.returncode, result.stdout, result.stderr


def pod_running(name_prefix: str, namespace: str = "default") -> tuple[bool, str]:
    """Check that a pod with the given name prefix is Running."""
    rc, stdout, _ = _kubectl("get", "pods", "-o", "json", namespace=namespace)
    if rc != 0:
        return False, f"kubectl get pods failed"

    try:
        pods = json.loads(stdout).get("items", [])
        for pod in pods:
            pod_name = pod["metadata"]["name"]
            phase = pod["status"].get("phase", "")
            if pod_name.startswith(name_prefix) and phase == "Running":
                return True, f"Pod '{pod_name}' is Running"
        return False, f"No Running pod with prefix '{name_prefix}' in namespace '{namespace}'"
    except Exception as exc:
        return False, f"Pod check error: {exc}"


def deployment_ready(name: str, namespace: str = "default") -> tuple[bool, str]:
    """Check that a Deployment has the desired replicas ready."""
    rc, stdout, stderr = _kubectl("get", "deployment", name, "-o", "json", namespace=namespace)
    if rc != 0:
        return False, f"Deployment '{name}' not found: {stderr.strip()[:100]}"

    try:
        data = json.loads(stdout)
        desired = data["spec"].get("replicas", 1)
        ready = data["status"].get("readyReplicas", 0)
        if ready >= desired:
            return True, f"Deployment '{name}' ready ({ready}/{desired})"
        return False, f"Deployment '{name}' not ready ({ready}/{desired})"
    except Exception as exc:
        return False, f"Deployment check error: {exc}"


def service_exists(name: str, namespace: str = "default") -> tuple[bool, str]:
    """Check that a Service exists."""
    rc, _, stderr = _kubectl("get", "service", name, namespace=namespace)
    if rc == 0:
        return True, f"Service '{name}' exists"
    return False, f"Service '{name}' not found"


def configmap_exists(name: str, namespace: str = "default") -> tuple[bool, str]:
    """Check that a ConfigMap exists."""
    rc, _, _ = _kubectl("get", "configmap", name, namespace=namespace)
    return rc == 0, f"ConfigMap '{name}' {'exists' if rc == 0 else 'not found'}"


def secret_exists(name: str, namespace: str = "default") -> tuple[bool, str]:
    """Check that a Secret exists."""
    rc, _, _ = _kubectl("get", "secret", name, namespace=namespace)
    return rc == 0, f"Secret '{name}' {'exists' if rc == 0 else 'not found'}"


def pvc_bound(name: str, namespace: str = "default") -> tuple[bool, str]:
    """Check that a PersistentVolumeClaim is Bound."""
    rc, stdout, _ = _kubectl("get", "pvc", name, "-o", "json", namespace=namespace)
    if rc != 0:
        return False, f"PVC '{name}' not found"
    try:
        phase = json.loads(stdout)["status"]["phase"]
        return phase == "Bound", f"PVC '{name}' phase: {phase}"
    except Exception as exc:
        return False, f"PVC check error: {exc}"


def namespace_exists(name: str) -> tuple[bool, str]:
    """Check that a namespace exists."""
    cmd = ["kubectl", "--context", CONTEXT, "get", "namespace", name]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    return result.returncode == 0, f"Namespace '{name}' {'exists' if result.returncode == 0 else 'not found'}"


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: k8s_validator.py <check> <name> [namespace]", file=sys.stderr)
        sys.exit(1)

    check = sys.argv[1]
    name = sys.argv[2]
    ns = sys.argv[3] if len(sys.argv) > 3 else "default"

    checks = {
        "pod-running": lambda n, ns: pod_running(n, ns),
        "deployment-ready": lambda n, ns: deployment_ready(n, ns),
        "service-exists": lambda n, ns: service_exists(n, ns),
        "configmap-exists": lambda n, ns: configmap_exists(n, ns),
        "secret-exists": lambda n, ns: secret_exists(n, ns),
        "pvc-bound": lambda n, ns: pvc_bound(n, ns),
        "namespace-exists": lambda n, _: namespace_exists(n),
    }

    fn = checks.get(check)
    if fn is None:
        print(f"Unknown check: {check}", file=sys.stderr)
        sys.exit(1)

    passed, msg = fn(name, ns)
    print(msg)
    sys.exit(0 if passed else 1)
