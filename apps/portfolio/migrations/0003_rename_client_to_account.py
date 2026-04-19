"""Rename Client model to Account, update fields and FKs."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portfolio", "0002_alter_client_options_alter_transaction_options"),
    ]

    operations = [
        # 1. Rename the model
        migrations.RenameModel(
            old_name="Client",
            new_name="Account",
        ),
        # 2. Rename FK fields on Holding and Transaction
        migrations.RenameField(
            model_name="holding",
            old_name="client",
            new_name="account",
        ),
        migrations.RenameField(
            model_name="transaction",
            old_name="client",
            new_name="account",
        ),
        # 3. Remove old Client fields
        migrations.RemoveField(
            model_name="account",
            name="first_name",
        ),
        migrations.RemoveField(
            model_name="account",
            name="last_name",
        ),
        migrations.RemoveField(
            model_name="account",
            name="email",
        ),
        migrations.RemoveField(
            model_name="account",
            name="phone",
        ),
        # 4. Add new Account fields
        migrations.AddField(
            model_name="account",
            name="account_name",
            field=models.CharField(default="Unnamed Account", max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="account",
            name="account_type",
            field=models.CharField(
                choices=[
                    ("isa", "ISA"),
                    ("sipp", "SIPP"),
                    ("gia", "GIA"),
                    ("brokerage", "Brokerage"),
                    ("savings", "Savings"),
                    ("other", "Other"),
                ],
                default="other",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="account",
            name="provider",
            field=models.CharField(blank=True, max_length=100),
        ),
        # 5. Update ordering and unique_together
        migrations.AlterModelOptions(
            name="account",
            options={"ordering": ("account_name",)},
        ),
        migrations.AlterUniqueTogether(
            name="holding",
            unique_together={("account", "asset")},
        ),
        # 6. Update owner FK related_name
        migrations.AlterField(
            model_name="account",
            name="owner",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="accounts",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
