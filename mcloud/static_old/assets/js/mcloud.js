

function Events(target){
  var events = {}, once = {};
  target = target || this;
    /**
     *  On: listen to events
     */
    target.on = function(type, func, ctx, once){
      events[type] || (events[type] = []);
      events[type].push({f:func, c:ctx, once: once})
    };
    target.once = function(type, func, ctx){
        target.on(type, func, ctx, true);
    };
    /**
     *  Off: stop listening to event / specific callback
     */
    target.off = function(type, func){
      var list = events[type] || [];
      var i = list.length = func ? list.length : 0;
      while(i-->0) func == list[i].f && list.splice(i,1)
    };
    /**
     * Emit: send event, callbacks will be triggered
     */
    target.emit = function(){
      var args = Array.apply([], arguments);
      var type = args.shift();

      var list = events[type] || [];
      list = Array.apply([], list);

      var i = list.length;
      for(var j=0;j<i;j++) {
          list[j].f.apply(list[j].c, args);
          if (list[j].once) {
              target.off(type, list[j].f);
          }
      }
    };
}
var u, module, cjs = module != u;
(cjs ? module : window)[(cjs ? 'exports' : 'Events')] = Events;


function McloudIO(host, port) {
    Events(this);
    var me = this;
    me.request_id = 0;
    me.requests = {};
    me.online = false;

    if (window.location.protocol != "https:") {
        me.api = new ReconnectingWebSocket('ws://' + host + ':' + (port || 7080) + '/ws/');
    } else {
        me.api = new ReconnectingWebSocket('wss://' + host + ':' + (port || 7080) + '/ws/');
    }


    me.api.onopen = function() {
        me.emit('connect');
        me.online = true;
    };

    me.api.onclose = function() {
        me.emit('disconnect');
        me.online = false;
    };

    /**
     * Waits for connection
     *
     * @returns {Promise}
     */
    me.wait_connect = function() {
        return new Promise(function(resolve, reject) {
            if (me.online) {
                resolve();
            }
            me.once('connect', function() {
                console.log('connect event');
                resolve();
            });
        });
    };

    me.api.onmessage = function(e) {
        me.emit('raw_message', JSON.parse(e.data));
    };

    me.on_raw_message = function(message) {
        if (message.type == 'response') {
            me.emit('response', message.id, message.success, message.response);
        }
        if (message.type == 'event') {
            me.emit('event', message.name, message.data);
            me.emit(message.name, message.data);
        }
    };

    me.on_response = function(id, success, response) {
        if (me.requests[id]) {
            var promise = me.requests[id];
            delete me.requests[id];

            if (success) {
                promise.resolve(response);
            } else {
                promise.reject(response);
            }
        }
    };

    /**
     * Subscrivbe to own events
     */
    me.on('raw_message', me.on_raw_message);
    me.on('response', me.on_response);


    me.call = function(task, args, kwargs) {
        var rqid = me.request_id++;
        me.api.send(JSON.stringify({
            task: task,
            id: rqid,
            args: args || [],
            kwargs: kwargs || {}
        }));

        return rqid;
    };

    me.request = function(task, args, kwargs) {
        console.log('call', task, args, kwargs);
        return me.wait_connect().then(function() {

            return new Promise(function(resolve, reject) {
                me.requests[me.call(task, args, kwargs)] = {
                    resolve: resolve,
                    reject: reject
                };
            });
        });

    };

    me.ping = function() {
        return request('ping').then(function(response) {
            console.log('response', response);
        });
    };

    me.kill = function(task_id) {
        return me.request('kill', [], {ticket_id: task_id});
    };

    me._task_start = function(args, kwargs) {
        return me.request('task_start', args, kwargs).then(function(result) {
            return new McloudIOTask(me, result.id);
        });
    };

    me.call_task = function(args, kwargs) {
        return new Promise(function(resolve, reject) {

            me._task_start(args, kwargs).then(function(task) {
                task.on('complete', function(result) {
                    resolve(result);
                })
            });
        });
    };

    /**
     * Public api
     */

    me.list = function() {
        return me.call_task(['list']);
    };

    me.inspect = function(app, service) {
        return me.call_task(['inspect', app, service]);
    };

    me.logs = function(service_name) {
        return me._task_start(['logs', service_name]);
    };

    me.run = function(service_name, commmand, width, height) {
        return me._task_start(['run', service_name, commmand, [height, width]]);
    }
}

function McloudIOTask(api, task_id) {
    Events(this);
    var me = this;
    me.id = task_id;

    api.on('task.success.' + task_id, function(data) {
        me.emit('complete', data);
    });

    api.on('task.progress.' + task_id, function(data) {
        me.emit('progress', data);
    });

    api.on('task.stdout.' + task_id, function(data) {
        me.emit('stdout', data);
    });

    api.on('task.failure.' + task_id, function(data) {
        me.emit('failure', data);
    });

    me.stdin = function(data) {
        api.call('stdin', [], {ticket_id: task_id, data: data});
    }

}


//var io = new McloudIO(location.hostname);
//
//io.list().then(function(result) {
//    console.log('List result:', result);
//});




