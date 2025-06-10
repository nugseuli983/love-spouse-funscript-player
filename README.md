# LoveSpouse Script Player

A web-based player for funscript files with video synchronization and BLE toy control.

## Features

- Load and play funscript files
- Synchronize script playback with video playback
- Control BLE toys based on script actions
- Support for multiple toy modes (shake, shock1, shock2, telescope)
- Video player with time display and progress bar
- Automatic matching of script and video files with the same name

## Setup

1. Make sure you have Python installed with the required packages:
   - `winsdk` for Bluetooth LE communication
   - Standard Python libraries

2. Create a `videos` folder in the same directory as the server script (this will be created automatically when the server starts)

3. Run the server:
   ```
   python lovespouse_server.py
   ```

4. Open a web browser and navigate to:
   ```
   http://localhost:8080
   ```

## Usage

### Loading Files

1. Select a toy mode from the dropdown menu (shake, shock1, shock2, or telescope)
2. Click "Choose Video File" to load a video
3. Click "Choose Funscript File" to load a funscript
   - If you load a funscript first, the system will look for a video with the same name
   - If you load a video first, the system will look for a funscript with the same name

### Playback Controls

- **Play/Pause Button**: Toggles between play and pause states
- **Stop Button**: Stops playback and resets to the beginning
- **Video Player**: Standard HTML5 video controls for seeking, volume, etc.

### Synchronization

When both a video and script are loaded:

1. The script playback will automatically synchronize with the video playback
2. The "Video Sync" indicator will turn green when synchronization is active
3. When you seek in the video, the script will automatically adjust to the new position
4. Pausing the video will also pause the script

## File Format

The script player supports funscript files with the following format:

```json
{
  "actions": [
    {"at": 1000, "pos": 50},
    {"at": 2000, "pos": 80},
    ...
  ],
  "metadata": {
    "title": "Example Script",
    "duration": 60,
    ...
  }
}
```

Where:
- `at`: Timestamp in milliseconds
- `pos`: Position value (0-100) that determines the intensity of the toy action

## Toy Control

The `pos` value in the funscript is mapped to intensity levels (0-9) for the toy:

- 0-10: Level 0
- 11-21: Level 1
- 22-32: Level 2
- ...and so on

## Troubleshooting

- If you encounter Bluetooth connection issues, make sure your toy is powered on and in pairing mode
- If the script doesn't sync properly with the video, try reloading both files
- Check the log messages at the bottom of the page for error information

## License

GPLv3
