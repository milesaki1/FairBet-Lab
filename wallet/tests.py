from decimal import Decimal
import uuid
from django.contrib.auth.models import User
from django.test import TestCase

from config.choices import TipoCuenta, Direccion
from wallet.models import LedgerEntry
from wallet import services


def crear_usuario(username="jugador1", password="Pass1234!"):
    user = User.objects.create_user(username=username, password=password)
    # Crear perfil asociado con valores por defecto
    from accounts.models import PerfilUsuario
    from datetime import date

    PerfilUsuario.objects.create(
        user=user,
        fecha_nacimiento=date(1990, 1, 1),
        dni="12345678",
    )
    return user


class LedgerEntryModelTest(TestCase):
    """Pruebas del modelo LedgerEntry y de la función get_balance usando inserciones directas."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")

    def test_model_fields_and_get_balance(self):
        # El saldo inicial debe ser cero
        self.assertEqual(
            LedgerEntry.get_balance(self.user, TipoCuenta.WALLET_USUARIO),
            Decimal("0.0000"),
        )

        tid = uuid.uuid4()
        # Agregar crédito manual
        LedgerEntry.objects.create(
            id_transaccion=tid,
            usuario=self.user,
            cuenta=TipoCuenta.WALLET_USUARIO,
            monto=Decimal("150.0000"),
            direccion=Direccion.CREDIT,
        )
        self.assertEqual(
            LedgerEntry.get_balance(self.user, TipoCuenta.WALLET_USUARIO),
            Decimal("150.0000"),
        )

        # Agregar débito manual
        LedgerEntry.objects.create(
            id_transaccion=tid,
            usuario=self.user,
            cuenta=TipoCuenta.WALLET_USUARIO,
            monto=Decimal("50.0000"),
            direccion=Direccion.DEBIT,
        )
        self.assertEqual(
            LedgerEntry.get_balance(self.user, TipoCuenta.WALLET_USUARIO),
            Decimal("100.0000"),
        )


class InvariantePartidaDobleTest(TestCase):
    """La suma de todas las entradas de una transacción siempre es cero."""

    def setUp(self):
        self.user = crear_usuario()

    def assertBalanceCero(self, tid):
        entradas = LedgerEntry.objects.filter(id_transaccion=tid)
        self.assertEqual(entradas.count(), 2)
        self.assertEqual(
            sum(e.monto if e.direccion == "CREDIT" else -e.monto for e in entradas),
            Decimal("0.0000"),
        )

    def test_recarga_crea_asientos_balanceados(self):
        self.assertBalanceCero(services.recargar(self.user, Decimal("100.00")))

    def test_retiro_crea_asientos_balanceados(self):
        services.recargar(self.user, Decimal("200.00"))
        self.assertBalanceCero(services.retirar(self.user, Decimal("50.00")))

    def test_transferencia_crea_asientos_balanceados(self):
        services.recargar(self.user, Decimal("500.00"))
        self.assertBalanceCero(
            services.transferencia_interna(
                self.user,
                TipoCuenta.WALLET_USUARIO,
                TipoCuenta.APUESTAS_PENDIENTES,
                Decimal("100.00"),
            )
        )


class SaldoCalculadoTest(TestCase):
    """El saldo se calcula dinámicamente, nunca se guarda."""

    def setUp(self):
        self.user = crear_usuario(username="jugador2")

    def test_saldo_inicial_es_cero(self):
        saldo = LedgerEntry.get_balance(self.user, TipoCuenta.WALLET_USUARIO)
        self.assertEqual(saldo, Decimal("0.0000"))

    def test_recarga_incrementa_saldo(self):
        services.recargar(self.user, Decimal("250.00"))
        saldo = LedgerEntry.get_balance(self.user, TipoCuenta.WALLET_USUARIO)
        self.assertEqual(saldo, Decimal("250.0000"))

    def test_multiples_recargas_acumulan_saldo(self):
        services.recargar(self.user, Decimal("100.00"))
        services.recargar(self.user, Decimal("200.00"))
        saldo = LedgerEntry.get_balance(self.user, TipoCuenta.WALLET_USUARIO)
        self.assertEqual(saldo, Decimal("300.0000"))

    def test_retiro_reduce_saldo(self):
        services.recargar(self.user, Decimal("300.00"))
        services.retirar(self.user, Decimal("100.00"))
        saldo = LedgerEntry.get_balance(self.user, TipoCuenta.WALLET_USUARIO)
        self.assertEqual(saldo, Decimal("200.0000"))

    def test_transferencia_interna_mueve_saldo_entre_cuentas(self):
        services.recargar(self.user, Decimal("500.00"))
        services.transferencia_interna(
            self.user,
            TipoCuenta.WALLET_USUARIO,
            TipoCuenta.APUESTAS_PENDIENTES,
            Decimal("150.00"),
        )
        self.assertEqual(
            LedgerEntry.get_balance(self.user, TipoCuenta.WALLET_USUARIO),
            Decimal("350.0000"),
        )
        self.assertEqual(
            LedgerEntry.get_balance(self.user, TipoCuenta.APUESTAS_PENDIENTES),
            Decimal("150.0000"),
        )
