import test.factory as factory

from django.test import TestCase

from VLE.models import Field
from VLE.utils.error_handling import VLEProgrammingError


class FormatAPITest(TestCase):
    def test_format_factory(self):
        self.assertRaises(VLEProgrammingError, factory.Format)
        assignment = factory.Assignment(format__templates=[])

        template = factory.TemplateAllTypes(format=assignment.format)
        assert template.format.pk == assignment.format.pk and assignment.format.template_set.count() == 1 \
            and assignment.format.template_set.get(pk=template.pk), \
            'A format can be generated via an assignment, and its templates can be set'

        assignment = factory.Assignment(format__templates=[{'type': Field.URL}])
        assert assignment.format.template_set.count() == 1, 'One template is created'
        field = Field.objects.get(template=assignment.format.template_set.first())
        assert field.type == Field.URL, 'And the template consists only out of the specified field'

        assignment = factory.Assignment(
            format__templates=[{'type': Field.URL, 'location': 1}, {'type': Field.TEXT, 'location': 0}])
        assert assignment.format.template_set.count() == 1, 'One template is created'
        # For the template two fields are generated
        field = Field.objects.get(template=assignment.format.template_set.first(), location=0)
        field = Field.objects.get(template=assignment.format.template_set.first(), location=1)
