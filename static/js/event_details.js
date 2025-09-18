document.addEventListener('DOMContentLoaded', function () {
    const seeAllBtn = document.getElementById('see-all-attendees-btn');
    const modal = document.getElementById('attendees-modal');
    const closeBtn = modal.querySelector('.close-button');
    const modalAttendeesList = document.getElementById('modal-attendees-list');

    function openModal() {
        modal.style.display = 'block';
        const eventId = seeAllBtn.dataset.eventId;

        // Fetch full attendee list
        fetch(`/api/event/${eventId}/attendees`)
            .then(response => response.json())
            .then(attendees => {
                modalAttendeesList.innerHTML = ''; // Clear previous list
                if (attendees.length > 0) {
                    attendees.forEach(attendee => {
                        const attendeeElement = `
                            <a href="${attendee.profile_url}" class="attendee-item-modal">
                                <img src="${attendee.profile_pic_url}" alt="${attendee.name}">
                                <span>${attendee.name}</span>
                            </a>
                        `;
                        modalAttendeesList.insertAdjacentHTML('beforeend', attendeeElement);
                    });
                } else {
                    modalAttendeesList.innerHTML = '<p>No attendees yet.</p>';
                }
            })
            .catch(error => {
                console.error('Error fetching attendees:', error);
                modalAttendeesList.innerHTML = '<p>Could not load attendees.</p>';
            });
    }

    function closeModal() {
        modal.style.display = 'none';
    }

    if (seeAllBtn) {
        // Store event ID on the button itself from the URL
        const eventId = window.location.pathname.split('/').pop();
        seeAllBtn.dataset.eventId = eventId;
        seeAllBtn.addEventListener('click', openModal);
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', closeModal);
    }

    window.addEventListener('click', function (event) {
        if (event.target === modal) {
            closeModal();
        }
    });
});
