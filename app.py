from flask import Flask, render_template, request, jsonify
from pathlib import Path
import subprocess
import json
import threading
import uuid
import sys
import time
import webbrowser


def resource_path(relative_path):
    """
    Returns the correct path both when running from source
    and when bundled with PyInstaller.
    """
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).parent / relative_path


app = Flask(
    __name__,
    template_folder=str(resource_path("templates"))
)

jobs = {}

BUNDLED_FFMPEG = resource_path("ffmpeg/ffmpeg.exe")
BUNDLED_FFPROBE = resource_path("ffmpeg/ffprobe.exe")

FFMPEG = str(BUNDLED_FFMPEG) if BUNDLED_FFMPEG.exists() else "ffmpeg"
FFPROBE = str(BUNDLED_FFPROBE) if BUNDLED_FFPROBE.exists() else "ffprobe"


VIDEO_EXTENSIONS = {
    ".mkv", ".mp4", ".avi", ".mov", ".m4v", ".webm", ".ts"
}


ENCODER_PRESETS = {
    "h264_nvenc_compatible": {
        "label": "H.264 NVENC - compatible MP4 for older devices",
        "codec": "h264_nvenc",
        "profile": "high",
        "level": "4.1",
        "pix_fmt": "yuv420p"
    },
    "h264_nvenc_fast": {
        "label": "H.264 NVENC - faster",
        "codec": "h264_nvenc",
        "profile": "high",
        "level": "4.1",
        "pix_fmt": "yuv420p"
    },
    "libx264_cpu": {
        "label": "H.264 libx264 - CPU fallback",
        "codec": "libx264",
        "profile": "high",
        "level": "4.1",
        "pix_fmt": "yuv420p"
    },
    "hevc_nvenc": {
        "label": "HEVC NVENC - smaller file size, lower compatibility",
        "codec": "hevc_nvenc",
        "profile": "main",
        "level": None,
        "pix_fmt": "yuv420p"
    }
}


QUALITY_PRESETS = {
    "high": {
        "label": "High quality / slower",
        "nvenc_preset": "p7",
        "nvenc_cq": "19",
        "x264_preset": "slow",
        "x264_crf": "20"
    },
    "medium": {
        "label": "Medium quality",
        "nvenc_preset": "p5",
        "nvenc_cq": "23",
        "x264_preset": "medium",
        "x264_crf": "23"
    },
    "low": {
        "label": "Lower quality / faster / smaller file",
        "nvenc_preset": "p3",
        "nvenc_cq": "27",
        "x264_preset": "fast",
        "x264_crf": "27"
    }
}


def run_command(cmd):
    result = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        check=True
    )
    return result.stdout


def probe_file(input_path):
    cmd = [
        FFPROBE,
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        input_path
    ]

    data = json.loads(run_command(cmd))

    audio_streams = []

    for stream in data.get("streams", []):
        if stream.get("codec_type") == "audio":
            tags = stream.get("tags", {})
            audio_streams.append({
                "index": stream.get("index"),
                "codec": stream.get("codec_name", "unknown"),
                "language": tags.get("language", "und"),
                "title": tags.get("title", ""),
                "channels": stream.get("channels", "?")
            })

    duration = float(data["format"]["duration"])

    return {
        "duration": duration,
        "audio_streams": audio_streams
    }


def parse_size_to_mb(size_text):
    """
    Supported examples:
    700M, 700MB, 1.5G, 1.5GB
    """
    s = size_text.strip().upper()

    if s.endswith("GB"):
        return float(s[:-2]) * 1024

    if s.endswith("G"):
        return float(s[:-1]) * 1024

    if s.endswith("MB"):
        return float(s[:-2])

    if s.endswith("M"):
        return float(s[:-1])

    return float(s)


