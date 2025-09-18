document.addEventListener('DOMContentLoaded', function () {
    const calendarPlaceholder = document.getElementById('calendar-placeholder');

    if (calendarPlaceholder) {
        fetch('/api/events/for_calendar')
            .then(response => response.json())
            .then(events => {
                // Clear the placeholder text
                calendarPlaceholder.innerHTML = '';
                calendarPlaceholder.style.backgroundColor = 'transparent'; // Remove placeholder bg
                calendarPlaceholder.style.alignItems = 'flex-start';
                calendarPlaceholder.style.justifyContent = 'flex-start';


                const calendar = new JSCalendar(calendarPlaceholder, {
                    views: ['month'], // Only show month view
                    buttons: ['previous', 'today', 'next'],
                    initialView: 'month',
                    dayFormat: 'DDD', // Short day names like 'Mon'
                    events: events.map(e => new JSCalendarEvent({
                        date: new Date(e.start),
                        title: e.title,
                        url: e.url
                    }))
                });

                calendar.init().render();
            })
            .catch(error => {
                console.error('Error fetching calendar events:', error);
                calendarPlaceholder.textContent = 'Could not load calendar.';
            });
    }
});
