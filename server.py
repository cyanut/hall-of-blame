from __future__ import absolute_import, division, print_function, unicode_literals

from gevent import monkey; monkey.patch_all()
from gevent.queue import Queue
#from multiprocessing import Queue
#from multiprocessing import Process as Thread
#from queue import Queue
from threading import Thread

from flask import Flask, request, render_template, abort
from flask.ext.socketio import SocketIO, emit
#from proxy import proxy, proxy_request, request
from listener import Listener
import pprint
import json
import time


app = Flask(__name__)
app.config['SECRET_KEY'] = 'hahaha'
#app.config['SERVER_NAME'] = 'my.cyansite.cc'
socketio = SocketIO(app)


SRV_ADDR="50.22.39.6"
PORT = 3336
q = Queue()

listener = None
updater = None
res_buff = []
#FIXME
import test_data
res_buff = test_data.game_res


def jinja_render_template(template, **context):
    return app.jinja_env.get_or_select_template(template).render(context)

@socketio.on('connect', namespace="/host")
def host_start():
    global q
    global listener
    listener = Listener(SRV_ADDR, PORT, PORT, q)
    if not listener.running:
        t = Thread(target=listener.serve)
        t.daemon = True
        t.start()
        updater = Thread(target=get_data, args=())
        updater.daemon = True
        updater.start()
    emit("data", "proxy server initiated.")

@socketio.on('disconnect', namespace="/host")
def host_stop():
    global listener
    listener.stop()
    

@app.route('/bbo')
def main_page():
    return render_template('bbo.html', address="127.0.0.1", port=PORT)

@app.route('/')
def result():
    msg = ""
    if listener is None or not listener.running:
        msg = "waiting for connection ..."
    return render_template('result.html', msg=msg)


def format_data(data):
    d = data
    if d["type"] == "this_table":
        s = jinja_render_template('board.html', **d)
    elif d["type"] == "other_tables":
        s = jinja_render_template('other_tables.html', **d)
    #json doesn't like new lines
    s = s.replace("\n","")
    return json.dumps({"board_num":d["board_num"], "type":d["type"], "content":s})

def get_data():
    global listener
    while listener is None or listener.running:
        data = q.get(block=True)
        res_buff.append(data)
        socketio.emit("data", format_data(data), namespace='/poll')

@socketio.on('connect', namespace='/poll')
def connect():
    print("hihi")
    for data in res_buff:
        emit("data", format_data(data))
        time.sleep(0.1)



#@app.route('/poll', methods=["GET", "POST"])
def poll():
    global q
    res = []
    board_list = request.form.get('boards', None)
    if board_list is None:
        abort(400)
    try:
        board_list = json.loads(board_list)
    except:
        abort(400)
    print(board_list)
    board_list = set(board_list)

    for data in res_buff:
        if not data['board_num'] in board_list:
            res.append(data)

    while not q.empty():
        data = q.get()
        res.append(data)
        res_buff.append(data)

    if res:
        return format_data(res)
    
    data = q.get(block=True)
    res_buff.append(data)
    return format_data([data])

gi = 0
@app.route('/test/<int:n>')
def test(n):
    global gi
    import time
    from test_data import get_game_res
    game_res = get_game_res()
    gi += 1
    gi = gi % 2
    return format_data(game_res[gi:gi+2])


@app.route('/dump')
def dump():
    import pickle
    pickle.dump(res_buff, open("game_res.pkl","wb"))

'''
@app.route('/v2/<fname>.php?<data>', methods=["GET", "POST", "PUT"])
def bbo_proxy(fname, data):
    print(fname, data)
    return proxy_request(request, SRV_ADDR, "{}{}?{}".format(fname,".php", data))
'''


@app.route('/languages/<fname>.xml', defaults={"ftype":"xml"})
@app.route('/config/default/<fname>.xml', defaults={"ftype":"xml"})
@app.route('/application/modules/<dummy>/<fname>.swf', defaults={"ftype":"swf"})
@app.route('/<fname>.swf', defaults={"ftype":"swf"})
def bbo_static(fname, ftype, dummy=""):
    print("get file %s", fname)
    return app.send_static_file("bbo/{}.{}".format(fname, ftype))



if __name__ == "__main__":
    import sys
    socketio.run(app, host="", port=8001)
