from django.db import models
from django.contrib.auth.models import User


TAMIL_NADU_DISTRICTS = [
    ('Chennai', 'Chennai'),
    ('Coimbatore', 'Coimbatore'),
    ('Madurai', 'Madurai'),
    ('Tiruchirappalli', 'Tiruchirappalli'),
    ('Salem', 'Salem'),
    ('Erode', 'Erode'),
    ('Tirunelveli', 'Tirunelveli'),
    ('Vellore', 'Vellore'),
    ('Thoothukudi', 'Thoothukudi'),
    ('Dindigul', 'Dindigul'),
    ('Thanjavur', 'Thanjavur'),
    ('Kanyakumari', 'Kanyakumari'),
    ('Namakkal', 'Namakkal'),
    ('Karur', 'Karur'),
    ('Krishnagiri', 'Krishnagiri'),
    ('Villupuram', 'Villupuram'),
    ('Cuddalore', 'Cuddalore'),
    ('Ramanathapuram', 'Ramanathapuram'),
    ('Sivagangai', 'Sivagangai'),
    ('Nagapattinam', 'Nagapattinam'),
    ('Perambalur', 'Perambalur'),
    ('Ariyalur', 'Ariyalur'),
    ('Tiruvarur', 'Tiruvarur'),
    ('Tirupur', 'Tirupur'),
]


class Public_user(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        related_name="public_user_profile"
    )

    name = models.CharField(max_length=150)
    occupation = models.CharField(max_length=150, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    age = models.PositiveIntegerField(blank=True, null=True)
    phone = models.CharField(max_length=15, unique=True)
    address = models.TextField(blank=True, null=True)

    district = models.CharField(
        max_length=100,
        choices=TAMIL_NADU_DISTRICTS,
        blank=True,
        null=True
    )

    def __str__(self):
        return self.name
