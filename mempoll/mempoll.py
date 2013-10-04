#!/usr/bin/env python
import threading
import sys
import time
import os
import subprocess
import json

from flask import Flask, Response, request, render_template
app = Flask(__name__)

db_mem = []
remote_host = ''

class GatherThread(threading.Thread):
    def __init__(self, remote_host):
        super(GatherThread, self).__init__()
        self.running = True
        self.remote_host = remote_host
    def run(self):
        i = 0
        while self.running:
            ts = int(time.time())
            print "Iteration {} @ {}".format(i, ts)
            params = ['ssh', '-o', 'LogLevel=quiet', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null']
            if len(sys.argv) > 2:
                params.extend(sys.argv[2:])
            params.extend([self.remote_host, '--'])
            p = subprocess.Popen(params + ['cat', '/proc/meminfo'], stdout=subprocess.PIPE)
            (meminfo_stdout, stderr) = p.communicate()

            db_mem.append(meminfo_to_json(meminfo_stdout))

            time.sleep(1)
            i += 1

def human_to_bytes(raw):
    suffix = ''.join(c for c in raw if c.isalpha() and c.lower() != 'b').lower()
    prefix = int(''.join(c for c in raw if c.isdigit()))

    d = { "k" : 2**10, "m" : 2**20 }

    return d.get(suffix, 1) * prefix

def procrank_to_json(raw):
    keys = []
    values = []
    for line in raw.splitlines():
        words = line.split()
        if (len(keys) == 0):
            keys = words
        elif (len(words) != len(keys)):
            continue
        else:
            for i in range(1,5):
                words[i] = human_to_bytes(words[i])
            
            values.append(words)
    
    return json.dumps([dict(i for i in zip(keys, x)) for x in values]) + ",\n"

def meminfo_to_json(raw):
    d = {}
    for line in raw.splitlines():
        pair = [x.strip() for x in line.split(':')]
        pair[1] = human_to_bytes(pair[1])
        d[pair[0]] = pair[1]
    
    return json.dumps(d)

@app.route("/")
def index():
    return render_template('chart.html')

@app.route("/data")
def data():
    last = int(request.args.get('l', 0))
    return Response('{{ {} }}'.format(','.join('"{}":{}'.format(i+last, x) for i, x in enumerate(db_mem[last:]))), mimetype="application/json")

def main():
    dir = "mem-samples.{}".format(int(time.time()))

    os.makedirs(dir)
    i = 0;

    procrank_file = open('{}/procrank'.format(dir), 'w')
    meminfo_file = open('{}/meminfo'.format(dir), 'w')

if __name__ == '__main__':
    remote_host = sys.argv[1]
    app.context_processor(lambda: dict(remote_host=remote_host))
    thread = GatherThread(remote_host)
    thread.daemon = True
    thread.start()
    #app.run(host='0.0.0.0', debug=True)
    app.run(host='0.0.0.0')
    thread.running = False
    thread.join()
    sys.exit()

