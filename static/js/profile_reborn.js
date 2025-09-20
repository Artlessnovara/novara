document.addEventListener('DOMContentLoaded', () => {
    // --- Theme Toggle ---
    const themeToggle = document.querySelector('#theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            document.body.classList.toggle('dark-mode');
            const isDarkMode = document.body.classList.contains('dark-mode');
            // In a real app, you would save this preference to the backend/localStorage
        });
    }

    // --- Modal Logic ---
    const modals = document.querySelectorAll('.modal');
    const closeModalBtns = document.querySelectorAll('.close-btn');

    function openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'block';
        }
    }

    function closeModal(modal) {
        if (modal) {
            modal.style.display = 'none';
        }
    }

    closeModalBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            closeModal(btn.closest('.modal'));
        });
    });

    window.addEventListener('click', (event) => {
        modals.forEach(modal => {
            if (event.target == modal) {
                closeModal(modal);
            }
        });
    });

    // --- Event Listeners for Modal Triggers ---
    document.querySelector('.edit-profile-btn')?.addEventListener('click', () => openModal('edit-profile-modal'));
    document.querySelector('#add-certificate-btn')?.addEventListener('click', () => openModal('add-certificate-modal'));
    document.querySelector('#add-badge-btn')?.addEventListener('click', () => openModal('add-badge-modal'));
    document.querySelector('#add-social-link-btn')?.addEventListener('click', () => openModal('add-social-link-modal'));
    document.querySelector('.fab')?.addEventListener('click', () => openModal('add-certificate-modal'));

    // --- AJAX Form Submission ---
    const handleFormSubmit = async (form, modalId) => {
        const formData = new FormData(form);
        try {
            const response = await fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            const data = await response.json();
            if (data.status === 'success') {
                closeModal(document.getElementById(modalId));
                if (modalId === 'edit-profile-modal') {
                    updateProfileData(data.user);
                } else {
                    // For other forms, a reload might still be the simplest option for now
                    window.location.reload();
                }
            } else {
                // Handle errors, e.g., display them in the modal
                alert('Error: ' + (data.message || 'An unknown error occurred.'));
            }
        } catch (error) {
            console.error('Form submission error:', error);
            alert('An unexpected error occurred.');
        }
    };

    document.getElementById('edit-profile-modal')?.querySelector('form')?.addEventListener('submit', (e) => {
        e.preventDefault();
        handleFormSubmit(e.target, 'edit-profile-modal');
    });
    document.getElementById('add-badge-modal')?.querySelector('form')?.addEventListener('submit', (e) => {
        e.preventDefault();
        handleFormSubmit(e.target, 'add-badge-modal');
    });
    document.getElementById('add-social-link-modal')?.querySelector('form')?.addEventListener('submit', (e) => {
        e.preventDefault();
        handleFormSubmit(e.target, 'add-social-link-modal');
    });
    document.getElementById('add-certificate-modal')?.querySelector('form')?.addEventListener('submit', (e) => {
        e.preventDefault();
        handleFormSubmit(e.target, 'add-certificate-modal');
    });

    const updateProfileData = (user) => {
        // Update profile header
        document.querySelector('.profile-header h1').textContent = user.name;
        document.querySelector('.profile-header .text-muted').textContent = `@${user.name.toLowerCase().replace(/\s+/g, '')}`; // A simple username approximation
        document.querySelector('.profile-bio p').textContent = user.bio;

        // Update profile picture in both the header and the top bar
        const newPicUrl = `/static/profile_pics/${user.profile_pic}`;
        document.querySelector('.profile-pic-container img').src = newPicUrl;
        document.querySelector('.top-bar-right .profile-avatar img').src = newPicUrl; // Assumes this selector is correct
    };


    // --- Carousels ---
    // The current CSS makes these sections horizontally scrollable on overflow.
    // A more advanced implementation would use a proper carousel library
    // or custom JS for prev/next buttons and snapping.
    // For now, the native scroll works as a baseline.

    // --- Animate Stat Counters ---
    const statNumbers = document.querySelectorAll('.stat-number');
    statNumbers.forEach(stat => {
        const target = +stat.innerText;
        stat.innerText = '0';
        const speed = 200; // Lower is faster

        const updateCount = () => {
            const count = +stat.innerText;
            const inc = target / speed;

            if (count < target) {
                stat.innerText = Math.ceil(count + inc);
                setTimeout(updateCount, 1);
            } else {
                stat.innerText = target;
            }
        };

        updateCount();
    });
});
