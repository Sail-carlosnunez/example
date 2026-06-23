# OUSTER TAKE HOME PROJECT - COMPLETE IN 1 HOUR
GOAL: USING THE OUSTER-SDK CREATE A TOOL THAT A TRAFFIC OR SECURITY CUSTOMER WOULD USE.


## LiDAR Point Cloud Viewer and Vehicle Counting

How to use the Ouster-SDK to identify, visualize, and count vehicles.

Value proposition to customer: Automated  Vehicle Counter.

![LiDAR Viewer](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Qt](https://img.shields.io/badge/Qt-PyQt6-green.svg)

![detection_player](https://github.com/user-attachments/assets/3aa1de2d-3059-4d78-8605-ab203b24b90e)

## Features

### ✅ Core Functionality
- **PCAP Playback** - Load and play Ouster LiDAR PCAP files
- **JSON Configuration** - Support for Ouster sensor metadata
- **3D Visualization** - Real-time OpenGL-based point cloud rendering
- **Drag & Drop** - Easy file loading via drag and drop
- **Multiple Color Modes**:
  - Reflectivity
  - Range
  - Height
  - Intensity
- **Adjustable Point Size** - Dynamic point size control (1-10 pixels)
- **Playback Controls** - Play, pause, stop, seek, and variable speed (0.25x - 4.0x)

### 🎯 Object Detection
- **Human Detection** - Height-based clustering (1.5-2.2m tall, narrow profile)
- **Vehicle Detection** - Size-based detection with PCA orientation
- **Configurable Parameters**:
  - Enable/disable detection types
  - Adjustable confidence threshold
- **3D Bounding Boxes** - Visual overlay of detected objects
- **Real-time Statistics** - Detection counts and point cloud info

### 🚀 Performance
- **Frame Caching** - Fast frame navigation
- **Efficient Rendering** - Optimized OpenGL visualization
- **Non-Maximum Suppression** - Reduces overlapping detections

### Running the Application

```bash
python main.py
```

Or make it executable:

```bash
chmod +x main.py
./main.py
```
After running main.py you should get
venv or any direct should work fine.
![mainpy_startup](https://github.com/user-attachments/assets/6ca52194-a383-4652-84e8-b0efb29b7a59)


### Loading Files

#### Method 1: Drag & Drop
1. Drag your `.pcap` file into the application window
2. Drag your `.json` sensor config file into the window
3. Files will load automatically

#### Method 2: File Dialogs
1. Click "Load PCAP" button to select your PCAP file
2. Click "Load JSON" button to select your JSON configuration
3. Both files must be loaded for playback to work

### Controls
![UI](https://github.com/user-attachments/assets/766ae740-a946-42a5-aa59-717ae5e37021)

#### Visualization Panel
- **Color Mode**: Choose how points are colored
  - Reflectivity: Based on surface reflectivity
  - Range: Distance from sensor
  - Height: Z-coordinate value
  - Intensity: Signal intensity
- **Point Size**: Adjust size of rendered points (1-10)

#### Object Detection Panel
- **Enable Detection**: Toggle object detection on/off
- **Detect Humans**: Enable human detection algorithm
- **Detect Vehicles**: Enable vehicle detection algorithm
- **Min Confidence**: Set minimum confidence threshold (0-1)

#### Playback Controls
- **Play/Pause**: Start or pause playback
- **Stop**: Stop playback and return to first frame
- **Frame Slider**: Manually navigate to specific frame
- **Speed**: Adjust playback speed (0.25x to 4.0x)

### 3D Viewer Navigation
- **Rotate**: Left-click and drag
- **Pan**: Middle-click and drag (or Shift + Left-click)
- **Zoom**: Scroll wheel (or Right-click and drag)

## File Formats

### PCAP Files
Standard packet capture files containing Ouster LiDAR data. These should be recorded using Ouster Studio or the Ouster SDK.

### JSON Configuration
Sensor metadata file containing:
- Sensor model and serial number
- Beam configuration
- Calibration parameters
- Operation mode

Example JSON structure:
```json
{
  "sensor_info": {
    "prod_line": "OS-1-64",
    "lidar_mode": "1024x10",
    "beam_altitude_angles": [...],
    "beam_azimuth_angles": [...]
  }
}
```

## Detection Algorithms

### Human Detection
- **Height-based clustering**: Filters points between 1.5-2.2m height
- **Profile analysis**: Looks for narrow vertical profiles
- **Minimum points**: Requires at least 30 points
- **DBSCAN clustering**: Groups nearby points (eps=0.5m)

### Vehicle Detection
- **Size-based filtering**: 
  - Length: 2.5-8.0m
  - Width: 1.5-3.0m
  - Height: 1.0-3.5m
- **PCA orientation**: Estimates vehicle orientation
- **Rectangular profile**: Prefers rectangular shapes
- **Minimum points**: Requires at least 50 points

### Detection Tuning
Confidence scores are calculated based on:
- Number of points in cluster
- Shape characteristics
- Dimensional constraints
- Profile analysis

## Project Structure

```
lidar_viewer/
├── main.py                     # Application entry point
├── pyproject.toml             # Dependencies and build config
├── ui/
│   ├── __init__.py
│   ├── main_window.py         # Main Qt window with controls
│   └── point_cloud_viewer.py  # 3D OpenGL viewer widget
├── core/
│   ├── __init__.py
│   ├── pcap_player.py         # PCAP file reader and processor
│   └── detector.py            # Object detection algorithms
└── README.md
```

## Development

### Code Style
- Black formatter (line length: 100)
- Ruff linter
- Type hints encouraged

### Adding Custom Detectors

To add a new detector class:

1. Create a detector class in `core/detector.py`:
```python
class CustomDetector:
    def detect(self, xyz: np.ndarray) -> List[Dict[str, Any]]:
        # Your detection logic
        return detections
```

2. Add it to `DetectionManager`:
```python
self.custom_detector = CustomDetector()
```

3. Add UI controls in `ui/main_window.py`

## Future Enhancements

- [ ] Manual annotation tool for ground truth labeling
- [ ] Export annotations to training formats (KITTI, COCO, etc.)
- [ ] Point cloud filtering (ground removal, ROI selection)
- [ ] Multiple PCAP file support
- [ ] Recording and export capabilities
- [ ] Advanced detection algorithms (deep learning)
- [ ] Track objects across frames
- [ ] Save/load detection configurations

## Troubleshooting

### "No module named 'ouster'"
Install the ouster-sdk: `pip install ouster-sdk`

### Slow Performance
- Reduce point size
- Disable detection when not needed
- Close other applications
- Reduce playback speed

### PCAP Won't Load
- Ensure JSON config matches the PCAP sensor
- Check that files aren't corrupted
- Verify Ouster SDK compatibility

### OpenGL Errors
- Update graphics drivers
- Try reducing point cloud density
- Check OpenGL version: `python -c "from OpenGL.GL import *; print(glGetString(GL_VERSION))"`

## License

MIT License - Feel free to use and modify

## Acknowledgments

- Ouster SDK for LiDAR data processing
- PyQtGraph for 3D visualization
- PyQt6 for the GUI framework

## Contributing

Contributions welcome! Please feel free to submit issues and pull requests.

## Contact

For questions or support, please open an issue on the repository.
