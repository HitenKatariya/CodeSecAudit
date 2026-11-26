#!/usr/bin/env python3
"""CodeSecAudit AI — Automated Screen Recording & System Showcase CLI.

Runs end-to-end with a visual terminal progress bar, mouse cursor capture,
and outputs the exact MP4 video file location upon completion.

Usage:
    python3 scripts/record_showcase_cli.py
"""

import os
import signal
import subprocess
import sys
import time
from playwright.sync_api import sync_playwright

OUTPUT_DIR = "/home/omchoksi/workspace/CodeSecurityAuditAgent"
OUTPUT_VIDEO = os.path.join(OUTPUT_DIR, "CodeSecAudit_Full_System_Showcase.mp4")
PLAYWRIGHT_DIR = os.path.join(OUTPUT_DIR, "videos")
DISPLAY = os.environ.get("DISPLAY", ":99")
USE_XVFB = True  # Ensures consistent 1920x1080 resolution across all window managers

TOTAL_STEPS = 16
CURRENT_STEP = 0

def print_progress(step_name: str, step_index: int = None):
    global CURRENT_STEP
    if step_index is not None:
        CURRENT_STEP = step_index
    else:
        CURRENT_STEP += 1
    
    percent = min(100, int((CURRENT_STEP / TOTAL_STEPS) * 100))
    bar_width = 30
    filled = int(bar_width * (percent / 100))
    bar = "█" * filled + "░" * (bar_width - filled)
    sys.stdout.write(f"\r\033[1;36m[{bar}] {percent:>3}% \033[0m| \033[1;32m{step_name:<50}\033[0m")
    sys.stdout.flush()

def smooth_mouse_move(start_x, start_y, end_x, end_y, steps=15, delay=0.01, env=None):
    for i in range(steps + 1):
        x = int(start_x + (end_x - start_x) * (i / steps))
        y = int(start_y + (end_y - start_y) * (i / steps))
        subprocess.run(f"xdotool mousemove {x} {y}", shell=True, env=env, check=False)
        time.sleep(delay)

