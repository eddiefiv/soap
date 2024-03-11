const promptInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const showNodesBtn = document.getElementById('show-nodes-btn');
const showConfigBtn = document.getElementById('show-config-btn');

// Config elements
const agentConfigSlider = document.getElementById('agent-slider');
const agentConfigCounter = document.getElementById('agent-counter');
const workerConfigSlider = document.getElementById('worker-slider');
const workerConfigCounter = document.getElementById('worker-counter');
const

const nodeModal = document.getElementById('node-modal');
const configModal = document.getElementById('config-modal');

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
            "content": promptInput.value
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
    const tableValues = document.querySelectorAll('.table-value'); //0 = Hostname, 1 = OS, 2 = Version, 3 = Machine, 4 = Processor, 5 = TVM, 6 = CPU Count
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
        document.getElementById('config-load-status').textContent = "Configs loaded from local config!"

        // Update the config elements

    } else {
        document.getElementById('config-load-status').textContent = "Config could not be loaded from local config. Ensure either config.json exists or autogen.json with a valid config filepath inside."
        document.getElementById('config-body').style.display = 'none';
    }
}

function onInputChanged(el) {
    el.style.fontWeight = 700;
    el.parentElement.parentElement.style.color = valueChangedColor;
}

// Modals
function openModal(modal) {
    modal.style.display = "block";
    activeModal = modal;
}

function closeActiveModal(modal) {
    modal.style.display = "none";
}

showNodesBtn.onclick = function () {
    openModal(nodeModal);
}

showConfigBtn.onclick = function () {
    openModal(configModal);
}

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
    var s = agentConfigSlider.parentElement.parentElement.querySelector('.cfg-title-container').style.color = valueChangedColor;
}

workerConfigSlider.oninput = function () {
    workerConfigCounter.innerHTML = this.value;

    // Get parent div (cfg-container)
    var s = workerConfigSlider.parentElement.parentElement.querySelector('.cfg-title-container').style.color = valueChangedColor;
}

// Fetch node metrics
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