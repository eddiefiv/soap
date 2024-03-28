// Base
var promptInput = document.getElementById('message-input');

// Config elements
var agentConfigSlider = document.getElementById('agent-slider');
var agentConfigCounter = document.getElementById('agent-counter');
var workerConfigSlider = document.getElementById('worker-slider');
var workerConfigCounter = document.getElementById('worker-counter');

// Node configs
var nodeModelFilepath = document.getElementById('node-fp-input');
var nodeChatFormat = document.getElementById('node-chat-format-input');
var nodeCtxSize = document.getElementById('node-ctx-input');
var nodeLayerCount = document.getElementById('node-layer-input');
var nodeBatchSize = document.getElementById('node-batch-input');

// Agent configs
var agentModelFilepath = document.getElementById('agent-fp-input');
var agentChatFormat = document.getElementById('agent-chat-format-input');
var agentCtxSize = document.getElementById('agent-ctx-input');
var agentLayerCount = document.getElementById('agent-layer-input');
var agentBatchSize = document.getElementById('agent-batch-input');

// Worker configs
var workerModelFilepath = document.getElementById('worker-fp-input');
var workerChatFormat = document.getElementById('worker-chat-format-input');
var workerCtxSize = document.getElementById('worker-ctx-input');
var workerLayerCount = document.getElementById('worker-layer-input');
var workerBatchSize = document.getElementById('worker-batch-input');

// Hyperparams
var temp = document.getElementById('temp-input');
var topP = document.getElementById('top_p-input');
var minP = document.getElementById('min_p-input');
var maxTokens = document.getElementById('max_token-input');
var repeatPenalty = document.getElementById('repeat_penalty-input');
var presencePenalty = document.getElementById('presence_penalty-input');
var topK = document.getElementById('top_k-input');
var microstatEta = document.getElementById('meta-input');
var microstatTau = document.getElementById('mtau-input');

// Modals
const nodeModal = document.getElementById('node-modal');
const configModal = document.getElementById('config-modal');

// Buttons
const sendBtn = document.getElementById('send-btn');
const showNodesBtn = document.getElementById('show-nodes-btn');
const showConfigBtn = document.getElementById('show-config-btn');
var configSubmitButton = document.getElementById('submit-configs');
var nodeStatusButton = document.getElementById('node-status-btn');


// Color
const valueChangedColor = "#c850c0";

var activeModal = null;

function sendMessage() {
    // Exit function if input is empty
    if (promptInput.value == "") {
        return;
    }
    fetch(window.location.protocol + "/prompt", {
        method: "POST",
        body: JSON.stringify({
            "type": "webui_prompt",
            "content": promptInput.value,
            "sub_message": "WebUI Prompt"
        }),
        headers: {
            'Content-Type': 'application/json'
        }
    })
        .then((response) => response.json())
        .then((json) => console.log(json));

    // Reset the input
    promptInput.value = "";
}

promptInput.addEventListener("keyup", function (event) {
    if (event.key == "Enter") {
        sendMessage();
    }
});

function setNodeMetrics(data) {
    console.log(data);
    var tableValues = document.querySelectorAll('.table-value'); //0 = Hostname, 1 = OS, 2 = Version, 3 = Machine, 4 = Processor, 5 = TVM, 6 = CPU Count
    if (data['hostname']) {
        document.getElementById('metrics-none1').style.display = 'none';
        document.getElementById('metrics-table1').style.dislpay = 'table';
        tableValues[0].textContent = data['hostname'];
        tableValues[1].textContent = data['system'];
        tableValues[2].textContent = data['version'];
        tableValues[3].textContent = data['machine'];
        tableValues[4].textContent = data['processor'];
        tableValues[5].textContent = data['total_virtual_memory'];
        tableValues[6].textContent = data['cpu_count'];
    } else {
        document.getElementById('metrics-none1').style.display = 'block';
        document.getElementById('metrics-table1').style.display = 'none';
    }

}

