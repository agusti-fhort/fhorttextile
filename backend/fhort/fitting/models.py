from django.db import models


class SizeFitting(models.Model):
    TIPUS_CHOICES = [
        ('Proto', 'Proto'),
        ('Fit', 'Fit'),
        ('SizeSet', 'SizeSet'),
        ('PP', 'PP'),
        ('TOP', 'TOP'),
    ]
    ESTAT_CHOICES = [
        ('Pendent', 'Pendent'),
        ('BaseOberta', 'Base oberta'),
        ('BaseTancada', 'Base tancada'),
        ('TallesGenerades', 'Talles generades'),
        ('Tancat', 'Tancat'),
    ]

    model = models.ForeignKey('models_app.Model', on_delete=models.CASCADE, related_name='size_fittings')
    numero = models.PositiveIntegerField()
    codi = models.CharField(max_length=60, unique=True)
    tipus = models.CharField(max_length=20, choices=TIPUS_CHOICES)
    sf_pare = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fills',
    )

    estat = models.CharField(max_length=30, choices=ESTAT_CHOICES, default='Pendent')

    data_creacio = models.DateTimeField(auto_now_add=True)
    data_tancament = models.DateTimeField(null=True, blank=True)
    creat_per = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.PROTECT,
        related_name='size_fittings_creats',
    )

    notes = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = 'Size & Fitting'
        verbose_name_plural = 'Size & Fittings'
        ordering = ['model', 'numero']
        unique_together = [('model', 'numero')]

    def __str__(self):
        return self.codi


class GradingVersion(models.Model):
    size_fitting = models.ForeignKey(SizeFitting, on_delete=models.CASCADE, related_name='grading_versions')
    nom = models.CharField(max_length=100)
    aprovada = models.BooleanField(default=False)
    data = models.DateTimeField(auto_now_add=True)
    creat_per = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.PROTECT,
        related_name='grading_versions_creades',
    )
    notes = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = 'Versió de grading'
        verbose_name_plural = 'Versions de grading'
        ordering = ['size_fitting', '-data']

    def __str__(self):
        return f'{self.size_fitting.codi} · {self.nom}'


class GradedSpecLine(models.Model):
    ESTAT_CHOICES = [('ok', 'OK'), ('avis', 'Avís'), ('error', 'Error')]

    grading_version = models.ForeignKey(GradingVersion, on_delete=models.CASCADE, related_name='linies')
    pom = models.ForeignKey('pom.POMMaster', on_delete=models.PROTECT, related_name='+')
    talla = models.ForeignKey('pom.SizeDefinition', on_delete=models.PROTECT, related_name='+')

    valor_target = models.DecimalField(max_digits=10, decimal_places=4)
    valor_pare = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    delta = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    motiu_delta = models.CharField(max_length=200, null=True, blank=True)

    estat = models.CharField(max_length=10, choices=ESTAT_CHOICES, default='ok')
    avis_text = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        verbose_name = 'Línia spec gradada'
        verbose_name_plural = 'Línies spec gradades'
        unique_together = [('grading_version', 'pom', 'talla')]

    def __str__(self):
        return f'{self.grading_version} · {self.pom.codi_client} · {self.talla.etiqueta}'


class Fitting(models.Model):
    TIPUS_CHOICES = [
        ('Proto', 'Proto'),
        ('Sample', 'Sample'),
        ('PPS', 'PPS'),
    ]
    ESTAT_CHOICES = [
        ('Pendent', 'Pendent'),
        ('Aprovat', 'Aprovat'),
        ('AmbCorreccions', 'Amb correccions'),
        ('Rebutjat', 'Rebutjat'),
    ]

    size_fitting = models.ForeignKey(SizeFitting, on_delete=models.CASCADE, related_name='fittings')
    numero = models.PositiveIntegerField()
    tipus = models.CharField(max_length=20, choices=TIPUS_CHOICES)
    data_fitting = models.DateField()
    lloc = models.CharField(max_length=200, null=True, blank=True)
    responsable = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.PROTECT,
        related_name='fittings_responsable',
    )
    estat = models.CharField(max_length=20, choices=ESTAT_CHOICES, default='Pendent')
    notes = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = 'Fitting'
        verbose_name_plural = 'Fittings'
        ordering = ['size_fitting', 'numero']
        unique_together = [('size_fitting', 'numero')]

    def __str__(self):
        return f'{self.size_fitting.codi} · #{self.numero} ({self.tipus})'


