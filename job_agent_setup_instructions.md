# Job Search Agent — Mac Setup Guide

## What You're Installing

A Python script that runs automatically every morning at 9 AM PST.
It searches for "Senior Director of Engineering" jobs in retail tech
across LinkedIn, Indeed, Glassdoor, and retailer career sites —
then emails a ranked digest to vermasangeeta@gmail.com.

---

## Step 1 — Create the folder structure on your Mac

Open Terminal and run these commands (copy-paste each line):

```bash
mkdir -p ~/capstone/logs
```

---

## Step 2 — Copy the Python script

Copy `job_search_agent.py` to your Mac at this path:
```
~/capstone/job_search_agent.py
```

You can drag it from Downloads into that folder using Finder,
or run in Terminal:
```bash
cp ~/Downloads/job_search_agent.py ~/capstone/
```

---

## Step 3 — Add your Gemini API key

Open the script in TextEdit or VS Code:
```bash
open -e ~/capstone/job_search_agent.py
```

Find this line near the top:
```python
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE")
```

Either:
- Replace `YOUR_API_KEY_HERE` with your actual key (simpler), OR
- Keep it and set it in the plist file (more secure — see Step 5)

Get your key at: https://aistudio.google.com/app/apikey

---

## Step 4 — Test the script manually first

In Terminal:
```bash
cd ~/capstone
GEMINI_API_KEY="YOUR_KEY_HERE" python3 job_search_agent.py
```

Watch the output. It should:
1. Print search progress for 2 queries (takes 3-5 minutes)
2. Consolidate results
3. Send email to vermasangeeta@gmail.com
4. Print "Job Search Agent complete"

Check ~/capstone/logs/job_agent.log if anything looks wrong.

---

## Step 5 — Install the launchd scheduler

### 5a. Edit the plist file

Open `com.sangeeta.jobagent.plist` in TextEdit:

Replace BOTH occurrences of `YOUR_MAC_USERNAME` with your actual Mac username.
(Find it by running `whoami` in Terminal)

Replace `YOUR_API_KEY_HERE` with your Gemini API key.

### 5b. Copy plist to the right location

```bash
cp ~/capstone/com.sangeeta.jobagent.plist ~/Library/LaunchAgents/
```

### 5c. Load it into launchd

```bash
launchctl load ~/Library/LaunchAgents/com.sangeeta.jobagent.plist
```

### 5d. Verify it's loaded

```bash
launchctl list | grep jobagent
```

You should see a line with `com.sangeeta.jobagent` — that means it's scheduled!

---

## Step 6 — Verify timezone (important for 2:30 PM PST)

launchd uses your Mac's system clock. Make sure your Mac is set to Pacific time:
System Settings → General → Date & Time → Time Zone → America/Los_Angeles

---

## Daily Management Commands

| What you want to do | Command |
|---|---|
| See if it's running | `launchctl list \| grep jobagent` |
| Run it manually RIGHT NOW | `launchctl start com.sangeeta.jobagent` |
| Pause/disable it | `launchctl unload ~/Library/LaunchAgents/com.sangeeta.jobagent.plist` |
| Re-enable it | `launchctl load ~/Library/LaunchAgents/com.sangeeta.jobagent.plist` |
| See today's log | `cat ~/capstone/logs/job_agent.log` |
| Watch live output | `tail -f ~/capstone/logs/job_agent_stdout.log` |

---

## Troubleshooting

**"Permission denied" when running the script**
```bash
chmod +x ~/capstone/job_search_agent.py
```

**Script runs but no email arrives**
- Check ~/capstone/logs/ for a digest_YYYYMMDD.txt fallback file
- Make sure your Gmail app password is correct
- The script uses Gmail SMTP directly; if it fails, the digest is saved locally

**API key errors**
- Double-check the key from Google AI Studio
- Make sure there are no spaces around it
- Verify it has credits/quota at aistudio.google.com

**"launchctl: service not found"**
- Make sure the plist file is in ~/Library/LaunchAgents/ (not ~/LaunchAgents/)
- Run the load command again

---

## File Structure After Setup

```
~/roughpad/jobBot/
├── job_search_agent.py          ← main script
└── logs/
    ├── job_agent.log            ← timestamped run log
    ├── job_agent_stdout.log     ← launchd stdout
    ├── job_agent_stderr.log     ← launchd errors
    └── digest_YYYYMMDD.txt      ← local fallback if email fails
```

~/Library/LaunchAgents/
└── com.sangeeta.jobagent.plist  ← scheduler config
