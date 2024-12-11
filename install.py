import subprocess
import sys
import os

# ANSI escape sequences for colored logs
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[0;33m'
NC = '\033[0m'  # No Color

# Path to store mode configuration
MODE_FILE = '/home/capstone/mode'
SITES_AVAILABLE_DEFAULT = "/etc/nginx/sites-available/default"
SITES_AVAILABLE_DEFAULT_81 = "/etc/nginx/sites-available/default81"
SITES_ENABLED_DEFAULT = "/etc/nginx/sites-enabled/default"
SITES_ENABLED_DEFAULT_81 = "/etc/nginx/sites-enabled/default81"
UPDATE_IP_SCRIPT_PATH = "/home/capstone/nginx_ip_update.sh"
UPDATE_NGINX_FILE_SERVICE_PATH = "/etc/systemd/system/nginx_ip_update.service"


# Command definitions for easy access and modification
DISABLE_NETWORK_MANAGER_WAIT_ONLINE = "sudo systemctl disable NetworkManager-wait-online.service"
INSTALL_PREREQUISITES = "sudo apt install -y nginx git nmap i2c-tools libgpiod-dev python3-libgpiod python3-pip python3-setuptools"
OPEN_RASPI_CONFIG = "sudo raspi-config"
CAT_MODE_FILE = f"cat {MODE_FILE}"
CREATE_BRIDGE_CONNECTION = "sudo nmcli connection add con-name 'BR0' ifname br0 type bridge ipv4.method auto ipv6.method disabled connection.autoconnect yes stp no"
CREATE_ETH_SLAVE_CONNECTION = "sudo nmcli connection add con-name 'ETH' ifname eth0 type bridge-slave master 'BR0' connection.autoconnect yes"
CREATE_AP_SLAVE_CONNECTION = "sudo nmcli connection add con-name 'AP' ifname wlan0 type wifi slave-type bridge master 'BR0' wifi.band bg wifi.mode ap wifi.ssid 'ChilipepperLABS' wifi-sec.key-mgmt wpa-psk wifi-sec.psk '12345678' autoconnect yes"
TURN_UP_ETH = "sudo nmcli connection up ETH"
TURN_UP_AP = "sudo nmcli connection up AP"
TURN_UP_BR0 = "sudo nmcli connection up BR0"
CREATE_ETH_STATIC_CONNECTION = "sudo nmcli connection add type ethernet con-name 'ETH' ifname eth0 ipv4.addresses '192.168.1.1/24' ipv4.gateway '192.168.1.1' ipv4.method manual autoconnect yes"
CREATE_DEFAULT_SYMLINK = f"sudo ln -sf {SITES_AVAILABLE_DEFAULT} {SITES_ENABLED_DEFAULT}"
CREATE_DEFAULT_81_SYMLINK = f"sudo ln -sf {SITES_AVAILABLE_DEFAULT_81} {SITES_ENABLED_DEFAULT_81}"
RELOAD_NGINX = "sudo systemctl reload nginx"
RELOAD_SYSTEMD = "sudo systemctl daemon-reload"


ETH_INTERFACE = "eth0"

SERVICE_FILE_PATH_WEB = "/etc/systemd/system/webserver.service"
SERVICE_FILE_PATH_SCRIPT = "/etc/systemd/system/screen.service"

REPO_URLS_STA = {
    "web": "https://github.com/danielzazzali/webserver-daughterbox.git",
    "screen": "https://github.com/ItiKvnAlf/oled-daughterbox.git"
}

REPO_URLS_AP = {
    "web": "https://github.com/danielzazzali/webserver-motherhub.git",
    "screen": "https://github.com/ItiKvnAlf/oled-motherhub.git"
}

CLONE_DIRS = {
    "web": "/home/capstone/web",
    "screen": "/home/capstone/screen"
}

CREATE_VENV_REPO = {
    "web": "python3 -m venv /home/capstone/web/venv",
    "screen": "python3 -m venv /home/capstone/screen/venv"
}

INSTALL_REQUIREMENTS_REPO = {
    "web": "bash -c 'source /home/capstone/web/venv/bin/activate; pip install -r /home/capstone/web/requirements.txt'",
    "screen": "bash -c 'source /home/capstone/screen/venv/bin/activate; pip install -r /home/capstone/screen/requirements.txt'"
}

nginx_conf_file_default = """
server {
    listen 80;
    listen [::]:80;

    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        add_header Cache-Control 'no-store, no-cache';
    }
}
"""

nginx_conf_file_default_81 = """
server {
    listen 81;
    listen [::]:81;

    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        add_header Cache-Control 'no-store, no-cache';
    }
}
"""

nginx_ip_update_script = f"""#!/bin/bash

NGINX_CONF_PATH_DEFAULT="{SITES_AVAILABLE_DEFAULT}"

# Check if the eth0 interface is connected
INTERFACE_STATUS=$(nmcli -g GENERAL.STATE device show eth0 | awk '{{print $1}}')

echo "Interface eth0 state: $INTERFACE_STATUS"

if [ "$INTERFACE_STATUS" -ne 100 ]; then
    echo "The eth0 interface is not connected. Using localhost as the target."
    CONNECTED_IP="127.0.0.1:8000/no_camera"

    # Update Nginx configuration with localhost
    cat <<EOL > $NGINX_CONF_PATH_DEFAULT
server {{
    listen 80;
    listen [::]:80;

    server_name _;

    location / {{
        proxy_pass http://$CONNECTED_IP/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        add_header Cache-Control 'no-store, no-cache';
    }}
}}
EOL

    # Reload Nginx to apply the changes
    {RELOAD_NGINX} || exit 1
fi

CURRENT_IP=$(nmcli -g ipv4.addresses connection show ETH | awk -F/ '{{print $1 "/" $2}}')

echo "Current IP address: $CURRENT_IP"

CURRENT_IP_NO_MASK=$(echo $CURRENT_IP | awk -F/ '{{print $1}}')

echo "Current IP address without mask: $CURRENT_IP_NO_MASK"

echo "Scanning for connected devices..."

CONNECTED_IP=$(nmap -sn $CURRENT_IP | grep 'Nmap scan report for' | awk '{{print $NF}}' | grep -v $CURRENT_IP_NO_MASK)

echo "Found connected device with IP: $CONNECTED_IP"

# Update the Nginx configuration with the found IP address
cat <<EOL > $NGINX_CONF_PATH_DEFAULT
server {{
    listen 80;
    listen [::]:80;

    server_name _;

    location / {{
        proxy_pass http://$CONNECTED_IP/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \\$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \\$host;
        proxy_cache_bypass \\$http_upgrade;
        add_header Cache-Control 'no-store, no-cache';
    }}
}}
EOL

# Reload Nginx to apply the changes
{RELOAD_NGINX} || exit 1
"""

systemd_service_content = f"""[Unit]
Description=Update Nginx configuration with connected device IP
After=network.target

[Service]
ExecStart=/usr/bin/bash -c 'sudo {UPDATE_IP_SCRIPT_PATH}'
Restart=always
RestartSec=30s

[Install]
WantedBy=multi-user.target
"""

def log_info(message):
    """Print an informational message in green."""
    print(f"{GREEN}[INFO]{NC} {message}")


def log_warning(message):
    """Print a warning message in yellow."""
    print(f"{YELLOW}[WARNING]{NC} {message}")


def log_error(message):
    """Print an error message in red."""
    print(f"{RED}[ERROR]{NC} {message}")


def run_command(command):
    """Execute a shell command and handle errors."""
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError:
        log_error(f"Failed to execute: {command}")
        sys.exit(1)


def disable_network_manager_service():
    """Prompt to disable NetworkManager-wait-online.service."""
    choice = input(f"{YELLOW}Do you want to disable NetworkManager-wait-online.service? (y/n): {NC}").strip().lower()
    if choice == 'y':
        log_info("Disabling NetworkManager-wait-online.service...")
        run_command(DISABLE_NETWORK_MANAGER_WAIT_ONLINE)
        log_info("Successfully disabled NetworkManager-wait-online.service.")
    else:
        log_warning("Skipped disabling NetworkManager-wait-online.service.")


def install_prerequisites():
    """Prompt to install nginx and git."""

    prerequisites = INSTALL_PREREQUISITES.split("-y")[-1]

    choice = input(f"{YELLOW}Do you want to install{prerequisites}? (y/n): {NC}").strip().lower()
    if choice == 'y':
        log_info(f"Installing{prerequisites}...")
        run_command(INSTALL_PREREQUISITES)
        log_info(f"Successfully installed{prerequisites}.")
    else:
        log_warning(f"Skipped installation{prerequisites}.")


def show_wlan_instructions():
    """Display instructions for setting the WLAN country."""
    log_info("Please follow these steps to set your WLAN country in 'raspi-config':")
    print(f"{YELLOW}-> 5 Localisation Options -> L4 WLAN Country -> <Country> -> OK -> Finish{NC}")


def open_raspi_config():
    """Open the raspi-config tool."""
    input(f"{YELLOW}Press Enter to continue and open 'raspi-config'...{NC}")
    run_command(OPEN_RASPI_CONFIG)


def configure_mode():
    """Prompt to configure Raspberry Pi as Access Point (AP) or Station (STA)."""
    while True:
        mode_choice = input(f"{YELLOW}Configure Raspberry Pi as 'AP' (Access Point) or 'STA' (Station): {NC}").strip().upper()
        if mode_choice in ('AP', 'STA'):
            log_info(f"You selected {mode_choice} mode.")
            with open(MODE_FILE, 'w') as file:
                file.write(mode_choice)
            log_info(f"Mode configuration saved to {MODE_FILE}.")
            print(f"{GREEN}Contents of {MODE_FILE}:{NC}")
            run_command(CAT_MODE_FILE)
            return mode_choice
        else:
            log_warning("Invalid input. Please enter 'AP' or 'STA'.")


def configure_ap_mode():
    """Configure Raspberry Pi as an Access Point (AP)."""
    log_info("Configuring Raspberry Pi as an Access Point (AP)...")

    # Create a bridge connection for eth0 and wlan0
    log_info("Creating bridge connection (br0)...")
    run_command(CREATE_BRIDGE_CONNECTION)

    log_info("Creating ethernet connection (eth0)...")
    run_command(CREATE_ETH_SLAVE_CONNECTION)

    # Set up the Wi-Fi Access Point with SSID ChilipepperLABS and password
    log_info("Setting up Wi-Fi Access Point with SSID 'ChilipepperLABS' and password '12345678'...")
    run_command(CREATE_AP_SLAVE_CONNECTION)

    log_info("Turning up the ETH...")
    run_command(TURN_UP_ETH)
    log_info("Turning up the AP...")
    run_command(TURN_UP_AP)
    log_info("Turning up the BR0...")
    run_command(TURN_UP_BR0)

    log_info("Access Point (AP) configuration completed successfully.")


def configure_sta_mode():
    """Configure Raspberry Pi as a Station (STA)."""
    log_info("Configuring Raspberry Pi as a Station (STA)...")

    log_info("Creating Ethernet connection with static IP 192.168.1.1/24...")
    run_command(CREATE_ETH_STATIC_CONNECTION)

    log_info("Turning up the ETH...")
    run_command(TURN_UP_ETH)

    log_info("Station (STA) configuration completed successfully.")


def create_nginx_file_ap():
    """Create nginx default file for AP."""
    log_info("Creating nginx default file for AP...")

    try:
        with open(SITES_AVAILABLE_DEFAULT, 'w') as file:
            file.write(nginx_conf_file_default)
        log_info(f"Nginx configuration file created successfully at {SITES_AVAILABLE_DEFAULT}")
    except IOError:
        log_error("Failed to create Nginx configuration file")
        return 1

    log_info("Creating symbolic link to enable the AP configuration...")
    run_command(CREATE_DEFAULT_SYMLINK)

    log_info("Reloading Nginx to apply the changes...")
    try:
        run_command(RELOAD_NGINX)
        log_info("Nginx reloaded successfully")
    except subprocess.CalledProcessError:
        log_error("Failed to reload Nginx")
        return 1


def create_nginx_files_sta():
    """Create nginx default and default81 files for STA mode."""
    log_info("Creating nginx default and default81 files for STA...")

    try:
        with open(SITES_AVAILABLE_DEFAULT_81, 'w') as file:
            file.write(nginx_conf_file_default_81)
        open(SITES_AVAILABLE_DEFAULT, 'w').close()
        log_info(f"Nginx configuration files created successfully:\n - {SITES_AVAILABLE_DEFAULT_81}\n - {SITES_AVAILABLE_DEFAULT}")
    except IOError:
        log_error("Failed to create Nginx configuration files")
        return 1

    log_info("Creating symbolic links to enable the configurations...")
    run_command(CREATE_DEFAULT_81_SYMLINK)
    run_command(CREATE_DEFAULT_SYMLINK)

    log_info("Reloading Nginx to apply the changes...")
    try:
        run_command(RELOAD_NGINX)
        log_info("Nginx reloaded successfully")
    except subprocess.CalledProcessError:
        log_error("Failed to reload Nginx")
        return 1


def create_nginx_ip_update_script():
    """Create the Nginx IP update script."""
    log_info("Creating the Nginx IP update script...")

    try:
        with open(UPDATE_IP_SCRIPT_PATH, 'w') as file:
            file.write(nginx_ip_update_script)
        os.chmod(UPDATE_IP_SCRIPT_PATH, 0o755)
        log_info(f"Nginx IP update script created successfully at {UPDATE_IP_SCRIPT_PATH}")
    except IOError:
        log_error("Failed to create Nginx IP update script")
        return 1


def create_systemd_service():
    """Create the systemd service unit file."""
    log_info("Creating the systemd service unit file...")

    try:
        with open(UPDATE_NGINX_FILE_SERVICE_PATH, 'w') as file:
            file.write(systemd_service_content)
        log_info(f"Systemd service unit file created successfully at {UPDATE_NGINX_FILE_SERVICE_PATH}")
    except IOError:
        log_error("Failed to create systemd service unit file")
        return 1



def reload_systemd():
    """Reload systemd to recognize the new service and timer."""
    log_info("Reloading systemd to recognize the new service and timer...")
    run_command(RELOAD_SYSTEMD)


def setup_repositories(mode_choice):
    """Clone the repositories, create virtual environments, and install requirements."""
    log_info(f"Cloning the repositories for mode: {mode_choice}...")

    # Chose repo URLs based on mode
    if mode_choice == 'AP':
        repo_urls = REPO_URLS_AP
    else:  # STA
        repo_urls = REPO_URLS_STA

    # Clone repositories
    run_command(f"git clone {repo_urls['web']} {CLONE_DIRS['web']}")
    run_command(f"git clone {repo_urls['screen']} {CLONE_DIRS['screen']}")

    # Create virtual environments
    log_info("Creating virtual environments...")
    run_command(CREATE_VENV_REPO['web'])
    run_command(CREATE_VENV_REPO['screen'])

    # Install requirements
    log_info("Installing the requirements for the repositories...")
    run_command(INSTALL_REQUIREMENTS_REPO['web'])
    run_command(INSTALL_REQUIREMENTS_REPO['screen'])

    log_info("Repositories set up and requirements installed successfully.")

def create_service(service_path, service_content, service_name):
    """Create a systemd service to run a script on boot."""
    log_info(f"Creating the systemd service unit file for {service_name}...")

    try:
        with open(service_path, 'w') as file:
            file.write(service_content)
        os.chmod(service_path, 0o644)
        log_info(f"Systemd service unit file created successfully at {service_path}")
    except IOError:
        log_error(f"Failed to create systemd service unit file for {service_name}")
        return 1

    log_info(f"Enabling and starting the {service_name} systemd service...")
    run_command(RELOAD_SYSTEMD)
    run_command(f"sudo systemctl enable {service_name}")
    run_command(f"sudo systemctl start {service_name}")
    log_info(f"Systemd service {service_name} enabled and started successfully.")

def create_service_for_mode(mode_choice):
    """Create systemd services for the web server and screen script based on the mode."""
    if mode_choice == 'AP':
        service_content_web = f"""[Unit]
Description=Run Web Server on boot (AP Mode)
After=network.target

[Service]
ExecStart=/bin/bash -c 'source /home/capstone/web/venv/bin/activate; python3 /home/capstone/web/app.py'
WorkingDirectory=/home/capstone/web

[Install]
WantedBy=multi-user.target
"""

        service_content_script = f"""[Unit]
Description=Run Screen Script on boot (AP Mode)
After=network-online.target multi-user.target
Wants=network-online.target

[Service]
ExecStart=/bin/bash -c 'source /home/capstone/screen/venv/bin/activate; python3 /home/capstone/screen/main.py'
WorkingDirectory=/home/capstone/screen

[Install]
WantedBy=multi-user.target
"""
    else:  # STA
        service_content_web = f"""[Unit]
Description=Run Web Server on boot (STA Mode)
After=network.target

[Service]
ExecStart=/bin/bash -c 'source /home/capstone/web/venv/bin/activate; python3 /home/capstone/web/app.py'
WorkingDirectory=/home/capstone/web

[Install]
WantedBy=multi-user.target
"""

        service_content_script = f"""[Unit]
Description=Run Screen Script on boot (STA Mode)
After=network-online.target multi-user.target
Wants=network-online.target

[Service]
ExecStart=/bin/bash -c 'source /home/capstone/screen/venv/bin/activate; python3 /home/capstone/screen/main.py'
WorkingDirectory=/home/capstone/screen

[Install]
WantedBy=multi-user.target
"""

    create_service(SERVICE_FILE_PATH_WEB, service_content_web, "webserver.service")
    create_service(SERVICE_FILE_PATH_SCRIPT, service_content_script, "screen.service")


def set_up_raspi_config():
    """
    This function sets up Raspberry Pi configurations by enabling various interfaces.
    """
    print("Enabling Raspberry Pi interfaces...")

    try:
        # Enable I2C
        print("Enabling I2C...")
        subprocess.run(["sudo", "raspi-config", "nonint", "do_i2c", "0"], check=True)

        # Enable SPI
        print("Enabling SPI...")
        subprocess.run(["sudo", "raspi-config", "nonint", "do_spi", "0"], check=True)

        # Enable Serial
        print("Enabling Serial...")
        subprocess.run(["sudo", "raspi-config", "nonint", "do_serial_hw", "0"], check=True)

        # Enable SSH
        print("Enabling SSH...")
        subprocess.run(["sudo", "raspi-config", "nonint", "do_ssh", "0"], check=True)

        # Enable Camera
        print("Enabling Camera...")
        subprocess.run(["sudo", "raspi-config", "nonint", "do_camera", "0"], check=True)

        # Disable raspi-config at Boot
        print("Disabling raspi-config at Boot...")
        subprocess.run(["sudo", "raspi-config", "nonint", "disable_raspi_config_at_boot", "0"], check=True)

        print("All Raspberry Pi interfaces have been successfully configured.")

    except subprocess.CalledProcessError as e:
        print(f"An error occurred while configuring Raspberry Pi interfaces: {e}")


def delete_all_nmcli_connections():
    """Delete all network connections using nmcli."""
    log_info("Deleting all network connections using nmcli...")
    try:
        # List all connections
        result = subprocess.run(["nmcli", "-t", "-f", "NAME", "connection", "show"], capture_output=True, text=True,
                                check=True)
        connections = result.stdout.splitlines()

        # Delete each connection
        for connection in connections:
            run_command(f"nmcli connection delete '{connection}'")

        log_info("All network connections deleted successfully.")
    except subprocess.CalledProcessError as e:
        log_error(f"Failed to delete network connections: {e}")


def enable_and_start_service(service_path):
    """Enable and start the systemd service."""
    service_name = os.path.basename(service_path)
    log_info(f"Enabling and starting the {service_name} service...")

    try:
        run_command(f"sudo systemctl enable {service_name}")
        run_command(f"sudo systemctl start {service_name}")
        log_info(f"Systemd service {service_name} enabled and started successfully.")
    except subprocess.CalledProcessError as e:
        log_error(f"Failed to enable and start the {service_name} service: {e}")



def main():
    """Main function to execute the installation script."""
    log_info("Starting installation script for Raspberry Pi.")
    disable_network_manager_service()
    set_up_raspi_config()
    install_prerequisites()
    show_wlan_instructions()
    open_raspi_config()

    mode_choice = configure_mode()

    if mode_choice == 'AP':
        setup_repositories(mode_choice)
        delete_all_nmcli_connections()
        configure_ap_mode()
        create_nginx_file_ap()
    elif mode_choice == 'STA':
        setup_repositories(mode_choice)
        delete_all_nmcli_connections()
        configure_sta_mode()
        create_nginx_files_sta()
        create_nginx_ip_update_script()
        create_systemd_service()
        reload_systemd()
        enable_and_start_service(UPDATE_NGINX_FILE_SERVICE_PATH)

    create_service_for_mode(mode_choice)

    log_info("Installation script completed successfully.")


if __name__ == "__main__":
    main()
