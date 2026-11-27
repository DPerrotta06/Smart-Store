# Smart Store

A self-checkout grocery store prototype running on a Raspberry Pi 5. Customers scan their whole basket at once with RFID, pay as members and receive their receipt by email. Store admins manage products and stock, view sales and customer reports, and monitor the store's fridges and room conditions from a live sensor dashboard.

School IoT project, built in four phases.

## Features

**For customers**
- Scan the whole basket at once with RFID tags
- Log in by scanning a membership card, or with email and password
- Members-only checkout with Quebec taxes (GST and QST)
- Loyalty points to earn and spend
- Receipts sent by email
- Purchase history with spending charts, item search and price-change history

**For admins**
- Product and stock management
- Live, colour-coded inventory
- Sales and customer activity reports with charts and PDF export
- Store sensor dashboard: fridge temperature and humidity, alert limits, fan control and email alerts
- Bluetooth room sensor showing temperature, humidity, light level and motion

## Technologies

**Software**
- Python, Flask, SQLAlchemy
- SQLite
- HTML, CSS, JavaScript
- MQTT (Mosquitto)
- reelyActive Pareto Anywhere and barnowl-hci (Bluetooth Low Energy)
- Socket.IO
- Gmail (SMTP and IMAP) for receipts and alerts
- bcrypt and signed login tokens for security
- html2pdf.js for PDF reports

**Hardware**
- Raspberry Pi 5
- UHF RFID reader and tags
- ESP32 with DHT11 temperature and humidity sensors
- DC motor fan
- Minew MSP01 Bluetooth sensor (temperature, humidity, light, motion)
