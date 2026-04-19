import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0006_noninvestmentaccount_recurringcontribution_goal'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PortfolioSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('total_value', models.DecimalField(decimal_places=2, max_digits=16)),
                ('account_snapshots', models.JSONField(
                    default=list,
                    help_text='List of {account_id, account_name, value} dicts.',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='snapshots',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ('date',),
                'unique_together': {('user', 'date')},
            },
        ),
    ]
