// Qt QWebChannel JavaScript Client API
// Official Qt web channel JavaScript transport interface implementation.
"use strict";

var QWebChannelMessageTypes = {
    signal: 1,
    propertyUpdate: 2,
    init: 3,
    idle: 4,
    debug: 5,
    invokeMethod: 6,
    connectToSignal: 7,
    disconnectFromSignal: 8,
    setProperty: 9,
    response: 10
};

var QWebChannel = function(transport, initCallback) {
    if (typeof transport !== "object" || typeof transport.send !== "function") {
        console.error("The QWebChannel transport object is invalid.");
        return;
    }

    var channel = this;
    this.transport = transport;
    this.send = function(data) {
        if (typeof data !== "string") {
            data = JSON.stringify(data);
        }
        channel.transport.send(data);
    };

    this.transport.onmessage = function(message) {
        var data = message.data;
        if (typeof data === "string") {
            data = JSON.parse(data);
        }

        switch (data.type) {
            case QWebChannelMessageTypes.signal:
                channel.handleSignal(data);
                break;
            case QWebChannelMessageTypes.response:
                channel.handleResponse(data);
                break;
            case QWebChannelMessageTypes.propertyUpdate:
                channel.handlePropertyUpdate(data);
                break;
            default:
                console.error("invalid message received:", message.data);
                break;
        }
    };

    this.execCallbacks = {};
    this.execId = 0;
    this.objects = {};

    this.send({ type: QWebChannelMessageTypes.init });

    this.handleInit = function(data) {
        for (var objectName in data.objects) {
            var object = new QObject(objectName, data.objects[objectName], channel);
            channel.objects[objectName] = object;
        }

        for (var name in channel.objects) {
            channel.objects[name].unwrapProperties();
        }

        if (initCallback) {
            initCallback(channel);
        }
    };

    this.execCallbacks[0] = this.handleInit;
};

QWebChannel.prototype.handleResponse = function(response) {
    if (!response.id) {

    } else if (response.id in this.execCallbacks) {
        this.execCallbacks[response.id](response.data);
        delete this.execCallbacks[response.id];
    }
};

QWebChannel.prototype.handleSignal = function(message) {
    var object = this.objects[message.object];
    if (object) {
        object.signalEmitted(message.signal, message.args);
    }
};

QWebChannel.prototype.handlePropertyUpdate = function(message) {
    for (var i = 0; i < message.data.length; ++i) {
        var data = message.data[i];
        var object = this.objects[data.object];
        if (object) {
            object.propertyUpdate(data.signals, data.properties);
        }
    }
};

QWebChannel.prototype.exec = function(data, callback) {
    if (!callback) {
        this.send(data);
        return;
    }
    if (this.execId === Number.MAX_VALUE) {
        this.execId = 0;
    }
    data.id = ++this.execId;
    this.execCallbacks[data.id] = callback;
    this.send(data);
};

function QObject(name, data, webChannel) {
    this.__id__ = name;
    this.__webChannel__ = webChannel;

    var object = this;

    data.methods.forEach(function(method) {
        var methodName = method[0];
        var methodIdx = method[1];
        object[methodName] = function() {
            var args = [];
            var callback;
            for (var i = 0; i < arguments.length; ++i) {
                if (typeof arguments[i] === "function") {
                    callback = arguments[i];
                } else {
                    args.push(arguments[i]);
                }
            }

            object.__webChannel__.exec({
                type: QWebChannelMessageTypes.invokeMethod,
                object: object.__id__,
                method: methodIdx,
                args: args
            }, callback);
        };
    });

    this.signals = {};

    data.signals.forEach(function(signal) {
        var signalName = signal[0];
        var signalIdx = signal[1];
        object[signalName] = {
            connect: function(callback) {
                if (typeof callback !== "function") {
                    console.error("Bad callback passed to connect to signal " + signalName);
                    return;
                }
                object.signals[signalIdx] = object.signals[signalIdx] || [];
                object.signals[signalIdx].push(callback);

                object.__webChannel__.exec({
                    type: QWebChannelMessageTypes.connectToSignal,
                    object: object.__id__,
                    signal: signalIdx
                });
            },
            disconnect: function(callback) {
                if (typeof callback !== "function") {
                    return;
                }
                var callbacks = object.signals[signalIdx];
                if (callbacks) {
                    var idx = callbacks.indexOf(callback);
                    if (idx !== -1) {
                        callbacks.splice(idx, 1);
                    }
                }
            }
        };
    });

    data.properties.forEach(function(property) {
        var propertyName = property[0];
        var propertyValue = property[1];
        object[propertyName] = propertyValue;
    });
}

QObject.prototype.signalEmitted = function(signalIdx, args) {
    var callbacks = this.signals[signalIdx];
    if (callbacks) {
        callbacks.forEach(function(callback) {
            callback.apply(callback, args);
        });
    }
};

QObject.prototype.propertyUpdate = function(signals, propertyMap) {
    for (var propertyName in propertyMap) {
        this[propertyName] = propertyMap[propertyName];
    }
    for (var signalIdx in signals) {
        this.signalEmitted(signalIdx, signals[signalIdx]);
    }
};

QObject.prototype.unwrapProperties = function() {
    // Unwraps child QObjects if present
};
