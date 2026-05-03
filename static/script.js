document.addEventListener("DOMContentLoaded", function () {
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const chatBox = document.getElementById("chat-box");

    function displayMessage(message, sender) {
        const messageWrapper = document.createElement("div");
        messageWrapper.classList.add("message", sender === "user" ? "user-message" : "bot-message");

        const messageBubble = document.createElement("span");
        messageBubble.textContent = message;

        messageWrapper.appendChild(messageBubble);
        chatBox.appendChild(messageWrapper);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    async function sendMessage() {
        const userMessage = chatInput.value.trim();
        if (userMessage === "") return;

        displayMessage(userMessage, "user");
        chatInput.value = "";

        try {
            const response = await fetch("/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: userMessage }),
            });

            const data = await response.json();
            displayMessage(data.response + " 🐕", "bot");
        } catch (error) {
            console.error("Error:", error);
            displayMessage("⚠️ Sorry, something went wrong! 🐶", "bot");
        }
    }

    chatForm.addEventListener("submit", function (e) {
        e.preventDefault();
        sendMessage();
    });

    chatInput.addEventListener("keypress", function (event) {
        if (event.key === "Enter") {
            event.preventDefault();
            sendMessage();
        }
    });
});
