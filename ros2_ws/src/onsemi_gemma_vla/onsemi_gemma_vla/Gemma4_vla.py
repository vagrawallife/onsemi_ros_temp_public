#!/usr/bin/env python3
"""Gemma 4 VLA demo using an RGB frame supplied by ROS.

Press SPACE to talk. Gemma decides whether it needs to inspect the latest
camera frame exported by the onsemi_gemma_vla ROS frame bridge.
"""

import os
import sys

# Configure runtimes before importing ONNX/Hugging Face packages.
os.environ["ORT_LOG_LEVEL"] = "3"
os.environ["ONNXRUNTIME_LOG_SEVERITY_LEVEL"] = "4"
os.environ["ORT_INTRA_OP_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["HF_HUB_VERBOSITY"] = "error"

import base64
import json
import select
import signal
import subprocess
import termios
import textwrap
import threading
import time
import tty
import urllib.error
import urllib.parse
import urllib.request
import wave

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
LLAMA_URL = os.getenv(
    "LLAMA_URL",
    "http://127.0.0.1:8080/v1/chat/completions",
)
MIC = os.getenv("MIC_DEVICE", "plughw:0,0")
SPK = os.getenv("SPK_DEVICE", "")
VOICE = os.getenv("VOICE", "af_jessica")

# The ROS frame bridge atomically updates this JPEG file.
FRAME_PATH = os.getenv("FRAME_PATH", "/tmp/gemma/latest.jpg")
CAMERA_FRAME_MAX_AGE_SEC = float(
    os.getenv("CAMERA_FRAME_MAX_AGE_SEC", "5")
)
LLAMA_WAIT_TIMEOUT_SEC = float(os.getenv("LLAMA_WAIT_TIMEOUT_SEC", "120"))

AUDIO_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "audio_prompts",
)
BGM_PATH = os.path.join(AUDIO_DIR, "bgm.wav")

VOL_VOICE, VOL_BGM, VOL_DUCK = "39321", "32768", "6553"

CY, BL, DM, MG, GR, YL, WH, BD, R = (
    "\033[96m",
    "\033[94m",
    "\033[90m",
    "\033[95m",
    "\033[92m",
    "\033[93m",
    "\033[97m",
    "\033[1m",
    "\033[0m",
)

SYSTEM = (
    "You are a helpful assistant running locally on a Jetson Orin Nano Super. "
    "You can inspect the robot's latest RGB camera frame through the "
    "look_and_answer tool. If the user asks about something physical or visual, "
    "call look_and_answer. Otherwise answer directly. Keep it brief, using one "
    "to three sentences, and match the user's language. When asked to identify "
    "the left or right object, answer from the camera's viewpoint unless the "
    "user explicitly requests another viewpoint. If the image is unclear, say so."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "look_and_answer",
            "description": (
                "Inspect the latest RGB frame published by the robot's ROS camera "
                "and answer a visual question."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "What to inspect in the current camera frame.",
                    }
                },
                "required": ["question"],
            },
        },
    }
]

PROMPTS = {
    "hello": "Hello, I am Gemma Four. I run locally on this Jetson robot.",
    "capturing_analyzing": "Capturing and analyzing image.",
    "understanding": "I'm understanding what I saw.",
}

stt = None
tts = None
bgm_proc = None
bgm_sink = None
bgm_on = False


