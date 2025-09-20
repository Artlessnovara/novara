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
    const editProfileBtn = document.querySelector('.edit-profile-btn');
    if (editProfileBtn) {
        editProfileBtn.addEventListener('click', () => openModal('edit-profile-modal'));
    }

    // This is a placeholder for editing individual details.
    // A real implementation would need to know which detail is being edited.
    const editDetailBtns = document.querySelectorAll('.btn-edit-detail');
    editDetailBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            alert('A modal for this specific item would open.');
        });
    });

    const addCertBtn = document.querySelector('.certificates-grid + .section-header .btn-add');
    if(addCertBtn) {
        addCertBtn.addEventListener('click', () => openModal('add-certificate-modal'));
    }

    const addBadgeBtn = document.querySelector('.badges-carousel + .section-header .btn-add');
    if(addBadgeBtn) {
        addBadgeBtn.addEventListener('click', () => openModal('add-badge-modal'));
    }

    const addSocialLinkBtn = document.querySelector('.social-links-row + .section-header .btn-add');
    if(addSocialLinkBtn) {
        addSocialLinkBtn.addEventListener('click', () => openModal('add-social-link-modal'));
    }

    const fab = document.querySelector('.fab');
    if(fab) {
        fab.addEventListener('click', () => openModal('add-certificate-modal'));
    }


    // --- Carousels ---
    // The current CSS makes these sections horizontally scrollable on overflow.
    // A more advanced implementation would use a proper carousel library
    // or custom JS for prev/next buttons and snapping.
    // For now, the native scroll works as a baseline.
});
