"""Full automated end-to-end screen recording script.

Orchestrates:
1. Xvfb 1920x1080 display with ffmpeg x11grab (mouse cursor visible, fragmented MP4 headers).
2. Playwright dual-recording (built-in video directory + ffmpeg screen grab).
3. VS Code / Codebase Showcase (engine.py, report_formatter.py, payment_service.py).
4. GitHub PRs (#16 blocked -> green synchronize -> merge, PR #17 & #18 by thecenteroftestingpentagon).
5. CodeSecAudit Web Application complete UI tour (Dashboard, PRs, Findings, Trends, Reports, Policies, Team, Integrations, Settings).
"""

import os
import signal
import subprocess
import time
from playwright.sync_api import sync_playwright

OUTPUT_VIDEO = "/home/omchoksi/workspace/CodeSecurityAuditAgent/CodeSecAudit_Full_System_Showcase.mp4"
PLAYWRIGHT_VIDEO_DIR = "/home/omchoksi/workspace/CodeSecurityAuditAgent/videos"
DISPLAY = ":99"

os.makedirs(PLAYWRIGHT_VIDEO_DIR, exist_ok=True)

def run_command(cmd, env=None):
    subprocess.run(cmd, shell=True, env=env, check=False)

def smooth_mouse_move(start_x, start_y, end_x, end_y, steps=15, delay=0.01, env=None):
    for i in range(steps + 1):
        x = int(start_x + (end_x - start_x) * (i / steps))
        y = int(start_y + (end_y - start_y) * (i / steps))
        run_command(f"xdotool mousemove {x} {y}", env=env)
        time.sleep(delay)

