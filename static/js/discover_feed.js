document.addEventListener('DOMContentLoaded', function() {
    // Story viewer logic
    const storyViewerModal = document.getElementById('story-viewer-modal');
    const storyContent = document.getElementById('story-content');
    const closeStoryViewerBtn = document.querySelector('.close-story-viewer');
    const storyCards = document.querySelectorAll('.story-card[data-story-user-id]');

    storyCards.forEach(card => {
        card.addEventListener('click', function() {
            const userId = this.dataset.storyUserId;
            fetch(`/feed/api/stories/${userId}`)
                .then(response => response.json())
                .then(stories => {
                    if (stories.length > 0) {
                        // For now, just show the first story
                        const story = stories[0];
                        if (story.content_type === 'image') {
                            storyContent.innerHTML = `<img src="/static/${story.content}" alt="Story">`;
                        } else if (story.content_type === 'video') {
                            storyContent.innerHTML = `<video src="/static/${story.content}" controls autoplay></video>`;
                        }
                        storyViewerModal.style.display = 'block';
                    }
                });
        });
    });

    if(closeStoryViewerBtn) {
        closeStoryViewerBtn.onclick = function() {
            storyViewerModal.style.display = 'none';
            storyContent.innerHTML = ''; // Clear content
        }
    }


    // "See More" functionality for long posts
    const seeMoreButtons = document.querySelectorAll('.see-more-btn');
    seeMoreButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const postText = this.parentElement;
            postText.classList.toggle('expanded');
            if (postText.classList.contains('expanded')) {
                this.textContent = '... See Less';
            } else {
                this.textContent = '... See More';
            }
        });
    });
});