def calculate_video_bitrate_kbps(target_size_mb, duration_seconds, audio_bitrate_kbps):
    """
    Calculates video bitrate from desired total output size.

    total bitrate = target size / duration
    video bitrate = total bitrate - audio bitrate - container overhead
    """
    total_kbits = target_size_mb * 1024 * 8
    total_kbps = total_kbits / duration_seconds

    container_overhead = 0.98
    usable_kbps = total_kbps * container_overhead

    video_kbps = usable_kbps - audio_bitrate_kbps

    if video_kbps < 300:
        raise ValueError(
            "Target file size is too small for this video duration and selected audio bitrate."
        )

    return int(video_kbps)


def build_scale_filter(resolution_mode):
    """
    Keeps aspect ratio and makes height automatically even.
    Example:
    3840x1920 -> 1920x960 for 1080p mode.
    """
    if resolution_mode == "source":
        return None

    if resolution_mode == "1080p":
        return "scale='min(1920,iw)':-2"

    if resolution_mode == "720p":
        return "scale='min(1280,iw)':-2"

    if resolution_mode == "480p":
        return "scale='min(854,iw)':-2"

    return "scale='min(1920,iw)':-2"


def find_audio_stream_by_language_or_first(input_path, preferred_language):
    info = probe_file(input_path)
    audio_streams = info["audio_streams"]

    if not audio_streams:
        raise ValueError("The input file does not contain any audio stream.")

    if preferred_language:
        preferred_language = preferred_language.lower().strip()

        for stream in audio_streams:
            if stream["language"].lower() == preferred_language:
                return stream["index"]

    return audio_streams[0]["index"]


def make_output_path(input_path, output_folder):
    input_path = Path(input_path)

    if output_folder and output_folder.strip():
        out_dir = Path(output_folder)
    else:
        out_dir = input_path.parent / "converted"

    out_dir.mkdir(parents=True, exist_ok=True)

    return str(out_dir / f"{input_path.stem}.mp4")


