document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('theme-toggle');
    const body = document.body;

    // Function to set the theme
    const setTheme = (theme) => {
        body.classList.remove('light-theme', 'dark-theme');
        body.classList.add(`${theme}-theme`);
        localStorage.setItem('theme', theme);

        // Update icon
        if (theme === 'dark') {
            themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
        } else {
            themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
        }
    };

    // Toggle theme on button click
    themeToggle.addEventListener('click', () => {
        const currentTheme = localStorage.getItem('theme') || 'light';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        setTheme(newTheme);
    });

    // Apply saved theme on page load
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);

    // Animated counters
    const counters = document.querySelectorAll('.animated-counter');
    counters.forEach(counter => {
        const target = +counter.getAttribute('data-target');
        const duration = 2000; // 2 seconds
        const stepTime = 20; // 50 steps per second
        const totalSteps = duration / stepTime;
        const increment = target / totalSteps;
        let current = 0;

        const updateCounter = () => {
            current += increment;
            if (current >= target) {
                counter.innerText = target + (counter.innerText.includes('%') ? '%' : '');
            } else {
                counter.innerText = Math.ceil(current) + (counter.innerText.includes('%') ? '%' : '');
                setTimeout(updateCounter, stepTime);
            }
        };
        updateCounter();
    });
});
