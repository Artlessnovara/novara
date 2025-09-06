// This file should be included in any page that needs to use the socket.io connection.
// It initializes the socket and makes it available as a global 'socket' variable.

// Make sure to include the Socket.IO client library before this script.
// <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>

var socket = io();

socket.on('connect', function() {
    console.log('Socket.IO connected via shared handler!');
});

// You can add other global, non-page-specific handlers here if needed.
// For example, a handler for global notifications.
socket.on('error', function(data) {
    console.error('Socket.IO Error:', data.msg);
    alert('An error occurred: ' + data.msg);
});

function register_chat_room_handlers(chat_info, current_user_id) {
    socket.on('message', function(data) {
        console.log('New message received:', data);
        if (data.room_id !== chat_info.id) {
            return; // Ignore messages for other rooms
        }

        const messageArea = document.querySelector('.message-area');
        const messageBubbleWrapper = document.createElement('div');
        messageBubbleWrapper.classList.add('message-bubble-wrapper');
        messageBubbleWrapper.dataset.messageId = data.message_id;
        if (data.user_id === current_user_id) {
            messageBubbleWrapper.classList.add('sender');
        } else {
            messageBubbleWrapper.classList.add('receiver');
        }

        let fileHtml = '';
        if (data.file_path) {
            const fileName = data.file_name.toLowerCase();
            if (fileName.match(/\.(png|jpg|jpeg|gif|webp)$/)) {
                fileHtml = `<img src="/static/${data.file_path}" alt="${data.file_name}" class="message-image">`;
            } else if (fileName.match(/\.(mp4|webm|ogg)$/) && fileName.includes('video')) {
                fileHtml = `<video src="/static/${data.file_path}" controls class="message-video"></video>`;
            } else if (fileName.match(/\.(mp3|wav|webm|ogg)$/)) {
                fileHtml = `<audio src="/static/${data.file_path}" controls class="message-audio"></audio>`;
            } else {
                fileHtml = `<a href="/static/${data.file_path}" class="message-file" download>
                                <i class="fa-solid fa-file-arrow-down"></i> ${data.file_name}
                            </a>`;
            }
        }

        let contentHtml;
        try {
            const contentData = JSON.parse(data.content);
            if (contentData && contentData.type === 'contact') {
                contentHtml = `
                    <div class="contact-card">
                        <img src="/static/profile_pics/${contentData.profile_pic}" alt="${contentData.name}">
                        <div class="contact-card-info">
                            <strong>${contentData.name}</strong>
                            <a href="/user/${contentData.user_id}">View Profile</a>
                        </div>
                    </div>
                `;
            } else if (contentData && contentData.type === 'location') {
                contentHtml = `
                    <div class="location-card">
                        <a href="https://www.openstreetmap.org/?mlat=${contentData.latitude}&mlon=${contentData.longitude}#map=15/${contentData.latitude}/${contentData.longitude}" target="_blank">
                            <i class="fa-solid fa-map-location-dot"></i>
                            <span>View Location</span>
                        </a>
                    </div>
                `;
            } else {
                throw new Error("Not a contact card");
            }
        } catch (e) {
            contentHtml = data.content ? `<p class="message-content">${data.content}</p>` : '';
        }

        const messageBubble = `
            <div class="message-bubble">
                ${fileHtml}
                ${contentHtml}
                <span class="message-timestamp">${new Date(data.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
            </div>
        `;
        messageBubbleWrapper.innerHTML = messageBubble;
        messageArea.appendChild(messageBubbleWrapper);
        messageArea.scrollTop = messageArea.scrollHeight;
    });

    // Read receipts logic
    const unreadMessages = new Map();
    const observer = new IntersectionObserver((entries) => {
        const messagesToMarkAsRead = [];
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const messageId = entry.target.dataset.messageId;
                if (unreadMessages.has(messageId)) {
                    messagesToMarkAsRead.push(messageId);
                    unreadMessages.delete(messageId);
                }
            }
        });

        if (messagesToMarkAsRead.length > 0) {
            socket.emit('mark_as_read', {
                message_ids: messagesToMarkAsRead,
                room_id: chat_info.id
            });
        }
    }, { threshold: 0.9 });

    function initializeReadReceipts() {
        document.querySelectorAll('.message-bubble-wrapper.receiver').forEach(bubble => {
            const messageId = bubble.dataset.messageId;
            if (messageId && bubble.dataset.isRead === 'false') {
                unreadMessages.set(messageId, bubble);
                observer.observe(bubble);
            }
        });
    }

    socket.on('messages_read', (data) => {
        if (data.room_id === chat_info.id) {
            data.message_ids.forEach(messageId => {
                const messageBubble = document.querySelector(`.message-bubble-wrapper.sender[data-message-id="${messageId}"]`);
                if (messageBubble) {
                    const receipt = messageBubble.querySelector('.read-receipts i');
                    if (receipt) {
                        receipt.classList.remove('fa-check');
                        receipt.classList.add('fa-check-double');
                    }
                    messageBubble.dataset.isRead = 'true';
                }
            });
        }
    });

    initializeReadReceipts();
}