def build_ffmpeg_command(
    input_path,
    output_path,
    audio_index,
    target_size,
    audio_bitrate,
    encoder_mode,
    quality_mode,
    resolution_mode
):
    info = probe_file(input_path)
    duration = info["duration"]

    encoder_config = ENCODER_PRESETS.get(
        encoder_mode,
        ENCODER_PRESETS["h264_nvenc_compatible"]
    )

    quality_config = QUALITY_PRESETS.get(
        quality_mode,
        QUALITY_PRESETS["medium"]
    )

    codec = encoder_config["codec"]
    use_target_size = bool(target_size and target_size.strip())

    cmd = [
        FFMPEG,
        "-y"
    ]

    if "nvenc" in codec:
        cmd += [
            "-hwaccel", "cuda"
        ]

    cmd += [
        "-i", input_path,
        "-map", "0:v:0",
        "-map", f"0:{audio_index}"
    ]

    scale_filter = build_scale_filter(resolution_mode)

    if scale_filter:
        cmd += [
            "-vf", scale_filter
        ]

    cmd += [
        "-c:v", codec
    ]

    if codec == "h264_nvenc":
        nvenc_preset = quality_config["nvenc_preset"]

        if encoder_mode == "h264_nvenc_fast" and quality_mode == "high":
            # Keeps the "fast" encoder option meaningfully faster
            # even if the user selects High quality.
            nvenc_preset = "p5"

        cmd += [
            "-preset", nvenc_preset,
            "-spatial_aq", "1",
            "-temporal_aq", "1",
            "-pix_fmt", encoder_config["pix_fmt"],
            "-profile:v", encoder_config["profile"],
            "-level:v", encoder_config["level"]
        ]

        if use_target_size:
            target_size_mb = parse_size_to_mb(target_size)
            video_bitrate = calculate_video_bitrate_kbps(
                target_size_mb=target_size_mb,
                duration_seconds=duration,
                audio_bitrate_kbps=int(audio_bitrate)
            )

            cmd += [
                "-rc", "vbr",
                "-b:v", f"{video_bitrate}k",
                "-maxrate", f"{int(video_bitrate * 1.5)}k",
                "-bufsize", f"{int(video_bitrate * 3)}k",
                "-multipass", "fullres"
            ]
        else:
            cmd += [
                "-rc", "vbr",
                "-cq", quality_config["nvenc_cq"],
                "-b:v", "0"
            ]

    elif codec == "hevc_nvenc":
        cmd += [
            "-preset", quality_config["nvenc_preset"],
            "-spatial_aq", "1",
            "-temporal_aq", "1",
            "-pix_fmt", encoder_config["pix_fmt"],
            "-profile:v", encoder_config["profile"]
        ]

        if use_target_size:
            target_size_mb = parse_size_to_mb(target_size)
            video_bitrate = calculate_video_bitrate_kbps(
                target_size_mb=target_size_mb,
                duration_seconds=duration,
                audio_bitrate_kbps=int(audio_bitrate)
            )

            cmd += [
                "-rc", "vbr",
                "-b:v", f"{video_bitrate}k",
                "-maxrate", f"{int(video_bitrate * 1.5)}k",
                "-bufsize", f"{int(video_bitrate * 3)}k",
                "-multipass", "fullres"
            ]
        else:
            cmd += [
                "-rc", "vbr",
                "-cq", quality_config["nvenc_cq"],
                "-b:v", "0"
            ]

    elif codec == "libx264":
        cmd += [
            "-preset", quality_config["x264_preset"],
            "-pix_fmt", encoder_config["pix_fmt"],
            "-profile:v", encoder_config["profile"],
            "-level:v", encoder_config["level"]
        ]

        if use_target_size:
            target_size_mb = parse_size_to_mb(target_size)
            video_bitrate = calculate_video_bitrate_kbps(
                target_size_mb=target_size_mb,
                duration_seconds=duration,
                audio_bitrate_kbps=int(audio_bitrate)
            )

            cmd += [
                "-b:v", f"{video_bitrate}k",
                "-maxrate", f"{int(video_bitrate * 1.5)}k",
                "-bufsize", f"{int(video_bitrate * 3)}k"
            ]
        else:
            cmd += [
                "-crf", quality_config["x264_crf"]
            ]

    else:
        raise ValueError(f"Unsupported video encoder: {codec}")

    cmd += [
        "-c:a", "aac",
        "-b:a", f"{audio_bitrate}k",
        "-ac:a", "2",
        "-movflags", "+faststart",
        output_path
    ]

    return cmd


