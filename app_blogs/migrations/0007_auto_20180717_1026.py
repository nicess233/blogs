# Generated by Django 2.0.4 on 2018-07-17 10:26

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app_blogs', '0006_auto_20180716_0857'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='article2tag',
            unique_together=set(),
        ),
    ]