function setConfigs(data) {
    console.log(data);
    if (data['general']) {
        document.getElementById('config-load-status').textContent = "Configs loaded from local config! (Reload the page to view the most recent version of configs)";

        const general = data['general'];
        const modelJson = data['network_configs'];

        // Update the config elements
        // General configs
        agentConfigSlider.value = general['agent_count'];
        agentConfigCounter.textContent = general['agent_count'];
        workerConfigSlider.value = general['worker_count'];
        workerConfigCounter.textContent = general['worker_count'];

        // Model configs
        nodeModelFilepath.value = modelJson['node']['filepath'];
        nodeChatFormat.selectedIndex = modelJson['node']['chat_format']['id'];
        nodeCtxSize.value = modelJson['node']['ctx_size'];
        nodeLayerCount.value = modelJson['node']['gpu_layer_count'];
        nodeBatchSize.value = modelJson['node']['batch_size'];

        agentModelFilepath.value = modelJson['agent']['filepath'];
        agentChatFormat.selectedIndex = modelJson['agent']['chat_format']['id'];
        agentCtxSize.value = modelJson['agent']['ctx_size'];
        agentLayerCount.value = modelJson['agent']['gpu_layer_count'];
        agentBatchSize.value = modelJson['agent']['batch_size'];

        workerModelFilepath.value = modelJson['worker']['filepath'];
        workerChatFormat.selectedIndex = modelJson['worker']['chat_format']['id'];
        workerCtxSize.value = modelJson['worker']['ctx_size'];
        workerLayerCount.value = modelJson['worker']['gpu_layer_count'];
        workerBatchSize.value = modelJson['worker']['batch_size'];

        // Hyperparam configs
        temp.value = modelJson['hyperparams']['temperature'];
        maxTokens.value = modelJson['hyperparams']['max_tokens'];
        topP.value = modelJson['hyperparams']['top_p'];
        minP.value = modelJson['hyperparams']['min_p'];
        repeatPenalty.value = modelJson['hyperparams']['repeat_penalty'];
        presencePenalty.value = modelJson['hyperparams']['presence_penalty'];
        topK.value = modelJson['hyperparams']['top_k'];
        microstatEta.value = modelJson['hyperparams']['microstat_eta'];
        microstatTau.value = modelJson['hyperparams']['microstat_tau'];

    } else {
        document.getElementById('config-load-status').textContent = "Config could not be loaded from local config. Ensure either config.json exists or gen.json with a valid config filepath inside."
        document.getElementById('config-body').style.display = 'none';
        configSubmitButton.disabled = true;
    }
}

function setNodeStatus(data) {
    console.log(data);
    if (data != undefined && data['success']) {
        if (data['msg']['nodeStatus'] === "active") {
            if (nodeStatusButton.classList.contains('working-status')) {
                nodeStatusButton.classList.remove("working-status");
            }
            nodeStatusButton.classList.add("active-status");

            nodeStatusButton.disabled = false;
            nodeStatusButton.textContent = "Current Node status: Active";
        } else if (data['msg']['nodeStatus'] === "inactive") {
            if (nodeStatusButton.classList.contains('active-status')) {
                nodeStatusButton.classList.remove("active-status");
            } else if (nodeStatusButton.classList.contains('working-status')) {
                nodeStatusButton.classList.remove("working-status");
            }
            nodeStatusButton.disabled = false;
            nodeStatusButton.textContent = "Current Node status: Inactive";
        } else if (data['msg']['nodeStatus'] === "working") {
            if (nodeStatusButton.classList.contains('active-status')) {
                nodeStatusButton.classList.remove("active-status");
            }
            nodeStatusButton.classList.add("working-status");

            nodeStatusButton.disabled = false;
            nodeStatusButton.textContent = "Current Node status: Working";
        }
        else {
            if (nodeStatusButton.classList.contains('active-status')) {
                nodeStatusButton.classList.remove("active-status");
            } else if (nodeStatusButton.classList.contains('working-status')) {
                nodeStatusButton.classList.remove("working-status");
            }
            nodeStatusButton.disabled = true;
            nodeStatusButton.textContent = "Current Node status: Offline";
        }
    } else {
        if (nodeStatusButton.classList.contains('active-status')) {
            nodeStatusButton.classList.remove("active-status");
        } else if (nodeStatusButton.classList.contains('working-status')) {
            nodeStatusButton.classList.remove("working-status");
        }
        nodeStatusButton.disabled = true;
        nodeStatusButton.textContent = "No connection to backend. Attempting to re-establish";
    }
}

function setLocalhostStatus(status) {
    if (status) {
        promptInput.placeholder = "Prompt for soap network...";
        promptInput.disabled = false;
        sendBtn.disabled = false;

        document.getElementById('config-load-status').textContent = "Configs loaded from local config! (Reload the page to view the most recent version of configs)";
        document.getElementById('config-body').style.display = 'flex';
    } else {
        promptInput.placeholder = "No connection to localhost. Ensure localserve.js is active. Attempting to re-establish...";

        document.getElementById('config-load-status').textContent = "Cannot establish a connection to the backend for config retrieval."
        document.getElementById('config-body').style.display = 'none';
        configSubmitButton.disabled = true;
        nodeStatusButton.disabled = true;

        promptInput.disabled = true;
        sendBtn.disabled = true;
    }
}

// Modals
function openModal(modal) {
    modal.style.display = "block";
    activeModal = modal;

    if (modal === configModal) {
        configSubmitButton.textContent = "Submit changes";
    }
}

function closeActiveModal() {
    activeModal.style.display = "none";
}

// Buttons
showNodesBtn.onclick = function () {
    openModal(nodeModal);
}

showConfigBtn.onclick = function () {
    openModal(configModal);
}

