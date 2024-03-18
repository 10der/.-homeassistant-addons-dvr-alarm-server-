#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import struct
import json
import socketserver
import paho.mqtt.publish as mqtt
import logging

root = logging.getLogger()
root.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)

logger: logging.Logger = logging.getLogger('dvr-alarm-server')


def log_info(info, *arguments):
    if len(arguments) == 0:
        logger.debug(info)
    elif len(arguments) == 1:
        logger.debug(info + "%s" % arguments)
    else:
        logger.debug(info + ' %r', arguments)


class MQTTPublisher:
    mqttHost = '127.0.0.1'
    mqttPort = 1883

    mqttUser = ''
    mqttPass = ''
    mqttTopic = ''

    mqttDebug = False

    def __init__(self, host, port, user, passwd, topic, debug):
        self.mqttHost = host
        self.mqttPort = port
        self.mqttUser = user
        self.mqttPass = passwd
        self.mqttTopic = topic
        self.mqttDebug = debug

    def publish(self, serialID, event):

        auth_data = None
        if (self.mqttUser and self.mqttPass):
            auth_data = {'username': self.mqttUser, 'password': self.mqttPass}

        topic = self.mqttTopic + '/{}/event'.format(serialID)
        mqtt.single(topic=topic, payload=event, retain=False,
                    hostname=self.mqttHost, port=self.mqttPort, auth=auth_data, tls=None)

        if self.mqttDebug:
            log_info("EVENT:", event)


class AlarmServerHandler(socketserver.BaseRequestHandler):

    def handle(self):
        header = self.request.recv(20)
        head, version, session, sequence_number, msgid, len_data = struct.unpack(
            "BB2xII2xHI", header
        )

        if self.server.debug:
            log_info("EVENT-HEADER:", head, version, session, sequence_number,
                     msgid, len_data, self.client_address)

        data = self.request.recv(1024).strip()
        payload = data.decode('ascii')

        json_data = json.loads(payload)
        serialID = json_data.get('SerialID')

        json_text = json.dumps(json_data, indent=4, sort_keys=True)
        self.server.publisher.publish(serialID, json_text)


class Configurator:
    config = {}

    def __init__(self, config):
        self.config = config

    def get(self, path, default=None):
        items = path.split(':')
        value = None

        for idx, item in enumerate(items):
            if idx == 0:
                value = self.config.get(item)
            else:
                value = None if value is None else value.get(item)

        return value or default


def main():
    log_info("DVR server running...")

    HOST, PORT = '0.0.0.0', 15002

    MQTT_HOST = "localhost"
    MQTT_PORT = 1883
    MQTT_USER = ""
    MQTT_PASSWD = ""
    MQTT_TOPIC = "home/camalarm"
    MQTT_DEBUG = False

    config = None
    if os.path.exists('./dvr-alarm-server.json'):
        log_info('Running in local mode')
        fp = open('./dvr-alarm-server.json', 'r')
        config = Configurator(json.load(fp))
        fp.close()
    elif os.path.exists('/data/options.json'):
        log_info('Running in hass.io add-on mode')
        fp = open('/data/options.json', 'r')
        config = Configurator(json.load(fp))
        fp.close()
    else:
        log_info('Configuration file not found, exiting.')
        sys.exit(1)

    if config.get('mqtt:debug'):
        log_info("Debugging messages enabled")
        MQTT_DEBUG = True

    if config.get('mqtt:username') and config.get('mqtt:password'):
        MQTT_USER = config.get('mqtt:username')
        MQTT_PASSWD = config.get('mqtt:password')

    MQTT_HOST = config.get('mqtt:host', MQTT_HOST)
    MQTT_PORT = config.get('mqtt:port', MQTT_PORT)
    MQTT_TOPIC = config.get('mqtt:topic', MQTT_TOPIC)

    publisher = MQTTPublisher(MQTT_HOST, MQTT_PORT,
                              MQTT_USER, MQTT_PASSWD, MQTT_TOPIC, MQTT_DEBUG)

    HOST = config.get('server:host', HOST)
    PORT = config.get('server:port', PORT)

    server = socketserver.TCPServer((HOST, PORT), AlarmServerHandler)
    server.publisher = publisher
    server.debug = MQTT_DEBUG

    server.serve_forever()

    server.server_close()


if __name__ == "__main__":
    main()
