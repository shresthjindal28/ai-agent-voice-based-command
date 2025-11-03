# Run and Deploy the Vani Agent with Docker and Kubernetes

This guide walks you through building the container image, pushing it to a registry, running locally with Docker, and deploying to Kubernetes. It also covers how to verify if pods are running correctly.

## Prerequisites
- Docker Desktop installed and running (macOS)
- kubectl installed and configured to your cluster (for Kubernetes steps)
- A container registry account (e.g., Docker Hub or GHCR) where you can push images
- OpenAI API key

## Environment configuration
- Create a local `.env` file (never commit secrets). Example:
  
  OPENAI_API_KEY="sk-..."
  
  Optional GitHub integration (only if you plan to use repo operations):
  
  GITHUB_TOKEN="ghp_..."  
  GITHUB_DEFAULT_VISIBILITY="private"  
  GITHUB_DEFAULT_ORG=""  
  GITHUB_DEFAULT_PROTOCOL="ssh"
  
- Note: `.env` is ignored by Git and Docker (see .gitignore/.dockerignore). You must pass env vars explicitly to the container at runtime.

## Build the Docker image
1. Ensure Docker Desktop is running.
2. From the project root, build the image:
   
   docker build -t vani-agent:latest .

## Push the image to a registry
Choose a registry and image name. Examples:
- Docker Hub: docker.io/<your-username>/vani-agent:latest
- GitHub Container Registry (GHCR): ghcr.io/<your-username-or-org>/vani-agent:latest

Steps:
1. Log in to your registry (example for Docker Hub):
   
   docker login

2. Tag the image for your registry:
   
   docker tag vani-agent:latest docker.io/<your-username>/vani-agent:latest

3. Push the image:
   
   docker push docker.io/<your-username>/vani-agent:latest

For GHCR:
- Log in: echo "<your-ghcr-token>" | docker login ghcr.io -u <your-username> --password-stdin
- Tag: docker tag vani-agent:latest ghcr.io/<your-username-or-org>/vani-agent:latest
- Push: docker push ghcr.io/<your-username-or-org>/vani-agent:latest

## Run locally with Docker (microphone caveat on macOS)
The agent records audio using PortAudio/sounddevice. Microphone passthrough inside Docker on macOS is not straightforward. If you only want to validate the container starts and reads the API key, you can run:

- Run with env var:
  
  docker run --rm -e OPENAI_API_KEY="sk-..." vani-agent:latest

If you need real microphone input, running directly on your host (without Docker) is recommended on macOS:

- Host run:
  
  python3 -m venv .venv && source .venv/bin/activate  
  pip install -r requirements.txt  
  OPENAI_API_KEY="sk-..." python agent.py

## Deploy to Kubernetes
1. Ensure your image is in a registry accessible by the cluster. Edit `k8s.yaml` to set the full image name. For example:
   
   containers:
     - name: vani-agent
       image: docker.io/<your-username>/vani-agent:latest
       imagePullPolicy: IfNotPresent

2. Create the OpenAI API key secret (name must match `openai-secrets` in k8s.yaml):
   
   kubectl create secret generic openai-secrets \
     --from-literal=OPENAI_API_KEY="sk-..."

3. Apply the deployment and service:
   
   kubectl apply -f k8s.yaml

4. Verify pods:
   
   kubectl get pods
   
   kubectl describe pod <pod-name>
   
   kubectl logs <pod-name>

Notes:
- The current agent records audio and does not expose an HTTP server. The `containerPort: 8000` and Service in k8s.yaml are placeholders and not used by the agent code. The pod will start and attempt audio capture. On typical Kubernetes clusters, microphone access is not available; therefore, the agent will not function as intended inside Kubernetes, but the pod health can still be observed.
- If you strictly need to test pod startup/health, leave it as-is. For real audio operation in containers, a Linux host with proper `/dev/snd` access and privileges is required (advanced setup).

## Troubleshooting
- Docker build errors: Ensure Docker Desktop is running. Try `docker info`.
- Image pull errors in Kubernetes: Confirm the image name is correct and the cluster/nodes can access the registry (auth for private registries may be required via imagePullSecrets).
- OpenAI API key errors: Ensure the secret was created and mounted via env (as per k8s.yaml) and that the value is correct.
- Pod CrashLoopBackOff: Check logs for missing env vars or audio device errors.

## Quick command recap
- Build: docker build -t vani-agent:latest .
- Tag: docker tag vani-agent:latest docker.io/<user>/vani-agent:latest
- Push: docker push docker.io/<user>/vani-agent:latest
- Create secret: kubectl create secret generic openai-secrets --from-literal=OPENAI_API_KEY="sk-..."
- Apply: kubectl apply -f k8s.yaml
- Check pods: kubectl get pods; kubectl logs <pod>; kubectl describe <pod>