document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggleBtn = document.getElementById('sidebar-toggle-btn');
    const themeToggleBtn = document.getElementById('theme-toggle');
    const fabContainer = document.getElementById('fab-container');
    const fab = document.getElementById('fab');

    // --- Theme Toggling ---
    const themeIcon = themeToggleBtn.querySelector('i');

    // Function to apply the currently stored theme on page load
    const applyInitialTheme = () => {
        const theme = localStorage.getItem('theme') || 'light'; // Default to light
        document.documentElement.setAttribute('data-theme', theme);

        if (theme === 'dark') {
            themeIcon.classList.remove('fa-moon');
            themeIcon.classList.add('fa-sun');
        } else {
            themeIcon.classList.remove('fa-sun');
            themeIcon.classList.add('fa-moon');
        }
    };

    // Event listener for theme toggle button
    themeToggleBtn.addEventListener('click', () => {
        // Get the current theme from the attribute
        const currentTheme = document.documentElement.getAttribute('data-theme');
        // Determine the new theme
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

        // Set the new theme
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);

        // Update the icon
        if (newTheme === 'dark') {
            themeIcon.classList.remove('fa-moon');
            themeIcon.classList.add('fa-sun');
        } else {
            themeIcon.classList.remove('fa-sun');
            themeIcon.classList.add('fa-moon');
        }
    });

    // Apply the theme when the DOM is loaded
    applyInitialTheme();


    // --- Sidebar Toggle for Mobile ---
    if (sidebarToggleBtn) {
        sidebarToggleBtn.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
    }

    // --- Close sidebar when clicking outside on mobile ---
    document.addEventListener('click', function(event) {
        if (window.innerWidth <= 768) {
            if (sidebar && sidebarToggleBtn) {
                const isClickInsideSidebar = sidebar.contains(event.target);
                const isClickOnToggleButton = sidebarToggleBtn.contains(event.target);

                if (!isClickInsideSidebar && !isClickOnToggleButton && sidebar.classList.contains('open')) {
                    sidebar.classList.remove('open');
                }
            }
        }
    });

    // --- Sidebar Expand/Collapse on Tablet ---
    if (window.innerWidth > 768 && window.innerWidth <= 1024) {
        sidebar.addEventListener('mouseenter', () => {
            sidebar.classList.add('expanded');
        });
        sidebar.addEventListener('mouseleave', () => {
            sidebar.classList.remove('expanded');
        });
    }

    // --- Dropdown Menu Logic ---
    const dropdownToggles = document.querySelectorAll('.sidebar-nav .dropdown-toggle');

    dropdownToggles.forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            const parent = this.parentElement;

            // Close other open dropdowns
            document.querySelectorAll('.nav-item-dropdown').forEach(item => {
                if (item !== parent) {
                    item.classList.remove('open');
                }
            });

            // Toggle current dropdown
            parent.classList.toggle('open');
        });
    });

    // --- Typewriter Effect ---
    const typewriterElement = document.querySelector('.typewriter');
    if (typewriterElement) {
        const text = typewriterElement.innerHTML;
        typewriterElement.innerHTML = '';
        let i = 0;
        function typeWriter() {
            if (i < text.length) {
                typewriterElement.innerHTML += text.charAt(i);
                i++;
                setTimeout(typeWriter, 100);
            }
        }
        typeWriter();
    }

    // --- Modal Logic ---
    const uploadModal = document.getElementById('library-upload-modal');
    const uploadTriggers = document.querySelectorAll('.upload-library-trigger');
    const closeBtn = document.querySelector('#library-upload-modal .close-btn');

    uploadTriggers.forEach(btn => {
        btn.onclick = function() {
            if(uploadModal) uploadModal.style.display = "block";
        }
    });

    if (closeBtn) {
        closeBtn.onclick = function() {
            uploadModal.style.display = "none";
        }
    }

    window.onclick = function(event) {
        if (event.target == uploadModal) {
            uploadModal.style.display = "none";
        }
    }

    // --- FAB Logic ---
    if (fab) {
        fab.addEventListener('click', () => {
            fabContainer.classList.toggle('open');
        });
    }

    // Close FAB when clicking outside
    document.addEventListener('click', function(event) {
        if (fabContainer && !fabContainer.contains(event.target) && fabContainer.classList.contains('open')) {
            fabContainer.classList.remove('open');
        }
    });
});
