# Cyclops Docker Instance

### Building Image

```bash
./build.sh [-n|--name container_name]
```
Default container name is `cyclops`

### Starting Instance
```bash
./start.sh [-n|--name container-name] [-b|-bind address:port] [-d|--data-root local/data/path]
```

## One Shot
```bash
cd docker
./build.sh
./start.sh
```
Docker instance will start to run at local port 9090 for interface 127.0.0.1