document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggleBtn = document.getElementById('sidebar-toggle-btn');

    // --- Sidebar Toggle for Mobile ---
    if (sidebarToggleBtn) {
        sidebarToggleBtn.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
    }

    // --- Close sidebar when clicking outside on mobile ---
    document.addEventListener('click', function(event) {
        if (window.innerWidth <= 768) {
            const isClickInsideSidebar = sidebar.contains(event.target);
            const isClickOnToggleButton = sidebarToggleBtn.contains(event.target);

            if (!isClickInsideSidebar && !isClickOnToggleButton && sidebar.classList.contains('open')) {
                sidebar.classList.remove('open');
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
});
