# LoveSpouse Script Player

A minimal web-based player for funscript files with video synchronization and BLE toy control.

## Features

- Load and play funscript files synchronized with video playback
- Control BLE toys based on funscript actions ("Shake" mode only)
- Robust client-side scheduling: device actions stay tightly synchronized with video playback, even with delays, seeks, or pauses
- Minimal UI: relies solely on the native HTML5 video controls
- Single file input for both video and funscript (both must be selected at once)
- Server only handles immediate device commands; all scheduling and sync is client-side

## Setup

1. Make sure you have Python installed with the required packages:
   - `winsdk` for Bluetooth LE communication
   - Standard Python libraries

2. Run the server:
   ```
   python lovespouse_server.py
   ```

3. Open a web browser and navigate to:
   ```
   http://localhost:8080
   ```

## Usage

### Loading Files

1. Only "Shake" mode is available (other modes are disabled)
2. Use the file input to select both a video file and a funscript file at the same time
   - Both files must be selected together; the UI will reset if only one is chosen

### Playback & Synchronization

- Use the native video player's controls to play, pause, seek, or stop
- Device actions are scheduled and fired on the client, always synced to the current video time
- Scheduler polls every 100ms and only schedules the next 5 seconds of actions, ensuring robust sync even with playback delays or seeks
- All scheduled actions are cleared and resynced on file change, pause, seek, or end

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
- Check the browser console for error information

## License

GPLv3
