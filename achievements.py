from models import Badge, Assignment, AssignmentSubmission, Course, User

def check_and_award_badges(student: User, course: Course):
    """
    Checks for and awards all relevant badges for a student in a given course.
    """
    _check_course_completion_badge(student, course)
    # Future achievement checks can be added here

def _check_course_completion_badge(student: User, course: Course):
    """
    Awards a badge if the student has passed all assignments in a course.
    """
    badge_name = f"Completed: {course.title}"

    # 1. Check if the user already has this badge
    existing_badge = Badge.query.filter_by(user_id=student.id, name=badge_name).first()
    if existing_badge:
        return

    # 2. Get all assignments for the course
    all_assignments = []
    for module in course.modules:
        if module.assignment:
            all_assignments.append(module.assignment)

    if not all_assignments:
        return # No assignments in this course to complete

    # 3. Check if all assignments have a passing grade
    for assignment in all_assignments:
        submission = AssignmentSubmission.query.filter_by(
            student_id=student.id,
            assignment_id=assignment.id
        ).first()
        # To pass, submission must exist, have a grade, and the grade must be 'pass' (case-insensitive)
        if not submission or not submission.grade or submission.grade.lower() != 'pass':
            return # Not all assignments are passed yet

    # 4. If all checks pass, award the badge
    from extensions import db
    new_badge = Badge(
        name=badge_name,
        icon_url='static/images/badges/course_complete.png', # Placeholder icon
        user_id=student.id
    )
    db.session.add(new_badge)
    db.session.commit()
    print(f"Awarded badge '{badge_name}' to user {student.name}") # For logging/debugging
