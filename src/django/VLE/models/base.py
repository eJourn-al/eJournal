from django.db import models


class CreateUpdateModel(models.Model):
    creation_date = models.DateTimeField(auto_now_add=True, editable=False)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
