# Custom n8n Docker Image Instructions

## Overview

Since n8n v1.101.1 is not loading custom nodes from the N8N_CUSTOM_EXTENSIONS directory, we need to use a custom Docker image with the nodes pre-installed.

## Building the Custom Image

1. **Navigate to the n8n directory**:
   ```bash
   cd /home/manesha/AI_Legal/Aletheia-v0.1/n8n
   ```

2. **Build the custom image**:
   ```bash
   docker build -f Dockerfile.custom -t aletheia/n8n-custom:latest .
   ```

## Using the Custom Image

1. **Update docker-compose.yml**:
   
   Replace:
   ```yaml
   n8n:
     image: n8nio/n8n:latest
   ```
   
   With:
   ```yaml
   n8n:
     image: aletheia/n8n-custom:latest
   ```

2. **Remove the custom node volume mount** (no longer needed):
   
   Remove this line from volumes:
   ```yaml
   - ./n8n/custom-nodes:/home/node/.n8n/custom
   ```

3. **Restart the service**:
   ```bash
   docker compose down n8n
   docker compose up -d n8n
   ```

## Verifying Custom Nodes

After starting with the custom image:

1. **Check logs**:
   ```bash
   docker compose logs n8n | grep -E "(n8n-init|Loading|custom|node)"
   ```

2. **Access n8n UI**:
   - Navigate to http://localhost:8080/n8n/
   - Check if custom nodes appear in the node palette
   - Workflows should activate without "Unrecognized node type" errors

## Updating Custom Nodes

When you need to update custom nodes:

1. Make changes to the node source code
2. Rebuild the node: `npm run build`
3. Rebuild the Docker image: `docker build -f Dockerfile.custom -t aletheia/n8n-custom:latest .`
4. Restart n8n: `docker compose restart n8n`

## Troubleshooting

### If nodes still don't appear:

1. **Check the build logs**:
   ```bash
   docker build -f Dockerfile.custom -t aletheia/n8n-custom:latest . --progress=plain
   ```

2. **Verify nodes are installed in the image**:
   ```bash
   docker run --rm aletheia/n8n-custom:latest ls -la /usr/local/lib/node_modules/n8n/node_modules/ | grep n8n-nodes-
   ```

3. **Check package.json in the image**:
   ```bash
   docker run --rm aletheia/n8n-custom:latest cat /usr/local/lib/node_modules/n8n/node_modules/n8n-nodes-haystack/package.json
   ```

## Alternative: Using npm link

If the Dockerfile approach doesn't work, you can try installing nodes directly in a running container:

```bash
# Enter the container
docker compose exec -u root n8n bash

# Install each custom node
cd /home/node/.n8n/custom/n8n-nodes-haystack
npm install --production
npm link
cd /usr/local/lib/node_modules/n8n
npm link n8n-nodes-haystack

# Repeat for other nodes...

# Exit and restart
exit
docker compose restart n8n
```

## Benefits of Custom Image

1. **Reliability**: Nodes are guaranteed to be available
2. **Performance**: No runtime installation needed
3. **Consistency**: Same environment across deployments
4. **Version Control**: Image can be tagged and versioned

## Next Steps

1. Build the custom image
2. Test with a simple workflow
3. Verify all custom nodes are recognized
4. Document any additional configuration needed