function register_chat_room_handlers(chat_info, current_user_id) {
    socket.on('message', function(data) {
        console.log('New message received:', data);
        if (data.room_id !== chat_info.id) {
            return; // Ignore messages for other rooms
        }

        const messageArea = document.querySelector('.message-area');
        const messageBubbleWrapper = document.createElement('div');
        messageBubbleWrapper.classList.add('message-bubble-wrapper');
        messageBubbleWrapper.dataset.messageId = data.message_id;
        if (data.user_id === current_user_id) {
            messageBubbleWrapper.classList.add('sender');
        } else {
            messageBubbleWrapper.classList.add('receiver');
        }

        let fileHtml = '';
        if (data.file_path) {
            const fileName = data.file_name.toLowerCase();
            if (fileName.match(/\.(png|jpg|jpeg|gif|webp)$/)) {
                fileHtml = `<img src="/static/${data.file_path}" alt="${data.file_name}" class="message-image">`;
            } else if (fileName.match(/\.(mp4|webm|ogg)$/) && fileName.includes('video')) {
                fileHtml = `<video src="/static/${data.file_path}" controls class="message-video"></video>`;
            } else if (fileName.match(/\.(mp3|wav|webm|ogg)$/)) {
                fileHtml = `<audio src="/static/${data.file_path}" controls class="message-audio"></audio>`;
            } else {
                fileHtml = `<a href="/static/${data.file_path}" class="message-file" download>
                                <i class="fa-solid fa-file-arrow-down"></i> ${data.file_name}
                            </a>`;
            }
        }

        let contentHtml;
        try {
            const contentData = JSON.parse(data.content);
            if (contentData && contentData.type === 'contact') {
                contentHtml = `
                    <div class="contact-card">
                        <img src="/static/profile_pics/${contentData.profile_pic}" alt="${contentData.name}">
                        <div class="contact-card-info">
                            <strong>${contentData.name}</strong>
                            <a href="/user/${contentData.user_id}">View Profile</a>
                        </div>
                    </div>
                `;
            } else if (contentData && contentData.type === 'location') {
                contentHtml = `
                    <div class="location-card">
                        <a href="https://www.openstreetmap.org/?mlat=${contentData.latitude}&mlon=${contentData.longitude}#map=15/${contentData.latitude}/${contentData.longitude}" target="_blank">
                            <i class="fa-solid fa-map-location-dot"></i>
                            <span>View Location</span>
                        </a>
                    </div>
                `;
            } else {
                throw new Error("Not a contact card");
            }
        } catch (e) {
            contentHtml = data.content ? `<p class="message-content">${data.content}</p>` : '';
        }

        const messageBubble = `
            <div class="message-bubble">
                ${fileHtml}
                ${contentHtml}
                <span class="message-timestamp">${new Date(data.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
            </div>
        `;
        messageBubbleWrapper.innerHTML = messageBubble;
        messageArea.appendChild(messageBubbleWrapper);
        messageArea.scrollTop = messageArea.scrollHeight;
    });
}
