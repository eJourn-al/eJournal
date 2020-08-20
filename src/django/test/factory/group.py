import factory


class GroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Group'

    name = factory.Sequence(lambda x: 'A' + str(x))
    lti_id = factory.Sequence(lambda x: 'LTI' + str(x))
    course = factory.SubFactory('test.factory.course.CourseFactory')