def main():
    print("=== Starting Full System Video Recording ===")
    
    # Clean previous processes
    run_command("killall Xvfb 2>/dev/null || true")
    time.sleep(1)

    # 1. Start Xvfb display on :99
    xvfb_proc = subprocess.Popen(["Xvfb", DISPLAY, "-screen", "0", "1920x1080x24"])
    time.sleep(2)
    
    env = os.environ.copy()
    env["DISPLAY"] = DISPLAY
    env["GDK_BACKEND"] = "x11"
    
    # Set dark sleek background
    run_command("xsetroot -solid '#0f172a'", env=env)
    
    # 2. Start ffmpeg recorder with mouse cursor capture and fragmented MP4 flags
    rec_cmd = [
        "ffmpeg", "-y",
        "-f", "x11grab",
        "-draw_mouse", "1",
        "-framerate", "25",
        "-video_size", "1920x1080",
        "-i", f"{DISPLAY}.0",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-movflags", "+frag_keyframe+empty_moov+default_base_moof",
        OUTPUT_VIDEO
    ]
    rec_proc = subprocess.Popen(rec_cmd)
    time.sleep(2)
    
    # Initial cursor placement
    smooth_mouse_move(100, 100, 960, 540, steps=20, env=env)
    time.sleep(1)

    # 3. Launch Playwright for browser interactions
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                f"--display={DISPLAY}",
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
            record_video_dir=PLAYWRIGHT_VIDEO_DIR,
            record_video_size={"width": 1920, "height": 1080},
        )
        page = context.new_page()

        # Scene 1: Codebase & Core Architecture in Editor
        print("Scene 1: Showcasing Core Architecture Code...")
        page.goto("https://github.com/HitenKatariya/CodeSecAudit/blob/main/main-server/app/reviews/engine.py", wait_until="domcontentloaded", timeout=25000)
        time.sleep(1.5)
        smooth_mouse_move(400, 300, 900, 500, steps=15, env=env)
        page.mouse.wheel(0, 700)
        time.sleep(1.5)

        page.goto("https://github.com/HitenKatariya/CodeSecAudit/blob/main/main-server/app/reviews/report_formatter.py", wait_until="domcontentloaded", timeout=25000)
        time.sleep(1.5)
        page.mouse.wheel(0, 600)
        time.sleep(1.5)

        page.goto("https://github.com/HitenKatariya/CodeSecAudit/blob/main/main-server/app/services/payment_service.py", wait_until="domcontentloaded", timeout=25000)
        time.sleep(1.5)
        page.mouse.wheel(0, 400)
        time.sleep(1.5)

        # Scene 2: Showcase GitHub PR #13 (Severe Security Gate)
        print("Scene 2: Showcasing PR #13 Lifecycle...")
        page.goto("https://github.com/HitenKatariya/CodeSecAudit/pull/13", wait_until="domcontentloaded", timeout=25000)
        time.sleep(1.5)
        smooth_mouse_move(500, 300, 800, 600, steps=15, env=env)
        page.mouse.wheel(0, 900)
        time.sleep(2)
        page.mouse.wheel(0, 1600)
        time.sleep(2)
        page.mouse.wheel(0, 2000)
        time.sleep(2.5)
        page.mouse.wheel(0, -4500)
        time.sleep(1.5)

        # Scene 3: Showcase PRs #14 & #15
        print("Scene 3: Showcasing PR #14...")
        page.goto("https://github.com/HitenKatariya/CodeSecAudit/pull/14", wait_until="domcontentloaded", timeout=25000)
        time.sleep(1.5)
        smooth_mouse_move(700, 350, 900, 600, steps=15, env=env)
        page.mouse.wheel(0, 800)
        time.sleep(2)

        print("Scene 3b: Showcasing PR #15...")
        page.goto("https://github.com/HitenKatariya/CodeSecAudit/pull/15", wait_until="domcontentloaded", timeout=25000)
        time.sleep(1.5)
        smooth_mouse_move(600, 350, 850, 600, steps=15, env=env)
        page.mouse.wheel(0, 800)
        time.sleep(2)

        # Scene 4: CodeSecAudit Enterprise Web Application - Complete UI Tour
        base_app_url = "https://codesec-client-v6a6.onrender.com"
        
        # 1. Dashboard
        print("Scene 4.1: Dashboard (/dashboard)...")
        page.goto(f"{base_app_url}/dashboard", wait_until="domcontentloaded", timeout=25000)
        time.sleep(1.5)
        smooth_mouse_move(400, 300, 850, 450, steps=15, env=env)
        page.mouse.wheel(0, 500)
        time.sleep(1.5)
        page.mouse.wheel(0, -500)
        time.sleep(1)

        # 2. Pull Requests View
        print("Scene 4.2: Pull Requests (/pull-requests)...")
        page.goto(f"{base_app_url}/pull-requests", wait_until="domcontentloaded", timeout=25000)
        time.sleep(1.5)
        smooth_mouse_move(400, 300, 750, 500, steps=15, env=env)
        page.mouse.wheel(0, 500)
        time.sleep(1.5)
        page.mouse.wheel(0, -500)
        time.sleep(1)

        # 3. Findings View
        print("Scene 4.3: Findings (/findings)...")
        page.goto(f"{base_app_url}/findings", wait_until="domcontentloaded", timeout=25000)
        time.sleep(1.5)
        smooth_mouse_move(500, 350, 850, 550, steps=15, env=env)
        page.mouse.wheel(0, 500)
        time.sleep(1.5)
        page.mouse.wheel(0, -500)
        time.sleep(1)

        # 4. Trends View
        print("Scene 4.4: Trends (/trends)...")
        page.goto(f"{base_app_url}/trends", wait_until="domcontentloaded", timeout=25000)
        time.sleep(1.5)
        smooth_mouse_move(700, 400, 1100, 500, steps=15, env=env)
        page.mouse.wheel(0, 500)
        time.sleep(1.5)
        page.mouse.wheel(0, -500)
        time.sleep(1)

        # 5. Reports View
        print("Scene 4.5: Compliance & Reports (/reports)...")
        page.goto(f"{base_app_url}/reports", wait_until="domcontentloaded", timeout=25000)
        time.sleep(1.5)
        smooth_mouse_move(600, 400, 900, 450, steps=15, env=env)
        page.mouse.wheel(0, 500)
        time.sleep(1.5)
        page.mouse.wheel(0, -500)
        time.sleep(1)

        # 6. Security Policies View
        print("Scene 4.6: Security Policies (/policies)...")
        page.goto(f"{base_app_url}/policies", wait_until="domcontentloaded", timeout=25000)
        time.sleep(1.5)
        smooth_mouse_move(600, 450, 1000, 550, steps=15, env=env)
        page.mouse.wheel(0, 500)
        time.sleep(1.5)
        page.mouse.wheel(0, -500)
        time.sleep(1)

        # 7. Team Collaborators View
        print("Scene 4.7: Team Collaborators (/team)...")
        page.goto(f"{base_app_url}/team", wait_until="domcontentloaded", timeout=25000)
        time.sleep(1.5)
        smooth_mouse_move(500, 350, 850, 450, steps=15, env=env)
        page.mouse.wheel(0, 400)
        time.sleep(1.5)
        page.mouse.wheel(0, -400)
        time.sleep(1)

        # 8. Integrations View
        print("Scene 4.8: Integrations (/integrations)...")
        page.goto(f"{base_app_url}/integrations", wait_until="domcontentloaded", timeout=25000)
        time.sleep(1.5)
        smooth_mouse_move(600, 400, 950, 550, steps=15, env=env)
        page.mouse.wheel(0, 500)
        time.sleep(1.5)
        page.mouse.wheel(0, -500)
        time.sleep(1)

        # 9. Settings View
        print("Scene 4.9: Settings (/settings)...")
        page.goto(f"{base_app_url}/settings", wait_until="domcontentloaded", timeout=25000)
        time.sleep(1.5)
        smooth_mouse_move(500, 400, 850, 500, steps=15, env=env)
        time.sleep(1.5)

        # Close context to flush Playwright video
        context.close()
        browser.close()

    # 4. Stop recording cleanly
    print("Finalizing video recording...")
    time.sleep(2)
    rec_proc.send_signal(signal.SIGINT)
    try:
        rec_proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        rec_proc.terminate()
        rec_proc.wait()

    xvfb_proc.terminate()
    try:
        xvfb_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        xvfb_proc.kill()

    if os.path.exists(OUTPUT_VIDEO):
        size_mb = os.path.getsize(OUTPUT_VIDEO) / (1024 * 1024)
        print(f"=== Video Successfully Generated: {OUTPUT_VIDEO} ({size_mb:.2f} MB) ===")
    else:
        print("Error: Video file was not created.")

if __name__ == "__main__":
    main()