# -----------------------------------------------------------------------------
# Audio playback and background music
# -----------------------------------------------------------------------------
def play_wav(path, vol=VOL_VOICE, wait=True):
    command = ["paplay"]
    if SPK:
        command.append(f"--device={SPK}")
    command.extend([f"--volume={vol}", path])

    if wait:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if result.returncode != 0 and result.stderr:
            print(f"  {YL}Audio playback warning: {result.stderr.strip()}{R}")
        return None

    return subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def bgm_vol(vol):
    if not bgm_sink:
        return
    try:
        subprocess.run(
            ["pactl", "set-sink-input-volume", bgm_sink, str(vol)],
            capture_output=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def bgm_start():
    global bgm_proc, bgm_sink, bgm_on

    bgm_kill()
    if not os.path.exists(BGM_PATH):
        return

    bgm_on = True

    def loop():
        global bgm_proc, bgm_sink

        while bgm_on:
            if bgm_proc is None or bgm_proc.poll() is not None:
                bgm_proc = play_wav(BGM_PATH, vol=VOL_BGM, wait=False)
                time.sleep(0.2)
                try:
                    output = subprocess.check_output(
                        ["pactl", "list", "short", "sink-inputs"],
                        text=True,
                        timeout=2,
                    )
                    for line in output.strip().splitlines():
                        parts = line.split()
                        if len(parts) >= 2:
                            bgm_sink = parts[0]
                except (OSError, subprocess.SubprocessError):
                    bgm_sink = None
            time.sleep(0.5)

    threading.Thread(target=loop, daemon=True).start()


def bgm_kill():
    global bgm_on, bgm_proc, bgm_sink

    bgm_on = False
    if bgm_proc and bgm_proc.poll() is None:
        bgm_proc.kill()
        bgm_proc.wait()
    bgm_proc = None
    bgm_sink = None


def play_prompt(name):
    path = os.path.join(AUDIO_DIR, f"{name}.wav")
    if not os.path.exists(path):
        return
    bgm_vol(VOL_DUCK)
    play_wav(path, wait=True)
    bgm_vol(VOL_BGM)


def speak(text):
    import soundfile

    pcm, sample_rate = tts.create(text[:500], voice=VOICE, speed=1.1)
    output_path = "/tmp/vla_tts.wav"
    soundfile.write(output_path, pcm, sample_rate)
    bgm_vol(VOL_DUCK)
    play_wav(output_path, wait=True)
    bgm_vol(VOL_BGM)


# -----------------------------------------------------------------------------
# STT and TTS initialization
# -----------------------------------------------------------------------------
def load_all():
    global stt, tts

    import kokoro_onnx
    import onnx_asr
    import onnxruntime as ort
    from huggingface_hub import hf_hub_download

    def status(message, step, total=4):
        bar = "█" * step + "░" * (total - step)
        sys.stdout.write(f"\r  {DM}[{bar}] {message}{R}    ")
        sys.stdout.flush()

    status("Loading STT engine...", 1)

    # These environment variables are applied by ONNX Runtime. The options below
    # document the intended low-thread behavior for future custom sessions.
    session_options = ort.SessionOptions()
    session_options.graph_optimization_level = (
        ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    )
    session_options.intra_op_num_threads = 1
    session_options.inter_op_num_threads = 1
    session_options.add_session_config_entry(
        "session.intra_op.allow_spinning",
        "0",
    )

    stt = onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v3")

    status("Loading TTS engine...", 2)
    model_path = hf_hub_download("fastrtc/kokoro-onnx", "kokoro-v1.0.onnx")
    voices_path = hf_hub_download("fastrtc/kokoro-onnx", "voices-v1.0.bin")
    tts = kokoro_onnx.Kokoro(model_path, voices_path)

    status("Generating prompts...", 3)
    os.makedirs(AUDIO_DIR, exist_ok=True)
    metadata_path = os.path.join(AUDIO_DIR, "meta.json")
    wanted = {"voice": VOICE, "prompts": PROMPTS}

    try:
        with open(metadata_path, encoding="utf-8") as stream:
            current = json.load(stream)
    except (OSError, json.JSONDecodeError):
        current = {}

    if current != wanted:
        import soundfile

        for name, prompt_text in PROMPTS.items():
            pcm, sample_rate = tts.create(
                prompt_text,
                voice=VOICE,
                speed=1.1,
            )
            soundfile.write(
                os.path.join(AUDIO_DIR, f"{name}.wav"),
                pcm,
                sample_rate,
            )
        with open(metadata_path, "w", encoding="utf-8") as stream:
            json.dump(wanted, stream, indent=2)

    status("Checking ROS camera frame...", 4)
    frame_status = get_frame_status()
    if frame_status:
        print(f"\n  {YL}Camera warning: {frame_status}{R}")
    else:
        status("Ready!", 4)
        print()


# -----------------------------------------------------------------------------
# Recording: SPACE -> talk -> SPACE
# -----------------------------------------------------------------------------
def record():
    if not sys.stdin.isatty():
        print("  Interactive recording requires a TTY. Use --text mode instead.")
        return False

    print(f"\n  {DM}Press SPACE to start recording, SPACE again to stop.{R}\n")
    old_settings = termios.tcgetattr(sys.stdin)

    try:
        tty.setcbreak(sys.stdin.fileno())

        while True:
            character = sys.stdin.read(1)
            if character == "\x03":
                raise KeyboardInterrupt
            if character == " ":
                break

        termios.tcflush(sys.stdin, termios.TCIFLUSH)
        bgm_vol(VOL_DUCK)

        for path in ("/tmp/vla.pcm", "/tmp/vla.wav"):
            if os.path.exists(path):
                os.remove(path)

        process = subprocess.Popen(
            [
                "arecord",
                "-D",
                MIC,
                "-t",
                "raw",
                "-f",
                "S16_LE",
                "-r",
                "16000",
                "-c",
                "1",
                "/tmp/vla.pcm",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        start_time = time.time()
        print(
            f"  {MG}● REC  {DM}(press SPACE to stop){R}        ",
            end="\r",
            flush=True,
        )

        while True:
            ready, _, _ = select.select([sys.stdin], [], [], 0.1)
            if not ready:
                continue
            character = sys.stdin.read(1)
            if character == "\x03":
                raise KeyboardInterrupt
            if character == " ":
                break

        if process.poll() is None:
            process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

        duration = time.time() - start_time
        print(" " * 60, end="\r")

        if (
            duration < 0.3
            or not os.path.exists("/tmp/vla.pcm")
            or os.path.getsize("/tmp/vla.pcm") < 1024
        ):
            print(f"  {DM}Too short; try again.{R}")
            return False

        with open("/tmp/vla.pcm", "rb") as stream:
            raw_audio = stream.read()

        with wave.open("/tmp/vla.wav", "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(raw_audio)

        print(f"  {DM}Recorded {duration:.1f}s{R}")
        return True

    finally:
        termios.tcsetattr(
            sys.stdin,
            termios.TCSADRAIN,
            old_settings,
        )


def transcribe():
    if (
        not os.path.exists("/tmp/vla.wav")
        or os.path.getsize("/tmp/vla.wav") < 1024
    ):
        return ""
    return (stt.recognize("/tmp/vla.wav") or "").strip()


# -----------------------------------------------------------------------------
# ROS-owned RGB camera frame
# -----------------------------------------------------------------------------
def get_frame_status():
    if not os.path.isfile(FRAME_PATH):
        return (
            f"No ROS RGB frame found at {FRAME_PATH}. Start the frame_bridge "
            "and verify GEMMA_RGB_TOPIC."
        )

    try:
        age = time.time() - os.path.getmtime(FRAME_PATH)
        size = os.path.getsize(FRAME_PATH)
    except OSError as error:
        return f"Cannot inspect ROS RGB frame: {error}"

    if size < 1024:
        return f"ROS RGB frame is too small ({size} bytes)."
    if age > CAMERA_FRAME_MAX_AGE_SEC:
        return (
            f"ROS RGB frame is stale ({age:.1f}s old; maximum allowed is "
            f"{CAMERA_FRAME_MAX_AGE_SEC:.1f}s)."
        )
    return None


def take_photo():
    """Read and base64-encode the latest JPEG exported by the ROS bridge."""
    status = get_frame_status()
    if status:
        print(f"  {YL}{status}{R}")
        return None

    try:
        with open(FRAME_PATH, "rb") as stream:
            jpeg = stream.read()
    except OSError as error:
        print(f"  {YL}Unable to read ROS RGB frame: {error}{R}")
        return None

    if not jpeg.startswith(b"\xff\xd8"):
        print(f"  {YL}ROS RGB frame is not a JPEG image.{R}")
        return None

    return base64.b64encode(jpeg).decode("ascii")


# -----------------------------------------------------------------------------
# llama-server client
# -----------------------------------------------------------------------------
def wait_for_llama_server():
    """Wait until the OpenAI-compatible llama-server endpoint is reachable."""
    deadline = time.time() + LLAMA_WAIT_TIMEOUT_SEC
    parsed_url = urllib.parse.urlsplit(LLAMA_URL)
    health_url = urllib.parse.urlunsplit(
        (parsed_url.scheme, parsed_url.netloc, "/health", "", "")
    )

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=3) as response:
                if 200 <= response.status < 300:
                    return True
        except (urllib.error.URLError, TimeoutError):
            time.sleep(2)

    return False


def llm(messages, tools=None):
    body = {
        "model": "gemma4",
        "messages": messages,
        "max_tokens": 500,
        "temperature": 0.4,
        "thinking": {"type": "disabled"},
    }
    if tools:
        body["tools"] = tools

    request = urllib.request.Request(
        LLAMA_URL,
        json.dumps(body).encode("utf-8"),
        {"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"llama-server returned HTTP {error.code}: {details}"
        ) from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Cannot reach llama-server at {LLAMA_URL}: {error}") from error

    message = payload["choices"][0]["message"]
    message["content"] = (
        message.get("content")
        or message.get("reasoning_content")
        or ""
    )

    timings = payload.get("timings") or {}
    return message, timings.get("predicted_per_second", 0)


# -----------------------------------------------------------------------------
# VLA agent
# -----------------------------------------------------------------------------
def agent(question):
    print(f"  {MG}Thinking...{R}")

    if not bgm_on:
        bgm_start()
    else:
        bgm_vol(VOL_BGM)

    message, tokens_per_second = llm(
        [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": question},
        ],
        tools=TOOLS,
    )

    if not message.get("tool_calls"):
        print(f"  {DM}Done; {tokens_per_second:.0f} tok/s{R}")
        return message["content"].strip()

    function = message["tool_calls"][0].get("function", {})
    try:
        arguments = json.loads(function.get("arguments", "{}"))
    except json.JSONDecodeError:
        arguments = {}

    visual_question = arguments.get("question", "Describe what you see.")
    print(f"  {CY}Gemma decided to inspect the ROS camera frame.{R}")
    play_prompt("capturing_analyzing")
    bgm_vol(VOL_BGM)
    print(f"  {MG}Capturing and analyzing...{R}")

    image_base64 = take_photo()
    if not image_base64:
        return (
            "I could not obtain a fresh RGB frame from the robot camera. "
            "Please check the ROS camera topic and frame bridge."
        )

    visual_message, _ = llm(
        [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            visual_question
                            + " Answer in one to three short sentences. "
                            + "If choosing between left and right, use the camera's "
                            + "viewpoint. If uncertain, explicitly say unclear."
                        ),
                    },
                ],
            }
        ]
    )

    print(f"  {DM}Done{R}")
    return visual_message["content"].strip()


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main():
    text_mode = "--text" in sys.argv
    width = 62

    print(f"\n  {BL}{'▄' * width}{R}")
    print(
        f"""
{BD}{CY}   ██████  ███████ ███    ███ ███    ███  █████      ██   ██
  ██       ██      ████  ████ ████  ████ ██   ██     ██   ██
  ██   ███ █████   ██ ████ ██ ██ ████ ██ ███████     ███████
  ██    ██ ██      ██  ██  ██ ██  ██  ██ ██   ██          ██
   ██████  ███████ ██      ██ ██      ██ ██   ██          ██{R}
"""
    )
    print(
        f"  {YL}{'Jetson robot · ROS RGB camera · 100% local':^{width}}{R}"
    )
    print(f"  {BL}{'▀' * width}{R}\n")

    if not wait_for_llama_server():
        print(
            f"  {YL}llama-server did not become ready at {LLAMA_URL} within "
            f"{LLAMA_WAIT_TIMEOUT_SEC:.0f}s.{R}"
        )
        return 1

    if not text_mode:
        start_time = time.time()
        load_all()
        separator = "─" * width
        print(f"  {DM}{separator}{R}")
        print(
            f"  {DM}STT: Parakeet 0.6B · TTS: Kokoro 82M · "
            f"LLM: Gemma 4 E2B · {time.time() - start_time:.0f}s{R}"
        )
        print(f"  {DM}{separator}{R}\n")
        play_prompt("hello")
        print(
            f"  {CY}{BD}[ SPACE ]{R} {DM}Talk to Gemma   "
            f"{CY}{BD}[ Ctrl+C ]{R} {DM}Quit{R}\n"
        )
    else:
        print(f"  {DM}Text mode; type a question and press Enter.{R}\n")

    while True:
        try:
            if text_mode:
                question = input(f"\n{CY}>{R} ").strip()
                if not question:
                    continue
            else:
                if not record():
                    continue
                print(f"  {DM}Transcribing...{R}")
                question = transcribe()
                if not question:
                    print(f"  {DM}Nothing detected.{R}\n")
                    bgm_vol(VOL_BGM)
                    continue
                print(f"  {BL}{BD}You:{R} {WH}{question}{R}\n")

            try:
                answer = agent(question)
            except RuntimeError as error:
                answer = f"VLA request failed: {error}"

            print(f"\n  {BL}{'─' * width}{R}")
            for line in textwrap.wrap(answer, width=width - 4):
                print(f"  {GR}{BD}  {line}{R}")
            print(f"  {BL}{'─' * width}{R}\n")

            if not text_mode:
                speak(answer)
                print()

        except (KeyboardInterrupt, EOFError):
            bgm_kill()
            print(f"\n\n  {CY}Bye!{R}\n")
            break

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
