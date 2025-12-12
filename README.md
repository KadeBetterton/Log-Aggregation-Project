# Log-Aggregation-Project
Digital Forensics final project, a simple python script and instructions on setup and usage. 
# CloudSec Monitoring Toolkit
This tool is a simple project meant to demonstrate aggregating logging from a Cloud-Hosted virtual environment, as well as simulating malicious intrusion data. Proceed at your own risk especially concerning downloading and hosting DVWA.

Lightweight cloud logging and monitoring lab using:
- AWS Lightsail (Ubuntu)
- DVWA in Docker
- Python log aggregator (`cloudsec_monitor.py`)
- Splunk for offline analysis

---

## 1. System Requirements

**Cloud instance**
- AWS Lightsail Ubuntu 22.04 LTS
- >= 1 vCPU, 1 GB RAM
- ~10 GB disk

**Local machine (Windows)**
- PuTTY and PuTTYgen
- WinSCP
- Splunk Enterprise (local only, free trial is fine)

**Ubuntu dependencies**
- Python 3 and pip  
- Docker  
- `vulnerables/web-dvwa` image  
- `auditd`, `audispd-plugins`  
- `conntrack`

---

## 2. Setup Overview (High Level)

1. Create Ubuntu Lightsail instance.  
2. Configure PuTTY (SSH) and WinSCP (file transfer).  
3. Install Python, Docker, DVWA, auditd, conntrack.  
4. Install `cloudsec_monitor.py`, run it as a systemd service.  
5. Generate DVWA activity and attacks.  
6. Pull `/var/log/cloudsec/*.log` to Windows with WinSCP.  
7. Import logs into Splunk and build dashboards.

---

## 3. Lightsail and SSH Setup

### 3.1 Create Lightsail instance

1. Go to AWS Lightsail and create an instance.  
2. Platform: Linux/Unix.  
3. Blueprint: Ubuntu 22.04 LTS.  
4. Choose cheapest or free tier.  
5. Name it (for example `CloudSec-Demo`).  
6. Download the `.pem` key.  
7. Create the instance.
8. *********IMPORTANT, CONFIGURE YOUR FIREWALL SETTINGS INSIDE THE LIGHTSAIL DASHBOARD TO ONLY ALLOW TRAFFIC TO AND FROM THE IP OF THE MACHINE YOU ARE ACTUALLY WORKING FROM********************
   

### 3.2 Convert `.pem` to `.ppk` (PuTTYgen)

1. Open PuTTYgen.  
2. Click Load and pick your `.pem` key.  
3. Click Save private key.  
4. Save as `lightsail.ppk`.

### 3.3 Connect with PuTTY

1. Open PuTTY.  
2. Host Name: `ubuntu@<Lightsail_Public_IP>`.  
3. In the left tree: Connection -> SSH -> Auth.  
4. Click Browse and select `lightsail.ppk`.  
5. Optional: go back to Session and Save this profile.  
6. Click Open and accept the host key.  
7. You should see a prompt like: `ubuntu@ip-...:~$`.

---

## 4. Prepare Ubuntu Environment

### 4.1 Update and install Python

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip -y
```

### 4.2 Install Docker and DVWA

```bash
sudo apt install docker.io -y
sudo systemctl enable docker
sudo systemctl start docker

sudo docker run -d -p 80:80 --name dvwa vulnerables/web-dvwa
sudo docker ps
```

You should see a container named `dvwa` or similar in the output.

### 4.3 Install auditd and conntrack

```bash
sudo apt install auditd audispd-plugins -y
sudo systemctl enable auditd
sudo systemctl start auditd

