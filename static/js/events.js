document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.querySelector('.search-bar input');
    const filterSelect = document.querySelector('.filters select');
    const eventsGrid = document.querySelector('.events-grid');

    function fetchAndRenderEvents() {
        const searchTerm = searchInput.value;
        const filterValue = filterSelect.value;

        const url = `/api/events/filter?search=${encodeURIComponent(searchTerm)}&filter=${encodeURIComponent(filterValue)}`;

        fetch(url)
            .then(response => response.json())
            .then(data => {
                renderEvents(data);
            })
            .catch(error => {
                console.error('Error fetching events:', error);
                eventsGrid.innerHTML = '<div class="no-events"><p>Error loading events. Please try again.</p></div>';
            });
    }

    function renderEvents(events) {
        eventsGrid.innerHTML = ''; // Clear existing events

        if (events.length === 0) {
            eventsGrid.innerHTML = '<div class="no-events"><p>No events match your criteria. Why not create one?</p></div>';
            return;
        }

        events.forEach(event => {
            const eventCard = `
                <div class="event-card">
                    <div class="event-card-banner">
                        <img src="${event.image_url}" alt="${event.title}">
                    </div>
                    <div class="event-card-content">
                        <h3 class="event-title">${event.title}</h3>
                        <p class="event-date"><i class="fas fa-calendar-alt"></i> ${event.date}</p>
                        <p class="event-location"><i class="fas fa-map-marker-alt"></i> ${event.location}</p>
                        <div class="event-organizer">
                            <img src="${event.organizer_pic}" alt="${event.organizer_name}">
                            <span>${event.organizer_name}</span>
                        </div>
                    </div>
                    <div class="event-card-footer">
                        <a href="${event.details_url}" class="btn btn-secondary">View Details</a>
                    </div>
                </div>
            `;
            eventsGrid.insertAdjacentHTML('beforeend', eventCard);
        });
    }

    // Debounce function to limit how often the fetch function is called
    let debounceTimer;
    function debounce(func, delay) {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(func, delay);
    }

    if (searchInput && filterSelect && eventsGrid) {
        searchInput.addEventListener('keyup', () => {
            debounce(fetchAndRenderEvents, 300); // Wait 300ms after user stops typing
        });

        filterSelect.addEventListener('change', fetchAndRenderEvents);
    }
});
