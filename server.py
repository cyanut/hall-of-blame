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
from listener import serve
import pprint
import json


app = Flask(__name__)
app.config['SECRET_KEY'] = 'hahaha'
socketio = SocketIO(app)


SRV_ADDR="192.155.229.163"
PORT = 3336
q = Queue()
listener = None
res_buff = []


@app.route('/bbo')
def main_page():
    global q
    global listener
    if listener is None or not listener.is_alive():
        listener = Thread(target=serve, args=(SRV_ADDR, PORT, q))
        listener.daemon = True
        listener.start()
    return render_template('base.html', address="127.0.0.1", port=PORT)

@app.route('/')
def result():
    msg = ""
    if listener is None or not listener.is_alive():
        msg = "waiting for connection ..."
    return render_template('result.html', msg=msg)


def format_data(data):
    res = []
    for d in data:
        if d["type"] == "this_table":
            s = render_template('board.html', **d)
        elif d["type"] == "other_tables":
            s = render_template('other_tables.html', **d)
        #json doesn't like new lines
        s = s.replace("\n","")
        res.append({"board_num":d["board_num"], "content":s})
    return json.dumps(res)


@app.route('/poll', methods=["GET", "POST"])
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
@app.route('/<fname>.swf', defaults={"ftype":"swf"})
def bbo_static(fname, ftype):
    return app.send_static_file("bbo/{}.{}".format(fname, ftype))



if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        app.run(debug=True, port=8001, threaded=True)
    else:
        from gevent.wsgi import WSGIServer
        http_server = WSGIServer(("", 8001), app)
        http_server.serve_forever()
    

            



