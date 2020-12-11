import factory

import VLE.models


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Category'

    name = factory.Faker('word')
    description = ''
    assignment = factory.SubFactory('test.factory.assignment.AssignmentFactory')

    @factory.post_generation
    def templates(self, create, extracted, **kwargs):
        if not create or extracted is False:
            return

        if isinstance(extracted, list):
            self.templates.set(extracted)
        else:
            template = VLE.models.Template.objects.filter(format__assignment=self.assignment).order_by('?').first()
            if template:
                self.templates.add(template)
