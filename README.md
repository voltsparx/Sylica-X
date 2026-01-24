# Silica-X ⚡

**Silica-X** is an advanced OSINT username scanner, inspired by Sherlock, developed in Python.  
It can scan multiple platforms, gather public info (bios, links), correlate results, generate HTML reports, and supports proxy/Tor anonymization.

---

## Disclaimer

- **Legal Use Only:** Silica-X is intended **solely for educational purposes, cybersecurity research, and authorized OSINT investigations**.  
- **User Responsibility:** You are responsible for complying with all local laws and regulations regarding data collection, privacy, and online scanning.  
- **No Liability:** The developer is **not responsible** for misuse, damages, or legal consequences resulting from unauthorized scanning or data collection.  
- **Ethical Use:** Only scan usernames/accounts you have permission to analyze or those publicly available for research.  

---

## Features

- **Contact Extraction:** Collect emails and phone numbers found on public profiles.
- **Live Dashboard:** Launch a live HTML dashboard (`live <username>`) to visualize scan results interactively in the browser.
- **Tor & Proxy Anonymization:** Configure Tor and HTTP proxy for anonymous scanning, improving privacy and security.
- **Async Scanning:** Faster scans using asynchronous requests across all platforms.
- **Enhanced Confidence Scoring:** Bio and contact information now contribute to reliability/confidence percentage.
- **Correlation Analysis:** Detect bios appearing on multiple platforms to uncover linked accounts.
- **Improved HTML Reports:** Detailed reports now include bios, public links, and collected contacts for each platform.
- **Clear Screen Functionality:** Console display is cleaned before each run for professional presentation.
- **Verbose Console Logging:** Each platform scan logs FOUND / NOT FOUND / ERROR with color-coded output.
- **Fully Editable Banner:** ASCII banner shows current anonymity status dynamically.
- **Error Handling:** Graceful handling of missing platforms, network errors, or invalid usernames.

---

## Key Changes / Enhancements

- **Contact Extraction:** Emails and phone numbers are now collected from profile pages.
- **Live HTML Dashboard:** Launch a live interactive dashboard with `live <username>`.
- **Tor & Proxy Support:** Configure anonymized scanning; both Tor and HTTP proxy supported.
- **Async Scanning:** All platform requests are asynchronous for faster execution.
- **Enhanced Confidence Scoring:** Bios and contacts increase confidence scores.
- **Correlation Analysis:** Detect bios appearing on multiple platforms.
- **Improved HTML Reports:** Reports now include bios, links, emails, phones, and correlations.
- **Verbose Console Output:** Each platform scan shows FOUND / NOT FOUND / ERROR with color.
- **Clear Screen Functionality:** Terminal is cleared before each run and on `clear` command.
- **Professional Banner:** Shows current anonymity status dynamically.

---

## New Commands

- `scan <username>` → Scan a username across all platforms.
- `anonymity` → Configure Tor and Proxy settings interactively.
- `clear` → Clear the terminal screen and refresh banner.
- `live <username>` → Launch a live HTML dashboard for username scan results.
- `help` → Show updated help menu with new commands.
- `exit` → Quit Silica-X.

## Features

- Scan multiple platforms (GitHub, Twitter, Instagram, Facebook, Reddit, YouTube, TikTok, StackOverflow, GitLab, Twitch)
- Display results in terminal with color
- Rich optional display
- Cross-platform correlation
- Confidence scoring + explanation
- HTML report generation per username
- Proxy/Tor support (interactive)
- Fully editable ASCII banner
- Async scanning for speed
- Results saved in `output/<username>/` as JSON + HTML

---

## Installation

```
bash
git clone https://github.com/voltsparx/Silica-X.git
cd Silica-X
pip install -r requirements.txt
```

---

## Usage

```terminal
python silica-x.py
```

### Available commands in console

```
- `scan <username>` → Scan a username across all supported platforms.
- `anonymity` → Configure Tor and Proxy settings interactively.
- `clear` → Clear the terminal screen and refresh the ASCII banner.
- `live <username>` → Launch the live HTML dashboard for the specified username.
- `help` → Display the updated help menu with all commands.
- `exit` → Quit Silica-X safely.
```

---

## Tor Setup

 1. Make sure Tor service is running (Tor Browser or Tor daemon)
 2. Set environment variable to enable Tor

### Linux / macOS
```bash
export TOR_ENABLED=1
```

### Windows 
```powershell
setx TOR_ENABLED 1
```

---

## Proxy Setup

 1. Set your HTTP proxy URL
 Example: "http://127.0.0.1:8080"

### Linux / macOS
```bash
export HTTP_PROXY="http://127.0.0.1:8080"
```

### Windows 
```powershell
setx HTTP_PROXY "http://127.0.0.1:8080"
```

---

## Notes

  **Username Rules:** Usernames must not contain spaces. Invalid usernames will be rejected.
- **Tor/Proxy Usage:**  
  - Tor requires the environment variable `TOR_ENABLED` to be set.  
  - Proxy requires `HTTP_PROXY` to be set.  
  - If either is requested but not configured, Silica-X will display an error in red and disable anonymization.
- **Live Dashboard:** The `live <username>` command opens the dashboard automatically in your default browser.
- **Reports:**  
  - JSON and HTML reports are saved under `output/<username>/`.  
  - HTML reports include bios, links, emails, phone numbers, and correlation analysis.  
- **Clear Screen:** Use the `clear` command to tidy the terminal, which also refreshes the banner with current anonymity status.
- **Confidence Scores:** Scores reflect platform reliability, public bio presence, and collected contact info.
- **Error Handling:** Any platform errors (network issues, invalid URLs, timeouts) are logged with `ERROR` status without stopping the scan.
- **Async Scanning:** All platform checks run asynchronously for faster execution.

---

=======
## Uses

```
python silica-x.py
```

## Author 

voltsparx

Contact: voltsparx@gmail.com or phanfronix@gmail.com

GitHub: https://github.com/voltsparx/Silica-X