configSubmitButton.onclick = function () {
    const dataToSend = {
        "general": {
            "agent_count": parseInt(agentConfigSlider.value),
            "worker_count": parseInt(workerConfigSlider.value)
        },
        "network_configs": {
            "node": {
                "filepath": nodeModelFilepath.value === "" ? null : nodeModelFilepath.value,
                "ctx_size": parseInt(nodeCtxSize.value),
                "gpu_layer_count": parseInt(nodeLayerCount.value),
                "batch_size": parseInt(nodeBatchSize.value),
                "chat_format": {
                    "format": nodeChatFormat.options[nodeChatFormat.selectedIndex].value,
                    "id": nodeChatFormat.selectedIndex
                }
            },
            "agent": {
                "filepath": agentModelFilepath.value === "" ? null : agentModelFilepath.value,
                "ctx_size": parseInt(agentCtxSize.value),
                "gpu_layer_count": parseInt(agentLayerCount.value),
                "batch_size": parseInt(agentBatchSize.value),
                "chat_format": {
                    "format": agentChatFormat.options[agentChatFormat.selectedIndex].value,
                    "id": agentChatFormat.selectedIndex
                }
            },
            "worker": {
                "filepath": workerModelFilepath.value === "" ? null : workerModelFilepath.value,
                "ctx_size": parseInt(workerCtxSize.value),
                "gpu_layer_count": parseInt(workerLayerCount.value),
                "batch_size": parseInt(workerBatchSize.value),
                "chat_format": {
                    "format": workerChatFormat.options[workerChatFormat.selectedIndex].value,
                    "id": workerChatFormat.selectedIndex
                }
            },
            "hyperparams": {
                "temperature": parseFloat(temp.value),
                "max_tokens": parseInt(maxTokens.value),
                "top_p": parseFloat(topP.value),
                "min_p": parseFloat(minP.value),
                "repeat_penalty": parseFloat(repeatPenalty.value),
                "presence_penalty": parseFloat(presencePenalty.value),
                "top_k": parseFloat(topK.value),
                "microstat_eta": parseFloat(microstatEta.value),
                "microstat_tau": parseFloat(microstatTau.value)
            }
        }
    }

    fetch(window.location.protocol + "/config", {
        method: "POST",
        body: JSON.stringify(dataToSend, null, "\t"),
        headers: {
            'Content-Type': 'application/json'
        }
    });

    // Close modal and reset styling
    configSubmitButton.disabled = true;
    configSubmitButton.textContent = "Configs submitted to local!";

    document.querySelectorAll('.cfg-container').forEach(function each(el) {
        el.querySelectorAll('.cfg-title-container').forEach(function eachTitle(title) {
            title.style.color = "white";
        });

        const inputChildContainer = el.querySelector('.input-container');

        // If is input
        if (inputChildContainer) {
            const inputChild = inputChildContainer.querySelector('.input');
            inputChild.style.color = "";
            inputChild.style.fontWeight = "";
        }
    });
}

// Misc
window.onclick = function (event) {
    if (event.target == activeModal) {
        activeModal.style.display = "none";
        activeModal = null;
    }
}

// Configs
agentConfigSlider.oninput = function () {
    agentConfigCounter.innerHTML = this.value;

    // Get parent div (cfg-container)
    agentConfigSlider.parentElement.parentElement.querySelector('.cfg-title-container').style.color = valueChangedColor;
}

workerConfigSlider.oninput = function () {
    workerConfigCounter.innerHTML = this.value;

    // Get parent div (cfg-container)
    workerConfigSlider.parentElement.parentElement.querySelector('.cfg-title-container').style.color = valueChangedColor;
}

configModal.addEventListener('change', function (event) {
    // Enable submit on a change
    configSubmitButton.disabled = false;
    configSubmitButton.textContent = "Submit changes";

    // If is not one of the manually handled sliders
    if (event.target != agentConfigSlider && event.target != workerConfigSlider) {
        event.target.style.color = valueChangedColor;
        event.target.style.fontWeight = 700;
        event.target.parentElement.parentElement.style.color = valueChangedColor;
    }
});

window.addEventListener('load', function () {
    var fetchInterval = 3000;

    this.setInterval(fetchNodeStatus, fetchInterval);
    this.setInterval(pingLocalhost, fetchInterval);
})

// Fetches
fetch(window.location.protocol + "/node-metrics", {
    method: "GET",
    headers: {
        'Content-Type': 'application/json'
    }
})
    .then((response) => response.json())
    .then((json) => setNodeMetrics(json));

fetch(window.location.protocol + "/config", {
    method: "GET",
    headers: {
        'Content-Type': 'application/json'
    }
})
    .then((response) => response.json())
    .then((json) => setConfigs(json));

function fetchNodeStatus() {
    fetch(window.location.protocol + "/node-status", {
        method: "GET",
        headers: {
            'Content-Type': 'application/json'
        }
    })
        .then((response) => response.json())
        .catch((error) => console.error(error))
        .then((json) => setNodeStatus(json));
}

function pingLocalhost() {
    fetch(window.location.protocol + "/ping", {
        method: "GET",
        headers: {
            'Content-Type': 'application/json'
        }
    })
        .then((response) => response.json())
        .then((json) => {
            if (json['success'] && json['msg'] === "pong") {
                setLocalhostStatus(true);
                console.log("Connection to localhost is good!");
            } else {
                setLocalhostStatus(false);
            }
        })
        .catch((error) => setLocalhostStatus(false));
}