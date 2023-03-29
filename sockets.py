#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import flask
from flask import Flask, request, redirect
from flask_sockets import Sockets
import gevent
from gevent import queue
import time
import json
import os

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True

class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data

    def update_listeners(self, entity):
        '''update the set listeners'''
        for listener in self.listeners:
            listener(entity, self.get(entity))

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())
    
    def world(self):
        return self.space

myWorld = World()        

connections = list()
        
@app.route('/')
def hello():
    '''Return something coherent here.. perhaps redirect to /static/index.html '''
    return redirect("/static/index.html")

def read_ws(ws):
    '''A greenlet function that reads from the websocket and updates the world'''
    entityAndData = flask_post_json(ws)
    print(entityAndData)
    if (entityAndData is not None):
        for key, value in entityAndData.items():
            myWorld.set(key, value)
        return entityAndData

@sockets.route('/subscribe')
def subscribe_socket(ws):
    '''Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket '''

    connections.append(ws)
    print("Subscribing and sending copy of the world")
    ws.send(json.dumps(myWorld.world()))
    try:
        while True:
            # block here
            msg = read_ws(ws)

            if (msg is not None):
                print("Got a message!")
                for connection in connections:
                    connection.send(json.dumps(msg))
                
            
    except Exception as e:# WebSocketError as e:
        print("WS Error %s" % e)
    finally:
        connections.remove(ws)
    return None


# I give this to you, this is how you get the raw body/data portion of a post in flask
# this should come with flask but whatever, it's not my project.
def flask_post_json(ws):
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    msg = ws.receive()

    if (msg is not None):
        return json.loads(msg)
    return None

@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    '''update the entities via this interface'''
    entityAndData = flask_post_json()
    if (entityAndData is not None):
        for key, value in entityAndData.items():
            myWorld.set(key, value)
    return myWorld.get(entity)

@app.route("/world", methods=['POST','GET'])    
def world():
    '''you should probably return the world here'''
    return myWorld.world()

@app.route("/entity/<entity>")    
def get_entity(entity):
    '''This is the GET version of the entity interface, return a representation of the entity'''
    return myWorld.get(entity)


@app.route("/clear", methods=['POST','GET'])
def clear():
    '''Clear the world out!'''
    myWorld.clear()
    return myWorld.world()



if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    app.run()
