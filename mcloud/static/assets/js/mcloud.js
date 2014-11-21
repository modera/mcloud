
function Events(target){
  var events = {}, A = Array;
  target = target || this;
    /**
     *  On: listen to events
     */
    target.on = function(type, func, ctx){
      events[type] || (events[type] = []);
      events[type].push({f:func, c:ctx})
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
      var args = A.apply([], arguments);
      var list = events[args.shift()] || [];
      var i = list.length;
      for(var j=0;j<i;j++) list[j].f.apply(list[j].c, args)
    };
}
var u, module, cjs = module != u;
(cjs ? module : window)[(cjs ? 'exports' : 'Events')] = Events;


function McloudIO(host, port) {
    Events(this);
    var me = this;
    me.request_id = 0;
    me.requests = {};

    me.api = new ReconnectingWebSocket('ws://' + host + ':' + (port || 7080));


    me.api.onopen = function() {
        me.emit('connect')
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


    function call(task, args, kwargs) {
        var rqid = me.request_id++;
        me.api.send(JSON.stringify({
            task: task,
            id: rqid,
            args: args || [],
            kwargs: kwargs || {}
        }));

        return rqid;
    }

    function request(task, args, kwargs) {
        return new Promise(function(resolve, reject) {
            me.requests[call(task, args, kwargs)] = {
                resolve: resolve,
                reject: reject
            };
        });
    }

    me.ping = function() {
        return request('ping').then(function(response) {
            console.log('response', response);
        });
    };

    me._task_start = function(args, kwargs) {
        return request('task_start', args, kwargs).then(function(result) {
            return new McloudIOTask(me, result.id);
        });
    };

    /**
     * Public api
     */

    me.list = function() {
        return me._task_start(['list'])
    }
}

function McloudIOTask(api, task_id) {
    Events(this);
    var me = this;

    console.log('task.success.' + task_id);
    api.on('task.success.' + task_id, function(data) {
        console.log('Success!!!!');
        me.emit('complete', data);
    })
}


var io = new McloudIO(location.hostname);
io.on('connect', function() {
    console.log('I am connected!');

    io.ping();
    io.list().then(function(task) {
        console.log('List result:', task);

        task.on('complete', function(result) {
            console.log('Task completed', result);
        })
    });
});

io.on('raw_message', function(data) {
    console.log('Raw message', data);
});

io.on('event', function(name, data) {
    console.log('Raw event', name, data);
});




