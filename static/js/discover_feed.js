document.addEventListener('DOMContentLoaded', function() {
    // Add Story Modal Logic
    const addStoryModal = document.getElementById('add-story-modal');
    const addStoryBtn = document.querySelector('.story-card:first-child'); // The "Add Story" button
    const closeAddStoryBtn = document.querySelector('#add-story-modal .close-btn');

    if(addStoryBtn) {
        addStoryBtn.onclick = function() {
            addStoryModal.style.display = "block";
        }
    }
    if(closeAddStoryBtn) {
        closeAddStoryBtn.onclick = function() {
            addStoryModal.style.display = "none";
        }
    }
    window.addEventListener('click', function(event) {
        if (event.target == addStoryModal) {
            addStoryModal.style.display = "none";
        }
    });

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

    // Video play button logic
    document.querySelectorAll('.video-container').forEach(container => {
        const video = container.querySelector('video');
        const overlay = container.querySelector('.play-button-overlay');

        container.addEventListener('click', () => {
            if (video.paused) {
                video.play();
                overlay.style.display = 'none';
                video.setAttribute('controls', 'true');
            } else {
                video.pause();
                overlay.style.display = 'flex';
                video.removeAttribute('controls');
            }
                });
        });

    // Like and comment functionality
    document.querySelectorAll('.post-action[data-action="like"]').forEach(button => {
        button.addEventListener('click', function() {
            const postId = this.dataset.postId;
            fetch(`/feed/api/post/${postId}/react`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ reaction_type: 'like' })
            }).then(response => response.json()).then(data => {
                if (data.status === 'success') {
                    // Update like count and button appearance
                    this.classList.toggle('liked', data.user_reaction === 'like');
                }
            });
        });
    });

    document.querySelectorAll('.post-action[data-action="comment"]').forEach(button => {
        button.addEventListener('click', function() {
            const postCard = this.closest('.post-card');
            const commentInput = postCard.querySelector('.comment-input');
            commentInput.focus();
        });
    });

    // Fetch latest comments
    document.querySelectorAll('.comment-preview').forEach(preview => {
        const postId = preview.id.split('-')[2];
        fetch(`/feed/api/post/${postId}/comments`)
            .then(response => response.json())
            .then(comments => {
                const latestComments = comments.slice(-2); // Get last 2
                latestComments.forEach(comment => {
                    const commentDiv = document.createElement('div');
                    commentDiv.innerHTML = `<strong>${comment.author.name}</strong> ${comment.content}`;
                    preview.appendChild(commentDiv);
                });
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
