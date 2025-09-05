from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from extensions import db
from datetime import datetime
from models import ChatRoom, ChatRoomMember, ChatMessage, User, Course, Community, MutedUser, MutedRoom, ReportedMessage, ReportedGroup, MessageReaction, UserLastRead, Poll, PollOption, PollVote, CallHistory
from utils import filter_profanity
from flask import request

# In-memory stores for call state. In a multi-server setup, this would need to be moved to a shared store like Redis.
user_sids = {} # {user_id: sid}
active_calls = {} # {call_id: {user_id: sid, ...}}

def register_chat_events(socketio):

    @socketio.on('connect')
    def on_connect():
        if current_user.is_authenticated:
            user_sids[current_user.id] = request.sid

    @socketio.on('disconnect')
    def on_disconnect():
        if current_user.is_authenticated and current_user.id in user_sids:
            # Also remove user from any active calls they are in
            for call_id, participants in list(active_calls.items()):
                if current_user.id in participants:
                    del participants[current_user.id]
                    # If call is now empty, remove it
                    if not participants:
                        del active_calls[call_id]
                    else:
                        # Notify remaining participants that a user has left
                        for user_id in participants:
                            emit('participant_left', {'user_id': current_user.id}, to=user_sids.get(user_id))

            del user_sids[current_user.id]


    def is_user_authorized_for_room(user, room):
        if user.role == 'admin':
            return True

        if room.room_type == 'private':
            if user.role == 'student':
                return False
            # Ensure the other member is also not a student
            members = room.members.all()
            if len(members) == 2:
                other_user = members[0].user if members[0].user_id != user.id else members[1].user
                if other_user.role == 'student':
                    return False
            # Let explicit membership check handle the rest

        if room.room_type == 'public' or room.room_type == 'community_channel':
            return True

        # Check for course-based access for course rooms
        if room.room_type == 'course' and room.course_room:
            if user.id == room.course_room.instructor_id or user.is_enrolled(room.course_room):
                return True

        # Check for explicit membership
        return ChatRoomMember.query.filter_by(user_id=user.id, chat_room_id=room.id).count() > 0


    @socketio.on('join')
    def on_join(data):
        if not current_user.is_authenticated:
            return

        room_id = data.get('room_id')
        room = ChatRoom.query.get(room_id)
        if not room or not is_user_authorized_for_room(current_user, room):
            return

        join_room(room_id)

        # Update last read timestamp
        last_read = UserLastRead.query.filter_by(user_id=current_user.id, room_id=room_id).first()
        if last_read:
            last_read.last_read_timestamp = datetime.utcnow()
        else:
            last_read = UserLastRead(user_id=current_user.id, room_id=room_id, last_read_timestamp=datetime.utcnow())
            db.session.add(last_read)
        db.session.commit()

    @socketio.on('leave')
    def on_leave(data):
        if not current_user.is_authenticated:
            return

        room_id = data.get('room_id')
        if room_id:
            leave_room(room_id)

    @socketio.on('message')
    def handle_message(data):
        try:
            if not current_user.is_authenticated:
                return

            room_id = data.get('room_id')
            content = data.get('content')
            file_path = data.get('file_path')
            file_name = data.get('file_name')
            replied_to_id = data.get('replied_to_id')

            if not room_id or (not content and not file_path):
                return

            room = ChatRoom.query.get(room_id)
            if not room or not is_user_authorized_for_room(current_user, room):
                return

            # Mute check
            is_muted = MutedUser.query.filter_by(user_id=current_user.id, room_id=room.id).first()
            if is_muted:
                emit('error', {'msg': 'You are muted in this room.'})
                return

            # Lock check - this is the new granular logic
            if room.is_locked:
                can_send = False
                if room.room_type == 'general' and current_user.role == 'admin':
                    can_send = True
                elif room.room_type == 'course' and (current_user.role == 'admin' or (room.course_room and current_user.id == room.course_room.instructor_id)):
                    can_send = True

                if not can_send:
                    emit('error', {'msg': 'This chat room is currently locked.'})
                    return

            filtered_content = filter_profanity(content)

            new_message = ChatMessage(
                room_id=room.id,
                user_id=current_user.id,
                content=filtered_content,
                file_path=file_path,
                file_name=file_name,
                replied_to_id=replied_to_id
            )
            db.session.add(new_message)

            # Update the room's last message timestamp
            room.last_message_timestamp = new_message.timestamp

            db.session.commit()

            replied_to_data = None
            if new_message.replied_to:
                replied_to_data = {
                    'user_name': new_message.replied_to.author.name,
                    'content': new_message.replied_to.content
                }

            msg_data = {
                'user_name': current_user.name,
                'user_id': current_user.id,
                'user_profile_pic': current_user.profile_pic or 'default.jpg',
                'content': new_message.content,
                'file_path': new_message.file_path,
                'file_name': new_message.file_name,
                'timestamp': new_message.timestamp.isoformat() + "Z",
                'room_id': room.id,
                'message_id': new_message.id,
                'is_pinned': new_message.is_pinned,
                'reactions': [], # New messages have no reactions
                'replied_to': replied_to_data
            }

            emit('message', msg_data, to=room_id)
        except Exception as e:
            print(f"Error handling message: {e}")
            emit('error', {'msg': 'An unexpected error occurred. Please try again.'})

    @socketio.on('delete_message')
    def delete_message(data):
        if not current_user.is_authenticated:
            return

        message_id = data.get('message_id')
        message = ChatMessage.query.get(message_id)

        if not message:
            return

        is_admin = current_user.role == 'admin'
        is_instructor_of_course = (
            current_user.role == 'instructor' and
            message.room.course_room and
            current_user.id == message.room.course_room.instructor_id
        )
        is_author = message.user_id == current_user.id

        if not (is_admin or is_instructor_of_course or is_author):
            return

        db.session.delete(message)
        db.session.commit()

        emit('message_deleted', {'message_id': message_id, 'room_id': message.room_id}, to=message.room_id)

    @socketio.on('pin_message')
    def pin_message(data):
        if not current_user.is_authenticated or not current_user.role in ['admin', 'instructor']:
            return

        message_id = data.get('message_id')
        message = ChatMessage.query.get(message_id)

        if not message:
            return

        if current_user.role == 'instructor' and current_user.id != message.room.course_room.instructor_id:
            return

        message.is_pinned = not message.is_pinned
        db.session.commit()

        emit('message_pinned', {'message_id': message_id, 'is_pinned': message.is_pinned, 'room_id': message.room_id}, to=message.room_id)

    @socketio.on('report_message')
    def report_message(data):
        if not current_user.is_authenticated:
            return

        message_id = data.get('message_id')
        message = ChatMessage.query.get(message_id)

        if not message:
            return

        existing_report = ReportedMessage.query.filter_by(
            message_id=message_id,
            reported_by_id=current_user.id
        ).first()

        if existing_report:
            emit('error', {'msg': 'You have already reported this message.'})
            return

        new_report = ReportedMessage(
            message_id=message_id,
            reported_by_id=current_user.id
        )
        db.session.add(new_report)
        db.session.commit()

        emit('status', {'msg': 'Message has been reported to administrators.'})

    @socketio.on('report_group')
    def report_group(data):
        if not current_user.is_authenticated:
            return

        room_id = data.get('room_id')
        reason = data.get('reason')

        if not room_id:
            return

        # Prevent duplicate reports
        existing_report = ReportedGroup.query.filter_by(
            room_id=room_id,
            reported_by_id=current_user.id
        ).first()

        if existing_report:
            emit('error', {'msg': 'You have already reported this group.'})
            return

        new_report = ReportedGroup(
            room_id=room_id,
            reported_by_id=current_user.id,
            reason=reason
        )
        db.session.add(new_report)
        db.session.commit()

        emit('status', {'msg': 'Group has been reported to administrators.'})


    @socketio.on('remove_member')
    def remove_member(data):
        if not current_user.is_authenticated:
            return

        room_id = data.get('room_id')
        user_id = data.get('user_id')

        room = ChatRoom.query.get(room_id)
        if not room:
            return

        # Authorization check
        user_membership = ChatRoomMember.query.filter_by(
            user_id=current_user.id,
            chat_room_id=room_id
        ).first()
        if not user_membership or user_membership.role_in_room != 'admin':
            return

        member_to_remove = ChatRoomMember.query.filter_by(
            user_id=user_id,
            chat_room_id=room_id
        ).first()

        if member_to_remove:
            db.session.delete(member_to_remove)
            db.session.commit()
            emit('member_removed', {'user_id': user_id, 'room_id': room_id}, to=room_id)

    @socketio.on('exit_group')
    def exit_group(data):
        if not current_user.is_authenticated:
            return

        room_id = data.get('room_id')
        if not room_id:
            return

        membership = ChatRoomMember.query.filter_by(
            user_id=current_user.id,
            chat_room_id=room_id
        ).first()

        if membership:
            db.session.delete(membership)
            db.session.commit()
            emit('status', {'msg': f"You have left the group. You will be redirected."})
            # The client should handle redirecting the user
        else:
            emit('error', {'msg': 'You are not a member of this group.'})

    @socketio.on('edit_group_description')
    def edit_group_description(data):
        if not current_user.is_authenticated:
            return

        room_id = data.get('room_id')
        new_description = data.get('description', '')

        room = ChatRoom.query.get(room_id)
        if not room:
            return

        # Authorization Check
        is_admin = current_user.role == 'admin'
        # Add more specific instructor check if needed
        is_creator = room.created_by_id == current_user.id

        if not (is_admin or is_creator):
             emit('error', {'msg': 'You do not have permission to edit this description.'})
             return

        room.description = new_description
        db.session.commit()

        emit('description_changed', {'room_id': room.id, 'new_description': new_description}, to=room_id)


    @socketio.on('react_to_message')
    def react_to_message(data):
        if not current_user.is_authenticated:
            return

        message_id = data.get('message_id')
        reaction_emoji = data.get('reaction')

        if not message_id or not reaction_emoji:
            return

        message = ChatMessage.query.get(message_id)
        if not message:
            return

        existing_reaction = MessageReaction.query.filter_by(
            message_id=message_id,
            user_id=current_user.id,
            reaction=reaction_emoji
        ).first()

        if existing_reaction:
            db.session.delete(existing_reaction)
        else:
            new_reaction = MessageReaction(
                message_id=message_id,
                user_id=current_user.id,
                reaction=reaction_emoji
            )
            db.session.add(new_reaction)

        db.session.commit()

        reactions = MessageReaction.query.filter_by(message_id=message_id).all()
        reactions_data = [{'user_name': r.user.name, 'reaction': r.reaction} for r in reactions]

        emit('message_reacted', {
            'message_id': message_id,
            'room_id': message.room_id,
            'reactions': reactions_data
        }, to=message.room_id)

    @socketio.on('edit_message')
    def edit_message(data):
        if not current_user.is_authenticated:
            return

        message_id = data.get('message_id')
        new_content = data.get('content')

        message = ChatMessage.query.get(message_id)
        if not message or message.user_id != current_user.id:
            return

        message.content = new_content
        message.is_edited = True
        db.session.commit()

        emit('message_edited', {
            'message_id': message_id,
            'room_id': message.room_id,
            'new_content': new_content
        }, to=message.room_id)

    @socketio.on('toggle_mute')
    def toggle_mute(data):
        if not current_user.is_authenticated:
            return

        room_id = data.get('room_id')
        if not room_id:
            return

        # Check for existing mute
        existing_mute = MutedRoom.query.filter_by(
            user_id=current_user.id,
            room_id=room_id
        ).first()

        new_status = False
        if existing_mute:
            db.session.delete(existing_mute)
            new_status = False # Unmuted
        else:
            new_mute = MutedRoom(user_id=current_user.id, room_id=room_id)
            db.session.add(new_mute)
            new_status = True # Muted

        db.session.commit()

        emit('mute_status_changed', {'room_id': room_id, 'is_muted': new_status})

    @socketio.on('create_poll')
    def create_poll(data):
        if not current_user.is_authenticated:
            return

        room_id = data.get('room_id')
        question = data.get('question')
        options = data.get('options')

        room = ChatRoom.query.get(room_id)
        if not room or not is_user_authorized_for_room(current_user, room) or not question or not options or len(options) < 2:
            return

        # Create a chat message to represent the poll
        poll_message = ChatMessage(
            room_id=room.id,
            user_id=current_user.id,
            content=f"Poll: {question}" # Simple text representation
        )
        db.session.add(poll_message)
        db.session.commit() # Commit to get message ID

        new_poll = Poll(
            room_id=room.id,
            user_id=current_user.id,
            question=question,
            message_id=poll_message.id
        )
        db.session.add(new_poll)

        for option_text in options:
            poll_option = PollOption(poll=new_poll, text=option_text)
            db.session.add(poll_option)

        db.session.commit()

        # Now that poll and options have IDs, construct the data to emit
        poll_data_to_emit = {
            'poll_id': new_poll.id,
            'message_id': poll_message.id,
            'room_id': room.id,
            'user_id': current_user.id,
            'user_name': current_user.name,
            'user_profile_pic': current_user.profile_pic or 'default.jpg',
            'question': new_poll.question,
            'options': [{'id': opt.id, 'text': opt.text, 'votes': 0} for opt in new_poll.options],
            'timestamp': poll_message.timestamp.isoformat() + "Z",
        }

        emit('new_poll', poll_data_to_emit, to=room_id)

    @socketio.on('poll_vote')
    def poll_vote(data):
        if not current_user.is_authenticated:
            return

        option_id = data.get('option_id')
        option = PollOption.query.get(option_id)
        if not option:
            return

        poll = option.poll
        room = poll.room

        if not is_user_authorized_for_room(current_user, room):
            return

        # Check if user has already voted
        existing_vote = PollVote.query.join(PollOption).filter(
            PollOption.poll_id == poll.id,
            PollVote.user_id == current_user.id
        ).first()

        if existing_vote:
            # If they voted for the same option, do nothing (or retract vote - simple for now)
            if existing_vote.option_id == option_id:
                return
            # If they voted for a different option, update their vote
            else:
                existing_vote.option_id = option_id
        else:
            # New vote
            new_vote = PollVote(option_id=option_id, user_id=current_user.id)
            db.session.add(new_vote)

        db.session.commit()

        # Recalculate vote counts
        options_with_votes = []
        for opt in poll.options:
            vote_count = PollVote.query.filter_by(option_id=opt.id).count()
            options_with_votes.append({'id': opt.id, 'text': opt.text, 'votes': vote_count})

        emit('poll_update', {
            'poll_id': poll.id,
            'room_id': room.id,
            'options': options_with_votes
        }, to=room.id)

    @socketio.on('leave_community')
    def leave_community(data):
        if not current_user.is_authenticated:
            return

        community_id = data.get('community_id')
        community = Community.query.get(community_id)
        if not community:
            return

        for channel in community.channels:
            membership = ChatRoomMember.query.filter_by(
                user_id=current_user.id,
                chat_room_id=channel.id
            ).first()
            if membership:
                db.session.delete(membership)

        db.session.commit()
        emit('status', {'msg': f"You have left the community '{community.name}'. You will be redirected."})

    @socketio.on('mute_community')
    def mute_community(data):
        if not current_user.is_authenticated:
            return

        community_id = data.get('community_id')
        community = Community.query.get(community_id)
        if not community:
            return

        # This is a toggle. First, check if ANY channel is muted.
        # If so, unmute all. If not, mute all.
        is_any_muted = False
        for channel in community.channels:
            if MutedRoom.query.filter_by(user_id=current_user.id, room_id=channel.id).first():
                is_any_muted = True
                break

        new_status = not is_any_muted
        for channel in community.channels:
            existing_mute = MutedRoom.query.filter_by(user_id=current_user.id, room_id=channel.id).first()
            if new_status and not existing_mute: # Mute
                new_mute = MutedRoom(user_id=current_user.id, room_id=channel.id)
                db.session.add(new_mute)
            elif not new_status and existing_mute: # Unmute
                db.session.delete(existing_mute)

        db.session.commit()
        emit('community_mute_status_changed', {'community_id': community_id, 'is_muted': new_status})

    # --- WebRTC Signaling Events ---

    @socketio.on('start_call')
    def start_call(data):
        if not current_user.is_authenticated: return

        room_id = data.get('room_id')
        call_type = data.get('call_type')
        callee_id = data.get('callee_id') # Will be null for group calls

        if current_user.role not in ['admin', 'instructor']:
            return emit('call_error', {'message': 'You do not have permission to start calls.'})

        room = ChatRoom.query.get(room_id)
        if not room or not is_user_authorized_for_room(current_user, room):
            return emit('call_error', {'message': 'Cannot start call in this room.'})

        # Check for an existing active call in the room
        existing_active_call = CallHistory.query.filter_by(room_id=room_id, is_active=True).first()
        if existing_active_call:
            return emit('call_error', {'message': 'There is already an active call in this room.'})

        new_call = CallHistory(
            caller_id=current_user.id,
            callee_id=callee_id, # Will be None for group calls
            room_id=room_id,
            call_type=call_type,
            status='initiated'
        )
        db.session.add(new_call)
        db.session.commit()

        if callee_id: # One-to-one call
            emit('call_started', {'call_id': new_call.id})
            emit('incoming_call', {
                'caller_id': current_user.id,
                'caller_name': current_user.name,
                'caller_profile_pic': current_user.profile_pic,
                'call_type': call_type,
                'room_id': room_id,
                'call_id': new_call.id
            }, to=room_id)
        else: # Group call
            emit('group_call_started', {
                'starter_name': current_user.name,
                'call_type': call_type,
                'room_id': room_id,
                'call_id': new_call.id
            }, to=room_id)

    @socketio.on('offer')
    def handle_offer(data):
        if not current_user.is_authenticated: return
        emit('offer_received', {
            'caller_id': current_user.id,
            'offer': data['offer'],
            'call_id': data['call_id']
        }, to=data['room_id'])

    @socketio.on('answer')
    def handle_answer(data):
        if not current_user.is_authenticated: return

        call = CallHistory.query.get(data['call_id'])
        if call:
            call.status = 'answered'
            call.answered_at = datetime.utcnow()
            db.session.commit()

        emit('answer_received', {
            'callee_id': current_user.id,
            'answer': data['answer'],
            'callee_info': {
                'name': current_user.name,
                'profile_pic': current_user.profile_pic
            }
        }, to=data['room_id'])

    @socketio.on('ice_candidate')
    def handle_ice_candidate(data):
        if not current_user.is_authenticated: return
        emit('ice_candidate_received', {
            'from_id': current_user.id,
            'candidate': data['candidate']
        }, to=data['room_id'])

    @socketio.on('end_call')
    def handle_end_call(data):
        if not current_user.is_authenticated: return

        call_id = data.get('call_id')
        reason = data.get('reason', 'ended') # e.g., 'ended', 'declined', 'missed'

        call = CallHistory.query.get(call_id)
        if call:
            # For now, any end_call marks the call as inactive.
            # A more robust solution would track participants.
            call.is_active = False

            # Only set status and duration if it's the first time the call is ending.
            if not call.ended_at:
                call.status = reason
                call.ended_at = datetime.utcnow()
                if call.answered_at:
                    duration = call.ended_at - call.answered_at
                    call.duration = int(duration.total_seconds())

            db.session.commit()

        # Notify all clients in the room that the call has ended
        emit('call_ended', {'call_id': call_id}, to=data['room_id'])

    # --- Group Call Signaling ---
    @socketio.on('join_group_call')
    def on_join_group_call(data):
        if not current_user.is_authenticated: return
        call_id = data['call_id']

        # Get existing participants
        if call_id in active_calls:
            existing_participants = active_calls[call_id]
            emit('existing_participants', {'participants': list(existing_participants.keys())})

            # Notify existing participants of the new user
            for user_id, sid in existing_participants.items():
                emit('new_participant', {'user_id': current_user.id}, to=sid)
        else:
            # This is the first person in the call
            active_calls[call_id] = {}
            emit('existing_participants', {'participants': []})

        # Add new user to the call
        active_calls[call_id][current_user.id] = request.sid

    @socketio.on('leave_group_call')
    def on_leave_group_call(data):
        if not current_user.is_authenticated: return
        call_id = data['call_id']
        if call_id in active_calls and current_user.id in active_calls[call_id]:
            del active_calls[call_id][current_user.id]
            # If call is now empty, remove it
            if not active_calls[call_id]:
                del active_calls[call_id]
            else:
                # Notify remaining participants
                for user_id, sid in active_calls[call_id].items():
                    emit('participant_left', {'user_id': current_user.id}, to=sid)

    @socketio.on('webrtc_offer')
    def handle_webrtc_offer(data):
        if not current_user.is_authenticated: return
        to_sid = user_sids.get(data['to_user_id'])
        if to_sid:
            emit('webrtc_offer_received', {
                'from_user_id': current_user.id,
                'offer': data['offer']
            }, to=to_sid)

    @socketio.on('webrtc_answer')
    def handle_webrtc_answer(data):
        if not current_user.is_authenticated: return
        to_sid = user_sids.get(data['to_user_id'])
        if to_sid:
            emit('webrtc_answer_received', {
                'from_user_id': current_user.id,
                'answer': data['answer']
            }, to=to_sid)

    @socketio.on('webrtc_ice_candidate')
    def handle_webrtc_ice_candidate(data):
        if not current_user.is_authenticated: return
        to_sid = user_sids.get(data['to_user_id'])
        if to_sid:
            emit('webrtc_ice_candidate_received', {
                'from_user_id': current_user.id,
                'candidate': data['candidate']
            }, to=to_sid)

    @socketio.on('send_contact')
    def send_contact(data):
        if not current_user.is_authenticated: return
        room_id = data.get('room_id')
        shared_user_id = data.get('shared_user_id')

        room = ChatRoom.query.get(room_id)
        shared_user = User.query.get(shared_user_id)

        if not room or not shared_user or not is_user_authorized_for_room(current_user, room):
            return

        import json
        contact_info = {
            "type": "contact",
            "user_id": shared_user.id,
            "name": shared_user.name,
            "profile_pic": shared_user.profile_pic
        }

        new_message = ChatMessage(
            room_id=room.id,
            user_id=current_user.id,
            content=json.dumps(contact_info)
        )
        db.session.add(new_message)
        room.last_message_timestamp = new_message.timestamp
        db.session.commit()

        msg_data = {
            'user_name': current_user.name,
            'user_id': current_user.id,
            'content': new_message.content,
            'timestamp': new_message.timestamp.isoformat() + "Z",
            'room_id': room.id,
            'message_id': new_message.id
        }
        emit('message', msg_data, to=room_id)

    @socketio.on('send_location')
    def send_location(data):
        if not current_user.is_authenticated: return
        room_id = data.get('room_id')
        latitude = data.get('latitude')
        longitude = data.get('longitude')

        room = ChatRoom.query.get(room_id)
        if not room or not latitude or not longitude or not is_user_authorized_for_room(current_user, room):
            return

        import json
        location_info = {
            "type": "location",
            "latitude": latitude,
            "longitude": longitude
        }

        new_message = ChatMessage(
            room_id=room.id,
            user_id=current_user.id,
            content=json.dumps(location_info)
        )
        db.session.add(new_message)
        room.last_message_timestamp = new_message.timestamp
        db.session.commit()

        msg_data = {
            'user_name': current_user.name,
            'user_id': current_user.id,
            'content': new_message.content,
            'timestamp': new_message.timestamp.isoformat() + "Z",
            'room_id': room.id,
            'message_id': new_message.id
        }
        emit('message', msg_data, to=room_id)
