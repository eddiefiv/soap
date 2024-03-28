// Constants
const WebSocket = require('ws');
const express = require('express');
const os = require('os');
const fs = require('fs');
const { Client, EmbedBuilder, GatewayIntentBits, WorkerReceivePayloadOp } = require('discord.js');
const { exit } = require('process');
const { botID } = require('./config/BOT_ID.json')

const PORT = 5001;
const WEBUI_PORT = 5000;

const NodeStatus = {
    ACTIVE: "active",
    INACTIVE: "inactive",
    WORKING: "working",
    OFFLINE: "offline"
}

// Other vars
var nodeWsClient = null;
var agentClients = [];
var workerClients = [];
var nodeStatus = NodeStatus.OFFLINE;

var channel = null;

// Try to grab the token from the file
let DISCORD_TOKEN = null
try {
    DISCORD_TOKEN = fs.readFileSync('./config/disctoken.txt', 'utf8').trim();
} catch {
    print("No token file found. Exiting.");
    exit(0);
}
const DISCORD_CHANNEL_ID = '1195786304563195984';

const discordClient = new Client({
    intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent,]
});
discordClient.login(DISCORD_TOKEN);

// ---- DISCORD FUNCTIONS ----
discordClient.on('ready', () => {
    // Discord channels
    channel = discordClient.channels.cache.get(DISCORD_CHANNEL_ID);

    print(`${discordClient.user.tag} has logged in`);
});
discordClient.on('messageCreate', (message) => {
    // Ignore messages from self
    if (message.author.id === botID) return;
    // Listen for messages from bots
    //print(message.content);
});

// Serve the webui
const app = express();

app.use(express.json());
app.use(express.static(__dirname + "/webui/"))
app.get("/", function (req, res) {
    res.sendFile(__dirname + "/webui/index.html");
});
app.get("/ping", function (req, res) {
    res.end(JSON.stringify({ "success": true, "msg": "pong" }));
})
app.get("/node-status", function (req, res) {
    res.end(JSON.stringify({ "success": true, "msg": { "nodeStatus": nodeStatus } }))
})
app.get("/node-metrics", function (req, res) {
    if (doesFileExist(__dirname + "/config/node_metrics.json")) {
        res.sendFile(__dirname + "/config/node_metrics.json");
    } else {
        res.end(JSON.stringify({ "success": false, "msg": "no metrics file" }));
    }
});
app.get("/config", function (req, res) {
    // First try to find gen
    if (doesFileExist(__dirname + "/config/gen.json")) {
        var genData = JSON.parse(fs.readFileSync(__dirname + "/config/gen.json"));
        var genConfigDirectory = genData['last_config_filepath'];

        // Check to see if the config found in gen exists, if so, send it
        if (doesFileExist(genConfigDirectory)) {
            res.sendFile(genConfigDirectory);
        }
        // Check if default config exists
    } else if (doesFileExist(__dirname + "/config/config.json")) {
        res.sendFile(__dirname + "/config/config.json");
    } else {
        res.end(JSON.stringify({ "success": false, "msg": "no config file" }));
    }
});
app.post("/prompt", function (req, res) {
    const body = JSON.stringify(req.body); // DOES NOT WORK LIKE JSON OBJECT, CANNOT body[item]!!!!
    // If a prompt was received, send to discord to be picked up by a node
    sendToDiscord({ 'type': 'WebUI Prompt', origin: 'WebUI | ' + os.hostname(), target: 'GCP soap Server', data: body });

    // Send the prompt to gcp
    GCPws.send(createWsMessage(type = 'webuiPrompt', origin = os.hostname(), target = 'GCP soap Server', data = { "prompt": req.body['content'] }))
});
app.post("/config", function (req, res) {
    // Write to the config
    // First try to find gen
    if (doesFileExist(__dirname + "/config/gen.json")) {
        var genData = JSON.parse(fs.readFileSync(__dirname + "/config/gen.json"));
        var genConfigDirectory = genData['last_config_filepath'];

        // Check to see if the config found in gen exists, if so, write to it
        if (doesFileExist(genConfigDirectory)) {
            fs.writeFile(genConfigDirectory, JSON.stringify(req.body, null, "\t"), (err) => {
                if (err) throw err;
                print("Config updated from WebUI");
                sendToAll(createWsMessage(type = 'update_config', origin = os.hostname(), target = "any", data = {}, false), null, false);
            });
        }
        // Check if default config exists
    } else if (doesFileExist(__dirname + "/config/config.json")) {
        fs.writeFile(__dirname + "/config/config.json", JSON.stringify(req.body, null, "\t"), (err) => {
            if (err) throw err;
            print("Config updated from WebUI");
            sendToAll(createWsMessage(type = 'update_config', origin = os.hostname(), target = "any", data = {}, false), null, false);
        });
    } else {
        res.end(JSON.stringify({ "success": false, "msg": "no config file" }));
    }
});
app.post("/node-status", function (req, res) {
    // Node is ready for functioning
    if (req.body['status'] === "active") {
        nodeStatus = NodeStatus.ACTIVE;
        res.end();
    } else if (req.body['status'] === "working") {
        nodeStatus = NodeStatus.WORKING;
        res.end();
    } else {
        nodeStatus = NodeStatus.INACTIVE;
        res.end();
    }

    // Let gcp know of a new node status so it can update records accordingly
    GCPws.send(createWsMessage(type = 'nodeStatusUpdate', origin = os.hostname(), target = "GCP soap Server", data = { "status": nodeStatus }));
});