def main():
    os.makedirs(PLAYWRIGHT_DIR, exist_ok=True)
    print("\n" + "="*70)
    print("  🛡️  CodeSecAudit AI — Full System Video Showcase Generator")
    print("="*70 + "\n")

    xvfb_proc = None
    target_display = DISPLAY
    
    # Clean previous processes on :99 if using Xvfb
    if USE_XVFB:
        target_display = ":99"
        subprocess.run("killall Xvfb 2>/dev/null || true", shell=True)
        time.sleep(1)
        print_progress("Initializing 1080p display buffer (Xvfb :99)...", 1)
        xvfb_proc = subprocess.Popen(["Xvfb", target_display, "-screen", "0", "1920x1080x24"])
        time.sleep(2)

    env = os.environ.copy()
    env["DISPLAY"] = target_display
    env["GDK_BACKEND"] = "x11"
    subprocess.run("xsetroot -solid '#0f172a' 2>/dev/null || true", shell=True, env=env)

    # Start ffmpeg recorder with mouse cursor capture
    print_progress("Starting high-resolution video capture engine (ffmpeg)...", 2)
    rec_cmd = [
        "ffmpeg", "-y",
        "-f", "x11grab",
        "-draw_mouse", "1",
        "-framerate", "25",
        "-video_size", "1920x1080",
        "-i", f"{target_display}.0",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-movflags", "+frag_keyframe+empty_moov+default_base_moof",
        OUTPUT_VIDEO
    ]
    rec_proc = subprocess.Popen(rec_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=[
                    f"--display={target_display}",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--start-maximized",
                    "--window-size=1920,1080",
                    "--window-position=0,0",
                ]
            )
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                device_scale_factor=1,
                record_video_dir=PLAYWRIGHT_DIR,
                record_video_size={"width": 1920, "height": 1080},
            )
            page = context.new_page()

            # Step 3: Core Architecture Code - engine.py
            print_progress("Showcasing Architecture: engine.py (Security Rules)", 3)
            page.goto("https://github.com/HitenKatariya/CodeSecAudit/blob/main/main-server/app/reviews/engine.py", wait_until="domcontentloaded", timeout=25000)
            time.sleep(1.5)
            smooth_mouse_move(400, 300, 900, 500, steps=15, env=env)
            page.mouse.wheel(0, 600)
            time.sleep(1.5)

            # Step 4: Core Architecture Code - report_formatter.py
            print_progress("Showcasing Architecture: report_formatter.py", 4)
            page.goto("https://github.com/HitenKatariya/CodeSecAudit/blob/main/main-server/app/reviews/report_formatter.py", wait_until="domcontentloaded", timeout=25000)
            time.sleep(1.5)
            page.mouse.wheel(0, 500)
            time.sleep(1.5)

            # Step 5: Remediated Bug-Free Code
            print_progress("Showcasing Remediated Code: payment_service.py", 5)
            page.goto("https://github.com/HitenKatariya/CodeSecAudit/blob/main/main-server/app/services/payment_service.py", wait_until="domcontentloaded", timeout=25000)
            time.sleep(1.5)
            page.mouse.wheel(0, 400)
            time.sleep(1.5)

            # Step 6: PR #13 Lifecycle (Severe PR Block)
            print_progress("Showcasing PR #13: Security Gate Evaluation", 6)
            page.goto("https://github.com/HitenKatariya/CodeSecAudit/pull/13", wait_until="domcontentloaded", timeout=25000)
            time.sleep(1.5)
            smooth_mouse_move(500, 300, 800, 600, steps=15, env=env)
            page.mouse.wheel(0, 900)
            time.sleep(2)
            page.mouse.wheel(0, 1600)
            time.sleep(2)
            page.mouse.wheel(0, 2000)
            time.sleep(2)
            page.mouse.wheel(0, -4500)
            time.sleep(1.5)

            # Step 7: PR #14
            print_progress("Showcasing PR #14 (CVSS Evaluation)", 7)
            page.goto("https://github.com/HitenKatariya/CodeSecAudit/pull/14", wait_until="domcontentloaded", timeout=25000)
            time.sleep(1.5)
            smooth_mouse_move(700, 350, 900, 600, steps=15, env=env)
            page.mouse.wheel(0, 800)
            time.sleep(2)

            # Step 8: PR #15
            print_progress("Showcasing PR #15 (Clean Security Verification)", 8)
            page.goto("https://github.com/HitenKatariya/CodeSecAudit/pull/15", wait_until="domcontentloaded", timeout=25000)
            time.sleep(1.5)
            smooth_mouse_move(600, 350, 850, 600, steps=15, env=env)
            page.mouse.wheel(0, 800)
            time.sleep(2)

            # Step 9-16: CodeSecAudit Web Application Tour
            base_url = "https://codesec-client-v6a6.onrender.com"

            print_progress("Touring Web App: /dashboard", 9)
            page.goto(f"{base_url}/dashboard", wait_until="domcontentloaded", timeout=25000)
            time.sleep(1.5)
            smooth_mouse_move(400, 300, 850, 450, steps=15, env=env)
            page.mouse.wheel(0, 400)
            time.sleep(1.5)

            print_progress("Touring Web App: /pull-requests", 10)
            page.goto(f"{base_url}/pull-requests", wait_until="domcontentloaded", timeout=25000)
            time.sleep(1.5)
            smooth_mouse_move(400, 300, 750, 500, steps=15, env=env)
            page.mouse.wheel(0, 500)
            time.sleep(1.5)

            print_progress("Touring Web App: /findings", 11)
            page.goto(f"{base_url}/findings", wait_until="domcontentloaded", timeout=25000)
            time.sleep(1.5)
            smooth_mouse_move(500, 350, 850, 550, steps=15, env=env)
            page.mouse.wheel(0, 500)
            time.sleep(1.5)

            print_progress("Touring Web App: /trends", 12)
            page.goto(f"{base_url}/trends", wait_until="domcontentloaded", timeout=25000)
            time.sleep(1.5)
            smooth_mouse_move(700, 400, 1100, 500, steps=15, env=env)
            page.mouse.wheel(0, 500)
            time.sleep(1.5)

            print_progress("Touring Web App: /reports", 13)
            page.goto(f"{base_url}/reports", wait_until="domcontentloaded", timeout=25000)
            time.sleep(1.5)
            smooth_mouse_move(600, 400, 900, 450, steps=15, env=env)
            page.mouse.wheel(0, 500)
            time.sleep(1.5)

            print_progress("Touring Web App: /policies", 14)
            page.goto(f"{base_url}/policies", wait_until="domcontentloaded", timeout=25000)
            time.sleep(1.5)
            smooth_mouse_move(600, 450, 1000, 550, steps=15, env=env)
            page.mouse.wheel(0, 500)
            time.sleep(1.5)

            print_progress("Touring Web App: /team (Connected Members)", 15)
            page.goto(f"{base_url}/team", wait_until="domcontentloaded", timeout=25000)
            time.sleep(1.5)
            smooth_mouse_move(500, 350, 850, 450, steps=15, env=env)
            page.mouse.wheel(0, 400)
            time.sleep(1.5)

            print_progress("Touring Web App: /integrations & /settings", 16)
            page.goto(f"{base_url}/integrations", wait_until="domcontentloaded", timeout=25000)
            time.sleep(1.5)
            page.goto(f"{base_url}/settings", wait_until="domcontentloaded", timeout=25000)
            time.sleep(1.5)

            context.close()
            browser.close()

    finally:
        # Finalize ffmpeg recording cleanly
        rec_proc.send_signal(signal.SIGINT)
        try:
            rec_proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            rec_proc.terminate()
            rec_proc.wait()

        if xvfb_proc:
            xvfb_proc.terminate()
            try:
                xvfb_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                xvfb_proc.kill()

    print("\n" + "="*70)
    if os.path.exists(OUTPUT_VIDEO) and os.path.getsize(OUTPUT_VIDEO) > 10000:
        size_mb = os.path.getsize(OUTPUT_VIDEO) / (1024 * 1024)
        print("  🎉 SUCCESS! VIDEO SHOWCASE SUCCESSFULLY GENERATED")
        print("="*70)
        print(f"\n  📍 Video Location : \033[1;32m{OUTPUT_VIDEO}\033[0m")
        print(f"  📊 File Size      : \033[1;33m{size_mb:.2f} MB\033[0m")
        print(f"  🎬 Format         : 1080p Full HD (1920x1080), 25 fps, H.264 MP4")
        print(f"  📁 Playwright Raw : {PLAYWRIGHT_DIR}/\n")
    else:
        # Check if playwright video is available
        pw_files = [f for f in os.listdir(PLAYWRIGHT_DIR) if f.endswith(".webm") or f.endswith(".mp4")]
        if pw_files:
            latest = os.path.join(PLAYWRIGHT_DIR, pw_files[-1])
            size_mb = os.path.getsize(latest) / (1024 * 1024)
            print(f"  📍 Video Location : \033[1;32m{latest}\033[0m ({size_mb:.2f} MB)")
        else:
            print("  ⚠️  Notice: Video encoding finished. Check:", OUTPUT_DIR)
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
