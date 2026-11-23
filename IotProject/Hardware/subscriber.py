import paho.mqtt.subscribe as subscribe
msgs = subscribe.simple(["Frig1/temperature", "Frig1/humidity", "Frig2/temperature", "Frig2/humidity"], hostname="192.168.0.106", msg_count=2)
for message in msgs:
    print("%s %s" % (message.topic, message.payload.decode()))
