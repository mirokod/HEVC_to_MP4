# HEVC_to_MP4

HEVC_to_MP4 is a lightweight local web application for converting HEVC/H.265 video files to MP4 using FFmpeg and NVIDIA GPU acceleration.

The project is designed especially for converting modern HEVC, 10-bit, HDR, or high-resolution video files into more compatible MP4 files that can be played on older devices. It uses NVIDIA NVENC/NVDEC when available, supports batch conversion, audio track selection by language, automatic output folders, configurable target file size, encoder presets, quality options, and resolution downscaling.

The app runs locally in the browser through a small Flask backend and can also be packaged as a standalone Windows executable with bundled FFmpeg and FFprobe, so Python does not need to be installed on the target machine.

---

## Features

* Convert HEVC/H.265 video files to MP4
* NVIDIA GPU acceleration using NVENC/NVDEC
* H.264 MP4 output for better compatibility with older devices
* Batch conversion of entire folders
* Automatic `converted` output folder creation
* Keeps original filenames and changes the extension to `.mp4`
* Audio track selection for single-file conversion
* Preferred audio language selection for batch conversion
* Target output file size control, for example `700M`, `1.5G`, or `2G`
* Quality presets: High, Medium, Low
* Resolution presets: source, max 1080p, max 720p, max 480p
* AAC stereo audio output
* Local browser-based interface
* Can be packaged as a standalone Windows `.exe`

---

## Why this project exists

Many modern video files are encoded as HEVC/H.265, often in 10-bit HDR and high resolutions such as 4K. These files are efficient, but they may not play correctly on older TVs, media players, set-top boxes, or older computers.

This app converts such files into a more compatible MP4 format, typically:

```text
H.264 video
AAC stereo audio
MP4 container
8-bit yuv420p pixel format
Optional downscaling to 1080p or lower
```

This combination is much more likely to work on older devices.

---

## How it works

The application is made of two parts:

```text
Browser UI
    ↓
Local Flask backend
    ↓
FFmpeg / FFprobe
    ↓
NVIDIA GPU acceleration when available
```

The browser interface lets the user choose input files or folders, audio language, encoder settings, quality presets, target file size, and output folder.

The Flask backend builds and runs the correct FFmpeg command.

---

## Recommended project structure

```text
HEVC_to_MP4/
│
├─ app.py
│
├─ templates/
│  └─ index.html
│
└─ ffmpeg/
   ├─ ffmpeg.exe
   └─ ffprobe.exe
```

If `ffmpeg.exe` and `ffprobe.exe` are placed inside the `ffmpeg` folder, the application will use them automatically.

If they are not found, the app will try to use `ffmpeg` and `ffprobe` from the system PATH.

---

## Requirements

### For running from source

* Windows
* Python 3.10 or newer recommended
* Flask
* FFmpeg with NVENC/NVDEC support
* NVIDIA GPU with NVENC/NVDEC support for GPU acceleration
* Recent NVIDIA drivers

Install Python dependencies:

```bash
pip install flask
```

### For running the packaged `.exe`

Python does not need to be installed.

The packaged executable can include:

```text
Python runtime
Flask
Application code
HTML template
ffmpeg.exe
ffprobe.exe
```

The target computer still needs:

* Windows
* NVIDIA drivers
* NVIDIA GPU with NVENC/NVDEC support if GPU acceleration is used
* Microsoft Visual C++ Redistributable if required by the bundled FFmpeg build

Most modern Windows systems already have the required Visual C++ runtime installed.

---

## FFmpeg

This project uses FFmpeg and FFprobe.

For Windows, a full FFmpeg build with NVIDIA support is recommended. The application expects the following files if bundled locally:

```text
ffmpeg/ffmpeg.exe
ffmpeg/ffprobe.exe
```

You can verify NVENC support with:

```bash
ffmpeg -encoders | findstr nvenc
```

Expected encoders include:

```text
h264_nvenc
hevc_nvenc
```

---

## Running from source

Clone or download the project, then open a terminal in the project folder.

```bash
cd HEVC_to_MP4
pip install flask
python app.py
```

The app should automatically open in your browser at:

```text
http://127.0.0.1:5000
```

If it does not open automatically, open that address manually.

---

## Basic usage

### Single-file conversion

1. Select **Single file** mode.
2. Enter the path to the input video file.
3. Click **Load audio tracks**.
4. Select the desired audio track.
5. Choose output settings.
6. Click **Convert**.

Example input path:

```text
C:\Videos\movie.mkv
```

If the output folder is left empty, the output will be saved to:

```text
C:\Videos\converted\movie.mp4
```

