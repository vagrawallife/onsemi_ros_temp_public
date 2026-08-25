#!/usr/bin/env python3
import pathlib,re,sys
p=pathlib.Path(sys.argv[1]);s=p.read_text()
marker='WEBCAM    = int(os.getenv("WEBCAM", "0"))'
if marker not in s: raise SystemExit('Expected WEBCAM line not found')
s=s.replace(marker,marker+'\nFRAME_PATH = os.getenv("FRAME_PATH", "/tmp/gemma/latest.jpg")\nCAMERA_FRAME_MAX_AGE_SEC = float(os.getenv("CAMERA_FRAME_MAX_AGE_SEC", "5"))')
lines=[
'def take_photo():',
'    """Read the latest JPEG exported by the ROS camera bridge."""',
'    try:',
'        age = time.time() - os.path.getmtime(FRAME_PATH)',
'        if age > CAMERA_FRAME_MAX_AGE_SEC:',
'            print(f"  Camera frame is stale ({age:.1f}s).")',
'            return None',
'        with open(FRAME_PATH, "rb") as stream:',
'            jpeg = stream.read()',
'        if len(jpeg) < 1024 or not jpeg.startswith(b"\xff\xd8"):',
'            print("  Camera frame is invalid.")',
'            return None',
'        return base64.b64encode(jpeg).decode("ascii")',
'    except OSError as error:',
'        print(f"  Unable to read ROS camera frame: {error}")',
'        return None',
]
replacement='\n'.join(lines)+'\n'
s,n=re.subn(r'def take_photo\(\):.*?(?=\n## .*LLM call)',replacement,s,flags=re.S)
if n != 1: raise SystemExit(f'Expected one take_photo function, found {n}')
p.write_text(s)
