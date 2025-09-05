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
