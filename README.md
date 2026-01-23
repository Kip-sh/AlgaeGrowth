# ASA Datacollector

## Setup
Simply execute the following commands, and everything will set itself up and start automatically
```bash
chmod +x setup.sh
sudo ./setup.sh
```

## Usage
### Systemd service
The system automatically runs as a systemd service.
you can use `sudo systemctl stop datacollector` to stop it, use `sudo systemctl start datacollector` to start it again, and `sudo systemctl restart datacollector` to, you guessed it, restart the service after having made changes.

### Make sure to edit your .env file! 
Make sure to add the correct paths to the devices (`/dev/ttyAMC0` for the colorimeter, and `/dev/ttyUSB0` for the ESP32 on linux, or find the COM ports using the `mode` command on windows). `AZURE_ENABLED` determines if measured data gets posted to azure, and `DEBUG` enables mocking devices for if you don't have access to the hardware and need to test something.