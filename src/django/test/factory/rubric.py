import test.factory

import factory

import VLE.models


class RubricFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Rubric'

    class Params:
        full = factory.Trait(
            criterion_1=factory.RelatedFactory(
                'test.factory.rubric.CriterionFactory', factory_related_name='rubric', add_levels=2),
            criterion_2=factory.RelatedFactory(
                'test.factory.rubric.CriterionFactory', factory_related_name='rubric', add_levels=1),
            criterion_3=factory.RelatedFactory('test.factory.rubric.CriterionFactory', factory_related_name='rubric'),
        )

    assignment = factory.SubFactory('test.factory.assignment.AssignmentFactory')
    name = factory.Sequence(lambda x: f'Rubric {x + 1}')
    description = 'Rubric description'
    visibility = VLE.models.Rubric.VISIBLE
    hide_score_from_students = False


class CriterionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Criterion'

    rubric = factory.SubFactory('test.factory.rubric.RubricFactory')
    name = factory.Sequence(lambda x: f'Criterion {x + 1}')
    description = 'Brief criterion description'
    long_description = factory.Faker('paragraphs')
    score_as_range = False
    location = factory.Sequence(lambda x: x)

    @factory.post_generation
    def add_levels(self, create, extracted, **kwargs):
        if not create:
            return

        if isinstance(extracted, list):
            for kwargs in extracted:
                test.factory.Level(**{**kwargs, 'criterion': self})
        elif isinstance(extracted, int):
            for _ in range(extracted):
                test.factory.Level(**{**kwargs, 'criterion': self})


class LevelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Level'

    criterion = factory.SubFactory('test.factory.rubric.Criterion')
    points = 3
    initial_feedback = 'Initial feedback snippet'
    location = factory.Sequence(lambda x: x)
