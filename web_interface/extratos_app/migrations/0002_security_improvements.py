# Generated migration for security improvements

from django.db import migrations, models
import extratos_app.models


class Migration(migrations.Migration):

    dependencies = [
        ('extratos_app', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='processamentoextrato',
            name='cpf_usuario_encrypted',
            field=models.TextField(blank=True, null=True, verbose_name='CPF Criptografado'),
        ),
        migrations.AddField(
            model_name='processamentoextrato',
            name='cpf_hash',
            field=models.CharField(blank=True, db_index=True, max_length=32, null=True, verbose_name='Hash CPF'),
        ),
        migrations.AddField(
            model_name='processamentoextrato',
            name='ip_address',
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='processamentoextrato',
            name='user_agent',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='processamentoextrato',
            name='arquivo_c6',
            field=models.FileField(blank=True, null=True, upload_to=extratos_app.models.upload_to_secure_path),
        ),
        migrations.AlterField(
            model_name='processamentoextrato',
            name='arquivo_bradesco',
            field=models.FileField(blank=True, null=True, upload_to=extratos_app.models.upload_to_secure_path),
        ),
        migrations.AlterField(
            model_name='processamentoextrato',
            name='arquivo_config',
            field=models.FileField(blank=True, null=True, upload_to=extratos_app.models.upload_config_secure_path, verbose_name='Arquivo de Configuração (opcional)'),
        ),
        migrations.AlterField(
            model_name='processamentoextrato',
            name='arquivo_resultado',
            field=models.FileField(blank=True, null=True, upload_to=extratos_app.models.upload_result_secure_path),
        ),
        migrations.AlterField(
            model_name='arquivoextrato',
            name='arquivo',
            field=models.FileField(upload_to=extratos_app.models.upload_to_secure_path),
        ),
    ]
