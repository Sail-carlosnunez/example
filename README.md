# AxleScan

Axle & (optional) pedestrian detection on Ouster PCAP + JSON metadata.  
Generates a portable **HTML report** plus CSV/Parquet tables and PNG thumbnails.

Run it **in Docker** (recommended) or **locally in a Python venv** (for development).

---

## TL;DR (Docker)

```bash
# From repo root (~/sail)
sudo docker build -t axlescan:latest .

# Ensure an output folder exists and is writable by your user
mkdir -p results && sudo chown -R $(id -u):$(id -g) results

# Run with your data (adjust paths)
sudo docker run --rm -it \
  -u $(id -u):$(id -g) \
  -v "/home/<you>/ouster_raw_data:/data:ro" \
  -v "$PWD/results:/results" \
  axlescan:latest \
  scan --pcap /data/Urban_Drive.pcap --meta /data/Urban_Drive.json \
       --out /results/demo --frames 120

Note: the image’s ENTRYPOINT is axlescan. Show help with:
sudo docker run --rm axlescan:latest --help
sudo docker run --rm axlescan:latest scan --help

Repo Layout (relevant bits)
sail/
├─ Dockerfile
├─ .dockerignore
├─ pyproject.toml           # build-system only (setuptools)
├─ setup.cfg                # package metadata + console_script (axlescan = axlescan.cli:main)
├─ perception/
│  └─ time_of_flight_lidar/
│     └─ ouster_lidar/
│        └─ axlescan/
│           ├─ __init__.py
│           ├─ __main__.py
│           ├─ cli.py       # argparse CLI with main()
│           ├─ pipeline.py
│           ├─ detect.py, track.py, render.py, report.py, reader.py, ...
└─ tools/

Build the Docker Image
cd ~/sail
sudo docker build -t axlescan:latest .
The image includes:

Python 3.11

ouster-sdk + OpenGL runtime (libgl1-mesa-glx) for decoding PCAPs

This repo installed as a CLI: axlescan

Run with Your Data
A) Data in WSL (Ubuntu)
# Example data directory in WSL:
ls -lh /home/<you>/ouster_raw_data
# Urban_Drive.pcap
# Urban_Drive.json

# Output will land in ./results/demo on the host
mkdir -p results && sudo chown -R $(id -u):$(id -g) results

sudo docker run --rm -it \
  -u $(id -u):$(id -g) \
  -v "/home/<you>/ouster_raw_data:/data:ro" \
  -v "$PWD/results:/results" \
  axlescan:latest \
  scan --pcap /data/Urban_Drive.pcap --meta /data/Urban_Drive.json \
       --out /results/demo --frames 120

B) Save Outputs to Your Windows Desktop
# Replace placeholders
WIN_DESK="/mnt/c/Users/<WindowsUser>/Desktop/axlescan_results"
DATA="/home/<you>/ouster_raw_data"

mkdir -p "$WIN_DESK"

sudo docker run --rm -it \
  -u $(id -u):$(id -g) \
  -v "$DATA:/data:ro" \
  -v "$WIN_DESK:/results" \
  axlescan:latest \
  scan --pcap /data/Urban_Drive.pcap --meta /data/Urban_Drive.json \
       --out /results/demo --frames 120

Open the report at:
C:\Users\<WindowsUser>\Desktop\axlescan_results\demo\report.html

Quick Network Health (netcheck)
sudo docker run --rm -it \
  -v "/home/<you>/ouster_raw_data:/data:ro" \
  -v "$PWD/results:/results" \
  axlescan:latest \
  netcheck --pcap /data/Urban_Drive.pcap --out /results/netcheck_demo

Opening the Report

Windows: double-click the HTML path above

WSL: wslview ~/sail/results/demo/report.html

Serve locally:
cd ~/sail/results/demo
python -m http.server 8000
# browse http://localhost:8000/report.html

Live-Code Dev Loop (Optional)

Run your mounted source without rebuilding the image:
sudo docker run --rm -it \
  -v "$PWD:/app" \
  -v "$PWD/results:/results" \
  --workdir /app \
  --entrypoint python \
  axlescan:latest \
  -m axlescan \
  scan --pcap perception/time_of_flight_lidar/ouster_lidar/data/raw/Urban_Drive.pcap \
       --meta perception/time_of_flight_lidar/ouster_lidar/data/raw/Urban_Drive.json \
       --out /results/dev_run --frames 60

Local (Non-Docker) Usage (Developers)
python -m venv .venv
source .venv/bin/activate
pip install -e .
axlescan scan --pcap /path/to/file.pcap --meta /path/to/meta.json --out results/local_run
Docker and venv are separate: when using Docker, the container is your isolated environment.

Troubleshooting

ouster.sdk unavailable … libGL.so.1
The image must include OpenGL runtime. Our Dockerfile installs libgl1-mesa-glx. Rebuild:
sudo docker build --no-cache -t axlescan:latest .
The CLI uses flags (not positional args):
axlescan scan --pcap /data/Urban_Drive.pcap --meta /data/Urban_Drive.json ...
“Permission denied” writing to /results
Ensure the host folder exists and is writable by your user:
mkdir -p results && sudo chown -R $(id -u):$(id -g) results
Or run the container as your UID/GID:
-u $(id -u):$(id -g)

Windows :Zone.Identifier sidecar files
Safe to ignore; they will not be read by the CLI.

Inspect inside the container
sudo docker run --rm axlescan:latest --help
sudo docker run --rm axlescan:latest scan --help
sudo docker run --rm axlescan:latest python -c "import ouster.sdk; print('ouster-sdk OK')"
sudo docker run --rm -v "/abs/path/to/data:/data:ro" axlescan:latest ls -lh /data

License
MIT