document.addEventListener('DOMContentLoaded', function() {
    // Story viewer logic
    const storyViewerModal = document.getElementById('story-viewer-modal');
    const storyContent = document.getElementById('story-content');
    const closeStoryViewerBtn = document.querySelector('.close-story-viewer');
    const storyCards = document.querySelectorAll('.story-card[data-story-user-id]');
    const nextStoryBtn = document.querySelector('.story-nav.next');
    const prevStoryBtn = document.querySelector('.story-nav.prev');

    let currentUserStories = [];
    let currentStoryIndex = 0;

    function showStory(index) {
        if (index < 0 || index >= currentUserStories.length) return;
        currentStoryIndex = index;
        const story = currentUserStories[index];
        if (story.content_type === 'image') {
            storyContent.innerHTML = `<img src="/static/${story.content}" alt="Story">`;
        } else if (story.content_type === 'video') {
            storyContent.innerHTML = `<video src="/static/${story.content}" controls autoplay></video>`;
        }
    }

    storyCards.forEach(card => {
        card.addEventListener('click', function() {
            const userId = this.dataset.storyUserId;
            fetch(`/feed/api/stories/${userId}`)
                .then(response => response.json())
                .then(stories => {
                    if (stories.length > 0) {
                        currentUserStories = stories;
                        showStory(0);
                        storyViewerModal.style.display = 'block';
                    }
                });
        });
    });

    if(nextStoryBtn) {
        nextStoryBtn.onclick = () => showStory(currentStoryIndex + 1);
    }

    if(prevStoryBtn) {
        prevStoryBtn.onclick = () => showStory(currentStoryIndex - 1);
    }

    if(closeStoryViewerBtn) {
        closeStoryViewerBtn.onclick = function() {
            storyViewerModal.style.display = 'none';
            storyContent.innerHTML = ''; // Clear content
            currentUserStories = [];
            currentStoryIndex = 0;
        }
    }


    // "See More" functionality for long posts
    document.querySelectorAll('.post-text').forEach(postText => {
        // Check if the content is overflowing
        if (postText.scrollHeight > postText.clientHeight) {
            const seeMoreBtn = document.createElement('a');
            seeMoreBtn.href = '#';
            seeMoreBtn.className = 'see-more-btn';
            seeMoreBtn.textContent = '... See More';
            postText.appendChild(seeMoreBtn);

            seeMoreBtn.addEventListener('click', function(e) {
                e.preventDefault();
                postText.classList.toggle('expanded');
                if (postText.classList.contains('expanded')) {
                    this.textContent = 'See Less';
                } else {
                    this.textContent = '... See More';
                }
            });
        }
    });
});
