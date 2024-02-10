const WebSocket = require('ws');

const PORT = 5002;

const wss = new WebSocket.Server({ port: PORT });

function print(message) {
    const timestamp = new Date().toISOString();

    console.log(`[${timestamp}] ${message}`);
}

function createWsMessage(type, origin, target, data = {}) {
    return JSON.stringify({ type: type, origin: origin, target: target, data: data });
}

function sendToAll(message, sender, exceptSender) {
    if (exceptSender) {
        wss.clients.forEach(function eachNoSender(client) {
            if (client !== sender && client.readyState === WebSocket.OPEN) {
                client.send(JSON.stringify(message));
            }
        });
    } else {
        wss.clients.forEach(function each(client) {
            if (client.readyState === WebSocket.OPEN) {
                client.send(JSON.stringify(message));
            }
        });
    }
}

function parseMessage(message, ws) {
    try {
        switch (message.type) {
            case 'function_invoke':
                sendToAll(message, ws, true);
            case 'agent_ready':
                ws.send(createWsMessage('agent_dequeue', 'locserv', message.origin));
            default:
                print(`Unknown message type: ${message.type}`)
        }
    } catch (error) {
        print(`Error parsing message with error: ${error}`)
    }
}

// Set the timeout options after creating the WebSocket server instance
wss.on('connection', function connection(ws) {
    print('Client connected');

    // Set the ping interval and timeout options on the WebSocket connection
    ws.isAlive = true;
    ws.on('pong', function heartbeat() {
        this.isAlive = true;
    });

    ws.on('message', function incoming(message) {
        const timestamp = new Date().toISOString();
        print(`Received message: ${message}`);

        // Parse incomming message
        parseMessage(JSON.parse(message), ws);
    });

    ws.on('close', function close() {
        print(`Client disconnected`);
    });
});

wss.on('listening', function () {
    print(`WebSocket server is listening on port ${PORT}`);
});

print(`Starting WebSocket server on port ${PORT}...`);