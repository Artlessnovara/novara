// This file handles Firebase initialization and push notification setup.

// --- STEP 1: PASTE YOUR FIREBASE CONFIGURATION HERE ---
// Replace this with the configuration object from your Firebase project.
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_AUTH_DOMAIN",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_STORAGE_BUCKET",
  messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
  appId: "YOUR_APP_ID",
  measurementId: "YOUR_MEASUREMENT_ID"
};
// ---------------------------------------------------------

// Initialize Firebase
try {
  if (firebaseConfig.apiKey !== "YOUR_API_KEY") {
    firebase.initializeApp(firebaseConfig);
    const messaging = firebase.messaging();

    // --- STEP 2: Main Notification Logic ---
    function requestNotificationPermission() {
      console.log('Requesting notification permission...');
      Notification.requestPermission().then((permission) => {
        if (permission === 'granted') {
          console.log('Notification permission granted.');
          // Get the token
          getAndSendToken(messaging);
        } else {
          console.log('Unable to get permission to notify.');
        }
      });
    }

    function getAndSendToken(messaging) {
        // IMPORTANT: You need a `firebase-messaging-sw.js` file for this to work.
        messaging.getToken({ vapidKey: 'YOUR_VAPID_KEY_FROM_FIREBASE_SETTINGS' })
        .then((currentToken) => {
            if (currentToken) {
                console.log('FCM Token:', currentToken);
                sendTokenToServer(currentToken);
            } else {
                console.log('No registration token available. Request permission to generate one.');
            }
        }).catch((err) => {
            console.log('An error occurred while retrieving token. ', err);
        });
    }

    function sendTokenToServer(token) {
        fetch('/api/fcm_token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ token: token }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                console.log('Token sent to server successfully.');
            } else {
                console.error('Failed to send token to server:', data.message);
            }
        })
        .catch((error) => {
            console.error('Error sending token to server:', error);
        });
    }

    // --- STEP 3: Listen for foreground messages ---
    messaging.onMessage((payload) => {
        console.log('Message received in foreground. ', payload);
        // You can show a custom in-app notification here.
        // For example, using a library like Toastify or just a simple div.
        const notificationTitle = payload.notification.title;
        const notificationOptions = {
            body: payload.notification.body,
            icon: '/static/images/logo.png' // Optional: path to an icon
        };

        // This shows a browser notification, which might not be desired
        // if the user is already active on the page.
        // new Notification(notificationTitle, notificationOptions);

        // A better approach would be to show a custom, non-intrusive UI element.
        alert(`New Message: ${notificationTitle}\n${payload.notification.body}`);
    });

    // --- STEP 4: Initial call to request permission ---
    // We should only request permission if the user is logged in.
    // This script is loaded on pages where the user is authenticated.
    requestNotificationPermission();

  } else {
    console.warn("Firebase config is not set. Push notifications will be disabled.");
  }
} catch (e) {
    console.error("Error initializing Firebase or setting up messaging:", e);
}
