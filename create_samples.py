import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import soundfile as sf
import cv2

os.makedirs("sample_data", exist_ok=True)

# 1. Create Sample Image
print("Creating sample image...")
img = Image.new("RGB", (800, 600), color=(30, 41, 59))
draw = ImageDraw.Draw(img)
# Draw geometric shapes and patterns for ELA variance
draw.rectangle([50, 50, 750, 150], fill=(15, 23, 42), outline=(56, 189, 248), width=3)
draw.text((70, 80), "TRUTHLENS FORENSIC VERIFICATION TARGET", fill=(248, 250, 252))
draw.text((70, 110), "Date: 2026-05-18 | Location: Bangalore Headquarters", fill=(148, 163, 184))

# Insert high-frequency pattern simulating localized alteration
for i in range(100, 400, 20):
    draw.line([(i, 250), (i + 150, 450)], fill=(244, 63, 94), width=2)
draw.ellipse([450, 250, 650, 450], fill=(16, 185, 129), outline=(255, 255, 255), width=2)

img.save("sample_data/sample_image.jpg", "JPEG", quality=95)

# 2. Create Sample Audio (3 seconds, 44.1kHz, dual tone voice simulation)
print("Creating sample audio...")
sr = 44100
duration = 3.0
t = np.linspace(0, duration, int(sr * duration), endpoint=False)
# Formant frequencies typical of human speech (300Hz, 1200Hz, 2500Hz) with natural decay
audio_signal = (
    0.4 * np.sin(2 * np.pi * 320 * t) +
    0.25 * np.sin(2 * np.pi * 1250 * t) +
    0.15 * np.sin(2 * np.pi * 2400 * t)
)
# Add amplitude envelope
envelope = np.exp(-t * 0.5)
audio_signal = (audio_signal * envelope).astype(np.float32)
sf.write("sample_data/sample_audio.wav", audio_signal, sr)

# 3. Create Sample Video (3 seconds, 24 FPS, 640x480)
print("Creating sample video...")
fps = 24.0
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter("sample_data/sample_video.mp4", fourcc, fps, (640, 480))
for frame_i in range(int(fps * 3)):
    f = np.zeros((480, 640, 3), dtype=np.uint8)
    f[:] = (20, 20, 35) # Dark navy background
    # Moving indicator
    x = int(50 + (frame_i * 8) % 500)
    cv2.circle(f, (x, 240), 40, (0, 180, 240), -1)
    ts = frame_i / fps
    cv2.putText(f, f"TruthLens Test Stream - Time: {ts:.2f}s", (30, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(f, f"Frame #{frame_i}", (30, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (148, 163, 184), 1)
    out.write(f)
out.release()

# 4. Create Sample Text Files
print("Creating sample text files...")
with open("sample_data/transcript_contradiction.txt", "w", encoding="utf-8") as f:
    f.write("Official field transcript: The executive conference occurred in Chennai on Monday with 45 delegates present. Security confirmed no breaches occurred during the sessions.")

with open("sample_data/transcript_corroborating.txt", "w", encoding="utf-8") as f:
    f.write("Intelligence brief: High-level discussions were held in Bangalore on Monday regarding regional digital infrastructure and cybersecurity protocols.")

print("All sample files generated successfully in sample_data/")
