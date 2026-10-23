# Smart-Store
A simulation of a smart store using real iot devices with a functional full stack environment

Frontend:
- HTML
- CSS
- Javascript

Backend:
- Python (Flask)

Database:
- SQLite
- Templating Engine: -Jinja

Libraries used: -lgpio -SQLAlchemy


# Features
Customer creation:
- Users can create a new account by providing data like first name, last name, phone number, etc. and get stored in the database

Tempearature reading and control:
- Using a python script to send an email to the admin if the temperature of a fridge has gone under or over a certain threshold
- Admin answers the email with yes to turn the fridge fan on
- Any other response will NOT turn it on
- Using RPi and ESP32 to simulate a Pub/Sub architecture using MQTT as a broker