def run_ffmpeg_job(job_id, files, settings):
    try:
        jobs[job_id]["status"] = "running"
        jobs[job_id]["log"] = ""
        jobs[job_id]["total"] = len(files)
        jobs[job_id]["current"] = 0
        jobs[job_id]["done_files"] = []
        jobs[job_id]["failed_files"] = []

        jobs[job_id]["log"] += "HEVC GPU Converter started.\n"
        jobs[job_id]["log"] += f"FFmpeg path: {FFMPEG}\n"
        jobs[job_id]["log"] += f"FFprobe path: {FFPROBE}\n\n"

        for index, input_path in enumerate(files, start=1):
            jobs[job_id]["current"] = index
            input_path = str(input_path)

            try:
                output_path = make_output_path(
                    input_path,
                    settings.get("output_folder", "")
                )

                audio_index = settings.get("audio_index")

                if audio_index is None or str(audio_index).strip() == "":
                    audio_index = find_audio_stream_by_language_or_first(
                        input_path,
                        settings.get("preferred_language", "")
                    )

                jobs[job_id]["log"] += "\n"
                jobs[job_id]["log"] += "=" * 80 + "\n"
                jobs[job_id]["log"] += f"File {index}/{len(files)}\n"
                jobs[job_id]["log"] += f"Input: {input_path}\n"
                jobs[job_id]["log"] += f"Output: {output_path}\n"
                jobs[job_id]["log"] += f"Audio stream index: {audio_index}\n"
                jobs[job_id]["log"] += f"Encoder mode: {settings.get('encoder_mode')}\n"
                jobs[job_id]["log"] += f"Quality mode: {settings.get('quality_mode')}\n"
                jobs[job_id]["log"] += f"Resolution mode: {settings.get('resolution_mode')}\n"
                jobs[job_id]["log"] += f"Target size: {settings.get('target_size') or 'quality-based'}\n"
                jobs[job_id]["log"] += f"Audio bitrate: {settings.get('audio_bitrate')} kbps\n\n"

                cmd = build_ffmpeg_command(
                    input_path=input_path,
                    output_path=output_path,
                    audio_index=audio_index,
                    target_size=settings.get("target_size", ""),
                    audio_bitrate=settings.get("audio_bitrate", "128"),
                    encoder_mode=settings.get("encoder_mode", "h264_nvenc_compatible"),
                    quality_mode=settings.get("quality_mode", "medium"),
                    resolution_mode=settings.get("resolution_mode", "1080p")
                )

                jobs[job_id]["log"] += "FFmpeg command:\n"
                jobs[job_id]["log"] += " ".join(cmd) + "\n\n"

                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )

                for line in process.stdout:
                    jobs[job_id]["log"] += line

                process.wait()

                if process.returncode == 0:
                    jobs[job_id]["done_files"].append(output_path)
                    jobs[job_id]["log"] += f"\nCompleted: {output_path}\n"
                else:
                    jobs[job_id]["failed_files"].append(input_path)
                    jobs[job_id]["log"] += f"\nFailed: {input_path}\n"

            except Exception as file_error:
                jobs[job_id]["failed_files"].append(input_path)
                jobs[job_id]["log"] += f"\nError while processing file {input_path}: {file_error}\n"

        if jobs[job_id]["failed_files"]:
            jobs[job_id]["status"] = "finished_with_errors"
            jobs[job_id]["log"] += "\nJob finished with errors.\n"
        else:
            jobs[job_id]["status"] = "done"
            jobs[job_id]["log"] += "\nJob completed successfully.\n"

    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["log"] += f"\nFatal error: {e}\n"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/probe", methods=["POST"])
def probe():
    input_path = request.json.get("input_path")

    if not input_path or not Path(input_path).exists():
        return jsonify({"error": "Input file does not exist."}), 400

    try:
        return jsonify(probe_file(input_path))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/convert", methods=["POST"])
def convert():
    data = request.json

    mode = data.get("mode", "single")
    files = []

    if mode == "batch":
        input_folder = data.get("input_folder")

        if not input_folder or not Path(input_folder).exists():
            return jsonify({"error": "Input folder does not exist."}), 400

        input_folder = Path(input_folder)

        files = [
            p for p in input_folder.iterdir()
            if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
        ]

        files.sort(key=lambda p: p.name.lower())

        if not files:
            return jsonify({"error": "No video files were found in the selected folder."}), 400

    else:
        input_path = data.get("input_path")

        if not input_path or not Path(input_path).exists():
            return jsonify({"error": "Input file does not exist."}), 400

        files = [Path(input_path)]

    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "status": "queued",
        "log": "",
        "total": len(files),
        "current": 0,
        "done_files": [],
        "failed_files": []
    }

    settings = {
        "audio_index": data.get("audio_index"),
        "preferred_language": data.get("preferred_language", ""),
        "target_size": data.get("target_size", ""),
        "audio_bitrate": data.get("audio_bitrate", "128"),
        "encoder_mode": data.get("encoder_mode", "h264_nvenc_compatible"),
        "quality_mode": data.get("quality_mode", "medium"),
        "resolution_mode": data.get("resolution_mode", "1080p"),
        "output_folder": data.get("output_folder", "")
    }

    thread = threading.Thread(
        target=run_ffmpeg_job,
        args=(job_id, files, settings),
        daemon=True
    )

    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>")
def status(job_id):
    job = jobs.get(job_id)

    if not job:
        return jsonify({"error": "Job does not exist."}), 404

    return jsonify(job)


def open_browser():
    time.sleep(1)
    webbrowser.open("http://127.0.0.1:5000")


if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        use_reloader=False
    )