---

### Batch conversion

1. Select **Batch folder** mode.
2. Enter the path to a folder containing video files.
3. Enter a preferred audio language code, for example `eng`, `cze`, or `slo`.
4. Choose output settings.
5. Click **Convert**.

The app will process supported video files in the selected folder and save the converted files to a `converted` folder by default.

Example:

```text
Input folder:
C:\Videos\Series

Output files:
C:\Videos\Series\converted\episode_01.mp4
C:\Videos\Series\converted\episode_02.mp4
C:\Videos\Series\converted\episode_03.mp4
```

---

## Supported input extensions

The app currently looks for the following video file extensions in batch mode:

```text
.mkv
.mp4
.avi
.mov
.m4v
.webm
.ts
```

---

## Audio language selection

In single-file mode, audio tracks are loaded with FFprobe and can be selected manually from a dropdown.

In batch mode, the app uses a preferred language code.

Examples:

```text
eng  English
cze  Czech
slo  Slovak
slk  Slovak, alternative ISO code sometimes used by files
ger  German
deu  German, alternative ISO code
fre  French
fra  French, alternative ISO code
spa  Spanish
```

If the preferred language is not found, the first available audio track is used.

---

## Recommended settings for older devices

For maximum compatibility with older TVs, media players, and set-top boxes:

```text
Video encoder: H.264 NVENC - compatible MP4 for older devices
Encoding quality: High or Medium
Resolution: Max 1080p
Target file size: 700M, 900M, 1.5G, or as needed
Audio bitrate: 128 kbps or 192 kbps
```

The compatible H.264 mode uses:

```text
H.264 video
AAC audio
MP4 container
8-bit yuv420p pixel format
High profile
Level 4.1
```

For 4K sources, using **Max 1080p** is recommended because many older devices cannot play 4K H.264 reliably.

---

## Target file size

The target file size field accepts values such as:

```text
700M
700MB
1.5G
1.5GB
2G
```

When a target size is provided, the app calculates the video bitrate automatically based on:

```text
target size
video duration
selected audio bitrate
estimated MP4 container overhead
```

This makes it possible to aim for a specific output size.

For example, for a 54-minute episode and a target size of `700M`, the app calculates the video bitrate that should fit the output close to 700 MB.

Very small target sizes may produce poor quality or fail if the calculated video bitrate is too low.

---

## Quality presets

The app contains three quality presets:

```text
High
Medium
Low
```

For NVIDIA NVENC encoders:

```text
High   -> preset p7, CQ 19
Medium -> preset p5, CQ 23
Low    -> preset p3, CQ 27
```

For libx264 CPU fallback:

```text
High   -> preset slow, CRF 20
Medium -> preset medium, CRF 23
Low    -> preset fast, CRF 27
```

Important note:

If **Target file size** is filled in, the final bitrate is calculated from that target size. In that case, the quality preset mainly affects encoder effort and efficiency.

If **Target file size** is empty, the quality preset directly controls CQ/CRF quality-based encoding.

---

## Resolution presets

The app can downscale input video while preserving aspect ratio.

Available modes:

```text
Source resolution
Max 1080p
Max 720p
Max 480p
```

The default recommended setting is:

```text
Max 1080p
```

The app preserves aspect ratio. For example, a 3840×1920 video is converted to approximately:

```text
1920×960
```

This is expected because the source aspect ratio is 2:1.

---

## Video encoders

### H.264 NVENC - compatible MP4 for older devices

Recommended default.

Uses NVIDIA GPU encoding and produces H.264 MP4 output with compatibility-oriented settings.

Best choice for older devices.

### H.264 NVENC - faster

Uses NVIDIA GPU encoding with faster settings.

Useful when speed is more important than maximum compression efficiency.

### H.264 libx264 - CPU fallback

Uses CPU encoding through libx264.

This can produce excellent quality, but it is much slower and does not use NVIDIA NVENC.

Useful as a fallback if NVENC is unavailable.

### HEVC NVENC

Uses NVIDIA GPU encoding to create HEVC/H.265 output.

This can produce smaller files at similar quality, but compatibility with older devices is much worse.

Not recommended if the goal is playback on older TVs or older media players.

---

## Packaging as a standalone Windows EXE

Install PyInstaller:

```bash
pip install pyinstaller
```

Make sure the project structure is:

```text
HEVC_to_MP4/
│
├─ app.py
│
├─ templates/
│  └─ index.html
│
└─ ffmpeg/
   ├─ ffmpeg.exe
   └─ ffprobe.exe
```

Build the executable:

```bash
pyinstaller --onefile --console --add-data "templates;templates" --add-binary "ffmpeg\ffmpeg.exe;ffmpeg" --add-binary "ffmpeg\ffprobe.exe;ffmpeg" --name HEVC_to_MP4 app.py
```

The output file will be created here:

```text
dist\HEVC_to_MP4.exe
```

Run it:

```bash
dist\HEVC_to_MP4.exe
```

The app should start a local server and open the browser automatically.

---

## Windowed build

After testing the console build, you can create a windowed build without the console window:

```bash
pyinstaller --onefile --windowed --add-data "templates;templates" --add-binary "ffmpeg\ffmpeg.exe;ffmpeg" --add-binary "ffmpeg\ffprobe.exe;ffmpeg" --name HEVC_to_MP4 app.py
```

The console build is recommended for debugging because FFmpeg and Flask errors are easier to see.

---

## Notes about PyInstaller onefile mode

In `--onefile` mode, PyInstaller extracts bundled files to a temporary directory when the executable starts.

This means:

* first startup may take a little longer
* bundled `ffmpeg.exe` and `ffprobe.exe` are extracted at runtime
* the app still runs as a normal local web application
* the browser connects to `http://127.0.0.1:5000`

---

## Testing the packaged EXE

After building the executable, copy only this file somewhere outside the project folder:

```text
dist\HEVC_to_MP4.exe
```

For example, copy it to the Desktop and run it from there.

This helps verify that:

* Python is not required
* templates are bundled correctly
* FFmpeg and FFprobe are bundled correctly
* the app does not depend on files from the source project folder

---

## Troubleshooting

### The browser opens but shows a template error

Make sure the `templates/index.html` file exists and was included in the PyInstaller build with:

```bash
--add-data "templates;templates"
```

### FFmpeg or FFprobe is not found

If running from source, either:

* add FFmpeg to PATH, or
* place `ffmpeg.exe` and `ffprobe.exe` inside the `ffmpeg` folder.

Expected structure:

```text
ffmpeg/ffmpeg.exe
ffmpeg/ffprobe.exe
```

### NVENC encoder is not available

Check whether your FFmpeg build supports NVENC:

```bash
ffmpeg -encoders | findstr nvenc
```

You should see:

```text
h264_nvenc
hevc_nvenc
```

Also make sure NVIDIA drivers are installed.

### H.264 NVENC fails with 10-bit input

Some HEVC sources are 10-bit. H.264 NVENC does not encode 10-bit H.264 output.

The compatible H.264 mode solves this by forcing:

```text
-pix_fmt yuv420p
```

This converts the output to 8-bit 4:2:0, which is better for compatibility.

### H.264 NVENC fails with Invalid Level

This can happen when trying to encode high-resolution video with a low H.264 level, for example 4K video with Level 4.1.

Use the recommended resolution setting:

```text
Max 1080p
```

This downscales 4K sources to a more compatible resolution.

### Output file is too large or too small

Use the **Target file size** field to control output size more directly.

Examples:

```text
700M
1.5G
2G
```

If target size is left empty, output size depends on the selected quality preset.

### Batch mode selects the wrong audio track

Check the language metadata in the input files.

Use single-file mode and click **Load audio tracks** to inspect available language codes.

Then use the matching code in batch mode, for example:

```text
eng
cze
slo
slk
```

### The app does not close with Ctrl+C

If running from a terminal, try:

```bash
Ctrl + Break
```

On Windows, you can also terminate Python processes:

```bash
taskkill /F /IM python.exe
```

For the packaged EXE:

```bash
taskkill /F /IM HEVC_to_MP4.exe
```

---

## Limitations

* The app is currently focused on local Windows usage.
* GPU acceleration requires compatible NVIDIA hardware and drivers.
* HEVC output is less compatible with older devices.
* Target file size mode estimates final size, but exact byte-perfect output size is not guaranteed.
* HDR to SDR tone mapping is not currently handled explicitly.
* Subtitle handling is not currently included in the default conversion flow.
* Batch mode processes files one by one.

---

## Future ideas

Possible future improvements:

* Progress percentage based on FFmpeg time output
* Built-in file/folder picker
* Subtitle selection or subtitle burning
* Optional HDR to SDR tone mapping
* More advanced audio options
* Multiple audio tracks in output
* Custom FFmpeg arguments
* Pause/cancel conversion button
* Better packaged desktop UI
* Cross-platform support

---

## License

GPLv3
due to ffmpeg

---

## Disclaimer

This project is a local utility wrapper around FFmpeg. It does not include any video content and is intended only for converting media files that you have the legal right to process.
