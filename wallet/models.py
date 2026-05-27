import uuid
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Case, DecimalField, Sum, When

from config.choices import Direccion, TipoCuenta


class LedgerEntry(models.Model):
    id_transaccion = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        db_index=True,
        verbose_name="ID de Transacción",
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="asientos_contables",
        verbose_name="Usuario",
    )
    cuenta = models.CharField(
        max_length=30,
        choices=TipoCuenta.choices,
        verbose_name="Cuenta",
    )
    monto = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        verbose_name="Monto",
    )
    direccion = models.CharField(
        max_length=6,
        choices=Direccion.choices,
        verbose_name="Dirección",
    )
    creado = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Creación",
    )

    class Meta:
        ordering = ["-creado"]
        verbose_name = "Asiento Contable"
        verbose_name_plural = "Asientos Contables"

    def __str__(self):
        usuario = self.usuario.username if self.usuario else "casa"
        return f"{self.direccion} {self.monto} [{self.cuenta}] — {usuario}"

    @classmethod
    def get_balance(cls, usuario, cuenta):
        """
        Calcula el saldo de una cuenta específica para un usuario.
        Saldo = SUM(CREDITs) - SUM(DEBITs)
        Nunca se guarda; siempre se recalcula.
        """
        resultado = cls.objects.filter(usuario=usuario, cuenta=cuenta).aggregate(
            total=Sum(
                Case(
                    When(direccion=Direccion.CREDIT, then="monto"),
                    When(
                        direccion=Direccion.DEBIT,
                        then=models.Value(Decimal("0")) - models.F("monto"),
                    ),
                    output_field=DecimalField(max_digits=18, decimal_places=4),
                )
            )
        )
        return resultado["total"] or Decimal("0.0000")