// 404 handling
app.use((req, res) => {
    res.end("404");
});

app.listen(WEBUI_PORT, function () {
    print(`============ WebUI and API Gateway is open on port ${WEBUI_PORT} ============`);
});

function doesFileExist(filepath) {
    if (fs.existsSync(filepath)) { return true; }
    return false;
}

// Serve the websocket
const wss = new WebSocket.Server({ port: PORT });

function print(message) {
    const timestamp = new Date().toISOString();

    console.log(`[${timestamp}] ${message}`);
}

function createWsMessage(type, origin, target, data = {}, strfy = true) {
    if (strfy) {
        return JSON.stringify({ type: type, origin: origin, target: target, data: data });
    } else {
        return { type: type, origin: origin, target: target, data: data }
    }
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

function sendToDiscord(content) {
    const chn = discordClient.channels.fetch(DISCORD_CHANNEL_ID);
    // Send discord embed
    const embed = new EmbedBuilder().setColor('#0099ff').setTitle('Ingress Node Message').setDescription(`\n\n ** Payload **\n\n > ** Originating Device **\n > ${content['origin']} \n\n > ** Interaction Type **\n > ${content['type']} \n\n > ** From **\n > ${content['origin']} \n\n > ** Target **\n > ${content['target']} \n\n > ** Metadata **\n > ${content['metadata']} `).setAuthor({ name: os.hostname(), iconURL: "https://icons.iconarchive.com/icons/elegantthemes/beautiful-flat/256/Computer-icon.png" });

    chn.then(channel => channel.send(({
        embeds: [embed]
    })))
        .catch(error => console.log(`Discord Send Error: ${error}`));
}

function parseMessage(unparsed, parsedmessage, ws) {
    try {
        switch (parsedmessage.type) {
            case 'new_instruction':
                sendToAll(parsedmessage, ws, true);
                break;
            case 'function_invoke':
                sendToAll(parsedmessage, ws, true);
                break;
            case 'node_ready':
                // Check to make sure node doesn't exist already
                if (nodeWsClient == null) {
                    nodeWsClient = ws;
                } else {
                    print("Only one node can run at a time. Sending shutdown signals to future Nodes while one is already active.");
                    // Send shutdown message to node if it already exists
                    ws.send(createWsMessage(type = "node_shutdown", origin = os.hostname(), target = parsedmessage['origin'], data = { "graceful": false }));
                }
            case 'node_add_queue_item':
                sendToAll(parsedmessage, ws, false);
                break;
            case 'agent_ready':
                // Check to make sure agent isn't already in the list
                let agentPresent = false;
                agentClients.forEach(function (ac) {
                    if (ac['agentName'] === parsedmessage['origin']) {
                        agentPresent = true;
                    }
                });
                if (!agentPresent) {
                    agentClients.push({ 'wsClient': ws, 'agentName': parsedmessage['origin'] })
                }
                sendToAll(parsedmessage, ws, false);
                break;
            case 'agent_complete':
                sendToAll(parsedmessage, ws, true);
                break;
            case 'agent_dequeue':
                sendToAll(parsedmessage, ws, true);
                break;
            case 'agent_dequeue_success':
                sendToAll(parsedmessage, ws, true);
                break;
            case 'worker_ready':
                // Check to make sure worker isn't already in the list
                let workerPresent = false;
                workerClients.forEach(function (wc) {
                    if (wc['workerName'] === parsedmessage['origin']) {
                        workerPresent = true;
                    }
                });
                if (!workerPresent) {
                    workerClients.push({ 'wsClient': ws, 'workerName': parsedmessage['origin'] })
                }
                sendToAll(parsedmessage, ws, true);
                break;
            case 'worker_complete':
                sendToAll(parsedmessage, ws, true);
                break;
            case 'worker_dequeue':
                sendToAll(parsedmessage, ws, true);
                break;
            case 'request_current_state':
                sendToAll(parsedmessage, ws, false);
                break;
            default:
                print(`Unknown message type: ${parsedmessage.type} `);
        }
    } catch (error) {
        print(`Error parsing message with error: ${error} `);
    }
}

// ---- LOCALHOST WEBSOCKET FUNCTIONS ----
// Set the timeout options after creating the WebSocket server instance
wss.on('connection', function connection(ws) {
    print('Client connected');

    // Set the ping interval and timeout options on the WebSocket connection
    ws.isAlive = true;
    ws.on('pong', function heartbeat() {
        this.isAlive = true;
    });

    ws.on('message', function incoming(message) {
        print(`Received message: ${message} `);
        const parsedMessage = JSON.parse(message);

        // Send discord embed
        const embed = new EmbedBuilder().setColor('#0099ff').setTitle('Ingress Node Message').setDescription(`\n\n ** Payload **\n\n > ** Originating Device **\n > ${os.hostname()} \n\n > ** Interaction Type **\n > ${parsedMessage.type} \n\n > ** From **\n > ${parsedMessage.origin} \n\n > ** Target **\n > ${parsedMessage.target} \n\n > ** Metadata **\n > ${JSON.stringify(parsedMessage.data) !== '{}' ? JSON.stringify(parsedMessage.data) : "Empty"} `).setAuthor({ name: os.hostname(), iconURL: "https://icons.iconarchive.com/icons/elegantthemes/beautiful-flat/256/Computer-icon.png" });

        if (channel) {
            channel.send({
                embeds: [embed]
            })
                .catch(console.error);
        } else {
            console.error(`Discord channel with ID ${DISCORD_CHANNEL_ID} not found`);
        }

        // Parse incomming message
        parseMessage(message, parsedMessage, ws);
    });

    ws.on('close', function close() {
        // Find out who disconnected
        if (nodeWsClient == ws) {
            nodeWsClient = null;
            nodeStatus = NodeStatus.OFFLINE;

            print("Node disconnected. No more instruction will be parsed on this machine until a Node reset.");
            return;
        } else {
            agentClients.forEach(function (ac) {
                if (ac['wsClient'] == ws) {
                    delete agentClients[agentClients.indexOf(ac)];
                    print(ac['agentName'] + " disconnected");
                    return;
                }
            });

            workerClients.forEach(function (wc) {
                if (wc['wsClient'] == ws) {
                    delete workerClients[workerClients.indexOf(wc)];
                    print(wc['workerName'] + " disconnected")
                    return;
                }
            });
        }

        print("Unknown client disconnected");
    });
});

wss.on('listening', function () {
    print(`WebSocket server is listening on localhost port ${PORT} `);
});

// ---- GCP WEBSOCKET CLIENT ----
const GCPws = new WebSocket("ws://34.42.227.43:8080");

GCPws.on('open', function () {
    GCPws.send(createWsMessage(type = "serverConnect", origin = os.hostname(), target = "GCP soap Server", data = { "hostname": os.hostname() }));
});
GCPws.on('error', function () {
    console.log("Error during interaction with GCP WebSocket. Could be fatal.");
});
GCPws.on('message', function (message) {
    const parsedMessage = JSON.parse(message);

    switch (parsedMessage['type']) {
        case 'node_status_check':
            GCPws.send(createWsMessage(type = 'node_status_res', origin = os.hostname(), target = "GCP soap Server", data = { "nodeStatus": nodeStatus }));
            break;
        case 'new_instruction':
            console.log(parsedMessage);
            const inst = { instruction: parsedMessage['data']['instruction'] };
            const comp = { type: 'new_instruction', origin: os.hostname(), target: "any_node", data: inst };
            console.log("TESTING: " + JSON.stringify(comp));
            sendToAll(comp, null, false);
            break;
        default:
            print(`Unknown message type: ${parsedMessage['type']} `)
    }
});