sudo apt install conntrack -y
```

---

## 5. CloudSec Script and Service

### 5.1 Create log directory

```bash
sudo mkdir -p /var/log/cloudsec/
sudo touch /var/log/cloudsec-full.log
sudo touch /var/log/cloudsec-alerts.log
sudo chmod 666 /var/log/cloudsec/*.log
```

### 5.2 Get `cloudsec_monitor.py`

From the home directory:

```bash
cd /home/ubuntu
wget https://raw.githubusercontent.com/<YOUR_USER>/<YOUR_REPO>/main/cloudsec_monitor.py
```

Move and make it executable:

```bash
sudo mv /home/ubuntu/cloudsec_monitor.py /usr/local/bin/cloudsec_monitor.py
sudo chmod +x /usr/local/bin/cloudsec_monitor.py
```

Make sure the first line of the file is not blank. It should start with `import` or a shebang.

### 5.3 Create systemd service

Create the service file:

```bash
sudo nano /etc/systemd/system/cloudsec.service
```

Paste:

```ini
[Unit]
Description=Unified Cloud Security Monitoring Service
After=network.target docker.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/local/bin/cloudsec_monitor.py
Restart=always
User=root

[Install]
WantedBy=multi-user.target
```

Save and exit, then reload and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable cloudsec.service
sudo systemctl start cloudsec.service
sudo systemctl status cloudsec.service
```

The service will:
- Monitor syslog, auth logs, auditd, conntrack.  
- Monitor DVWA Docker logs.  
- Write everything to `/var/log/cloudsec-full.log`.  
- Write alert lines with specific keywords to `/var/log/cloudsec-alerts.log`.

---

## 6. DVWA and Attack Simulation

### 6.1 Access DVWA

In your browser go to:

```text
http://<Lightsail_Public_IP>/
```

Default DVWA login:

- Username: `admin`  
- Password: `password`

### 6.2 Example actions and attacks

With `cloudsec.service` running, perform actions in DVWA:

- Log in and log out.  
- Open vulnerabilities:
  - Brute Force  
  - SQL Injection  
  - Command Execution  
  - File Inclusion  
  - XSS pages  
- Example SQL injection:
  - Normal input: `id=1`  
  - Injection: `id=1' OR '1'='1`  

These requests will appear in your logs as lines like:

```text
[dvwa-docker] 98.110.x.x - - [date] "GET /vulnerabilities/sqli/?id=1' OR '1'='1&Submit=Submit HTTP/1.1" 200 ...
```

### 6.3 Confirm aggregated logs

Check the last lines of each log:

```bash
sudo tail -n 20 /var/log/cloudsec-full.log
sudo tail -n 20 /var/log/cloudsec-alerts.log
```

You should see entries with `[dvwa-docker]` and various authentication and network events.

---

## 7. File Transfer Using WinSCP

### 7.1 Connect with WinSCP

1. Open WinSCP.  
2. New Site:  
   - File protocol: SFTP  
   - Host name: `<Lightsail_Public_IP>`  
   - Port number: `22`  
   - User name: `ubuntu`  
3. Click Advanced -> SSH -> Authentication.  
4. Browse for your `lightsail.ppk` key.  
5. OK, then Login and accept the host key.

### 7.2 Download logs

On the right (remote side):

1. Navigate to `/var/log/cloudsec/`.  
2. Select:
   - `cloudsec-full.log`  
   - `cloudsec-alerts.log`  
3. Drag them to a folder on your PC (left side) to copy.

You now have offline copies of the logs for Splunk.

---

## 8. Splunk Setup and Dashboards (Local PC)

### 8.1 Install Splunk Enterprise

1. Download Splunk Enterprise for Windows.  
2. Run the installer with default options.  
3. When it finishes, Splunk will open in your browser at `http://localhost:8000`.  
4. Create an admin account.

### 8.2 Import logs into Splunk

1. In Splunk Web, click Add Data.  
2. Choose Upload.  
3. Select `cloudsec-full.log`.  
4. Click Next, verify the preview and timestamps.  
5. Click Next again, set index to `main` or create a custom index.  
6. Click Review, then Submit.  
7. Repeat for `cloudsec-alerts.log` if you want it as a separate source.

### 8.3 Create a dashboard

1. In Splunk, go to Dashboards.  
2. Click Create new dashboard.  
3. Name it `CloudSec`, click Create.

Add panels:

**Panel 1: Event count over time**

Search:

```spl
source="cloudsec-full.log" | timechart span=10m count
```

Save as a timechart panel.

**Panel 2: DVWA events**

```spl
source="cloudsec-full.log" "dvwa-docker"
```

Save as a table or timechart.

**Panel 3: SQL injection patterns**

```spl
source="cloudsec-full.log" ("sqli" OR "id=1' OR '1'='1" OR "injection")
```

**Panel 4: Failed SSH logins**

```spl
source="cloudsec-full.log" "Failed password"
```

Set your time range to Last 24 hours or All time as needed.

---

## 9. Normal Run Cycle for Demo

Each time you want to demonstrate:

On the Ubuntu instance:

```bash
# Ensure Docker and DVWA are running
sudo systemctl start docker
sudo docker start dvwa

# Ensure monitoring is running
sudo systemctl start cloudsec.service
sudo systemctl status cloudsec.service
```

Then:

1. In the browser, open DVWA and perform logins and attacks.  
2. On Ubuntu, you can verify activity with:

   ```bash
   sudo tail -n 20 /var/log/cloudsec-full.log
   ```

3. Use WinSCP to download fresh versions of:
   - `cloudsec-full.log`  
   - `cloudsec-alerts.log`  
4. Upload the new log files into Splunk.  
5. Refresh your `CloudSec` dashboard to show the new data.

---

## 10. Troubleshooting

**PuTTY cannot connect**
- Confirm username `ubuntu`.  
- Confirm `.ppk` key path.  
- Check Lightsail firewall: inbound rule for port 22 must be allowed.  

**DVWA container not running**

```bash
sudo docker ps -a
sudo docker start dvwa
sudo docker logs dvwa
```

**CloudSec logs are empty**

- Check permissions:

  ```bash
  ls -l /var/log/cloudsec/
  sudo chmod 666 /var/log/cloudsec/*.log
  ```

- Check service:

  ```bash
  sudo systemctl status cloudsec.service
  ```

**No events in Splunk**

- Make sure you generated fresh activity in DVWA and on the host.  
- Ensure you uploaded the latest copies of `cloudsec-full.log` and `cloudsec-alerts.log`.  
- In Splunk, set the time range to All time and run:

  ```spl
  source="cloudsec-full.log"
  ```

If that returns data, your dashboard panels should work with the correct index and time range.
