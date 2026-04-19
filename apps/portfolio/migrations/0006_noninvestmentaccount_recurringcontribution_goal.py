# Generated manually for items 13, 14, 15 (Net Worth, Recurring Contributions, Goals)

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0005_asset_currency_exchangerate_watchlistitem'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='NonInvestmentAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('account_type', models.CharField(
                    choices=[('savings', 'Savings'), ('property', 'Property'), ('debt', 'Debt'), ('other', 'Other')],
                    default='other',
                    max_length=20,
                )),
                ('balance', models.DecimalField(decimal_places=2, max_digits=14)),
                ('currency', models.CharField(default='GBP', max_length=3)),
                ('notes', models.TextField(blank=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='non_investment_accounts',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ('name',)},
        ),
        migrations.CreateModel(
            name='RecurringContribution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('frequency', models.CharField(
                    choices=[('monthly', 'Monthly'), ('quarterly', 'Quarterly'), ('annually', 'Annually')],
                    default='monthly',
                    max_length=20,
                )),
                ('start_date', models.DateField()),
                ('next_due_date', models.DateField()),
                ('notes', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='recurring_contributions',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('account', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='recurring_contributions',
                    to='portfolio.account',
                )),
            ],
            options={'ordering': ('next_due_date',)},
        ),
        migrations.CreateModel(
            name='Goal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('target_amount', models.DecimalField(decimal_places=2, max_digits=14)),
                ('target_date', models.DateField()),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='goals',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('account', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='goals',
                    to='portfolio.account',
                )),
            ],
            options={'ordering': ('target_date',)},
        ),
    ]
