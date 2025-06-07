# LoveSpouse BLE Script Player

This project provides a BLE control server for LoveSpouse devices with script playback functionality. It allows you to control your device using predefined scripts with precise timing.

## Features

- Control LoveSpouse devices via Bluetooth Low Energy (BLE)
- Play scripts with precise timing control
- Pause, resume, and stop script playback
- Web interface for easy script management
- Support for different toy modes (shock1, shock2, shake, telescope)
- Compatible with the Milovana EOS userscript

## Requirements

- Windows 10/11 with Bluetooth support
- Python 3.7+
- Web browser (Chrome, Firefox, Edge, etc.)

## Installation

1. Make sure you have Python 3.7 or higher installed
2. Install required Python packages:
   ```
   pip install winsdk
   ```

## Usage

### Starting the Server

Run the server script:

```
python lovespouse_server.py
```

The server will start on port 8080 by default.

### Using the Web Interface

1. Open `script_player.html` in your web browser
2. Select the toy mode from the dropdown menu
3. Paste your script JSON in the text area or click "Load Sample Script"
4. Click "Load Script" to load the script
5. Use the Start, Pause, and Stop buttons to control playback

### Script Format

Scripts should be in JSON format with the following structure:

```json
{
  "actions": [
    {"at": 0, "pos": 20},
    {"at": 500, "pos": 40},
    {"at": 1000, "pos": 60}
  ],
  "metadata": {
    "title": "Script Title",
    "duration": 5,
    "description": "Script description"
  },
  "range": 100,
  "version": "1.0"
}
```

- `at`: Timestamp in milliseconds
- `pos`: Position/intensity value (0-100)

### HTTP API Endpoints

The server provides the following HTTP endpoints:

#### Basic Control

- `POST /lovespouse`: Control the device directly
  - Body: `{"mode": "shake", "submode": 5, "duration": 1.0}`

#### Script Control

- `POST /lovespouse/script/load`: Load a script
  - Body: Script JSON
  - Headers: `X-Toy-Mode` (optional, defaults to "shake")

- `GET /lovespouse/script?action=start`: Start or resume script playback
- `GET /lovespouse/script?action=pause`: Pause script playback
- `GET /lovespouse/script?action=stop`: Stop script playback
- `GET /lovespouse/script?action=status`: Get script playback status

## Integration with Milovana EOS

This server is compatible with the LoveSpouseEOS userscript for Milovana. The userscript sends commands to this server to control your device based on the content in Milovana teases.

## Troubleshooting

- Make sure Bluetooth is enabled on your computer
- Ensure your device is charged and within range
- Check that no other applications are using the device
- Verify that the server is running (check for the "LoveSpouse BLE control server running" message)
- If you encounter connection issues, try restarting the server and/or your device

## License

GPLv3
