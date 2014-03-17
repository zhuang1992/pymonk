# -*- coding: utf-8 -*-
"""
Created on Sat Feb 01 10:46:02 2014
Aggregate individual models periodically
@author: pacif_000
"""
import configuration
import logging
from kafka.client import KafkaClient
from kafka.consumer import SimpleConsumer
from ..monk import initialize, aggregate
import simplejson

config = configuration.Configuration("master.yml")
initialize(config)
logger = logging.getLogger("monk")
turtle_id = config.kafkaTopic
try:
    kafka = KafkaClient(config.kafkaConnectionString)
    consumer = SimpleConsumer(kafka, config.kafkaGroup,
                              config.kafkaTopic,
                              partitions=[0])
    for message in consumer:
        decoded_message = simplejson.loads(message)
        user_id = decoded_message['userId']
        aggregate(turtle_id, user_id)
except Exception as e:
    logger.warning('Exception {0}'.format(e))
    logger.warning('Can not consume aggregation')

kafka.close()