class FittingLine(models.Model):
    ESTAT_CHOICES = [('ok', 'OK'), ('avis', 'Avís'), ('error', 'Error')]

    fitting = models.ForeignKey(Fitting, on_delete=models.CASCADE, related_name='linies')
    pom = models.ForeignKey('pom.POMMaster', on_delete=models.PROTECT, related_name='+')
    talla = models.ForeignKey('pom.SizeDefinition', on_delete=models.PROTECT, related_name='+')

    valor_target = models.DecimalField(max_digits=10, decimal_places=4)
    valor_mesurat = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    delta_real = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    estat = models.CharField(max_length=10, choices=ESTAT_CHOICES, default='ok')
    nota = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        verbose_name = 'Línia de fitting'
        verbose_name_plural = 'Línies de fitting'
        unique_together = [('fitting', 'pom', 'talla')]

    def __str__(self):
        return f'{self.fitting} · {self.pom.codi_client} · {self.talla.etiqueta}'


class FitComment(models.Model):
    ESTAT_CHOICES = [
        ('Pendent', 'Pendent'),
        ('Aplicat', 'Aplicat'),
        ('Rebutjat', 'Rebutjat'),
    ]

    fitting = models.ForeignKey(Fitting, on_delete=models.CASCADE, related_name='comentaris')
    tipus = models.CharField(max_length=40)
    descripcio = models.TextField()
    estat = models.CharField(max_length=20, choices=ESTAT_CHOICES, default='Pendent')
    resolt_en = models.ForeignKey(
        GradingVersion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='comentaris_resolts',
    )

    class Meta:
        verbose_name = 'Comentari de fitting'
        verbose_name_plural = 'Comentaris de fitting'

    def __str__(self):
        return f'{self.fitting} · {self.tipus}'


class FitCommentFitxer(models.Model):
    fit_comment = models.ForeignKey(FitComment, on_delete=models.CASCADE, related_name='fitxers')
    path_servidor = models.CharField(max_length=500)
    nom_fitxer = models.CharField(max_length=255)
    data_pujada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Fitxer de comentari'
        verbose_name_plural = 'Fitxers de comentari'

    def __str__(self):
        return self.nom_fitxer


class POMAlert(models.Model):
    TIPUS_CHOICES = [
        ('desviacio', 'Desviació'),
        ('fora_rang', 'Fora de rang'),
        ('manca', 'Manca'),
        ('conflicte', 'Conflicte'),
    ]
    ESTAT_CHOICES = [
        ('Pendent', 'Pendent'),
        ('Acceptat', 'Acceptat'),
        ('Corregit', 'Corregit'),
    ]

    model = models.ForeignKey('models_app.Model', on_delete=models.CASCADE, related_name='pom_alerts')
    size_fitting = models.ForeignKey(
        SizeFitting,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pom_alerts',
    )
    pom = models.ForeignKey('pom.POMMaster', on_delete=models.PROTECT, related_name='alerts')
    tipus = models.CharField(max_length=20, choices=TIPUS_CHOICES)
    valor_detectat = models.DecimalField(max_digits=10, decimal_places=4)
    valor_esperat = models.DecimalField(max_digits=10, decimal_places=4)
    z_score = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    estat = models.CharField(max_length=20, choices=ESTAT_CHOICES, default='Pendent')
    creat_per = models.CharField(max_length=100, default='sistema')
    data_creacio = models.DateTimeField(auto_now_add=True)
    resolt_per = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pom_alerts_resoltes',
    )
    data_resolucio = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Alerta POM'
        verbose_name_plural = 'Alertes POM'

    def __str__(self):
        return f'{self.model.codi_intern} · {self.pom.codi_client} ({self.tipus})'
