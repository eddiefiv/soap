const WebSocket = require('ws');
const express = require('express');
const os = require('os');
const fs = require('fs');
const { REST, Client, EmbedBuilder, GatewayIntentBits, ThreadAutoArchiveDuration } = require('discord.js');
const { exit } = require('process');
const { botID } = require('./config/BOT_ID.json')

const PORT = 5001;
const WEBUI_PORT = 5000;

// Try to grab the token from the file
let DISCORD_TOKEN = null
try {
    DISCORD_TOKEN = fs.readFileSync('./config/disctoken.txt', 'utf8').trim();
} catch {
    print("No token file found. Exiting.")
    exit(0);
}
const DISCORD_CHANNEL_ID = '1195786304563195984';

const discordClient = new Client({
    intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent,]
});
discordClient.login(DISCORD_TOKEN);

// Discord channels
const channel = discordClient.channels.cache.get(DISCORD_CHANNEL_ID);

// ---- DISCORD FUNCTIONS ----
discordClient.on('ready', () => {
    print(`${discordClient.user.tag} has logged in`);
})
discordClient.on('messageCreate', (message) => {
    // Ignore messages from self
    if (message.author.id === botID) return;
    // Listen for messages from bots
    print(message.content);
})


// Serve the webui
const app = express();

app.use(express.json());
app.use(express.static(__dirname + "/webui/"))
app.get("/", function (req, res) {
    res.sendFile(__dirname + "/webui/index.html");
});
app.get("/node-metrics", function (req, res) {
    try {
        res.sendFile(__dirname + "/config/node_metrics.json");
    } catch {
        res.end("No node_metrics.json found.");
    }
});
app.get("/config", function (req, res) {
    // First try to find autogen
    if (doesFileExist(__dirname + "/config/autogen.json")) {
        var autogenData = JSON.parse(fs.readFileSync(__dirname + "/config/autogen.json"));
        var autogenConfigDirectory = autogenData['last_config_filepath'];

        // Check to see if the config found in autogen exists, if so, send it
        if (doesFileExist(autogenConfigDirectory)) {
            res.sendFile(autogenConfigDirectory);
        }
        // Check if default config exists
    } else if (doesFileExist(__dirname + "/config/config.json")) {
        res.sendFile(__dirname + "/config/config.json");
    }
});
app.post("/prompt", function (req, res) {
    // If a prompt was received, send t
    print(JSON.stringify(req.body));
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

function parseMessage(unparsed, parsedmessage, ws) {
    try {
        switch (parsedmessage.type) {
            case 'new_instruction':
                sendToAll(parsedmessage, ws, true);
                break;
            case 'function_invoke':
                sendToAll(parsedmessage, ws, true);
                break;
            case 'node_add_queue_item':
                sendToAll(parsedmessage, ws, false);
                break;
            case 'agent_ready':
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
                print(`Unknown message type: ${parsedmessage.type}`)
        }
    } catch (error) {
        print(`Error parsing message with error: ${error}`)
    }
}

// ---- WEBSOCKET FUNCTIONS ----
// Set the timeout options after creating the WebSocket server instance
wss.on('connection', function connection(ws) {
    print('Client connected');

    // Set the ping interval and timeout options on the WebSocket connection
    ws.isAlive = true;
    ws.on('pong', function heartbeat() {
        this.isAlive = true;
    });

    ws.on('message', function incoming(message) {
        print(`Received message: ${message}`);
        const parsedMessage = JSON.parse(message);

        // Send discord embed
        const embed = new EmbedBuilder().setColor('#0099ff').setTitle('WebSocket Interaction Received').setDescription(`\n\n**Payload**\n\n> **Originating Device**\n> ${os.hostname()}\n\n> **Interaction Type**\n> ${parsedMessage.type}\n\n> **From**\n> ${parsedMessage.origin}\n\n> **Target**\n> ${parsedMessage.target}\n\n> **Metadata**\n> ${JSON.stringify(parsedMessage.data) !== '{}' ? JSON.stringify(parsedMessage.data) : "Empty"}`).setAuthor({ name: "Corporate America", iconURL: "https://icons.iconarchive.com/icons/elegantthemes/beautiful-flat/256/Computer-icon.png" });

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
        print(`Client disconnected`);
    });
});

wss.on('listening', function () {
    print(`WebSocket server is listening on localhost port ${PORT}`);
});