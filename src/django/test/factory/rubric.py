import test.factory

import factory

import VLE.models


class RubricFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Rubric'

    class Params:
        full = factory.Trait(
            criterion_1=factory.RelatedFactory(
                'test.factory.rubric.CriterionFactory', factory_related_name='rubric', add_levels=3),
            criterion_2=factory.RelatedFactory('test.factory.rubric.CriterionFactory', factory_related_name='rubric'),
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
    description = factory.Faker('paragraph')
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
        else:
            test.factory.Level(
                criterion=self,
                name='Full marks',
                points=5,
                location=0,
            )
            test.factory.Level(
                criterion=self,
                name='No marks',
                points=0,
                location=1,
            )


class LevelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Level'

    criterion = factory.SubFactory('test.factory.rubric.Criterion')
    name = factory.Sequence(lambda x: f'Level {x + 1}')
    description = factory.Faker('paragraph')
    points = 5
    initial_feedback = 'Initial feedback snippet'
    location = factory.Sequence(lambda x: x)


class RubricCreationParamsFactory(factory.Factory):
    class Meta:
        model = dict

    name = factory.Sequence(lambda x: f'Rubric {x + 1}')
    description = 'Rubric description'
    visibility = VLE.models.Rubric.VISIBLE
    hide_score_from_students = False

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        assert kwargs['assignment_id'], 'assignment_id is a required parameter key for rubric creation'

        n_criteria = kwargs.pop('n_criteria', 2)

        kwargs['criteria'] = []
        for i in range(n_criteria):
            levels = [
                {
                    'criterion': -1 - i,
                    'name': 'Pass',
                    'description': '',
                    'points': 10,
                    'initial_feedback': '',
                    'location': 0,
                },
                {
                    'criterion': -1 - i,
                    'name': 'Fail',
                    'description': '',
                    'points': 0,
                    'initial_feedback': '',
                    'location': 1,
                },
            ]

            kwargs['criteria'].append({
                'rubric': -1,
                'name': f'Criterion {i + 1}',
                'description': '',
                'location': i,
                'levels': levels,
            })

        return kwargs
