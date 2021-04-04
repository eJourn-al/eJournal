
from VLE import factory
from VLE.models import Comment, Entry


def publish_all_journal_grades(journal, publisher):
    """publish all grades that are not None for a journal.

    - journal: the journal in question
    - publisher: the publisher of the grade
    """
    entries = Entry.objects.filter(node__journal=journal).exclude(grade=None)

    for entry in entries:
        factory.make_grade(entry, publisher.pk, entry.grade.grade, True)

    Comment.objects.filter(entry__node__journal=journal).exclude(entry__grade=None).update(published=True)
