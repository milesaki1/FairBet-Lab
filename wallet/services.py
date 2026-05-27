import uuid
from decimal import Decimal
from django.db import transaction
from config.choices import Direccion, TipoCuenta
from wallet.models import LedgerEntry


def registrar_movimiento(
    tid, usuario_debito, cuenta_debito, usuario_credito, cuenta_credito, monto
):
    LedgerEntry.objects.create(
        id_transaccion=tid,
        usuario=usuario_debito,
        cuenta=cuenta_debito,
        monto=monto,
        direccion=Direccion.DEBIT,
    )
    LedgerEntry.objects.create(
        id_transaccion=tid,
        usuario=usuario_credito,
        cuenta=cuenta_credito,
        monto=monto,
        direccion=Direccion.CREDIT,
    )


@transaction.atomic
def recargar(user, amount):
    monto = Decimal(str(amount))
    tid = uuid.uuid4()
    registrar_movimiento(
        tid=tid,
        usuario_debito=None,
        cuenta_debito=TipoCuenta.CASA,
        usuario_credito=user,
        cuenta_credito=TipoCuenta.WALLET_USUARIO,
        monto=monto,
    )
    return tid


@transaction.atomic
def retirar(user, amount):
    monto = Decimal(str(amount))

    # Bloqueo pesimista
    LedgerEntry.objects.select_for_update().filter(
        usuario=user, cuenta=TipoCuenta.WALLET_USUARIO
    )

    tid = uuid.uuid4()
    registrar_movimiento(
        tid=tid,
        usuario_debito=user,
        cuenta_debito=TipoCuenta.WALLET_USUARIO,
        usuario_credito=None,
        cuenta_credito=TipoCuenta.CASA,
        monto=monto,
    )
    return tid


@transaction.atomic
def transferencia_interna(user, cuenta_origen, cuenta_destino, amount):
    monto = Decimal(str(amount))
    tid = uuid.uuid4()
    registrar_movimiento(
        tid=tid,
        usuario_debito=user,
        cuenta_debito=cuenta_origen,
        usuario_credito=user,
        cuenta_credito=cuenta_destino,
        monto=monto,
    )
    return tid
